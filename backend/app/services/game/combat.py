"""
Battle Phase service for the Dune board game.

Rulebook reference: p.10–12 — "Battle"

Battles occur when two or more factions have forces in the same territory.
The aggressor (the player whose turn it is, going clockwise from the storm)
chooses which battle to fight first.

Each battle:
  1. Both players secretly commit a Battle Plan (forces dialed, leader, cards).
  2. Plans are revealed simultaneously.
  3. Traitor calls are checked.
  4. Weapon/defense matching determines leader kills.
  5. Lasgun/shield check (mutual annihilation).
  6. Battle totals are compared; loser's forces go to tanks.

Entry points:
    init_battles(game_state) -> GameState
    submit_battle_plan(game_state, player_id, plan) -> GameState
    resolve_battle(game_state) -> GameState
"""

from __future__ import annotations

from ...models.card import DefenseType, TreacheryCard, TreacheryCardType, WeaponType
from ...models.faction import FactionName
from ...models.game_state import ActiveBattle, BattlePlan, GamePhase, GameState
from ...models.leader import Leader, LeaderStatus
from ...models.player import ForceGroup, Player
from .handlers.registry import get_handler
from .phases import next_phase


def init_battles(game_state: GameState) -> GameState:
    """
    Find the first territory where a battle must occur and set up
    the ActiveBattle. If no battles exist, advance to the next phase.
    """
    battle = _find_next_battle(game_state)
    if battle is None:
        return game_state.model_copy(update={
            "current_phase": next_phase(GamePhase.BATTLE),
            "active_battle": None,
        })

    return game_state.model_copy(update={
        "active_battle": battle,
    })


def submit_battle_plan(
    game_state: GameState,
    player_id: str,
    forces_dialed: int,
    leader_id: str | None = None,
    weapon_card_id: str | None = None,
    defense_card_id: str | None = None,
    special_forces_dialed: int = 0,
) -> GameState:
    """
    Submit a battle plan for the active battle.
    Once both plans are submitted, the battle is resolved automatically.
    """
    ab = game_state.active_battle
    if ab is None:
        raise ValueError("No active battle")

    player = _get_player(game_state, player_id)

    # Determine if this player is attacker or defender
    if player.faction == ab.attacker_faction:
        if ab.attacker_plan is not None:
            raise ValueError("Attacker plan already submitted")
        role = "attacker"
    elif player.faction == ab.defender_faction:
        if ab.defender_plan is not None:
            raise ValueError("Defender plan already submitted")
        role = "defender"
    else:
        raise ValueError(f"{player.faction.value} is not part of this battle")

    # Validate forces dialed
    forces_in_territory = _count_forces_in_territory(
        player, ab.territory_name
    )
    if forces_dialed < 0 or forces_dialed > forces_in_territory:
        raise ValueError(
            f"Can dial 0-{forces_in_territory} forces, got {forces_dialed}"
        )

    # Validate special_forces_dialed
    special_in_territory = _count_special_forces_in_territory(
        player, ab.territory_name
    )
    if special_forces_dialed < 0 or special_forces_dialed > min(forces_dialed, special_in_territory):
        raise ValueError(
            f"Can dial 0-{min(forces_dialed, special_in_territory)} special forces, "
            f"got {special_forces_dialed}"
        )

    # Validate leader via faction handler (supports Harkonnen captured leaders + KH)
    leader = None
    is_kh = leader_id == "kwisatz_haderach"
    if leader_id and not is_kh:
        # Search this player's leaders and all players' leaders (for captured)
        leader = next((l for l in player.leaders if l.id == leader_id), None)
        if leader is None:
            # Check all players' leaders (Harkonnen can use captured leaders)
            for p in game_state.players:
                leader = next((l for l in p.leaders if l.id == leader_id), None)
                if leader is not None:
                    break
        if leader is None:
            raise ValueError(f"Leader not found: {leader_id}")
        handler = get_handler(player.faction)
        if not handler.can_use_leader(leader, player, game_state):
            raise ValueError(f"Leader {leader.name} cannot be used")

    # Validate Kwisatz Haderach
    if is_kh:
        from ...models.faction import FactionName as FN
        if player.faction != FN.ATREIDES:
            raise ValueError("Only Atreides can use the Kwisatz Haderach")
        if player.kwisatz_haderach is None or not player.kwisatz_haderach.is_active:
            raise ValueError("Kwisatz Haderach is not active")

    # Validate weapon/defense cards
    weapon_card = None
    defense_card = None
    if weapon_card_id:
        weapon_card = next(
            (c for c in player.treachery_hand if c.id == weapon_card_id),
            None
        )
        if weapon_card is None:
            raise ValueError(f"Card not found in hand: {weapon_card_id}")
        if weapon_card.card_type != TreacheryCardType.WEAPON:
            raise ValueError(f"{weapon_card.name} is not a weapon card")

    if defense_card_id:
        defense_card = next(
            (c for c in player.treachery_hand if c.id == defense_card_id),
            None
        )
        if defense_card is None:
            raise ValueError(f"Card not found in hand: {defense_card_id}")
        if defense_card.card_type != TreacheryCardType.DEFENSE:
            raise ValueError(f"{defense_card.name} is not a defense card")

    plan = BattlePlan(
        faction=player.faction,
        forces_dialed=forces_dialed,
        special_forces_dialed=special_forces_dialed,
        leader_id=leader_id,
        weapon_card=weapon_card,
        defense_card=defense_card,
    )

    # Update the active battle
    if role == "attacker":
        updated_ab = ab.model_copy(update={"attacker_plan": plan})
    else:
        updated_ab = ab.model_copy(update={"defender_plan": plan})

    game_state = game_state.model_copy(update={"active_battle": updated_ab})

    # If both plans submitted, resolve the battle
    if updated_ab.attacker_plan is not None and updated_ab.defender_plan is not None:
        return resolve_battle(game_state)

    return game_state


