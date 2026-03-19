"""
Game engine for the Dune board game.

The engine is a state machine that advances through the 9 phases of each
game turn. Each call to advance_phase() resolves the current phase and
moves to the next one — one step at a time so every phase is visible
to the players.

Automated phases (Storm, Spice Blow, CHOAM Charity, Spice Collection,
Mentat Pause) resolve their effects immediately and populate
``phase_messages`` so players can see what happened. The host then
clicks "Advance Phase" to move on.

Interactive phases (Bidding, Revival, Shipment & Movement, Battle)
cycle through players one at a time.

Entry points:
    advance_phase(game_state) -> GameState
    run_automated_phases(game_state) -> GameState  (test helper only)
    advance_turn(game_state) -> GameState
"""

from __future__ import annotations

from ...models.faction import FactionName
from ...models.game_state import GamePhase, GameState
from .phases import AUTOMATED_PHASES, next_phase
from .spice import apply_spice_collection_effects, resolve_spice_blow, resolve_spice_collection
from .storm import resolve_storm


from .bidding import init_bidding
from .combat import init_battles
from .nexus import init_nexus
from .phases import resolve_choam_charity
from .revival import resolve_free_revival


# Maximum number of turns in a standard Dune game.
MAX_TURNS: int = 10

# Display names for phase messages
_FACTION_DISPLAY: dict[FactionName, str] = {
    FactionName.ATREIDES: "Atreides",
    FactionName.HARKONNEN: "Harkonnen",
    FactionName.BENE_GESSERIT: "Bene Gesserit",
    FactionName.FREMEN: "Fremen",
    FactionName.SPACING_GUILD: "Spacing Guild",
    FactionName.EMPEROR: "Emperor",
}


def advance_phase(game_state: GameState) -> GameState:
    """
    Resolve the current phase and advance to the next one.

    Automated phases use a two-step pattern:
      1. First call: resolve effects, populate phase_messages, stay on phase.
      2. Second call (host clicks advance): clear messages, move to next phase.

    Interactive phases advance per-player or per-phase as before.
    """
    # ------------------------------------------------------------------
    # Step 2: phase already resolved — clear messages and advance
    # ------------------------------------------------------------------
    if game_state.phase_messages:
        if game_state.current_phase == GamePhase.MENTAT_PAUSE:
            return advance_turn(game_state).model_copy(
                update={"phase_messages": []}
            )

        nxt = next_phase(game_state.current_phase)

        # Skip NEXUS if Shai-Hulud was not drawn this turn
        if nxt == GamePhase.NEXUS and not game_state.nexus_triggered:
            nxt = next_phase(GamePhase.NEXUS)

        base = game_state.model_copy(update={
            "current_phase": nxt,
            "current_player_index": 0,
            "phase_messages": [],
            "nexus_triggered": False,
        })
        # Entering NEXUS requires initialisation
        if nxt == GamePhase.NEXUS:
            return init_nexus(base)
        # Entering BIDDING requires initialisation
        if nxt == GamePhase.BIDDING:
            return init_bidding(base)
        return base

    # ------------------------------------------------------------------
    # Step 1: resolve the current phase
    # ------------------------------------------------------------------
    match game_state.current_phase:

        # ---- Automated: resolve immediately, generate messages --------

        case GamePhase.STORM:
            resolved = resolve_storm(game_state)
            messages = _storm_messages(game_state, resolved)
            new_log = (game_state.game_log + messages)[-60:]
            return resolved.model_copy(update={
                "current_phase": GamePhase.STORM,
                "phase_messages": messages,
                "game_log": new_log,
                "current_player_index": 0,
            })

        case GamePhase.SPICE_BLOW:
            resolved = resolve_spice_blow(game_state)
            messages = _spice_blow_messages(game_state, resolved)
            new_log = (game_state.game_log + messages)[-60:]
            return resolved.model_copy(update={
                "current_phase": GamePhase.SPICE_BLOW,
                "phase_messages": messages,
                "game_log": new_log,
                "current_player_index": 0,
            })

        case GamePhase.CHOAM_CHARITY:
            resolved = resolve_choam_charity(game_state)
            messages = _choam_charity_messages(game_state, resolved)
            new_log = (game_state.game_log + messages)[-60:]
            return resolved.model_copy(update={
                "current_phase": GamePhase.CHOAM_CHARITY,
                "phase_messages": messages,
                "game_log": new_log,
                "current_player_index": 0,
            })

        case GamePhase.SPICE_COLLECTION:
            resolved = apply_spice_collection_effects(game_state)
            messages = _spice_collection_messages(game_state, resolved)
            new_log = (game_state.game_log + messages)[-60:]
            return resolved.model_copy(update={
                "phase_messages": messages,
                "game_log": new_log,
            })

        case GamePhase.MENTAT_PAUSE:
            winner = _check_stronghold_victory(game_state)
            if winner:
                return game_state.model_copy(update={
                    "is_game_over": True,
                    "winner": winner,
                })
            alt_winner = _check_turn_limit_winner(game_state)
            if alt_winner:
                return game_state.model_copy(update={
                    "is_game_over": True,
                    "winner": alt_winner,
                })
            if game_state.current_turn >= MAX_TURNS:
                return game_state.model_copy(update={
                    "is_game_over": True,
                    "winner": None,
                })
            messages = [
                f"No faction controls 3 strongholds. "
                f"Turn {game_state.current_turn + 1} begins next."
            ]
            new_log = (game_state.game_log + messages)[-60:]
            return game_state.model_copy(update={
                "phase_messages": messages,
                "game_log": new_log,
            })

        # ---- Interactive phases ----------------------------------------

        case GamePhase.NEXUS:
            # Nexus is interactive — players take alliance actions.
            # If nexus_state is None, it's already been resolved.
            if game_state.nexus_state is None:
                nxt = next_phase(GamePhase.NEXUS)
                base = game_state.model_copy(update={
                    "current_phase": nxt,
                    "current_player_index": 0,
                })
                if nxt == GamePhase.BIDDING:
                    return init_bidding(base)
                return base
            return game_state  # Nexus in progress, can't advance via button

        case GamePhase.BIDDING:
            # Skip bidding if it's already been resolved (bidding_state is None)
            if game_state.bidding_state is None:
                return game_state.model_copy(update={
                    "current_phase": next_phase(GamePhase.BIDDING),
                    "current_player_index": 0,
                })
            return game_state  # Can't advance — bidding is in progress

        case GamePhase.REVIVAL:
            return _advance_player_or_phase(game_state, GamePhase.REVIVAL)

        case GamePhase.BATTLE:
            if game_state.active_battle is not None:
                return game_state
            return init_battles(game_state)

        case GamePhase.SHIPMENT_AND_MOVEMENT:
            return _advance_player_or_phase(game_state, GamePhase.SHIPMENT_AND_MOVEMENT)

        case _:
            return game_state.model_copy(update={
                "current_phase": next_phase(game_state.current_phase),
            })


