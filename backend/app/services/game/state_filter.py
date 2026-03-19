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
    """
    result = {**state_dict}

    # Strip deck order (show count only)
    if "treachery_deck" in result:
        result["treachery_deck_count"] = len(result["treachery_deck"])
        result["treachery_deck"] = []
    if "spice_deck" in result:
        result["spice_deck_count"] = len(result["spice_deck"])
        result["spice_deck"] = []

    # Filter player secrets
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

    # Filter setup state
    if result.get("setup_state"):
        setup = {**result["setup_state"]}

        # Only show this player's dealt traitor hand
        if "traitor_hands_dealt" in setup:
            my_hand = setup["traitor_hands_dealt"].get(player_id, [])
            setup["traitor_hands_dealt"] = {player_id: my_hand}

        # Show whether others submitted storm dial, but not their number
        if "storm_dial_submissions" in setup:
            filtered_subs = {}
            for pid, num in setup["storm_dial_submissions"].items():
                if pid == player_id:
                    filtered_subs[pid] = num
                else:
                    filtered_subs[pid] = -1  # -1 = submitted but hidden
            setup["storm_dial_submissions"] = filtered_subs

        result["setup_state"] = setup

    # Filter bidding state — cards are auctioned face-down (unknown to bidders).
    # Replace card details with a placeholder so players can't see what they're
    # bidding on. (Future: Atreides prescience will let them peek.)
    if result.get("bidding_state"):
        bidding = {**result["bidding_state"]}
        if "cards_up_for_bid" in bidding:
            hidden_cards = []
            for card in bidding["cards_up_for_bid"]:
                hidden_cards.append({
                    "id": card.get("id", "unknown"),
                    "name": "Unknown",
                    "card_type": "unknown",
                    "weapon_type": None,
                    "defense_type": None,
                    "special_type": None,
                    "is_advanced": False,
                })
            bidding["cards_up_for_bid"] = hidden_cards
        result["bidding_state"] = bidding

    # Filter active battle — hide opponent's plan until both are submitted
    if result.get("active_battle"):
        battle = {**result["active_battle"]}
        my_faction = None
        for p in state_dict.get("players", []):
            if p.get("id") == player_id:
                my_faction = p.get("faction")
                break

        both_submitted = battle.get("attacker_plan") is not None and battle.get("defender_plan") is not None

        if not both_submitted:
            # Hide the opponent's plan
            if my_faction != battle.get("attacker_faction"):
                battle["attacker_plan"] = None
            if my_faction != battle.get("defender_faction"):
                battle["defender_plan"] = None

        result["active_battle"] = battle

    return result