def resolve_battle(game_state: GameState) -> GameState:
    """
    Resolve the active battle after both plans are submitted.
    """
    ab = game_state.active_battle
    if ab is None or ab.attacker_plan is None or ab.defender_plan is None:
        raise ValueError("Battle plans not ready")

    atk_plan = ab.attacker_plan
    def_plan = ab.defender_plan

    attacker = _get_player_by_faction(game_state, ab.attacker_faction)
    defender = _get_player_by_faction(game_state, ab.defender_faction)

    # Check for traitor calls
    atk_traitor_called = _check_traitor(attacker, def_plan.leader_id, ab.defender_faction)
    def_traitor_called = _check_traitor(defender, atk_plan.leader_id, ab.attacker_faction)

    # If both call traitor, they cancel out (no effect)
    if atk_traitor_called and def_traitor_called:
        atk_traitor_called = False
        def_traitor_called = False

    # Check lasgun/shield explosion
    atk_has_lasgun = (
        atk_plan.weapon_card and
        atk_plan.weapon_card.weapon_type == WeaponType.LASGUN
    )
    def_has_shield = (
        def_plan.defense_card and
        def_plan.defense_card.defense_type == DefenseType.SHIELD
    )
    def_has_lasgun = (
        def_plan.weapon_card and
        def_plan.weapon_card.weapon_type == WeaponType.LASGUN
    )
    atk_has_shield = (
        atk_plan.defense_card and
        atk_plan.defense_card.defense_type == DefenseType.SHIELD
    )

    lasgun_explosion = (atk_has_lasgun and def_has_shield) or (def_has_lasgun and atk_has_shield)

    if lasgun_explosion:
        # Both sides are completely destroyed
        game_state = _destroy_all_forces(game_state, ab.territory_name, ab.attacker_faction)
        game_state = _destroy_all_forces(game_state, ab.territory_name, ab.defender_faction)
        game_state = _kill_leader_if_used(game_state, ab.attacker_faction, atk_plan.leader_id)
        game_state = _kill_leader_if_used(game_state, ab.defender_faction, def_plan.leader_id)
        game_state = _discard_battle_cards(game_state, ab.attacker_faction, atk_plan)
        game_state = _discard_battle_cards(game_state, ab.defender_faction, def_plan)
        return _after_battle(game_state)

    # Traitor resolution
    if atk_traitor_called:
        # Attacker called traitor on defender's leader - defender loses everything
        game_state = _destroy_all_forces(game_state, ab.territory_name, ab.defender_faction)
        game_state = _kill_leader_if_used(game_state, ab.defender_faction, def_plan.leader_id)
        game_state = _discard_battle_cards(game_state, ab.attacker_faction, atk_plan)
        game_state = _discard_battle_cards(game_state, ab.defender_faction, def_plan)
        return _after_battle(game_state)

    if def_traitor_called:
        # Defender called traitor on attacker's leader - attacker loses everything
        game_state = _destroy_all_forces(game_state, ab.territory_name, ab.attacker_faction)
        game_state = _kill_leader_if_used(game_state, ab.attacker_faction, atk_plan.leader_id)
        game_state = _discard_battle_cards(game_state, ab.attacker_faction, atk_plan)
        game_state = _discard_battle_cards(game_state, ab.defender_faction, def_plan)
        return _after_battle(game_state)

    # Calculate battle totals
    atk_total = _calculate_battle_total(
        game_state, atk_plan, ab.attacker_faction, ab.defender_faction
    )
    def_total = _calculate_battle_total(
        game_state, def_plan, ab.defender_faction, ab.attacker_faction
    )

    # Check weapon/defense - does the leader die?
    atk_leader_killed = _check_leader_killed(atk_plan, def_plan)
    def_leader_killed = _check_leader_killed(def_plan, atk_plan)

    # Determine winner (defender wins ties)
    if atk_total > def_total:
        winner_faction = ab.attacker_faction
        loser_faction = ab.defender_faction
        loser_plan = def_plan
        winner_plan = atk_plan
        winner_leader_killed = atk_leader_killed
        loser_leader_killed = def_leader_killed
    else:
        winner_faction = ab.defender_faction
        loser_faction = ab.attacker_faction
        loser_plan = atk_plan
        winner_plan = def_plan
        winner_leader_killed = def_leader_killed
        loser_leader_killed = atk_leader_killed

    # Loser loses ALL forces in the territory
    loser_forces_lost = _count_forces_in_territory(
        _get_player_by_faction(game_state, loser_faction), ab.territory_name
    )
    game_state = _destroy_all_forces(game_state, ab.territory_name, loser_faction)

    # Winner loses dialed forces
    game_state = _remove_dialed_forces(
        game_state, ab.territory_name, winner_faction, winner_plan.forces_dialed
    )

    # Handle leader kills — check for KH or Harkonnen capture
    if loser_leader_killed and loser_plan.leader_id:
        if loser_plan.leader_id == "kwisatz_haderach":
            game_state = _kill_kwisatz_haderach(game_state, loser_faction)
        else:
            # Let the winner's handler process the kill (Harkonnen may capture)
            winner_handler = get_handler(winner_faction)
            loser_player = _get_player_by_faction(game_state, loser_faction)
            killed_leader = next(
                (l for l in loser_player.leaders if l.id == loser_plan.leader_id), None
            )
            if killed_leader:
                game_state = winner_handler.on_leader_killed(
                    killed_leader, winner_faction, loser_player, game_state
                )
                # Check if the leader was captured (status changed to CAPTURED)
                updated_leader = _find_leader_by_id(game_state, loser_plan.leader_id)
                if updated_leader is None or updated_leader.status != LeaderStatus.CAPTURED:
                    # Not captured — send to tanks as normal
                    game_state = _kill_leader_if_used(game_state, loser_faction, loser_plan.leader_id)

    if winner_leader_killed and winner_plan.leader_id:
        if winner_plan.leader_id == "kwisatz_haderach":
            game_state = _kill_kwisatz_haderach(game_state, winner_faction)
        else:
            # Let the loser's handler process the kill (Harkonnen may capture)
            loser_handler = get_handler(loser_faction)
            winner_player = _get_player_by_faction(game_state, winner_faction)
            killed_leader = next(
                (l for l in winner_player.leaders if l.id == winner_plan.leader_id), None
            )
            if killed_leader:
                game_state = loser_handler.on_leader_killed(
                    killed_leader, loser_faction, winner_player, game_state
                )
                updated_leader = _find_leader_by_id(game_state, winner_plan.leader_id)
                if updated_leader is None or updated_leader.status != LeaderStatus.CAPTURED:
                    game_state = _kill_leader_if_used(game_state, winner_faction, winner_plan.leader_id)

    # Track force losses for faction handlers (e.g. Atreides KH activation)
    loser_handler = get_handler(loser_faction)
    loser_player_updated = _get_player_by_faction(game_state, loser_faction)
    game_state = loser_handler.on_battle_forces_lost(
        loser_forces_lost, loser_player_updated, game_state
    )

    winner_handler_for_losses = get_handler(winner_faction)
    winner_player_updated = _get_player_by_faction(game_state, winner_faction)
    game_state = winner_handler_for_losses.on_battle_forces_lost(
        winner_plan.forces_dialed, winner_player_updated, game_state
    )

    # Discard used treachery cards
    game_state = _discard_battle_cards(game_state, ab.attacker_faction, atk_plan)
    game_state = _discard_battle_cards(game_state, ab.defender_faction, def_plan)

    return _after_battle(game_state)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _after_battle(game_state: GameState) -> GameState:
    """After a battle resolves, check for more battles or advance phase."""
    # Clear the active battle
    game_state = game_state.model_copy(update={"active_battle": None})

    # Check for more battles
    next_battle = _find_next_battle(game_state)
    if next_battle is not None:
        return game_state.model_copy(update={"active_battle": next_battle})

    # No more battles - advance phase
    return game_state.model_copy(update={
        "current_phase": next_phase(GamePhase.BATTLE),
    })