def run_automated_phases(game_state: GameState) -> GameState:
    """
    Keep calling advance_phase() while the current phase is automated.
    Used by tests to fast-forward. The live game advances one phase at a time.
    """
    for _ in range(40):
        if game_state.is_game_over:
            break
        if game_state.current_phase not in AUTOMATED_PHASES:
            break
        game_state = advance_phase(game_state)
    return game_state


def _advance_player_or_phase(game_state: GameState, current_phase: GamePhase) -> GameState:
    """
    In turn-based interactive phases (Revival, Shipment & Movement),
    advance to the next player. If all players have had their turn,
    advance to the next phase and reset current_player_index to 0.

    Also resets moves_this_turn for the player finishing their turn so they
    start fresh in the next game turn's Shipment phase.
    """
    curr_idx = game_state.current_player_index
    next_idx = curr_idx + 1

    # Reset moves_this_turn for the player who just finished their turn
    players = list(game_state.players)
    if 0 <= curr_idx < len(players):
        players[curr_idx] = players[curr_idx].model_copy(update={"moves_this_turn": 0})

    if next_idx >= len(players):
        # All players have gone — advance to next phase
        return game_state.model_copy(update={
            "current_phase": next_phase(current_phase),
            "current_player_index": 0,
            "players": players,
        })
    else:
        return game_state.model_copy(update={
            "current_player_index": next_idx,
            "players": players,
        })


def advance_turn(game_state: GameState) -> GameState:
    """
    Increment the turn counter and reset the phase to STORM.

    If the game has reached the maximum number of turns (10), the game
    is over. In Advanced mode, the Spacing Guild wins if no other faction
    has claimed victory by then.

    Returns the updated GameState.
    """
    new_turn = game_state.current_turn + 1

    if new_turn > MAX_TURNS:
        # Game over — check for Guild alternate win (Advanced)
        winner = _check_turn_limit_winner(game_state)
        return game_state.model_copy(update={
            "is_game_over": True,
            "winner": winner,
        })

    return game_state.model_copy(update={
        "current_turn": new_turn,
        "current_phase": GamePhase.STORM,
        "current_player_index": 0,
    })


# ---------------------------------------------------------------------------
# Phase message generators
# ---------------------------------------------------------------------------

def _storm_messages(before: GameState, after: GameState) -> list[str]:
    msgs = [f"Storm moves {after.last_storm_move} sectors to sector {after.storm_sector}."]
    for old_p, new_p in zip(before.players, after.players):
        old_board = sum(fg.regular_count + fg.special_count for fg in old_p.forces_on_board)
        new_board = sum(fg.regular_count + fg.special_count for fg in new_p.forces_on_board)
        lost = old_board - new_board
        if lost > 0:
            name = _FACTION_DISPLAY.get(old_p.faction, old_p.faction)
            msgs.append(f"{name} lost {lost} force{'s' if lost != 1 else ''} to the storm.")
    return msgs


