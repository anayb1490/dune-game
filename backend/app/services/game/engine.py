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
        # Entering SHIPMENT_AND_MOVEMENT: reveal top spice card to Atreides (Advanced)
        if nxt == GamePhase.SHIPMENT_AND_MOVEMENT:
            return _inject_atreides_movement_prescience(base)
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
            # ----------------------------------------------------------------
            # Victory check order (each level takes precedence over those below):
            # 1. Bene Gesserit prediction (Advanced) — wins instead of predicted faction
            # 2. Fremen special victory (Advanced) — 3 Fremen sietchs, no ally
            # 3. Standard stronghold victory — 3 solo or 4 allied
            # 4. Spacing Guild alternate victory (Advanced) — wins at turn 10 if no one else did
            # 5. Turn limit (turn 10 with no winner) — game ends, no victor
            # ----------------------------------------------------------------

            # 1. BG prediction win (Advanced, takes precedence over everything)
            bg_win = _check_bg_prediction_victory(game_state)
            if bg_win:
                bg_player = next(
                    (p for p in game_state.players if p.faction == bg_win), None
                )
                if bg_player and bg_player.prediction:
                    predicted_name = _FACTION_DISPLAY.get(
                        bg_player.prediction.faction, str(bg_player.prediction.faction)
                    )
                    msg = (
                        f"Bene Gesserit prediction correct! "
                        f"{predicted_name} wins on turn {bg_player.prediction.turn} "
                        f"— Bene Gesserit claim victory!"
                    )
                else:
                    msg = "Bene Gesserit prediction fulfilled — they win!"
                new_log = (game_state.game_log + [msg])[-60:]
                return game_state.model_copy(update={
                    "is_game_over": True,
                    "winner": bg_win,
                    "ally_winner": None,
                    "win_condition": "Bene Gesserit prediction fulfilled",
                    "bg_prediction_revealed": True,
                    "phase_messages": [msg],
                    "game_log": new_log,
                })

            # 2. Fremen special victory (Advanced) — must be checked before standard stronghold
            fremen_win = _check_fremen_special_victory(game_state)
            if fremen_win:
                msg = (
                    "Fremen victory! They control Sietch Tabr, Habbanya Sietch, "
                    "and Tuek's Sietch — the desert is theirs!"
                )
                new_log = (game_state.game_log + [msg])[-60:]
                return game_state.model_copy(update={
                    "is_game_over": True,
                    "winner": fremen_win,
                    "ally_winner": None,
                    "win_condition": "Fremen desert control (Sietch Tabr, Habbanya Sietch, Tuek's Sietch)",
                    "phase_messages": [msg],
                    "game_log": new_log,
                })

            # 3. Standard stronghold victory (3 solo, 4 allied)
            winner = _check_stronghold_victory(game_state)
            if winner:
                winner_player = next(
                    (p for p in game_state.players if p.faction == winner), None
                )
                ally_winner = winner_player.ally if winner_player else None
                winner_name = _FACTION_DISPLAY.get(winner, str(winner))
                if ally_winner:
                    ally_name = _FACTION_DISPLAY.get(ally_winner, str(ally_winner))
                    msg = (
                        f"{winner_name} and {ally_name} win together — "
                        f"their alliance controls 4 strongholds!"
                    )
                else:
                    msg = f"{winner_name} wins — they control 3 strongholds!"
                new_log = (game_state.game_log + [msg])[-60:]
                win_cond = (
                    "Alliance controls 4 strongholds" if ally_winner
                    else "Controls 3 strongholds"
                )
                return game_state.model_copy(update={
                    "is_game_over": True,
                    "winner": winner,
                    "ally_winner": ally_winner,
                    "win_condition": win_cond,
                    "phase_messages": [msg],
                    "game_log": new_log,
                })

            # 4. Spacing Guild alternate victory (Advanced, turn 10 only)
            guild_win = _check_guild_alternate_victory(game_state)
            if guild_win:
                msg = (
                    "No faction has conquered Arrakis. "
                    "The Spacing Guild tightens its monopoly — Guild wins!"
                )
                new_log = (game_state.game_log + [msg])[-60:]
                return game_state.model_copy(update={
                    "is_game_over": True,
                    "winner": guild_win,
                    "ally_winner": None,
                    "win_condition": "Spacing Guild economic monopoly (turn 10)",
                    "phase_messages": [msg],
                    "game_log": new_log,
                })

            # 5. Hard turn limit — game ends with no victor
            if game_state.current_turn >= MAX_TURNS:
                msg = "The game ends with no faction controlling enough strongholds. No victor."
                new_log = (game_state.game_log + [msg])[-60:]
                return game_state.model_copy(update={
                    "is_game_over": True,
                    "winner": None,
                    "ally_winner": None,
                    "win_condition": "Stalemate — no faction achieved victory",
                    "phase_messages": [msg],
                    "game_log": new_log,
                })

            messages = [
                f"No faction controls enough strongholds "
                f"(3 solo or 4 with an ally). "
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
            # Any un-used BG free ship opportunity expires when the turn advances
            "bg_free_ship_pending": False,
            "bg_free_ship_last_territory": None,
        })
    else:
        return game_state.model_copy(update={
            "current_player_index": next_idx,
            "players": players,
            # Any un-used BG free ship opportunity expires when the turn advances
            "bg_free_ship_pending": False,
            "bg_free_ship_last_territory": None,
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

def _check_bg_prediction_victory(game_state: GameState) -> FactionName | None:
    """
    Check if the Bene Gesserit prediction win condition is satisfied.
    BG wins immediately if, at Mentat Pause, the faction they predicted controls
    enough strongholds AND it is the exact turn they predicted.
    This takes precedence over all other win conditions (Advanced only).
    """
    if game_state.mode.value != "advanced":
        return None
    from .handlers.registry import get_handler
    for player in game_state.players:
        if player.faction == FactionName.BENE_GESSERIT and not player.is_eliminated:
            handler = get_handler(player.faction)
            if handler.check_alternate_victory(player, game_state):
                return FactionName.BENE_GESSERIT
    return None


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


def _check_fremen_special_victory(game_state: GameState) -> FactionName | None:
    """
    Check whether Fremen have won via their special victory condition (Advanced).
    Fremen win if they control Sietch Tabr, Habbanya Sietch, and Tuek's Sietch
    with no ally, regardless of how many other factions control standard strongholds.
    This takes precedence over the standard stronghold check.
    """
    if game_state.mode.value != "advanced":
        return None
    from .handlers.registry import get_handler
    for player in game_state.players:
        if player.faction == FactionName.FREMEN and not player.is_eliminated:
            handler = get_handler(player.faction)
            if handler.check_alternate_victory(player, game_state):
                return FactionName.FREMEN
    return None


def _check_guild_alternate_victory(game_state: GameState) -> FactionName | None:
    """
    Check whether the Spacing Guild wins via their alternate victory condition.
    Guild wins at the end of turn 10 if no other faction controls enough strongholds
    (Advanced mode only).
    """
    if game_state.mode.value != "advanced":
        return None
    from .handlers.registry import get_handler
    for player in game_state.players:
        if player.faction == FactionName.SPACING_GUILD and not player.is_eliminated:
            handler = get_handler(player.faction)
            if handler.check_alternate_victory(player, game_state):
                return FactionName.SPACING_GUILD
    return None


def _check_turn_limit_winner(game_state: GameState) -> FactionName | None:
    """
    Called from advance_turn() when the game exceeds MAX_TURNS.
    Checks Guild's alternate victory (Advanced) and falls back to None.
    Kept for backward compatibility with advance_turn().
    """
    return _check_guild_alternate_victory(game_state)


def _inject_atreides_movement_prescience(game_state: GameState) -> GameState:
    """
    Advanced: when entering the Shipment & Movement phase, reveal the top card
    of the Spice Deck to the Atreides player (and only them).

    Stores the card as a dict on `atreides_movement_prescience` and resets
    the `atreides_movement_prescience_seen` flag. The state_filter will expose
    this to Atreides and hide it from everyone else.
    """
    if game_state.mode.value != "advanced":
        return game_state

    # Check if Atreides is in the game
    atreides = next(
        (p for p in game_state.players
         if p.faction == FactionName.ATREIDES and not p.is_eliminated),
        None,
    )
    if atreides is None:
        return game_state

    if not game_state.spice_deck:
        return game_state

    top_card = game_state.spice_deck[0]
    card_dict = top_card.model_dump(mode="json")

    return game_state.model_copy(update={
        "atreides_movement_prescience": card_dict,
        "atreides_movement_prescience_seen": False,
    })
