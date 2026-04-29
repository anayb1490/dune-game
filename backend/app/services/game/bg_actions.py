"""
Bene Gesserit faction-specific actions.

Rulebook references:
  Basic  p.13 — Spiritual Advisors: whenever any other faction ships forces onto
                 Dune from off-planet, BG may ship 1 force FREE into the Polar Sink.
  Adv.   p.13 — Advisors: whenever any other faction ships, BG may ship 1 ADVISOR
                 for free into that SAME TERRITORY instead.

  Advisors (Advanced):
    - Flip fighters→advisors when another faction enters your territory (intrusion).
    - Flip advisors→fighters before Shipment phase when you want to battle.
    - Moving advisors into an UNOCCUPIED territory automatically flips them fighters.
    - Shipping into an UNOCCUPIED territory → must ship as fighters.

Entry points:
    trigger_bg_free_shipment(game_state, bg_player_id, as_advisor, territory, sector)
        Called after another faction ships. BG may ship 1 force for free.

    flip_advisors_to_fighters(game_state, bg_player_id, territory_name)
        BG flips all advisors in a territory to fighters before the battle.

    flip_fighters_to_advisors(game_state, bg_player_id, territory_name)
        BG flips fighters to advisors on intrusion (another faction enters).
"""

from __future__ import annotations

from ...models.faction import FactionName
from ...models.game_state import GameState
from ...models.player import ForceGroup, Player

POLAR_SINK = "Polar Sink"


def trigger_bg_free_shipment(
    game_state: GameState,
    bg_player_id: str,
    territory_name: str,
    sector: int,
    as_advisor: bool = False,
) -> GameState:
    """
    BG ships 1 force for free in response to another faction's shipment.

    Basic:  must go to Polar Sink; as_advisor ignored.
    Advanced:
      - May go to the SAME territory the triggering faction just shipped to, OR Polar Sink.
      - as_advisor=True only allowed when another faction has forces in that territory.
      - If destination is unoccupied, force is placed as a Fighter regardless of as_advisor.
    """
    player = _get_player(game_state, bg_player_id)

    if player.faction != FactionName.BENE_GESSERIT:
        raise ValueError("Only Bene Gesserit can use this ability")

    # Must be triggered by another faction's shipment
    if not game_state.bg_free_ship_pending:
        raise ValueError(
            "No pending free shipment — another faction must ship first to trigger this ability"
        )

    if player.forces_in_reserve <= 0:
        raise ValueError("No forces in reserve to ship")

    if territory_name not in game_state.territories:
        raise ValueError(f"Unknown territory: {territory_name}")

    # Territory-restriction checks (before sector validation for clearer errors)
    # Basic: can only ship to Polar Sink
    if game_state.mode.value != "advanced" and territory_name != POLAR_SINK:
        raise ValueError("Basic game: BG free shipment must go to the Polar Sink")

    # Advanced: can only ship to the triggering territory or Polar Sink
    if game_state.mode.value == "advanced" and territory_name != POLAR_SINK:
        allowed = game_state.bg_free_ship_last_territory
        if territory_name != allowed:
            raise ValueError(
                f"Advanced: BG may only free-ship to {allowed} (triggering territory) "
                "or the Polar Sink"
            )

    territory = game_state.territories[territory_name]
    if sector not in territory.sectors:
        raise ValueError(f"Sector {sector} is not part of {territory_name}")

    # Storm check — can't ship to a storm-blocked sand sector
    if (territory.is_sand and not territory.storm_exception
            and sector == game_state.storm_sector):
        raise ValueError("Cannot ship to a sector currently in the storm")

    # Advisor rule: may only ship as advisor if others are present in that territory
    is_advisor = False
    if game_state.mode.value == "advanced" and territory_name != POLAR_SINK:
        other_present = _others_present(game_state, territory_name, FactionName.BENE_GESSERIT)
        if as_advisor and not other_present:
            # Territory is unoccupied — must flip to fighter
            is_advisor = False
        elif as_advisor and other_present:
            is_advisor = True
        else:
            is_advisor = False  # explicitly shipping as fighter

    # Add the force to the board
    new_forces = list(player.forces_on_board)
    existing = _find_force_group(new_forces, territory_name, sector, is_advisor)

    if existing is not None:
        idx = new_forces.index(existing)
        new_forces[idx] = existing.model_copy(update={
            "regular_count": existing.regular_count + 1,
        })
    else:
        new_forces.append(ForceGroup(
            territory_name=territory_name,
            sector=sector,
            regular_count=1,
            is_advisor=is_advisor,
        ))

    updated_players = [
        p.model_copy(update={
            "forces_on_board": new_forces,
            "forces_in_reserve": p.forces_in_reserve - 1,
        }) if p.id == bg_player_id else p
        for p in game_state.players
    ]

    return game_state.model_copy(update={
        "players": updated_players,
        "bg_free_ship_pending": False,
        "bg_free_ship_last_territory": None,
    })


