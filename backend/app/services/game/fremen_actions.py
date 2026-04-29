"""
Advanced Fremen faction abilities.

SANDWORM RIDING (Advanced)
  After Shai-Hulud appears (turn 2+) and attacks a territory, Fremen may
  ride the sandworm: move any or all of their forces in the attacked territory
  to any other territory, subject to storm and occupancy rules.

  This move does NOT count as the Fremen player's normal movement for the turn.
  If Fremen choose not to ride, they call fremen_skip_sandworm_ride instead.

  Tracked via game_state.fremen_sandworm_ride_territory:
    - Set by resolve_spice_blow when Shai-Hulud draws on turn > 1.
    - Cleared by fremen_sandworm_ride() or fremen_skip_sandworm_ride().
"""

from __future__ import annotations

from ...models.faction import FactionName
from ...models.game_state import GameState
from ...models.player import ForceGroup


def fremen_sandworm_ride(
    game_state: GameState,
    player_id: str,
    to_territory: str,
    to_sector: int,
    regular_count: int = 0,
    special_count: int = 0,
) -> GameState:
    """
    Move Fremen forces from the sandworm-attacked territory to any other territory.

    Rules:
    - Only Fremen (or Advanced ally if BG Alliance benefit applies) may call this.
    - fremen_sandworm_ride_territory must be set (sandworm attacked this turn).
    - Forces are moved from ALL sectors of the attacked territory (combined into
      the destination sector).
    - Destination cannot be a storm-blocked sector (storm_sector in territory sectors).
    - Destination cannot already be occupied by enemies (basic occupancy rule).
    - Does NOT cost spice and does NOT consume the turn's movement action.
    - Alliance benefit: Fremen may optionally protect allied forces too — but
      only Fremen forces ride the worm; allied forces are simply not devoured
      (that immunity is already handled in _shai_hulud_attack).
    """
    if game_state.mode.value != "advanced":
        raise ValueError("Sandworm riding is an Advanced mode ability")

    from_territory = game_state.fremen_sandworm_ride_territory
    if from_territory is None:
        raise ValueError("No sandworm ride available this turn")

    # Find the Fremen player
    fremen = next(
        (p for p in game_state.players if p.id == player_id),
        None,
    )
    if fremen is None:
        raise ValueError(f"Player not found: {player_id}")
    if fremen.faction != FactionName.FREMEN:
        raise ValueError("Only the Fremen player may ride the sandworm")

    if to_territory == from_territory:
        raise ValueError("Must ride to a different territory")

    # Destination territory exists?
    dest_territory = game_state.territories.get(to_territory)
    if dest_territory is None:
        raise ValueError(f"Unknown territory: {to_territory}")

    if to_sector not in dest_territory.sectors:
        raise ValueError(
            f"Sector {to_sector} is not in {to_territory} "
            f"(valid: {dest_territory.sectors})"
        )

    # Storm check on destination
    if game_state.storm_sector in dest_territory.sectors:
        raise ValueError(f"{to_territory} sector {to_sector} is in the storm")

    # Count available Fremen forces in the attacked territory
    available_regular = sum(
        fg.regular_count
        for fg in fremen.forces_on_board
        if fg.territory_name == from_territory
    )
    available_special = sum(
        fg.special_count
        for fg in fremen.forces_on_board
        if fg.territory_name == from_territory
    )

    if regular_count < 0 or special_count < 0:
        raise ValueError("Force counts cannot be negative")
    if regular_count > available_regular:
        raise ValueError(
            f"Only {available_regular} regular Fremen in {from_territory}, "
            f"cannot ride {regular_count}"
        )
    if special_count > available_special:
        raise ValueError(
            f"Only {available_special} Fedaykin in {from_territory}, "
            f"cannot ride {special_count}"
        )
    if regular_count + special_count == 0:
        raise ValueError("Must ride at least 1 force (use skip action to pass)")

    # Occupancy check: destination cannot be held by enemies (non-allied)
    for other in game_state.players:
        if other.faction == FactionName.FREMEN or other.is_eliminated:
            continue
        if other.faction == fremen.ally:
            continue  # Allies can coexist
        enemy_there = any(
            fg.territory_name == to_territory
            and (fg.regular_count + fg.special_count) > 0
            and not fg.is_advisor
            for fg in other.forces_on_board
        )
        if enemy_there:
            raise ValueError(
                f"Cannot ride to {to_territory}: occupied by {other.faction.value}"
            )

    # --- Apply the move ---
    remaining_regular = regular_count
    remaining_special = special_count
    new_forces: list[ForceGroup] = []

    for fg in fremen.forces_on_board:
        if fg.territory_name != from_territory:
            new_forces.append(fg)
            continue

        # Remove from source
        take_reg = min(fg.regular_count, remaining_regular)
        take_spec = min(fg.special_count, remaining_special)
        remaining_regular -= take_reg
        remaining_special -= take_spec

        leftover_reg = fg.regular_count - take_reg
        leftover_spec = fg.special_count - take_spec
        if leftover_reg > 0 or leftover_spec > 0:
            new_forces.append(fg.model_copy(update={
                "regular_count": leftover_reg,
                "special_count": leftover_spec,
            }))

    # Merge into destination (collapse same sector)
    dest_idx = next(
        (i for i, fg in enumerate(new_forces)
         if fg.territory_name == to_territory and fg.sector == to_sector
         and not fg.is_advisor),
        None,
    )
    if dest_idx is not None:
        existing = new_forces[dest_idx]
        new_forces[dest_idx] = existing.model_copy(update={
            "regular_count": existing.regular_count + regular_count,
            "special_count": existing.special_count + special_count,
        })
    else:
        new_forces.append(ForceGroup(
            territory_name=to_territory,
            sector=to_sector,
            regular_count=regular_count,
            special_count=special_count,
        ))

    updated_fremen = fremen.model_copy(update={"forces_on_board": new_forces})
    updated_players = [
        updated_fremen if p.faction == FactionName.FREMEN else p
        for p in game_state.players
    ]

    return game_state.model_copy(update={
        "players": updated_players,
        "fremen_sandworm_ride_territory": None,  # Consumed
    })


def fremen_skip_sandworm_ride(game_state: GameState, player_id: str) -> GameState:
    """
    Fremen choose not to ride the sandworm this turn.
    Clears fremen_sandworm_ride_territory without moving any forces.
    """
    fremen = next((p for p in game_state.players if p.id == player_id), None)
    if fremen is None:
        raise ValueError(f"Player not found: {player_id}")
    if fremen.faction != FactionName.FREMEN:
        raise ValueError("Only the Fremen player may skip the sandworm ride")
    if game_state.fremen_sandworm_ride_territory is None:
        raise ValueError("No sandworm ride pending this turn")

    return game_state.model_copy(update={"fremen_sandworm_ride_territory": None})
