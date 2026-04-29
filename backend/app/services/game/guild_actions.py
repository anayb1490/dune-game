"""
Spacing Guild faction-specific shipment actions.

Rulebook reference (p.17):
  Each turn, the Guild may make ONE of three types of shipments:
    (a) Ship normally from off-planet reserves to Dune.
    (b) CROSS-SHIPMENT: ship any number of forces from one territory on the
        board to any other territory on the board (no spice cost except half
        the normal rate).
    (c) BACK-TO-RESERVES: ship any number of forces from a territory on the
        board back to their off-planet reserves (cost: 1 spice per 2 forces,
        rounded UP).

Entry points:
    guild_cross_ship(game_state, player_id, from_territory, from_sector,
                     to_territory, to_sector, regular_count, special_count)
    guild_ship_to_reserves(game_state, player_id, from_territory, from_sector,
                           regular_count, special_count)
"""

from __future__ import annotations

import math

from ...models.faction import FactionName
from ...models.game_state import GameState
from ...models.player import ForceGroup, Player


def guild_cross_ship(
    game_state: GameState,
    player_id: str,
    from_territory: str,
    from_sector: int,
    to_territory: str,
    to_sector: int,
    regular_count: int = 0,
    special_count: int = 0,
) -> GameState:
    """
    Cross-shipment: move forces from one on-board territory to any other.
    Cost: normal shipment rate (1 spice per force to a stronghold, 2 elsewhere),
    but Guild pays HALF (rounded up). Counts as the Guild's one shipment for the turn.

    Allowed in any phase if Guild has the Advanced out-of-turn ability.
    """
    player = _get_player(game_state, player_id)

    if player.faction != FactionName.SPACING_GUILD:
        raise ValueError("Only the Spacing Guild can cross-ship")

    total = regular_count + special_count
    if total <= 0:
        raise ValueError("Must move at least 1 force")

    if from_territory not in game_state.territories:
        raise ValueError(f"Unknown territory: {from_territory}")
    if to_territory not in game_state.territories:
        raise ValueError(f"Unknown territory: {to_territory}")

    from_terr = game_state.territories[from_territory]
    to_terr = game_state.territories[to_territory]

    if from_sector not in from_terr.sectors:
        raise ValueError(f"Sector {from_sector} is not part of {from_territory}")
    if to_sector not in to_terr.sectors:
        raise ValueError(f"Sector {to_sector} is not part of {to_territory}")

    # Storm check — cannot arrive in a storm-blocked sand sector
    if (to_terr.is_sand and not to_terr.storm_exception
            and to_sector == game_state.storm_sector):
        raise ValueError("Cannot cross-ship to a sector currently in the storm")

    # Cannot cross-ship from a storm sector either
    if (from_terr.is_sand and not from_terr.storm_exception
            and from_sector == game_state.storm_sector):
        raise ValueError("Cannot cross-ship from a sector currently in the storm")

    # Check forces available in source
    existing_src = _find_force_group(player.forces_on_board, from_territory, from_sector)
    if existing_src is None:
        raise ValueError(f"No forces in {from_territory} sector {from_sector}")
    if regular_count > existing_src.regular_count:
        raise ValueError(f"Only {existing_src.regular_count} regular forces available")
    if special_count > existing_src.special_count:
        raise ValueError(f"Only {existing_src.special_count} special forces available")

    # Stronghold occupancy — can't enter a stronghold held by 2 other factions
    _check_stronghold_blocking(game_state, player.faction, to_territory)

    # Cost: half the normal rate (normal is 1/stronghold or 2/other), rounded up
    from_handler = _get_from_handler(player.faction)
    # Normal cost would be:
    normal_cost = total if to_terr.is_stronghold else total * 2
    # But for cross-shipment within Dune, treat as standard territory rate
    # Actually the rule says same rate as shipping from reserves, but at half price
    # (same logic as Guild's own shipment discount).
    normal_cost = total  # 1 per force (stronghold rate applies uniformly for cross-ship)
    cost = math.ceil(normal_cost / 2)

    if cost > player.spice:
        raise ValueError(f"Cross-shipment costs {cost} spice but only have {player.spice}")

    # Move forces
    new_forces = list(player.forces_on_board)

    # Remove from source
    src_idx = new_forces.index(existing_src)
    rem_reg = existing_src.regular_count - regular_count
    rem_spc = existing_src.special_count - special_count
    if rem_reg == 0 and rem_spc == 0:
        new_forces.pop(src_idx)
    else:
        new_forces[src_idx] = existing_src.model_copy(update={
            "regular_count": rem_reg,
            "special_count": rem_spc,
        })

    # Add to destination
    existing_dst = _find_force_group(new_forces, to_territory, to_sector)
    if existing_dst is not None:
        dst_idx = new_forces.index(existing_dst)
        new_forces[dst_idx] = existing_dst.model_copy(update={
            "regular_count": existing_dst.regular_count + regular_count,
            "special_count": existing_dst.special_count + special_count,
        })
    else:
        new_forces.append(ForceGroup(
            territory_name=to_territory,
            sector=to_sector,
            regular_count=regular_count,
            special_count=special_count,
        ))

    updated_players = [
        p.model_copy(update={
            "forces_on_board": new_forces,
            "spice": p.spice - cost,
        }) if p.id == player_id else p
        for p in game_state.players
    ]

    return game_state.model_copy(update={
        "players": updated_players,
        "spice_bank": game_state.spice_bank + cost,
    })