def flip_advisors_to_fighters(
    game_state: GameState,
    bg_player_id: str,
    territory_name: str,
) -> GameState:
    """
    Advanced: BG flips all advisors in territory_name to fighters.

    Used:
      - Before Shipment phase starts (announce intent to battle).
      - After moving advisors into an unoccupied territory.
      - Anytime BG wants to engage in combat.
    """
    player = _get_player(game_state, bg_player_id)

    if player.faction != FactionName.BENE_GESSERIT:
        raise ValueError("Only Bene Gesserit can flip advisors")

    if game_state.mode.value != "advanced":
        raise ValueError("Advisor mechanics only apply in Advanced mode")

    advisors = [
        fg for fg in player.forces_on_board
        if fg.territory_name == territory_name and fg.is_advisor
    ]
    if not advisors:
        raise ValueError(f"No advisors in {territory_name}")

    # Merge with any existing fighter stack in the same sectors
    new_forces: list[ForceGroup] = []
    flipped: dict[int, int] = {}  # sector -> count of advisors flipped

    for fg in player.forces_on_board:
        if fg.territory_name == territory_name and fg.is_advisor:
            flipped[fg.sector] = flipped.get(fg.sector, 0) + fg.regular_count
            # Drop the advisor group (will be merged into fighters below)
        else:
            new_forces.append(fg)

    # Add as fighters
    for sector, count in flipped.items():
        existing_fighter = _find_force_group(new_forces, territory_name, sector, is_advisor=False)
        if existing_fighter is not None:
            idx = new_forces.index(existing_fighter)
            new_forces[idx] = existing_fighter.model_copy(update={
                "regular_count": existing_fighter.regular_count + count,
            })
        else:
            new_forces.append(ForceGroup(
                territory_name=territory_name,
                sector=sector,
                regular_count=count,
                is_advisor=False,
            ))

    updated_players = [
        p.model_copy(update={"forces_on_board": new_forces})
        if p.id == bg_player_id else p
        for p in game_state.players
    ]

    return game_state.model_copy(update={"players": updated_players})


def flip_fighters_to_advisors(
    game_state: GameState,
    bg_player_id: str,
    territory_name: str,
) -> GameState:
    """
    Advanced: BG flips all fighters in territory_name to advisors.

    Used when another faction ships or moves into a territory where BG has fighters
    (intrusion rule — BG may choose to coexist peacefully as advisors instead of fighting).

    Advisors coexist with all factions and have no combat effect.
    """
    player = _get_player(game_state, bg_player_id)

    if player.faction != FactionName.BENE_GESSERIT:
        raise ValueError("Only Bene Gesserit can flip to advisors")

    if game_state.mode.value != "advanced":
        raise ValueError("Advisor mechanics only apply in Advanced mode")

    fighters = [
        fg for fg in player.forces_on_board
        if fg.territory_name == territory_name and not fg.is_advisor
        and (fg.regular_count + fg.special_count) > 0
    ]
    if not fighters:
        raise ValueError(f"No fighters in {territory_name}")

    new_forces: list[ForceGroup] = []
    flipped: dict[int, tuple[int, int]] = {}  # sector -> (regular, special)

    for fg in player.forces_on_board:
        if fg.territory_name == territory_name and not fg.is_advisor:
            prev = flipped.get(fg.sector, (0, 0))
            flipped[fg.sector] = (
                prev[0] + fg.regular_count,
                prev[1] + fg.special_count,
            )
            # Drop the fighter group
        else:
            new_forces.append(fg)

    # Add as advisors (special forces become regular advisors — BG advisors have no starred variant)
    for sector, (reg, spc) in flipped.items():
        total = reg + spc
        existing_adv = _find_force_group(new_forces, territory_name, sector, is_advisor=True)
        if existing_adv is not None:
            idx = new_forces.index(existing_adv)
            new_forces[idx] = existing_adv.model_copy(update={
                "regular_count": existing_adv.regular_count + total,
            })
        else:
            new_forces.append(ForceGroup(
                territory_name=territory_name,
                sector=sector,
                regular_count=total,
                is_advisor=True,
            ))

    updated_players = [
        p.model_copy(update={"forces_on_board": new_forces})
        if p.id == bg_player_id else p
        for p in game_state.players
    ]

    return game_state.model_copy(update={"players": updated_players})


# ---------------------------------------------------------------------------
# Internal helpers
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
    is_advisor: bool,
) -> ForceGroup | None:
    for fg in forces:
        if (fg.territory_name == territory
                and fg.sector == sector
                and fg.is_advisor == is_advisor):
            return fg
    return None


def _others_present(
    game_state: GameState,
    territory_name: str,
    own_faction: FactionName,
) -> bool:
    """Return True if any non-BG faction has forces (fighters) in territory_name."""
    for p in game_state.players:
        if p.faction == own_faction or p.is_eliminated:
            continue
        for fg in p.forces_on_board:
            if (fg.territory_name == territory_name
                    and not fg.is_advisor
                    and (fg.regular_count + fg.special_count) > 0):
                return True
    return False
