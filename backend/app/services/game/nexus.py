"""
Nexus Phase service for the Dune board game.

Rulebook reference: p.16 — "Breaking An Alliance" / "Joining Another"

A Nexus occurs whenever a Shai-Hulud card is drawn (except on the first
turn). During a Nexus, every player gets the opportunity to:
  • Break their current alliance (unilateral — does not end turn).
  • Propose an alliance to another faction (ends turn).
  • Accept a pending proposal from another faction (ends turn, forms alliance).
  • Pass (ends turn with no action).

Each player can have at most ONE ally at a time. When all players are
done, the Nexus ends and the game advances to CHOAM Charity.

Entry points:
    init_nexus(game_state) -> GameState
    propose_alliance(game_state, player_id, target_faction) -> GameState
    accept_alliance(game_state, player_id, proposer_faction) -> GameState
    break_alliance(game_state, player_id) -> GameState
    pass_nexus(game_state, player_id) -> GameState
"""

from __future__ import annotations

from ...models.faction import FactionName
from ...models.game_state import GamePhase, GameState, NexusState
from ...models.player import Player
from .phases import next_phase


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_nexus(game_state: GameState) -> GameState:
    """
    Initialise the Nexus phase: create a NexusState and set the current
    faction to the first non-eliminated player in seating order.
    """
    first_faction = _first_active_faction(game_state)
    if first_faction is None:
        # No active players — skip the nexus entirely
        return game_state.model_copy(update={
            "current_phase": next_phase(GamePhase.NEXUS),
            "nexus_state": None,
        })

    nexus_state = NexusState(
        proposals={},
        factions_done=[],
        current_faction=first_faction,
    )

    return game_state.model_copy(update={
        "current_phase": GamePhase.NEXUS,
        "nexus_state": nexus_state,
    })


def propose_alliance(
    game_state: GameState,
    player_id: str,
    target_faction_str: str,
) -> GameState:
    """
    Propose an alliance to another faction.

    If the target has already proposed to this player, the alliance forms
    immediately (mutual match). Otherwise the proposal is recorded and
    the turn advances to the next player.

    Ends the player's nexus turn.
    """
    ns = _get_nexus_state(game_state)
    player = _get_player(game_state, player_id)
    _validate_is_current(ns, player)

    # Cannot propose if you already have an ally
    if player.ally is not None:
        raise ValueError(
            f"{player.faction.value} already has an ally "
            f"({player.ally.value}). Break the alliance first."
        )

    # Validate target
    target_faction = _parse_faction(target_faction_str)
    if target_faction == player.faction:
        raise ValueError("Cannot propose an alliance to yourself.")
    target_player = _get_player_by_faction(game_state, target_faction)
    if target_player.is_eliminated:
        raise ValueError(f"{target_faction.value} is eliminated.")
    if target_player.ally is not None:
        raise ValueError(f"{target_faction.value} is already allied with someone.")

    my_faction_str = player.faction.value
    target_str = target_faction.value

    # Check for mutual match: target already proposed to us
    if ns.proposals.get(target_str) == my_faction_str:
        # Alliance forms immediately!
        return _form_alliance(game_state, player.faction, target_faction)

    # Record the proposal
    new_proposals = dict(ns.proposals)
    new_proposals[my_faction_str] = target_str
    new_done = list(ns.factions_done) + [my_faction_str]
    updated_ns = ns.model_copy(update={
        "proposals": new_proposals,
        "factions_done": new_done,
    })
    updated_state = game_state.model_copy(update={"nexus_state": updated_ns})
    return _advance_nexus(updated_state)


def accept_alliance(
    game_state: GameState,
    player_id: str,
    proposer_faction_str: str,
) -> GameState:
    """
    Accept a pending alliance proposal.

    Forms the alliance between proposer and accepter.
    Ends the player's nexus turn.
    """
    ns = _get_nexus_state(game_state)
    player = _get_player(game_state, player_id)
    _validate_is_current(ns, player)

    if player.ally is not None:
        raise ValueError(
            f"{player.faction.value} already has an ally. Break the alliance first."
        )

    proposer_faction = _parse_faction(proposer_faction_str)
    proposer_str = proposer_faction.value
    my_str = player.faction.value

    # Validate there is a pending proposal from proposer to this player
    if ns.proposals.get(proposer_str) != my_str:
        raise ValueError(
            f"No pending proposal from {proposer_str} to {my_str}."
        )

    return _form_alliance(game_state, proposer_faction, player.faction)


def break_alliance(game_state: GameState, player_id: str) -> GameState:
    """
    Break the player's current alliance.

    Both players' ally fields are cleared. The breaking player's turn
    is NOT over — they can still propose a new alliance or pass.
    """
    ns = _get_nexus_state(game_state)
    player = _get_player(game_state, player_id)
    _validate_is_current(ns, player)

    if player.ally is None:
        raise ValueError(f"{player.faction.value} has no alliance to break.")

    ally_faction = player.ally
    updated_players = []
    for p in game_state.players:
        if p.faction == player.faction or p.faction == ally_faction:
            updated_players.append(p.model_copy(update={"ally": None}))
        else:
            updated_players.append(p)

    # Log the break
    log_entry = (
        f"{player.faction.value} breaks alliance with {ally_faction.value}."
    )
    new_log = (game_state.game_log + [log_entry])[-60:]

    # Stay on the same player — they can still propose or pass
    return game_state.model_copy(update={
        "players": updated_players,
        "game_log": new_log,
    })