def _find_next_battle(game_state: GameState) -> ActiveBattle | None:
    """
    Find the next territory where a battle needs to occur.
    A battle happens when 2+ non-allied factions have forces in the same territory.
    """
    # Build territory -> list of factions with forces
    territory_factions: dict[str, list[FactionName]] = {}

    for player in game_state.players:
        if player.is_eliminated:
            continue
        for fg in player.forces_on_board:
            # BG Advisors don't trigger or participate in battles
            if fg.is_advisor:
                continue
            total = (fg.regular_count or 0) + (fg.special_count or 0)
            if total > 0:
                key = fg.territory_name
                if key not in territory_factions:
                    territory_factions[key] = []
                if player.faction not in territory_factions[key]:
                    territory_factions[key].append(player.faction)

    # Find first territory with 2+ non-allied factions
    for terr_name, factions in territory_factions.items():
        if len(factions) < 2:
            continue

        # Check if any pair is not allied
        for i, f1 in enumerate(factions):
            for f2 in factions[i + 1:]:
                p1 = _get_player_by_faction(game_state, f1)
                p2 = _get_player_by_faction(game_state, f2)
                if p1.ally == f2:
                    continue  # Allied, no battle

                # Determine attacker/defender
                # The player earlier in turn order is the attacker
                p1_idx = next(i for i, p in enumerate(game_state.players) if p.faction == f1)
                p2_idx = next(i for i, p in enumerate(game_state.players) if p.faction == f2)

                if p1_idx < p2_idx:
                    attacker, defender = f1, f2
                else:
                    attacker, defender = f2, f1

                # Get a sector for this battle
                territory = game_state.territories.get(terr_name)
                sector = territory.sectors[0] if territory and territory.sectors else 0

                return ActiveBattle(
                    territory_name=terr_name,
                    sector=sector,
                    attacker_faction=attacker,
                    defender_faction=defender,
                )

    return None


