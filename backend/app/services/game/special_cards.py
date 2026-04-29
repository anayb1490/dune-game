"""
Special Treachery Card actions for the Dune board game.

Handles the six special card types that have out-of-battle effects:
  • Karama (basic)  — cancel any faction's special ability for one turn
  • Karama (Advanced power) — use your faction's unique Karama power
  • Tleilaxu Ghola  — revive one dead leader OR up to 5 forces for free
  • Family Atomics  — permanently destroy the Shield Wall
  • Hajr            — grant your faction one extra force-move this turn
  • Weather Control — set the next storm movement to an exact sector count

Weapon/defense cards (poison, projectile, lasgun, snooper, shield) and
Worthless cards are handled at battle-plan submission time in combat.py.
"""

from __future__ import annotations

import math
from typing import Optional

from ...models.card import SpecialCardType, TreacheryCard, TreacheryCardType
from ...models.faction import FactionName
from ...models.game_state import GameState
from ...models.leader import LeaderStatus
from ...models.player import ForceGroup, Player

# ---------------------------------------------------------------------------
# Shield Wall territory
# ---------------------------------------------------------------------------
_SHIELD_WALL = "Shield Wall"

# Advanced Karama powers by faction
_KARAMA_POWER_DESCRIPTIONS: dict[FactionName, str] = {
    FactionName.ATREIDES:      "Look at any one player's complete Battle Plan",
    FactionName.EMPEROR:       "Revive up to 3 forces or 1 leader for free",
    FactionName.FREMEN:        "Place the sandworm token in any sand territory",
    FactionName.SPACING_GUILD: "Stop one off-planet shipment of any one player",
    FactionName.HARKONNEN:     "Take cards from any one player (exchange 1-for-1)",
    FactionName.BENE_GESSERIT: "BG may use any Worthless card as Karama (no unique power)",
}


# ===========================================================================
# Karama — Basic: cancel a faction's special ability
# ===========================================================================

def play_karama_block(
    game_state: GameState,
    player_id: str,
    target_faction: FactionName,
) -> GameState:
    """
    Basic Karama use: prevent ``target_faction`` from using any one of their
    faction-specific advantages this turn.

    The block is stored on GameState for the current turn.  Individual ability
    functions (bg_free_ship, guild_cross_ship, etc.) check this flag before
    executing; callers should check ``is_karama_blocked(game_state, faction)``
    before performing the blocked action.

    Rules:
      - Player must hold a Karama card (or a Worthless card if BG in Advanced).
      - Cannot block your own faction.
      - The card is discarded after use.
    """
    player = _get_player(game_state, player_id)

    if player.faction == target_faction:
        raise ValueError("Cannot Karama your own faction.")

    karama = _find_usable_karama(player, game_state)
    if karama is None:
        raise ValueError("No Karama card (or eligible Worthless card) in hand.")

    game_state = _discard_from_hand(game_state, player_id, karama.id)
    return game_state.model_copy(update={
        "karama_blocked_faction": target_faction,
        "karama_blocked_turn": game_state.current_turn,
    })


def is_karama_blocked(game_state: GameState, faction: FactionName) -> bool:
    """Return True if ``faction`` is currently blocked by a Karama card."""
    return (
        game_state.karama_blocked_faction == faction
        and game_state.karama_blocked_turn == game_state.current_turn
    )


# ===========================================================================
# Karama — Advanced faction power
# ===========================================================================

