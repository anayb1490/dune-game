"""
Shipment & Movement Phase service for the Dune board game.

Rulebook reference: p.9–10 — "Shipment and Movement"

Each player, in turn order:
  1. May ship forces from reserve to any territory (costs spice).
  2. May move forces from one territory to an adjacent territory.

Entry points:
    ship_forces(game_state, player_id, territory, sector, count) -> GameState
    move_forces(game_state, player_id, from_territory, from_sector,
                to_territory, to_sector, count) -> GameState
"""

from __future__ import annotations

from ...data.adjacency import get_reachable_within, is_adjacent
from ...models.faction import FactionName
from ...models.game_state import GameState
from ...models.player import ForceGroup, Player
from .handlers.registry import get_handler
from .special_cards import is_karama_blocked

# Territories that grant ornithopter access when a player has forces there.
_ORNITHOPTER_TERRITORIES: frozenset[str] = frozenset({"Arrakeen", "Carthag"})
# Movement range (territory hops) granted by ornithopter access.
ORNITHOPTER_RANGE: int = 3


def ship_forces(
    game_state: GameState,
    player_id: str,
    territory_name: str,
    sector: int,
    count: int,
    special_count: int = 0,
) -> GameState:
    """
    Ship forces from reserve to a territory on the board.
    Cost: 1 spice per force shipped (faction abilities may modify).
    """
    player = _get_player(game_state, player_id)

    # Guild Karama power: the player's shipment may be blocked for this turn
    if is_karama_blocked(game_state, player.faction):
        raise ValueError(
            "Your shipment has been blocked by a Karama card this turn."
        )

    if territory_name not in game_state.territories:
        raise ValueError(f"Unknown territory: {territory_name}")

    territory = game_state.territories[territory_name]
    if sector not in territory.sectors:
        raise ValueError(f"Sector {sector} is not part of {territory_name}")

    regular_count = count - special_count
    if regular_count < 0:
        raise ValueError("Regular count cannot be negative")

    if regular_count > player.forces_in_reserve:
        raise ValueError(
            f"Only {player.forces_in_reserve} regular forces in reserve"
        )

    if special_count > player.special_forces_in_reserve:
        raise ValueError(
            f"Only {player.special_forces_in_reserve} special forces in reserve"
        )

    total = regular_count + special_count
    handler = get_handler(player.faction)
    cost = handler.calculate_shipment_cost(total, territory_name, player, game_state)

    if cost > player.spice:
        raise ValueError(f"Shipment costs {cost} spice but only have {player.spice}")

    # Check storm - can't ship to sand territory in storm sector
    storm_sector = game_state.storm_sector
    if territory.is_sand and not territory.storm_exception and sector == storm_sector:
        raise ValueError("Cannot ship to a sector currently in the storm")

    # Alliance constraint: can't ship into a territory where your ally has forces
    # (Polar Sink is exempt — any number of factions may coexist there)
    if player.ally and territory_name != "Polar Sink":
        for p in game_state.players:
            if p.faction == player.ally:
                ally_present = any(
                    fg.territory_name == territory_name
                    and (fg.regular_count + fg.special_count) > 0
                    for fg in p.forces_on_board
                )
                if ally_present:
                    raise ValueError(
                        f"Cannot ship to {territory_name} — your ally has forces there."
                    )

    # Add forces to the board
    new_forces = list(player.forces_on_board)
    existing = _find_force_group(new_forces, territory_name, sector)

    if existing is not None:
        idx = new_forces.index(existing)
        new_forces[idx] = existing.model_copy(update={
            "regular_count": existing.regular_count + regular_count,
            "special_count": existing.special_count + special_count,
        })
    else:
        new_forces.append(ForceGroup(
            territory_name=territory_name,
            sector=sector,
            regular_count=regular_count,
            special_count=special_count,
        ))

    # Update player
    updated_players = []
    spice_bank = game_state.spice_bank
    for p in game_state.players:
        if p.id == player_id:
            updated_players.append(p.model_copy(update={
                "forces_on_board": new_forces,
                "forces_in_reserve": p.forces_in_reserve - regular_count,
                "special_forces_in_reserve": p.special_forces_in_reserve - special_count,
                "spice": p.spice - cost,
            }))
        else:
            updated_players.append(p)

    # Shipment fee goes to Emperor if playing, otherwise to bank
    emperor_player = next(
        (p for p in game_state.players if p.faction.value == "emperor"),
        None
    )
    if emperor_player and emperor_player.id != player_id and cost > 0:
        # Emperor collects the fee
        updated_players = [
            p.model_copy(update={"spice": p.spice + cost})
            if p.faction.value == "emperor" else p
            for p in updated_players
        ]
    else:
        spice_bank += cost

    result = game_state.model_copy(update={
        "players": updated_players,
        "spice_bank": spice_bank,
    })
    return _maybe_set_bg_pending(result, player.faction, territory_name)