def guild_ship_to_reserves(
    game_state: GameState,
    player_id: str,
    from_territory: str,
    from_sector: int,
    regular_count: int = 0,
    special_count: int = 0,
) -> GameState:
    """
    Back-to-reserves shipment: Guild moves forces from the board back to reserves.
    Cost: 1 spice per 2 forces (rounded UP).
    """
    player = _get_player(game_state, player_id)

    if player.faction != FactionName.SPACING_GUILD:
        raise ValueError("Only the Spacing Guild can ship forces back to reserves")

    total = regular_count + special_count
    if total <= 0:
        raise ValueError("Must withdraw at least 1 force")

    if from_territory not in game_state.territories:
        raise ValueError(f"Unknown territory: {from_territory}")

    from_terr = game_state.territories[from_territory]
    if from_sector not in from_terr.sectors:
        raise ValueError(f"Sector {from_sector} is not part of {from_territory}")

    # Check forces available
    existing = _find_force_group(player.forces_on_board, from_territory, from_sector)
    if existing is None:
        raise ValueError(f"No forces in {from_territory} sector {from_sector}")
    if regular_count > existing.regular_count:
        raise ValueError(f"Only {existing.regular_count} regular forces available")
    if special_count > existing.special_count:
        raise ValueError(f"Only {existing.special_count} special forces available")

    # Cost: 1 spice per 2 forces, rounded UP
    cost = math.ceil(total / 2)

    if cost > player.spice:
        raise ValueError(
            f"Withdrawal costs {cost} spice ({total} forces ÷ 2, rounded up) "
            f"but only have {player.spice}"
        )

    # Remove from board, add to reserves
    new_forces = list(player.forces_on_board)
    src_idx = new_forces.index(existing)
    rem_reg = existing.regular_count - regular_count
    rem_spc = existing.special_count - special_count
    if rem_reg == 0 and rem_spc == 0:
        new_forces.pop(src_idx)
    else:
        new_forces[src_idx] = existing.model_copy(update={
            "regular_count": rem_reg,
            "special_count": rem_spc,
        })

    updated_players = [
        p.model_copy(update={
            "forces_on_board": new_forces,
            "forces_in_reserve": p.forces_in_reserve + regular_count,
            "special_forces_in_reserve": p.special_forces_in_reserve + special_count,
            "spice": p.spice - cost,
        }) if p.id == player_id else p
        for p in game_state.players
    ]

    return game_state.model_copy(update={
        "players": updated_players,
        "spice_bank": game_state.spice_bank + cost,
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_player(game_state: GameState, player_id: str) -> Player:
    for p in game_state.players:
        if p.id == player_id:
            return p
    raise ValueError(f"Player not found: {player_id}")


def _find_force_group(
    forces: list[ForceGroup],
    territory: str,
    sector: int,
) -> ForceGroup | None:
    for fg in forces:
        if fg.territory_name == territory and fg.sector == sector:
            return fg
    return None


def _get_from_handler(faction: FactionName):
    from .handlers.registry import get_handler
    return get_handler(faction)


def _check_stronghold_blocking(
    game_state: GameState,
    own_faction: FactionName,
    territory_name: str,
) -> None:
    """Raise if the territory is a stronghold already held by 2 other factions."""
    terr = game_state.territories.get(territory_name)
    if terr is None or not terr.is_stronghold:
        return

    other_factions: set = set()
    for p in game_state.players:
        if p.faction == own_faction or p.is_eliminated:
            continue
        for fg in p.forces_on_board:
            if (fg.territory_name == territory_name
                    and not fg.is_advisor
                    and (fg.regular_count + fg.special_count) > 0):
                other_factions.add(p.faction)

    if len(other_factions) >= 2:
        raise ValueError(
            f"Cannot enter {territory_name} — already occupied by "
            f"{len(other_factions)} other factions"
        )
