"""
Storm Phase service for the Dune board game.

Rulebook reference: p.7 — "Storm Phase"

The storm moves counterclockwise around the board. Any forces in a sand
sector that the storm passes through or stops on are destroyed — except:
  • Forces in rock, stronghold, or polar sink territories (always safe)
  • Forces in Imperial Basin (sand, but explicitly storm-exempt per rules)
  • Fremen forces (storm-immune via FactionHandler.is_immune_to_storm())

Entry point:
    resolve_storm(game_state, storm_move=None) -> GameState
"""

from __future__ import annotations

import random

from typing import Optional

from ...models.game_state import GamePhase, GameState
from ...models.player import Player
from .handlers.registry import get_handler


def resolve_storm(
    game_state: GameState,
    storm_move: Optional[int] = None,
) -> GameState:
    """
    Execute the Storm Phase and return the updated GameState.

    Parameters
    ----------
    game_state : GameState
        Current state — must be in STORM phase.
    storm_move : int, optional
        Number of sectors to move the storm (counterclockwise).
        If None, a random move is generated (2–6, simulating two
        battle-wheel dials of 1–3 each).

    Returns
    -------
    GameState with:
      - storm_sector updated to the new position
      - last_storm_move recorded
      - Forces in swept sectors destroyed (moved to tanks)
      - current_phase advanced to SPICE_BLOW
    """
    if storm_move is None:
        # Simulate two players each dialing 1–3 on battle wheels
        storm_move = random.randint(1, 3) + random.randint(1, 3)

    if storm_move == 0:
        # Edge case: no movement — just advance the phase
        return game_state.model_copy(update={
            "last_storm_move": 0,
            "current_phase": GamePhase.SPICE_BLOW,
        })

    old_sector = game_state.storm_sector

    # Determine which sectors the storm sweeps through.
    # Counterclockwise movement: sector decreases (mod 18).
    # The storm does NOT destroy forces at its starting sector —
    # only sectors it passes through and its final resting position.
    swept_sectors: list[int] = []
    for step in range(1, storm_move + 1):
        swept_sectors.append((old_sector - step) % 18)

    new_sector = swept_sectors[-1]

    # Destroy forces in swept sectors
    updated_players = _apply_storm_damage(
        game_state.players, swept_sectors, game_state
    )

    return game_state.model_copy(update={
        "storm_sector": new_sector,
        "last_storm_move": storm_move,
        "players": updated_players,
        "current_phase": GamePhase.SPICE_BLOW,
    })


def _apply_storm_damage(
    players: list[Player],
    swept_sectors: list[int],
    game_state: GameState,
) -> list[Player]:
    """
    For each player, destroy any forces sitting in a swept sector of an
    unprotected territory. Destroyed forces go to the Tleilaxu Tanks.

    Returns a new list of Player objects (immutable update).
    """
    swept_set = set(swept_sectors)
    updated_players: list[Player] = []

    for player in players:
        handler = get_handler(player.faction)

        # Fremen are completely immune to the storm
        if handler.is_immune_to_storm():
            updated_players.append(player)
            continue

        surviving_groups = []
        regular_killed = 0
        special_killed = 0

        for fg in player.forces_on_board:
            # Is this force group in a swept sector?
            if fg.sector not in swept_set:
                surviving_groups.append(fg)
                continue

            # Is the territory protected from the storm?
            territory = game_state.territories.get(fg.territory_name)
            if territory and territory.is_protected_from_storm:
                surviving_groups.append(fg)
                continue

            # Forces are destroyed — tally the casualties
            regular_killed += fg.regular_count
            special_killed += fg.special_count
            # ForceGroup is NOT added to surviving_groups → removed from board

        if regular_killed == 0 and special_killed == 0:
            # No damage — keep the original player object
            updated_players.append(player)
        else:
            updated_players.append(player.model_copy(update={
                "forces_on_board": surviving_groups,
                "forces_in_tanks": player.forces_in_tanks + regular_killed,
                "special_forces_in_tanks": (
                    player.special_forces_in_tanks + special_killed
                ),
            }))

    return updated_players