def move_forces(
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
    Move forces from one territory to an adjacent territory.
    Movement is free (no spice cost) but limited to one move per turn.
    Forces cannot move through the storm sector.
    """
    player = _get_player(game_state, player_id)
    total = regular_count + special_count

    if total <= 0:
        raise ValueError("Must move at least 1 force")

    if from_territory not in game_state.territories:
        raise ValueError(f"Unknown territory: {from_territory}")
    if to_territory not in game_state.territories:
        raise ValueError(f"Unknown territory: {to_territory}")

    to_terr = game_state.territories[to_territory]
    if to_sector not in to_terr.sectors:
        raise ValueError(f"Sector {to_sector} is not part of {to_territory}")

    # Check storm - can't move to storm sector in sand
    if to_terr.is_sand and not to_terr.storm_exception and to_sector == game_state.storm_sector:
        raise ValueError("Cannot move to a sector currently in the storm")

    # Alliance constraint: can't move into a territory where your ally has forces
    # (Polar Sink is exempt — any number of factions may coexist there)
    if player.ally and to_territory != "Polar Sink":
        for p in game_state.players:
            if p.faction == player.ally:
                ally_present = any(
                    fg.territory_name == to_territory
                    and (fg.regular_count + fg.special_count) > 0
                    for fg in p.forces_on_board
                )
                if ally_present:
                    raise ValueError(
                        f"Cannot move to {to_territory} — your ally has forces there."
                    )

    # Check movement limit (standard: 1 action, Fremen Advanced: 2 actions)
    handler = get_handler(player.faction)
    max_move_actions = handler.get_max_movement_distance(player, game_state)
    # Hajr card grants one extra movement action this turn
    if game_state.hajr_extra_move_faction == player.faction:
        max_move_actions += 1
    if player.moves_this_turn >= max_move_actions:
        if max_move_actions == 1:
            raise ValueError("You have already moved forces this turn.")
        raise ValueError(f"You have already used all {max_move_actions} moves this turn.")

    # Determine movement range (hops per action).
    # Ornithopter: owning forces in Arrakeen or Carthag grants range 3.
    # Otherwise range is 1 (standard adjacency only).
    move_range = _get_move_range(player, game_state)

    # Validate that the destination is reachable within the allowed range.
    if move_range == 1:
        if not is_adjacent(from_territory, to_territory):
            raise ValueError(f"{from_territory} is not adjacent to {to_territory}.")
    else:
        # BFS reachability, excluding storm-blocked sand territories as waypoints
        blocked = _get_storm_blocked_territories(game_state)
        reachable = get_reachable_within(from_territory, move_range, blocked)
        if to_territory not in reachable:
            raise ValueError(
                f"{to_territory} is not reachable from {from_territory} "
                f"within {move_range} territory hops."
            )

    # Find existing force group
    existing = _find_force_group(player.forces_on_board, from_territory, from_sector)
    if existing is None:
        raise ValueError(f"No forces in {from_territory} sector {from_sector}")

    if regular_count > existing.regular_count:
        raise ValueError(f"Only {existing.regular_count} regular forces available")
    if special_count > existing.special_count:
        raise ValueError(f"Only {existing.special_count} special forces available")

    # Update forces
    new_forces = list(player.forces_on_board)

    # Remove from source
    src_idx = new_forces.index(existing)
    remaining_regular = existing.regular_count - regular_count
    remaining_special = existing.special_count - special_count
    if remaining_regular == 0 and remaining_special == 0:
        new_forces.pop(src_idx)
    else:
        new_forces[src_idx] = existing.model_copy(update={
            "regular_count": remaining_regular,
            "special_count": remaining_special,
        })

    # Add to destination
    dest_existing = _find_force_group(new_forces, to_territory, to_sector)
    if dest_existing is not None:
        dest_idx = new_forces.index(dest_existing)
        new_forces[dest_idx] = dest_existing.model_copy(update={
            "regular_count": dest_existing.regular_count + regular_count,
            "special_count": dest_existing.special_count + special_count,
        })
    else:
        new_forces.append(ForceGroup(
            territory_name=to_territory,
            sector=to_sector,
            regular_count=regular_count,
            special_count=special_count,
        ))

    # Update player — increment moves_this_turn counter
    updated_players = []
    for p in game_state.players:
        if p.id == player_id:
            updated_players.append(p.model_copy(update={
                "forces_on_board": new_forces,
                "moves_this_turn": p.moves_this_turn + 1,
            }))
        else:
            updated_players.append(p)

    return game_state.model_copy(update={
        "players": updated_players,
    })


def _find_force_group(
    forces: list[ForceGroup],
    territory_name: str,
    sector: int,
) -> ForceGroup | None:
    for fg in forces:
        if fg.territory_name == territory_name and fg.sector == sector:
            return fg
    return None


def _get_player(game_state: GameState, player_id: str) -> Player:
    for player in game_state.players:
        if player.id == player_id:
            return player
    raise ValueError(f"Player not found: {player_id}")


def _has_ornithopter_access(player: Player) -> bool:
    """
    Returns True if the player currently has at least one force in Arrakeen
    or Carthag. Per the rules, ANY force in either city grants ornithopter
    access for that player's entire movement action.
    """
    return any(
        fg.territory_name in _ORNITHOPTER_TERRITORIES
        and (fg.regular_count + fg.special_count) > 0
        for fg in player.forces_on_board
    )


def _get_move_range(player: Player, game_state: GameState) -> int:
    """
    Return the movement range (territory hops) for a single move action.

    Ornithopter (forces in Arrakeen or Carthag): range 3.
    All other players: range 1 (standard single-adjacency move).

    Note: Fremen Advanced double-movement is handled separately via
    get_max_movement_distance(), which allows 2 separate move actions.
    """
    if _has_ornithopter_access(player):
        return ORNITHOPTER_RANGE
    return 1


def _maybe_set_bg_pending(
    game_state: GameState,
    shipping_faction: FactionName,
    territory_name: str,
) -> GameState:
    """
    After a non-BG faction ships, set the BG free-ship pending flag so BG gets
    a chance to respond out-of-turn (Basic: Polar Sink; Advanced: that territory
    or Polar Sink).

    Does nothing if:
      - BG was the one who shipped.
      - BG is not in the game.
      - BG has no forces in reserve.
    """
    if shipping_faction == FactionName.BENE_GESSERIT:
        return game_state
    bg_player = next(
        (p for p in game_state.players
         if p.faction == FactionName.BENE_GESSERIT and not p.is_eliminated),
        None,
    )
    if bg_player is None or bg_player.forces_in_reserve <= 0:
        return game_state
    return game_state.model_copy(update={
        "bg_free_ship_pending": True,
        "bg_free_ship_last_territory": territory_name,
    })


def _get_storm_blocked_territories(game_state: GameState) -> frozenset[str]:
    """
    Return the set of sand territories where the storm sector is present.
    These territories cannot be entered or used as ornithopter waypoints.

    Imperial Basin is excluded because it has storm_exception=True.
    The Polar Sink is never in storm and is not sand, so it is always safe.
    """
    storm = game_state.storm_sector
    return frozenset(
        name
        for name, terr in game_state.territories.items()
        if terr.is_sand and not terr.storm_exception and storm in terr.sectors
    )
