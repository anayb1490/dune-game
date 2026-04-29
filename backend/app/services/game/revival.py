"""
Revival Phase service for the Dune board game.

Rulebook reference: p.9 — "Revival"

During the Revival Phase, players may revive forces from the Tleilaxu Tanks:
  - Each faction gets a number of free revivals per turn (faction-specific).
  - Additional forces can be revived by paying 2 spice each.
  - The COMBINED total of free + paid revivals cannot exceed 3 per turn.
  - Fremen may NOT pay for extra revivals (their free count is already 3).
  - Leaders can only be revived when ALL of a player's leaders are in the Tanks.
  - Only ONE leader may be revived per Revival phase.

Entry points:
    resolve_free_revival(game_state) -> GameState
    revive_forces(game_state, player_id, count) -> GameState
    revive_leader(game_state, player_id, leader_id) -> GameState
"""

from __future__ import annotations

from ...models.faction import FactionName
from ...models.game_state import GameState
from ...models.leader import LeaderStatus
from ...models.player import Player
from .handlers.registry import get_handler
from .phases import next_phase
from ...models.game_state import GamePhase

# Maximum total forces (free + paid) that may be revived in one Revival phase.
MAX_REVIVAL_PER_TURN: int = 3


def resolve_free_revival(game_state: GameState) -> GameState:
    """
    Automatically revive each player's free forces from the Tleilaxu Tanks.
    This is the automated portion of the Revival Phase.

    Also resets the per-turn revival counters (forces_revived_this_turn,
    leader_revived_this_turn) for every player so the cap is enforced
    correctly for subsequent paid revival actions.
    """
    updated_players: list[Player] = []

    for player in game_state.players:
        if player.is_eliminated:
            updated_players.append(player.model_copy(update={
                "forces_revived_this_turn": 0,
                "leader_revived_this_turn": False,
            }))
            continue

        handler = get_handler(player.faction)
        free_count = handler.get_free_revival_count(player, game_state)

        # Revive regular forces first
        regular_to_revive = min(free_count, player.forces_in_tanks)
        remaining_free = free_count - regular_to_revive

        # Revive special forces with remaining free slots
        special_to_revive = min(remaining_free, player.special_forces_in_tanks)

        total_revived = regular_to_revive + special_to_revive

        updated_players.append(player.model_copy(update={
            "forces_in_reserve": player.forces_in_reserve + regular_to_revive,
            "forces_in_tanks": player.forces_in_tanks - regular_to_revive,
            "special_forces_in_reserve": player.special_forces_in_reserve + special_to_revive,
            "special_forces_in_tanks": player.special_forces_in_tanks - special_to_revive,
            # Track how many free forces were revived; reset leader flag
            "forces_revived_this_turn": total_revived,
            "leader_revived_this_turn": False,
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

    Enforces:
      - Fremen cannot purchase extra revivals (their free count already fills the cap).
      - The total of free + paid revivals may not exceed MAX_REVIVAL_PER_TURN (3).
      - Players must have enough forces in tanks and enough spice.
    """
    player = _get_player(game_state, player_id)

    if count <= 0:
        raise ValueError("Must revive at least 1 force")

    # Fremen rule: cannot buy extra revivals
    if player.faction == FactionName.FREMEN:
        raise ValueError(
            "Fremen may only revive forces for free and cannot pay for extra revivals"
        )

    # Enforce combined free + paid cap of 3 per turn
    remaining_slots = MAX_REVIVAL_PER_TURN - player.forces_revived_this_turn
    if remaining_slots <= 0:
        raise ValueError(
            f"You have already revived {player.forces_revived_this_turn} forces this turn "
            f"(maximum {MAX_REVIVAL_PER_TURN})"
        )
    if count > remaining_slots:
        raise ValueError(
            f"Cannot revive {count} forces: already revived {player.forces_revived_this_turn} "
            f"this turn. Only {remaining_slots} slot(s) remaining (maximum {MAX_REVIVAL_PER_TURN})"
        )

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
                "forces_revived_this_turn": p.forces_revived_this_turn + count,
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

    Enforces:
      - ALL of the player's leaders must currently be in the Tleilaxu Tanks.
      - Only ONE leader may be revived per Revival phase.
    """
    player = _get_player(game_state, player_id)

    # One leader per Revival phase
    if player.leader_revived_this_turn:
        raise ValueError("You have already revived a leader this Revival phase")

    # All leaders must be in the Tanks before any can be revived
    total_leaders = len(player.leaders)
    leaders_in_tanks = sum(
        1 for l in player.leaders if l.status == LeaderStatus.IN_TANKS
    )
    if leaders_in_tanks < total_leaders:
        raise ValueError(
            f"Can only revive a leader when all {total_leaders} of your leaders are in the "
            f"Tleilaxu Tanks ({leaders_in_tanks} of {total_leaders} are currently in tanks)"
        )

    # Find the requested leader
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
                "leader_revived_this_turn": True,
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