def _calculate_battle_total(
    game_state: GameState,
    plan: BattlePlan,
    own_faction: FactionName,
    opponent_faction: FactionName,
) -> int:
    """
    Calculate total battle strength:
    regular_forces + (special_forces * special_strength) + leader + spice
    """
    # Special forces (Sardaukar / Fedaykin) may count as more than 1 each
    regular_dialed = plan.forces_dialed - plan.special_forces_dialed
    handler = get_handler(own_faction)
    special_strength = handler.get_special_force_strength(opponent_faction, game_state)
    total = regular_dialed + (plan.special_forces_dialed * special_strength)

    if plan.leader_id:
        if plan.leader_id == "kwisatz_haderach":
            # KH provides +2 bonus strength
            total += 2
        else:
            player = _get_player_by_faction(game_state, own_faction)
            leader = next((l for l in player.leaders if l.id == plan.leader_id), None)
            if leader:
                total += leader.strength

    total += plan.spice_to_expend

    return total


def _check_leader_killed(
    victim_plan: BattlePlan,
    attacker_plan: BattlePlan,
) -> bool:
    """
    Check if the victim's leader is killed by the attacker's weapon.
    A leader is killed if the attacker has a weapon and the victim
    doesn't have the matching defense.
    """
    if not victim_plan.leader_id:
        return False

    weapon = attacker_plan.weapon_card
    if weapon is None:
        return False

    defense = victim_plan.defense_card

    if weapon.weapon_type == WeaponType.LASGUN:
        return True  # Lasgun always kills (but explosion handled separately)

    if weapon.weapon_type == WeaponType.POISON:
        # Blocked by Snooper
        if defense and defense.defense_type == DefenseType.SNOOPER:
            return False
        return True

    if weapon.weapon_type == WeaponType.PROJECTILE:
        # Blocked by Shield
        if defense and defense.defense_type == DefenseType.SHIELD:
            return False
        return True

    return False