def play_karama_faction_power(
    game_state: GameState,
    player_id: str,
    payload: dict,
) -> GameState:
    """
    Advanced Karama use: activate the player's faction-specific Karama power.

    Dispatches to the appropriate faction handler.  ``payload`` carries any
    additional parameters the power needs (e.g. target_faction for Guild/Harkonnen,
    territory for Fremen, leader_id/force_count for Emperor).

    Rulebook — Advanced Karama powers:
      Atreides:      Look at any one player's entire Battle Plan.
      Emperor:       Revive up to 3 forces or 1 leader for free.
      Fremen:        Place sandworm token in any sand territory (no Nexus).
      Guild:         Stop one off-planet shipment of any one faction this turn.
      Harkonnen:     Take N cards from a player; give them N of your own.
      BG:            No unique power — they may use any Worthless card as Karama.
    """
    if game_state.mode.value != "advanced":
        raise ValueError("Karama faction powers are only available in Advanced mode.")

    player = _get_player(game_state, player_id)
    karama = _find_usable_karama(player, game_state)
    if karama is None:
        raise ValueError("No Karama card (or eligible Worthless card) in hand.")

    game_state = _discard_from_hand(game_state, player_id, karama.id)

    faction = player.faction

    if faction == FactionName.ATREIDES:
        return _karama_atreides(game_state, player_id, payload)

    if faction == FactionName.EMPEROR:
        return _karama_emperor(game_state, player_id, payload)

    if faction == FactionName.FREMEN:
        return _karama_fremen(game_state, player_id, payload)

    if faction == FactionName.SPACING_GUILD:
        return _karama_guild(game_state, player_id, payload)

    if faction == FactionName.HARKONNEN:
        return _karama_harkonnen(game_state, player_id, payload)

    if faction == FactionName.BENE_GESSERIT:
        # BG has no unique Karama power — the card was already discarded above.
        return game_state

    raise ValueError(f"Unknown faction: {faction}")


# ---------------------------------------------------------------------------
# Faction-specific Karama implementations
# ---------------------------------------------------------------------------

def _karama_atreides(game_state: GameState, player_id: str, payload: dict) -> GameState:
    """
    Atreides Karama: look at any one player's entire Battle Plan.

    Requires ``target_faction`` in payload.  The revealed plan is stored on
    ActiveBattle so the Atreides player can view it through the state filter.
    """
    ab = game_state.active_battle
    if ab is None:
        raise ValueError("Atreides Karama power can only be used during an active battle.")

    target_str = payload.get("target_faction", "")
    if not target_str:
        raise ValueError("target_faction is required for Atreides Karama power.")

    target = FactionName(target_str)

    # Reveal the target's plan (set a flag so the state filter exposes it)
    plan = None
    if ab.attacker_faction == target:
        plan = ab.attacker_plan
    elif ab.defender_faction == target:
        plan = ab.defender_plan

    if plan is None:
        raise ValueError(f"{target.value} has not yet submitted a battle plan.")

    # Store it as a special karama-revealed plan on ActiveBattle
    updated_ab = ab.model_copy(update={
        "atreides_karama_revealed_faction": target,
        "atreides_karama_revealed_plan": plan,
    })
    return game_state.model_copy(update={"active_battle": updated_ab})


def _karama_emperor(game_state: GameState, player_id: str, payload: dict) -> GameState:
    """
    Emperor Karama: revive up to 3 forces OR 1 leader for free.

    payload keys:
      leader_id   (str)  — revive this leader; mutually exclusive with force_count
      force_count (int)  — revive this many regular forces (1-3)
    """
    player = _get_player(game_state, player_id)

    leader_id = payload.get("leader_id")
    force_count = int(payload.get("force_count", 0))

    if leader_id and force_count:
        raise ValueError("Choose either leader OR forces, not both.")

    if leader_id:
        # Revive a single leader from tanks
        updated_leaders = []
        revived = False
        for ldr in player.leaders:
            if ldr.id == leader_id and ldr.status == LeaderStatus.IN_TANKS:
                updated_leaders.append(ldr.model_copy(update={"status": LeaderStatus.AVAILABLE}))
                revived = True
            else:
                updated_leaders.append(ldr)
        if not revived:
            raise ValueError(f"Leader {leader_id} is not in the Tleilaxu Tanks.")
        updated_player = player.model_copy(update={"leaders": updated_leaders})

    elif force_count:
        if force_count > 3:
            raise ValueError("Emperor Karama can revive at most 3 forces.")
        if player.forces_in_tanks < force_count:
            raise ValueError(
                f"Only {player.forces_in_tanks} forces in tanks (need {force_count})."
            )
        updated_player = player.model_copy(update={
            "forces_in_tanks": player.forces_in_tanks - force_count,
            "forces_in_reserve": player.forces_in_reserve + force_count,
        })

    else:
        raise ValueError("Specify leader_id or force_count for Emperor Karama.")

    return _replace_player(game_state, updated_player)