def pass_nexus(game_state: GameState, player_id: str) -> GameState:
    """
    Pass — the player takes no alliance action this Nexus.
    Ends the player's nexus turn.
    """
    ns = _get_nexus_state(game_state)
    player = _get_player(game_state, player_id)
    _validate_is_current(ns, player)

    new_done = list(ns.factions_done) + [player.faction.value]
    updated_ns = ns.model_copy(update={"factions_done": new_done})
    updated_state = game_state.model_copy(update={"nexus_state": updated_ns})
    return _advance_nexus(updated_state)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _form_alliance(
    game_state: GameState,
    faction_a: FactionName,
    faction_b: FactionName,
) -> GameState:
    """
    Form an alliance between two factions. Sets both ally fields,
    marks both as done in the nexus, clears related proposals, and
    advances to the next player.
    """
    ns = _get_nexus_state(game_state)

    # Set ally on both players
    updated_players = []
    for p in game_state.players:
        if p.faction == faction_a:
            updated_players.append(p.model_copy(update={"ally": faction_b}))
        elif p.faction == faction_b:
            updated_players.append(p.model_copy(update={"ally": faction_a}))
        else:
            updated_players.append(p)

    # Clean up proposals and mark both factions done
    new_proposals = {
        k: v for k, v in ns.proposals.items()
        if k not in (faction_a.value, faction_b.value)
    }
    new_done = list(ns.factions_done)
    for fv in (faction_a.value, faction_b.value):
        if fv not in new_done:
            new_done.append(fv)

    updated_ns = ns.model_copy(update={
        "proposals": new_proposals,
        "factions_done": new_done,
    })

    # Log the alliance
    log_entry = f"{faction_a.value} and {faction_b.value} form an alliance!"
    new_log = (game_state.game_log + [log_entry])[-60:]

    updated_state = game_state.model_copy(update={
        "players": updated_players,
        "nexus_state": updated_ns,
        "game_log": new_log,
    })
    return _advance_nexus(updated_state)


def _advance_nexus(game_state: GameState) -> GameState:
    """
    Move to the next player who hasn't completed their nexus turn.
    If everyone is done, end the Nexus and advance to CHOAM Charity.
    """
    ns = game_state.nexus_state
    if ns is None:
        return game_state

    next_faction = _next_active_faction(game_state, ns)

    if next_faction is None:
        # Everyone is done — end the Nexus
        messages = _nexus_summary_messages(game_state)
        new_log = (game_state.game_log + messages)[-60:]
        return game_state.model_copy(update={
            "nexus_state": None,
            "current_phase": next_phase(GamePhase.NEXUS),
            "current_player_index": 0,
            "phase_messages": messages,
            "game_log": new_log,
        })

    updated_ns = ns.model_copy(update={"current_faction": next_faction})
    return game_state.model_copy(update={"nexus_state": updated_ns})


def _nexus_summary_messages(game_state: GameState) -> list[str]:
    """Generate phase messages summarising what happened during the Nexus."""
    msgs: list[str] = []

    # Show all current alliances
    seen = set()
    for p in game_state.players:
        if p.ally and p.faction.value not in seen:
            msgs.append(f"Alliance: {p.faction.value} + {p.ally.value}")
            seen.add(p.faction.value)
            seen.add(p.ally.value)

    if not msgs:
        msgs.append("Nexus concluded — no alliances formed.")
    else:
        msgs.insert(0, "Nexus concluded.")

    return msgs


def _first_active_faction(game_state: GameState) -> str | None:
    """The first non-eliminated player's faction value string."""
    for p in game_state.players:
        if not p.is_eliminated:
            return p.faction.value
    return None


def _next_active_faction(game_state: GameState, ns: NexusState) -> str | None:
    """
    Find the next non-eliminated faction in seating order that hasn't
    completed their nexus turn. Returns None if everyone is done.
    """
    done_set = set(ns.factions_done)
    for p in game_state.players:
        if p.is_eliminated:
            continue
        if p.faction.value not in done_set:
            return p.faction.value
    return None


def _get_nexus_state(game_state: GameState) -> NexusState:
    if game_state.nexus_state is None:
        raise ValueError("No active Nexus phase.")
    return game_state.nexus_state


def _validate_is_current(ns: NexusState, player: Player) -> None:
    if player.faction.value != ns.current_faction:
        raise ValueError(
            f"Not {player.faction.value}'s turn in the Nexus "
            f"(waiting for {ns.current_faction})."
        )


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


def _parse_faction(value: str) -> FactionName:
    try:
        return FactionName(value)
    except ValueError:
        raise ValueError(f"Unknown faction: {value}")