def _check_traitor(
    caller: Player,
    opponent_leader_id: str | None,
    opponent_faction: FactionName,
) -> bool:
    """Check if caller has a traitor card matching the opponent's leader."""
    if not opponent_leader_id:
        return False
    # Kwisatz Haderach cannot be called as a traitor
    if opponent_leader_id == "kwisatz_haderach":
        return False
    return any(
        tc.leader_id == opponent_leader_id
        for tc in caller.traitor_cards
    )


def _destroy_all_forces(
    game_state: GameState,
    territory_name: str,
    faction: FactionName,
) -> GameState:
    """Remove all of a faction's forces from a territory, sending them to tanks."""
    player = _get_player_by_faction(game_state, faction)
    surviving = []
    regular_killed = 0
    special_killed = 0

    for fg in player.forces_on_board:
        if fg.territory_name == territory_name:
            regular_killed += fg.regular_count
            special_killed += fg.special_count
        else:
            surviving.append(fg)

    updated_players = []
    for p in game_state.players:
        if p.faction == faction:
            updated_players.append(p.model_copy(update={
                "forces_on_board": surviving,
                "forces_in_tanks": p.forces_in_tanks + regular_killed,
                "special_forces_in_tanks": p.special_forces_in_tanks + special_killed,
            }))
        else:
            updated_players.append(p)

    return game_state.model_copy(update={"players": updated_players})