def _spice_blow_messages(before: GameState, after: GameState) -> list[str]:
    from ...models.card import SpiceCardType

    msgs: list[str] = []

    # Check for territories that lost all spice (Shai-Hulud ate it)
    for name, t_before in before.territories.items():
        t_after = after.territories.get(name)
        if t_before.current_spice > 0 and t_after and t_after.current_spice == 0:
            msgs.append(f"Shai-Hulud devours all spice in {name}!")

    # Check for player force losses (Shai-Hulud kills)
    for old_p, new_p in zip(before.players, after.players):
        old_board = sum(fg.regular_count + fg.special_count for fg in old_p.forces_on_board)
        new_board = sum(fg.regular_count + fg.special_count for fg in new_p.forces_on_board)
        lost = old_board - new_board
        if lost > 0:
            display = _FACTION_DISPLAY.get(old_p.faction, old_p.faction)
            msgs.append(f"{display} lost {lost} force{'s' if lost != 1 else ''} to Shai-Hulud.")

    # Check which territories gained spice (from territory card)
    spice_placed = False
    for name, t_after in after.territories.items():
        t_before = before.territories.get(name)
        if t_before and t_after.current_spice > t_before.current_spice:
            gained = t_after.current_spice - t_before.current_spice
            msgs.append(f"Spice blow: {gained} spice placed in {name}.")
            spice_placed = True

    # Detect storm-blocked spice: territory card drawn but no spice placed
    if not spice_placed:
        new_discard_ids = {c.id for c in after.spice_discard} - {c.id for c in before.spice_discard}
        for card in after.spice_discard:
            if card.id in new_discard_ids and card.card_type == SpiceCardType.TERRITORY:
                terr = after.territories.get(card.territory_name)
                if terr and before.storm_sector in terr.sectors:
                    msgs.append(
                        f"Spice blow in {card.territory_name} blocked by storm "
                        f"(sector {before.storm_sector})."
                    )

    if not msgs:
        msgs.append("No spice blow this turn.")
    return msgs


def _choam_charity_messages(before: GameState, after: GameState) -> list[str]:
    msgs: list[str] = []
    for old_p, new_p in zip(before.players, after.players):
        gained = new_p.spice - old_p.spice
        if gained > 0:
            name = _FACTION_DISPLAY.get(old_p.faction, old_p.faction)
            msgs.append(f"{name} receives {gained} spice from CHOAM.")
    if not msgs:
        msgs.append("No faction qualifies for CHOAM Charity.")
    return msgs


def _spice_collection_messages(before: GameState, after: GameState) -> list[str]:
    msgs: list[str] = []
    for old_p, new_p in zip(before.players, after.players):
        gained = new_p.spice - old_p.spice
        if gained > 0:
            name = _FACTION_DISPLAY.get(old_p.faction, old_p.faction)
            msgs.append(f"{name} collects {gained} spice.")
    if not msgs:
        msgs.append("No spice collected this turn.")
    return msgs


# ---------------------------------------------------------------------------
# Victory checks
# ---------------------------------------------------------------------------

def _check_stronghold_victory(game_state: GameState) -> FactionName | None:
    """
    Check if any faction (or alliance) controls enough strongholds.

    Solo faction: 3 strongholds to win.
    Alliance:     4 strongholds to win (counted jointly).

    A stronghold is controlled by an alliance unit if any member has
    forces there and no non-allied faction also has forces there.
    """
    from ...data.territories import STRONGHOLD_NAMES

    # Build map: stronghold -> set of factions with forces there
    stronghold_occupants: dict[str, set[FactionName]] = {s: set() for s in STRONGHOLD_NAMES}

    for player in game_state.players:
        if player.is_eliminated:
            continue
        for fg in player.forces_on_board:
            # BG Advisors don't count for stronghold control
            if fg.is_advisor:
                continue
            total = (fg.regular_count or 0) + (fg.special_count or 0)
            if total > 0 and fg.territory_name in stronghold_occupants:
                stronghold_occupants[fg.territory_name].add(player.faction)

    # Check each non-eliminated player (and their alliance as a unit)
    checked_alliances: set[tuple[str, ...]] = set()

    for player in game_state.players:
        if player.is_eliminated:
            continue

        # Build the alliance unit
        alliance_factions = {player.faction}
        if player.ally:
            alliance_factions.add(player.ally)

        # Avoid double-checking the same alliance
        key = tuple(sorted(f.value for f in alliance_factions))
        if key in checked_alliances:
            continue
        checked_alliances.add(key)

        # Threshold: 3 solo, 4 with ally
        threshold = 4 if player.ally else 3

        controlled = 0
        for sh_name, occupants in stronghold_occupants.items():
            # Does any member of this alliance occupy this stronghold?
            if not alliance_factions.intersection(occupants):
                continue
            # Is it contested by a non-allied faction?
            contested = False
            for other_faction in occupants:
                if other_faction in alliance_factions:
                    continue
                contested = True
                break
            if not contested:
                controlled += 1

        if controlled >= threshold:
            return player.faction

    return None


def _check_turn_limit_winner(game_state: GameState) -> FactionName | None:
    """
    When the turn limit is reached with no winner, the Spacing Guild
    wins (Advanced mode only) if they are in the game.

    Returns the winning faction or None.
    """
    from .handlers.registry import get_handler

    for player in game_state.players:
        handler = get_handler(player.faction)
        if handler.check_alternate_victory(player, game_state):
            return player.faction

    return None