def _karama_fremen(game_state: GameState, player_id: str, payload: dict) -> GameState:
    """
    Fremen Karama: place sandworm token in any sand territory.

    Destroys non-Fremen forces and all spice in that territory, but does NOT
    trigger a Nexus event.  The Fremen may then use sandworm riding normally.

    payload keys:
      territory_name (str) — target territory (must be sand type)
    """
    from ...data.territories import TERRITORIES
    from ...models.territory import TerritoryType

    territory_name = payload.get("territory_name", "")
    if not territory_name:
        raise ValueError("territory_name is required for Fremen Karama power.")

    territory = game_state.territories.get(territory_name)
    if territory is None:
        raise ValueError(f"Territory not found: {territory_name}")

    static_terr = TERRITORIES.get(territory_name)
    if static_terr is None or static_terr.territory_type != TerritoryType.SAND:
        raise ValueError(f"{territory_name} is not a sand territory.")

    from .handlers.registry import get_handler

    # Destroy non-Fremen forces in the territory
    updated_players = []
    for p in game_state.players:
        if p.is_eliminated:
            updated_players.append(p)
            continue
        handler = get_handler(p.faction)
        if handler.is_immune_to_shai_hulud():
            updated_players.append(p)
            continue
        surviving = [fg for fg in p.forces_on_board if fg.territory_name != territory_name]
        killed_r = sum(fg.regular_count for fg in p.forces_on_board if fg.territory_name == territory_name)
        killed_s = sum(fg.special_count for fg in p.forces_on_board if fg.territory_name == territory_name)
        if killed_r or killed_s:
            updated_players.append(p.model_copy(update={
                "forces_on_board": surviving,
                "forces_in_tanks": p.forces_in_tanks + killed_r,
                "special_forces_in_tanks": p.special_forces_in_tanks + killed_s,
            }))
        else:
            updated_players.append(p)

    # Remove spice
    territories = {n: t.model_copy() for n, t in game_state.territories.items()}
    old_spice = territories[territory_name].current_spice if territory_name in territories else 0
    if territory_name in territories:
        territories[territory_name] = territories[territory_name].model_copy(
            update={"current_spice": 0}
        )

    return game_state.model_copy(update={
        "players": updated_players,
        "territories": territories,
        "spice_bank": game_state.spice_bank + old_spice,
        # Sandworm riding is available (non-Nexus)
        "fremen_sandworm_ride_territory": territory_name,
    })


def _karama_guild(game_state: GameState, player_id: str, payload: dict) -> GameState:
    """
    Guild Karama: stop one off-planet shipment of any one faction this turn.

    Stores the blocked faction on GameState; shipment.py checks before executing.

    payload keys:
      target_faction (str) — which faction's next shipment is cancelled
    """
    target_str = payload.get("target_faction", "")
    if not target_str:
        raise ValueError("target_faction is required for Guild Karama power.")

    target = FactionName(target_str)
    # Reuse the karama block mechanism — it already exists on GameState
    return game_state.model_copy(update={
        "karama_blocked_faction": target,
        "karama_blocked_turn": game_state.current_turn,
    })


def _karama_harkonnen(game_state: GameState, player_id: str, payload: dict) -> GameState:
    """
    Harkonnen Karama: take N cards from a target player; give them N cards back.

    payload keys:
      target_faction (str)        — faction to steal from
      take_card_ids  (list[str])  — IDs of cards to take from target
      give_card_ids  (list[str])  — IDs of Harkonnen cards to give in return
    """
    player = _get_player(game_state, player_id)
    target_str = payload.get("target_faction", "")
    take_ids: list[str] = payload.get("take_card_ids", [])
    give_ids: list[str] = payload.get("give_card_ids", [])

    if not target_str:
        raise ValueError("target_faction is required for Harkonnen Karama power.")
    if len(take_ids) != len(give_ids):
        raise ValueError("Must give exactly as many cards as you take (1-for-1 exchange).")
    if not take_ids:
        raise ValueError("Must take at least one card.")

    target = _get_player_by_faction(game_state, FactionName(target_str))

    # Validate take_ids exist in target's hand
    target_hand = {c.id: c for c in target.treachery_hand}
    for cid in take_ids:
        if cid not in target_hand:
            raise ValueError(f"Card {cid} not in {target.faction.value}'s hand.")

    # Validate give_ids exist in Harkonnen's hand
    player_hand = {c.id: c for c in player.treachery_hand}
    for cid in give_ids:
        if cid not in player_hand:
            raise ValueError(f"Card {cid} not in your hand.")

    # Perform the exchange
    taken = [target_hand[cid] for cid in take_ids]
    given = [player_hand[cid] for cid in give_ids]

    new_player_hand = [c for c in player.treachery_hand if c.id not in give_ids] + taken
    new_target_hand = [c for c in target.treachery_hand if c.id not in take_ids] + given

    updated_player = player.model_copy(update={"treachery_hand": new_player_hand})
    updated_target = target.model_copy(update={"treachery_hand": new_target_hand})

    players = [
        updated_player if p.id == player.id
        else updated_target if p.id == target.id
        else p
        for p in game_state.players
    ]
    return game_state.model_copy(update={"players": players})