def _remove_dialed_forces(
    game_state: GameState,
    territory_name: str,
    faction: FactionName,
    dialed: int,
) -> GameState:
    """Remove dialed forces from a faction's forces in a territory."""
    if dialed <= 0:
        return game_state

    player = _get_player_by_faction(game_state, faction)
    new_forces = list(player.forces_on_board)
    remaining_to_remove = dialed
    regular_killed = 0
    special_killed = 0

    for i, fg in enumerate(new_forces):
        if fg.territory_name != territory_name or remaining_to_remove <= 0:
            continue

        # Remove regular forces first
        reg_remove = min(fg.regular_count, remaining_to_remove)
        remaining_to_remove -= reg_remove
        regular_killed += reg_remove

        # Then special forces
        spec_remove = min(fg.special_count, remaining_to_remove)
        remaining_to_remove -= spec_remove
        special_killed += spec_remove

        new_reg = fg.regular_count - reg_remove
        new_spec = fg.special_count - spec_remove

        if new_reg == 0 and new_spec == 0:
            new_forces[i] = None  # Mark for removal
        else:
            new_forces[i] = fg.model_copy(update={
                "regular_count": new_reg,
                "special_count": new_spec,
            })

    new_forces = [fg for fg in new_forces if fg is not None]

    updated_players = []
    for p in game_state.players:
        if p.faction == faction:
            updated_players.append(p.model_copy(update={
                "forces_on_board": new_forces,
                "forces_in_tanks": p.forces_in_tanks + regular_killed,
                "special_forces_in_tanks": p.special_forces_in_tanks + special_killed,
            }))
        else:
            updated_players.append(p)

    return game_state.model_copy(update={"players": updated_players})


def _kill_leader_if_used(
    game_state: GameState,
    faction: FactionName,
    leader_id: str | None,
) -> GameState:
    """Set a leader's status to IN_TANKS if they were used in battle."""
    if not leader_id:
        return game_state

    updated_players = []
    for p in game_state.players:
        if p.faction == faction:
            updated_leaders = []
            for l in p.leaders:
                if l.id == leader_id:
                    updated_leaders.append(l.model_copy(update={
                        "status": LeaderStatus.IN_TANKS,
                    }))
                else:
                    updated_leaders.append(l)
            updated_players.append(p.model_copy(update={"leaders": updated_leaders}))
        else:
            updated_players.append(p)

    return game_state.model_copy(update={"players": updated_players})


def _discard_battle_cards(
    game_state: GameState,
    faction: FactionName,
    plan: BattlePlan,
) -> GameState:
    """Remove used weapon/defense cards from player's hand and add to discard."""
    cards_to_discard: list[TreacheryCard] = []
    card_ids_to_remove: set[str] = set()

    if plan.weapon_card:
        cards_to_discard.append(plan.weapon_card)
        card_ids_to_remove.add(plan.weapon_card.id)
    if plan.defense_card:
        cards_to_discard.append(plan.defense_card)
        card_ids_to_remove.add(plan.defense_card.id)

    if not card_ids_to_remove:
        return game_state

    updated_players = []
    for p in game_state.players:
        if p.faction == faction:
            new_hand = [c for c in p.treachery_hand if c.id not in card_ids_to_remove]
            updated_players.append(p.model_copy(update={"treachery_hand": new_hand}))
        else:
            updated_players.append(p)

    return game_state.model_copy(update={
        "players": updated_players,
        "treachery_discard": list(game_state.treachery_discard) + cards_to_discard,
    })


def _count_forces_in_territory(player: Player, territory_name: str) -> int:
    """Count total forces a player has in a territory."""
    total = 0
    for fg in player.forces_on_board:
        if fg.territory_name == territory_name:
            total += (fg.regular_count or 0) + (fg.special_count or 0)
    return total


def _count_special_forces_in_territory(player: Player, territory_name: str) -> int:
    """Count special forces a player has in a territory."""
    total = 0
    for fg in player.forces_on_board:
        if fg.territory_name == territory_name:
            total += fg.special_count or 0
    return total


def _find_leader_by_id(game_state: GameState, leader_id: str) -> Leader | None:
    """Find a leader by ID across all players."""
    for p in game_state.players:
        for l in p.leaders:
            if l.id == leader_id:
                return l
    return None


def _get_player(game_state: GameState, player_id: str) -> Player:
    for player in game_state.players:
        if player.id == player_id:
            return player
    raise ValueError(f"Player not found: {player_id}")


def _get_player_by_faction(game_state: GameState, faction: FactionName) -> Player:
    for player in game_state.players:
        if player.faction == faction:
            return player
    raise ValueError(f"No player with faction: {faction.value}")
