"""
Per-player state filtering.

Strips hidden information from GameState before sending to a specific player.
Each player should only see their own secret data (traitor cards, treachery
hand, dealt traitor choices) — not other players'.
"""

from __future__ import annotations

from typing import Any


def filter_state_for_player(state_dict: dict[str, Any], player_id: str) -> dict[str, Any]:
    """
    Filter a serialised GameState dict so it only shows secrets belonging
    to the given player_id.

    Strips from other players:
      - traitor_cards
      - treachery_hand

    Strips globally:
      - treachery_deck (deck order is secret)
      - spice_deck (deck order is secret)

    Strips from setup_state:
      - Other players' dealt traitor hands
      - Other players' storm dial numbers (shows only whether they submitted)
      - atreides_prescience_cards for non-Atreides players

    Reveals (bidding):
      - The current card's full details to the Atreides player (prescience)
    """
    result = {**state_dict}

    # Determine the requesting player's faction
    my_faction: str | None = None
    for p in state_dict.get("players", []):
        if p.get("id") == player_id:
            my_faction = p.get("faction")
            break

    # ------------------------------------------------------------------
    # Atreides setup prescience: expose top 5 cards before stripping deck
    # ------------------------------------------------------------------
    setup = result.get("setup_state") or {}
    if (
        setup.get("sub_phase") == "atreides_prescience"
        and my_faction == "atreides"
    ):
        result["atreides_prescience_preview"] = list(result.get("treachery_deck", [])[:5])
    else:
        result["atreides_prescience_preview"] = []

    # ------------------------------------------------------------------
    # Strip deck order (show count only)
    # ------------------------------------------------------------------
    if "treachery_deck" in result:
        result["treachery_deck_count"] = len(result["treachery_deck"])
        result["treachery_deck"] = []
    if "spice_deck" in result:
        result["spice_deck_count"] = len(result["spice_deck"])
        result["spice_deck"] = []

    # ------------------------------------------------------------------
    # Filter player secrets
    # ------------------------------------------------------------------
    if "players" in result:
        filtered_players = []
        for p in result["players"]:
            if p.get("id") == player_id:
                filtered_players.append(p)
            else:
                filtered_p = {**p}
                filtered_p["traitor_cards"] = []
                filtered_p["treachery_hand"] = []
                filtered_p["treachery_hand_count"] = len(p.get("treachery_hand", []))
                filtered_players.append(filtered_p)
        result["players"] = filtered_players

    # ------------------------------------------------------------------
    # Filter setup state
    # ------------------------------------------------------------------
    if result.get("setup_state"):
        setup_f = {**result["setup_state"]}

        # Only show this player's dealt traitor hand
        if "traitor_hands_dealt" in setup_f:
            my_hand = setup_f["traitor_hands_dealt"].get(player_id, [])
            setup_f["traitor_hands_dealt"] = {player_id: my_hand}

        # Show whether others submitted storm dial, but not their number
        if "storm_dial_submissions" in setup_f:
            filtered_subs = {}
            for pid, num in setup_f["storm_dial_submissions"].items():
                if pid == player_id:
                    filtered_subs[pid] = num
                else:
                    filtered_subs[pid] = -1  # -1 = submitted but hidden
            setup_f["storm_dial_submissions"] = filtered_subs

        # Hide Atreides prescience card list from non-Atreides players
        if my_faction != "atreides":
            setup_f["atreides_prescience_cards"] = []

        result["setup_state"] = setup_f

    # ------------------------------------------------------------------
    # Filter bidding state
    # Atreides prescience: the card whose ID matches atreides_prescience_card_id
    # is revealed in full to the Atreides player. All other cards are hidden.
    # ------------------------------------------------------------------
    if result.get("bidding_state"):
        # We need the original (unfiltered) card data to reveal to Atreides
        original_bidding = state_dict.get("bidding_state", {})
        bidding = {**result["bidding_state"]}
        prescience_card_id = bidding.get("atreides_prescience_card_id")
        original_cards = original_bidding.get("cards_up_for_bid", [])

        if "cards_up_for_bid" in bidding:
            hidden_cards = []
            for orig_card in original_cards:
                if (
                    my_faction == "atreides"
                    and prescience_card_id
                    and orig_card.get("id") == prescience_card_id
                ):
                    # Reveal the full card to Atreides
                    hidden_cards.append(orig_card)
                else:
                    hidden_cards.append({
                        "id": orig_card.get("id", "unknown"),
                        "name": "Unknown",
                        "card_type": "unknown",
                        "weapon_type": None,
                        "defense_type": None,
                        "special_type": None,
                        "is_advanced": False,
                    })
            bidding["cards_up_for_bid"] = hidden_cards
        result["bidding_state"] = bidding

    # ------------------------------------------------------------------
    # Atreides movement prescience — only Atreides (+ ally in Advanced) see it
    # ------------------------------------------------------------------
    if "atreides_movement_prescience" in result:
        # Determine whether this player is allowed to see it
        atreides_ally: str | None = None
        for p in state_dict.get("players", []):
            if p.get("faction") == "atreides":
                atreides_ally = p.get("ally")
                break
        is_advanced = state_dict.get("mode", "") == "advanced"
        can_see_prescience = (
            my_faction == "atreides"
            or (is_advanced and my_faction == atreides_ally)
        )
        if not can_see_prescience:
            result["atreides_movement_prescience"] = None

    # ------------------------------------------------------------------
    # Filter active battle — hide opponent's plan until both are submitted;
    # hide prescience_revealed_value from non-Atreides parties;
    # hide voice_command details from factions not involved in the battle.
    # ------------------------------------------------------------------
    if result.get("active_battle"):
        battle = {**result["active_battle"]}

        # Battle plans: hide opponent's plan until both submitted
        both_submitted = (
            battle.get("attacker_plan") is not None
            and battle.get("defender_plan") is not None
        )
        if not both_submitted:
            if my_faction != battle.get("attacker_faction"):
                battle["attacker_plan"] = None
            if my_faction != battle.get("defender_faction"):
                battle["defender_plan"] = None

        # prescience_revealed_value: only visible to Atreides side (and their ally)
        if battle.get("prescience_revealed_value") is not None:
            atreides_faction_in_battle = battle.get("atreides_faction")
            atreides_ally_in_battle: str | None = None
            for p in state_dict.get("players", []):
                if p.get("faction") == atreides_faction_in_battle:
                    atreides_ally_in_battle = p.get("ally")
                    break
            is_adv = state_dict.get("mode", "") == "advanced"
            can_see_reveal = (
                my_faction == atreides_faction_in_battle
                or (is_adv and my_faction == atreides_ally_in_battle)
            )
            if not can_see_reveal:
                battle["prescience_revealed_value"] = None

        # voice_command: only visible to battle participants (issuer + target)
        if battle.get("voice_command") is not None:
            battle_factions = {battle.get("attacker_faction"), battle.get("defender_faction")}
            if my_faction not in battle_factions:
                battle["voice_command"] = None

        # Atreides Karama revealed plan: only visible to Atreides (+ ally in Advanced)
        if battle.get("atreides_karama_revealed_plan") is not None:
            atreides_ally_k: str | None = None
            for p in state_dict.get("players", []):
                if p.get("faction") == "atreides":
                    atreides_ally_k = p.get("ally")
                    break
            is_adv = state_dict.get("mode", "") == "advanced"
            can_see_karama = (
                my_faction == "atreides"
                or (is_adv and my_faction == atreides_ally_k)
            )
            if not can_see_karama:
                battle["atreides_karama_revealed_plan"] = None
                battle["atreides_karama_revealed_faction"] = None

        result["active_battle"] = battle

    return result