# ===========================================================================
# Tleilaxu Ghola — revive one leader or up to 5 forces for free
# ===========================================================================

def play_tleilaxu_ghola(
    game_state: GameState,
    player_id: str,
    leader_id: Optional[str] = None,
    force_count: int = 0,
) -> GameState:
    """
    Play a Tleilaxu Ghola card to revive for free:
      - ONE leader from the Tleilaxu Tanks, OR
      - Up to FIVE regular forces from the Tleilaxu Tanks.

    The card must be in the player's treachery hand.
    The card is discarded after use.  No spice cost.
    """
    player = _get_player(game_state, player_id)
    ghola = _find_special_card(player, SpecialCardType.TLEILAXU_GHOLA)
    if ghola is None:
        raise ValueError("No Tleilaxu Ghola card in hand.")

    if leader_id and force_count > 0:
        raise ValueError("Choose either a leader OR forces, not both.")
    if not leader_id and force_count <= 0:
        raise ValueError("Specify leader_id or force_count > 0.")

    # Validate intent before discarding
    if leader_id:
        # Validate leader is in tanks
        found = next((l for l in player.leaders if l.id == leader_id), None)
        if found is None:
            raise ValueError(f"Leader {leader_id} not found.")
        if found.status != LeaderStatus.IN_TANKS:
            raise ValueError(f"Leader {found.name} is not in the Tleilaxu Tanks.")
    else:
        if force_count > 5:
            raise ValueError("Tleilaxu Ghola can revive at most 5 forces.")
        if player.forces_in_tanks < force_count:
            raise ValueError(
                f"Only {player.forces_in_tanks} forces in tanks "
                f"(need {force_count})."
            )

    # Discard first so updated player reflects the removed card
    game_state = _discard_from_hand(game_state, player_id, ghola.id)
    # Refresh player reference (card now removed from hand)
    player = _get_player(game_state, player_id)

    if leader_id:
        updated_leaders = [
            ldr.model_copy(update={"status": LeaderStatus.AVAILABLE})
            if ldr.id == leader_id else ldr
            for ldr in player.leaders
        ]
        updated_player = player.model_copy(update={"leaders": updated_leaders})
    else:
        updated_player = player.model_copy(update={
            "forces_in_tanks": player.forces_in_tanks - force_count,
            "forces_in_reserve": player.forces_in_reserve + force_count,
        })

    return _replace_player(game_state, updated_player)


# ===========================================================================
# Family Atomics — destroy the Shield Wall permanently
# ===========================================================================

