"""
Revival Phase service for the Dune board game.

Rulebook reference: p.9 — "Revival"

During the Revival Phase, players may revive forces from the Tleilaxu Tanks:
  - Each faction gets a number of free revivals per turn (faction-specific).
  - Additional forces can be revived by paying 2 spice each.
  - Leaders in the tanks can be revived by paying their strength in spice.

For simplicity, free revival is automated. Paid revival requires player action.

Entry points:
    resolve_free_revival(game_state) -> GameState
    revive_forces(game_state, player_id, count, pay_for_extra) -> GameState
    revive_leader(game_state, player_id, leader_id) -> GameState
"""

from __future__ import annotations

from ...models.game_state import GameState
from ...models.leader import LeaderStatus
from ...models.player import Player
from .handlers.registry import get_handler
from .phases import next_phase
from ...models.game_state import GamePhase


def resolve_free_revival(game_state: GameState) -> GameState:
    """
    Automatically revive each player's free forces from the Tleilaxu Tanks.
    This is the automated portion of the Revival Phase.
    """
    updated_players: list[Player] = []

    for player in game_state.players:
        if player.is_eliminated:
            updated_players.append(player)
            continue

        handler = get_handler(player.faction)
        free_count = handler.get_free_revival_count(player, game_state)

        # Revive regular forces first
        regular_to_revive = min(free_count, player.forces_in_tanks)
        remaining_free = free_count - regular_to_revive

        # Revive special forces with remaining free slots
        special_to_revive = min(remaining_free, player.special_forces_in_tanks)

        updated_players.append(player.model_copy(update={
            "forces_in_reserve": player.forces_in_reserve + regular_to_revive,
            "forces_in_tanks": player.forces_in_tanks - regular_to_revive,
            "special_forces_in_reserve": player.special_forces_in_reserve + special_to_revive,
            "special_forces_in_tanks": player.special_forces_in_tanks - special_to_revive,
        }))

    return game_state.model_copy(update={
        "players": updated_players,
    })


def revive_forces(
    game_state: GameState,
    player_id: str,
    count: int,
) -> GameState:
    """
    A player pays to revive additional forces (2 spice each).
    """
    player = _get_player(game_state, player_id)

    if count <= 0:
        raise ValueError("Must revive at least 1 force")

    available_in_tanks = player.forces_in_tanks + player.special_forces_in_tanks
    if count > available_in_tanks:
        raise ValueError(f"Only {available_in_tanks} forces in tanks")

    cost = count * 2
    if cost > player.spice:
        raise ValueError(f"Need {cost} spice but only have {player.spice}")

    # Revive regular first, then special
    regular_to_revive = min(count, player.forces_in_tanks)
    special_to_revive = count - regular_to_revive

    updated_players = []
    for p in game_state.players:
        if p.id == player_id:
            updated_players.append(p.model_copy(update={
                "spice": p.spice - cost,
                "forces_in_reserve": p.forces_in_reserve + regular_to_revive,
                "forces_in_tanks": p.forces_in_tanks - regular_to_revive,
                "special_forces_in_reserve": p.special_forces_in_reserve + special_to_revive,
                "special_forces_in_tanks": p.special_forces_in_tanks - special_to_revive,
            }))
        else:
            updated_players.append(p)

    return game_state.model_copy(update={
        "players": updated_players,
        "spice_bank": game_state.spice_bank + cost,
    })


def revive_leader(
    game_state: GameState,
    player_id: str,
    leader_id: str,
) -> GameState:
    """
    A player pays to revive a leader from the Tleilaxu Tanks.
    Cost = leader's strength in spice.
    """
    player = _get_player(game_state, player_id)

    leader = None
    for l in player.leaders:
        if l.id == leader_id:
            leader = l
            break

    if leader is None:
        raise ValueError(f"Leader not found: {leader_id}")

    if leader.status != LeaderStatus.IN_TANKS:
        raise ValueError(f"Leader {leader.name} is not in tanks (status: {leader.status})")

    cost = leader.strength
    if cost > player.spice:
        raise ValueError(f"Need {cost} spice to revive {leader.name} but only have {player.spice}")

    # Update leader status
    updated_leaders = []
    for l in player.leaders:
        if l.id == leader_id:
            updated_leaders.append(l.model_copy(update={"status": LeaderStatus.AVAILABLE}))
        else:
            updated_leaders.append(l)

    updated_players = []
    for p in game_state.players:
        if p.id == player_id:
            updated_players.append(p.model_copy(update={
                "spice": p.spice - cost,
                "leaders": updated_leaders,
            }))
        else:
            updated_players.append(p)

    return game_state.model_copy(update={
        "players": updated_players,
        "spice_bank": game_state.spice_bank + cost,
    })


def _get_player(game_state: GameState, player_id: str) -> Player:
    for player in game_state.players:
        if player.id == player_id:
            return player
    raise ValueError(f"Player not found: {player_id}")