def play_family_atomics(
    game_state: GameState,
    player_id: str,
) -> GameState:
    """
    Play Family Atomics (Advanced only).

    Effects per the rulebook:
      1. The Shield Wall is permanently destroyed (shield_wall_destroyed = True).
         Sectors 4-5 (previously blocked by the wall) are now exposed to storms.
      2. All non-Fremen forces in the Shield Wall territory are sent to the tanks.
      3. All spice in the Shield Wall territory is returned to the Spice Bank.

    The card is discarded.
    """
    if game_state.mode.value != "advanced":
        raise ValueError("Family Atomics is an Advanced-only card.")

    player = _get_player(game_state, player_id)
    atomics = _find_special_card(player, SpecialCardType.FAMILY_ATOMICS)
    if atomics is None:
        raise ValueError("No Family Atomics card in hand.")

    if game_state.shield_wall_destroyed:
        raise ValueError("The Shield Wall has already been destroyed.")

    # Discard card first; iterate post-discard players so card is gone from hand
    game_state = _discard_from_hand(game_state, player_id, atomics.id)

    from .handlers.registry import get_handler

    # Destroy forces in Shield Wall (non-Fremen only)
    updated_players = []
    for p in game_state.players:
        if p.is_eliminated:
            updated_players.append(p)
            continue
        handler = get_handler(p.faction)
        surviving = []
        killed_r = 0
        killed_s = 0
        for fg in p.forces_on_board:
            if fg.territory_name == _SHIELD_WALL:
                if handler.is_immune_to_shai_hulud():
                    # Fremen survive Family Atomics just as they survive sandworms
                    surviving.append(fg)
                else:
                    killed_r += fg.regular_count
                    killed_s += fg.special_count
            else:
                surviving.append(fg)
        if killed_r or killed_s:
            updated_players.append(p.model_copy(update={
                "forces_on_board": surviving,
                "forces_in_tanks": p.forces_in_tanks + killed_r,
                "special_forces_in_tanks": p.special_forces_in_tanks + killed_s,
            }))
        else:
            updated_players.append(p)

    # Return Shield Wall spice to bank
    territories = {n: t.model_copy() for n, t in game_state.territories.items()}
    shield_wall_spice = 0
    if _SHIELD_WALL in territories:
        shield_wall_spice = territories[_SHIELD_WALL].current_spice
        territories[_SHIELD_WALL] = territories[_SHIELD_WALL].model_copy(
            update={"current_spice": 0}
        )

    return game_state.model_copy(update={
        "players": updated_players,
        "territories": territories,
        "spice_bank": game_state.spice_bank + shield_wall_spice,
        "shield_wall_destroyed": True,
    })


# ===========================================================================
# Hajr — extra movement action this turn
# ===========================================================================

def play_hajr(
    game_state: GameState,
    player_id: str,
) -> GameState:
    """
    Play a Hajr card: take an additional force-move this Shipment & Movement turn.

    The card is discarded immediately.  The engine and movement handler check
    ``hajr_extra_move_faction`` to allow the player one additional move on top of
    their normal maximum.

    Can only be played during the Shipment & Movement phase.
    """
    from ...models.game_state import GamePhase

    if game_state.current_phase != GamePhase.SHIPMENT_AND_MOVEMENT:
        raise ValueError("Hajr can only be played during the Shipment & Movement phase.")

    player = _get_player(game_state, player_id)
    hajr = _find_special_card(player, SpecialCardType.HAJR)
    if hajr is None:
        raise ValueError("No Hajr card in hand.")

    game_state = _discard_from_hand(game_state, player_id, hajr.id)
    return game_state.model_copy(update={
        "hajr_extra_move_faction": player.faction,
    })


# ===========================================================================
# Weather Control — override next storm movement
# ===========================================================================

def play_weather_control(
    game_state: GameState,
    player_id: str,
    sectors: int,
) -> GameState:
    """
    Play a Weather Control card to set the next storm movement exactly.

    ``sectors`` must be 0-10.  The value overrides the random battle-wheel draw
    in ``resolve_storm``; it is consumed (cleared) once the storm resolves.

    Can be played at any time before the next Storm Phase.
    """
    if not 0 <= sectors <= 10:
        raise ValueError("Weather Control must set storm movement between 0 and 10 sectors.")

    player = _get_player(game_state, player_id)
    wc = _find_special_card(player, SpecialCardType.WEATHER_CONTROL)
    if wc is None:
        raise ValueError("No Weather Control card in hand.")

    game_state = _discard_from_hand(game_state, player_id, wc.id)
    return game_state.model_copy(update={
        "weather_control_override": sectors,
    })


# ===========================================================================
# Truthtrance — force an opponent to answer a yes/no question truthfully
# ===========================================================================

def play_truthtrance(
    game_state: GameState,
    player_id: str,
    target_faction: FactionName,
    question: str,
) -> GameState:
    """
    Play a Truthtrance card (Advanced only).

    The player asks a yes/no question and the target faction is honour-bound
    to answer truthfully.  Mechanical enforcement is impossible; the server
    records the event in the game log and discards the card so both players
    know it was played.

    ``question`` is a short free-text string (max 200 chars) shown in the log.
    ``target_faction`` identifies the faction being questioned.
    """
    if game_state.mode.value != "advanced":
        raise ValueError("Truthtrance is an Advanced-only card.")

    question = question.strip()
    if not question:
        raise ValueError("A question must be provided.")
    if len(question) > 200:
        raise ValueError("Question must be 200 characters or fewer.")

    player = _get_player(game_state, player_id)
    card = _find_special_card(player, SpecialCardType.TRUTHTRANCE)
    if card is None:
        raise ValueError("No Truthtrance card in hand.")

    # Target must be another player in the game
    target_player = next(
        (p for p in game_state.players if p.faction == target_faction), None
    )
    if target_player is None:
        raise ValueError(f"Faction '{target_faction.value}' is not in this game.")
    if target_player.id == player_id:
        raise ValueError("Cannot use Truthtrance on yourself.")

    # Discard and log
    game_state = _discard_from_hand(game_state, player_id, card.id)

    faction_label = target_faction.value.replace("_", " ").title()
    player_label = player.faction.value.replace("_", " ").title()
    log_msg = (
        f"🔮 {player_label} plays Truthtrance on {faction_label}: "
        f'"{question}" — {faction_label} must answer truthfully.'
    )
    new_log = list(game_state.game_log) + [log_msg]
    if len(new_log) > 60:
        new_log = new_log[-60:]
    return game_state.model_copy(update={"game_log": new_log})


# ===========================================================================
# Private helpers
# ===========================================================================

def _get_player(game_state: GameState, player_id: str) -> Player:
    for p in game_state.players:
        if p.id == player_id:
            return p
    raise ValueError(f"Player not found: {player_id}")


def _get_player_by_faction(game_state: GameState, faction: FactionName) -> Player:
    for p in game_state.players:
        if p.faction == faction:
            return p
    raise ValueError(f"Faction not found: {faction.value}")


def _replace_player(game_state: GameState, updated_player: Player) -> GameState:
    players = [
        updated_player if p.id == updated_player.id else p
        for p in game_state.players
    ]
    return game_state.model_copy(update={"players": players})


def _find_usable_karama(player: Player, game_state: GameState) -> Optional[TreacheryCard]:
    """
    Find a Karama card in the player's hand.
    BG in Advanced mode may also use any Worthless card as a Karama.
    """
    for card in player.treachery_hand:
        if (
            card.card_type == TreacheryCardType.SPECIAL
            and card.special_type == SpecialCardType.KARAMA
        ):
            return card
    # BG Advanced: Worthless card substitution
    if (
        game_state.mode.value == "advanced"
        and player.faction == FactionName.BENE_GESSERIT
    ):
        for card in player.treachery_hand:
            if card.card_type == TreacheryCardType.WORTHLESS:
                return card
    return None


def _find_special_card(player: Player, special_type: SpecialCardType) -> Optional[TreacheryCard]:
    for card in player.treachery_hand:
        if (
            card.card_type == TreacheryCardType.SPECIAL
            and card.special_type == special_type
        ):
            return card
    return None


def _discard_from_hand(
    game_state: GameState,
    player_id: str,
    card_id: str,
) -> GameState:
    """Remove ``card_id`` from the player's hand and add it to the treachery discard."""
    updated_players = []
    discarded_card = None

    for p in game_state.players:
        if p.id != player_id:
            updated_players.append(p)
            continue
        new_hand = []
        for c in p.treachery_hand:
            if c.id == card_id and discarded_card is None:
                discarded_card = c
            else:
                new_hand.append(c)
        updated_players.append(p.model_copy(update={"treachery_hand": new_hand}))

    new_discard = list(game_state.treachery_discard)
    if discarded_card:
        new_discard.append(discarded_card)

    return game_state.model_copy(update={
        "players": updated_players,
        "treachery_discard": new_discard,
    })
