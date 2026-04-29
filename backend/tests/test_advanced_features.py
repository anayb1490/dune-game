"""
Tests for advanced game features:
  - Double Spice Blow (Advanced Phase 2)
  - Increased Spice Flow (Advanced Spice Collection)
  - Advisor exclusion from spice collection
  - Advanced Combat: spice-supported forces (half-strength)
  - Advanced Combat: KH +2 suppressed when leader killed
  - Advanced Combat: spice deducted post-battle
  - Advanced Combat: spice_to_expend validation
  - Fremen sandworm riding
"""

from __future__ import annotations

import pytest

from ..app.models.card import SpiceCard, SpiceCardType
from ..app.models.faction import FactionName
from ..app.models.game_state import (
    ActiveBattle,
    BattlePlan,
    GameMode,
    GamePhase,
    GameState,
)
from ..app.models.player import ForceGroup, Player
from ..app.services.game.fremen_actions import (
    fremen_sandworm_ride,
    fremen_skip_sandworm_ride,
)
from ..app.services.game.spice import (
    apply_spice_collection_effects,
    resolve_spice_blow,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _spice_card(card_id: str, territory: str, amount: int) -> SpiceCard:
    return SpiceCard(
        id=card_id,
        name=territory,
        card_type=SpiceCardType.TERRITORY,
        territory_name=territory,
        spice_amount=amount,
    )


def _worm_card(card_id: str = "worm1") -> SpiceCard:
    return SpiceCard(
        id=card_id,
        name="Shai-Hulud",
        card_type=SpiceCardType.SHAI_HULUD,
        territory_name="ignored",
        spice_amount=1,
    )


def _make_player(
    pid: str,
    faction: FactionName,
    spice: int = 10,
    forces_on_board: list | None = None,
    forces_in_reserve: int = 10,
) -> Player:
    return Player(
        id=pid,
        name=faction.value,
        faction=faction,
        spice=spice,
        forces_on_board=forces_on_board or [],
        forces_in_reserve=forces_in_reserve,
    )


def _base_game(
    players: list[Player],
    mode: GameMode = GameMode.ADVANCED,
    storm_sector: int = 5,
    phase: GamePhase = GamePhase.SPICE_BLOW,
) -> GameState:
    from ..app.data.territories import TERRITORIES
    territories = {n: t.model_copy() for n, t in TERRITORIES.items()}
    return GameState(
        id="test",
        mode=mode,
        players=players,
        current_phase=phase,
        current_player_index=0,
        storm_sector=storm_sector,
        territories=territories,
        spice_bank=100,
        current_turn=2,  # Turn 2+ so Shai-Hulud triggers Nexus
    )


# ===========================================================================
# Double Spice Blow (Advanced)
# ===========================================================================

class TestDoubleSpiceBlow:
    def test_advanced_draws_two_cards(self):
        """Advanced mode draws two territory cards."""
        card_a = _spice_card("a", "Hagga Basin", 4)
        card_b = _spice_card("b", "Cielago North", 3)
        game = _base_game([_make_player("p1", FactionName.ATREIDES)])
        game = game.model_copy(update={"spice_deck": [card_a, card_b], "current_turn": 1})

        result = resolve_spice_blow(game)
        assert result.territories["Hagga Basin"].current_spice == 4
        assert result.territories["Cielago North"].current_spice == 3

    def test_advanced_uses_separate_ab_discards(self):
        """Cards go into separate A and B discard piles."""
        card_a = _spice_card("a", "Hagga Basin", 4)
        card_b = _spice_card("b", "Cielago North", 3)
        game = _base_game([_make_player("p1", FactionName.ATREIDES)])
        game = game.model_copy(update={"spice_deck": [card_a, card_b], "current_turn": 1})

        result = resolve_spice_blow(game)
        assert len(result.spice_discard_a) == 1
        assert len(result.spice_discard_b) == 1
        assert result.spice_discard_a[0].id == "a"
        assert result.spice_discard_b[0].id == "b"

    def test_basic_draws_one_card(self):
        """Basic mode still draws only one card."""
        card_a = _spice_card("a", "Hagga Basin", 4)
        card_b = _spice_card("b", "Cielago North", 3)
        game = _base_game(
            [_make_player("p1", FactionName.ATREIDES)],
            mode=GameMode.BASIC,
        )
        game = game.model_copy(update={"spice_deck": [card_a, card_b], "current_turn": 1})

        result = resolve_spice_blow(game)
        assert result.territories["Hagga Basin"].current_spice == 4
        assert result.territories["Cielago North"].current_spice == 0  # not drawn

    def test_advanced_worm_in_first_draw_triggers_nexus(self):
        """Shai-Hulud in first draw triggers nexus."""
        prev = _spice_card("prev", "Hagga Basin", 4)
        worm = _worm_card()
        next_terr = _spice_card("next", "Cielago North", 2)
        second = _spice_card("second", "Red Chasm", 3)

        game = _base_game([_make_player("p1", FactionName.ATREIDES)])
        # Pre-populate discard_a so worm has a territory to attack
        game = game.model_copy(update={
            "spice_deck": [worm, next_terr, second],
            "spice_discard_a": [prev],
        })

        result = resolve_spice_blow(game)
        assert result.nexus_triggered is True
        # Worm attacks last territory in pile A = Hagga Basin
        assert result.fremen_sandworm_ride_territory == "Hagga Basin"

    def test_advanced_worm_attacks_correct_discard_pile_territory(self):
        """Worm in pile A attacks last territory in pile A, not pile B."""
        pile_a_prev = _spice_card("prev_a", "Hagga Basin", 4)
        pile_b_prev = _spice_card("prev_b", "Red Chasm", 3)

        worm = _worm_card()
        after_worm = _spice_card("aw", "Cielago North", 2)
        second_draw = _spice_card("sd", "Sihaya Ridge", 1)

        game = _base_game([_make_player("p1", FactionName.ATREIDES)])
        # Place spice on Hagga Basin to verify it gets destroyed
        terrs = dict(game.territories)
        terrs["Hagga Basin"] = terrs["Hagga Basin"].model_copy(update={"current_spice": 5})
        game = game.model_copy(update={
            "territories": terrs,
            "spice_deck": [worm, after_worm, second_draw],
            "spice_discard_a": [pile_a_prev],
            "spice_discard_b": [pile_b_prev],
        })

        result = resolve_spice_blow(game)
        # Worm (pile A draw) attacks Hagga Basin (last territory in pile A)
        assert result.territories["Hagga Basin"].current_spice == 0
        # Red Chasm (in pile B) not attacked by pile A worm
        assert result.territories["Red Chasm"].current_spice == 0  # was 0 to start

    def test_advanced_only_one_card_if_deck_has_one(self):
        """If only one card in deck, second draw is skipped gracefully."""
        card = _spice_card("a", "Hagga Basin", 4)
        game = _base_game([_make_player("p1", FactionName.ATREIDES)])
        game = game.model_copy(update={"spice_deck": [card], "current_turn": 1})

        result = resolve_spice_blow(game)
        assert result.territories["Hagga Basin"].current_spice == 4
        # Only pile A filled
        assert len(result.spice_discard_a) == 1
        assert len(result.spice_discard_b) == 0


# ===========================================================================
# Increased Spice Flow (Advanced)
# ===========================================================================

class TestIncreasedSpiceFlow:
    def _game_with_forces_at(self, faction, territory, sector, mode=GameMode.ADVANCED):
        player = _make_player(
            "p1", faction,
            forces_on_board=[ForceGroup(
                territory_name=territory, sector=sector, regular_count=2
            )],
        )
        return _base_game([player], mode=mode, phase=GamePhase.SPICE_COLLECTION)

    def test_arrakeen_occupant_gets_2_bonus(self):
        game = self._game_with_forces_at(FactionName.ATREIDES, "Arrakeen", 1)
        result = apply_spice_collection_effects(game)
        p = next(p for p in result.players if p.faction == FactionName.ATREIDES)
        # Base spice 10 + 2 bonus
        assert p.spice == 12

    def test_carthag_occupant_gets_2_bonus(self):
        game = self._game_with_forces_at(FactionName.HARKONNEN, "Carthag", 17)
        result = apply_spice_collection_effects(game)
        p = next(p for p in result.players if p.faction == FactionName.HARKONNEN)
        assert p.spice == 12

    def test_tueks_sietch_occupant_gets_1_bonus(self):
        game = self._game_with_forces_at(FactionName.SPACING_GUILD, "Tuek's Sietch", 13)
        result = apply_spice_collection_effects(game)
        p = next(p for p in result.players if p.faction == FactionName.SPACING_GUILD)
        assert p.spice == 11

    def test_no_increased_flow_in_basic_mode(self):
        game = self._game_with_forces_at(FactionName.ATREIDES, "Arrakeen", 1, mode=GameMode.BASIC)
        result = apply_spice_collection_effects(game)
        p = next(p for p in result.players if p.faction == FactionName.ATREIDES)
        assert p.spice == 10  # No bonus

    def test_both_arrakeen_and_carthag_stacks(self):
        """Player in both Arrakeen and Carthag gets 4 total bonus."""
        player = _make_player(
            "p1", FactionName.ATREIDES,
            forces_on_board=[
                ForceGroup(territory_name="Arrakeen", sector=1, regular_count=1),
                ForceGroup(territory_name="Carthag", sector=17, regular_count=1),
            ],
        )
        game = _base_game([player], phase=GamePhase.SPICE_COLLECTION)
        result = apply_spice_collection_effects(game)
        p = next(p for p in result.players if p.faction == FactionName.ATREIDES)
        assert p.spice == 14  # 10 + 2 + 2

    def test_spice_bank_reduced_by_flow_bonus(self):
        game = self._game_with_forces_at(FactionName.ATREIDES, "Arrakeen", 1)
        result = apply_spice_collection_effects(game)
        assert result.spice_bank == 98  # 100 - 2

    def test_advisors_excluded_from_increased_flow(self):
        """BG advisors at Arrakeen do NOT receive the Increased Spice Flow bonus."""
        player = _make_player(
            "bg1", FactionName.BENE_GESSERIT,
            forces_on_board=[
                ForceGroup(
                    territory_name="Arrakeen", sector=1,
                    regular_count=1, is_advisor=True
                )
            ],
        )
        game = _base_game([player], phase=GamePhase.SPICE_COLLECTION)
        result = apply_spice_collection_effects(game)
        p = next(p for p in result.players if p.faction == FactionName.BENE_GESSERIT)
        assert p.spice == 10  # No bonus


# ===========================================================================
# Advisor exclusion from standard spice collection
# ===========================================================================

class TestAdvisorSpiceExclusion:
    def test_advisors_do_not_collect_territory_spice(self):
        """BG advisors in a spice territory collect nothing."""
        player = _make_player(
            "bg1", FactionName.BENE_GESSERIT,
            forces_on_board=[
                ForceGroup(territory_name="Hagga Basin", sector=4, regular_count=2, is_advisor=True)
            ],
        )
        game = _base_game([player], phase=GamePhase.SPICE_COLLECTION)
        terrs = dict(game.territories)
        terrs["Hagga Basin"] = terrs["Hagga Basin"].model_copy(update={"current_spice": 8})
        game = game.model_copy(update={"territories": terrs})

        result = apply_spice_collection_effects(game)
        p = next(p for p in result.players if p.faction == FactionName.BENE_GESSERIT)
        # Spice still on territory (advisors didn't collect)
        assert result.territories["Hagga Basin"].current_spice == 8
        assert p.spice == 10

    def test_fighters_do_collect_territory_spice(self):
        """BG fighters (not advisors) collect normally."""
        player = _make_player(
            "bg1", FactionName.BENE_GESSERIT,
            forces_on_board=[
                ForceGroup(territory_name="Hagga Basin", sector=4, regular_count=2, is_advisor=False)
            ],
        )
        game = _base_game([player], phase=GamePhase.SPICE_COLLECTION)
        terrs = dict(game.territories)
        terrs["Hagga Basin"] = terrs["Hagga Basin"].model_copy(update={"current_spice": 8})
        game = game.model_copy(update={"territories": terrs})

        result = apply_spice_collection_effects(game)
        p = next(p for p in result.players if p.faction == FactionName.BENE_GESSERIT)
        assert p.spice == 14  # 10 + 2*2


# ===========================================================================
# Advanced Combat: spice-supported forces
# ===========================================================================

def _combat_game(
    attacker_faction: FactionName,
    defender_faction: FactionName,
    territory: str = "Arrakeen",
    sector: int = 1,
    mode: GameMode = GameMode.ADVANCED,
) -> GameState:
    from ..app.data.territories import TERRITORIES
    atk_player = _make_player(
        "atk", attacker_faction, spice=10,
        forces_on_board=[ForceGroup(territory_name=territory, sector=sector, regular_count=5)],
    )
    def_player = _make_player(
        "def", defender_faction, spice=10,
        forces_on_board=[ForceGroup(territory_name=territory, sector=sector, regular_count=5)],
    )
    territories = {n: t.model_copy() for n, t in TERRITORIES.items()}
    return GameState(
        id="test",
        mode=mode,
        players=[atk_player, def_player],
        current_phase=GamePhase.BATTLE,
        current_player_index=0,
        storm_sector=5,
        territories=territories,
        spice_bank=50,
        active_battle=ActiveBattle(
            territory_name=territory,
            sector=sector,
            attacker_faction=attacker_faction,
            defender_faction=defender_faction,
            attacker_prebattle_done=True,
            defender_prebattle_done=True,
        ),
    )


class TestAdvancedCombatSpiceSupport:
    def test_full_support_counts_full_strength(self):
        """5 forces + 5 spice = 5 total force strength."""
        from ..app.services.game.combat import _calculate_battle_total
        game = _combat_game(FactionName.ATREIDES, FactionName.HARKONNEN)
        plan = BattlePlan(faction=FactionName.ATREIDES, forces_dialed=5, spice_to_expend=5)
        total = _calculate_battle_total(game, plan, FactionName.ATREIDES, FactionName.HARKONNEN)
        assert total == 5.0

    def test_no_support_counts_half_strength(self):
        """5 forces + 0 spice = 2.5 total force strength."""
        from ..app.services.game.combat import _calculate_battle_total
        game = _combat_game(FactionName.ATREIDES, FactionName.HARKONNEN)
        plan = BattlePlan(faction=FactionName.ATREIDES, forces_dialed=5, spice_to_expend=0)
        total = _calculate_battle_total(game, plan, FactionName.ATREIDES, FactionName.HARKONNEN)
        assert total == 2.5

    def test_partial_support_mixed_strength(self):
        """4 forces + 2 spice = 2 full + 2 half = 3.0 total."""
        from ..app.services.game.combat import _calculate_battle_total
        game = _combat_game(FactionName.ATREIDES, FactionName.HARKONNEN)
        plan = BattlePlan(faction=FactionName.ATREIDES, forces_dialed=4, spice_to_expend=2)
        total = _calculate_battle_total(game, plan, FactionName.ATREIDES, FactionName.HARKONNEN)
        assert total == 3.0

    def test_fremen_forces_always_full_strength(self):
        """Fremen: 5 forces + 0 spice = 5.0 (exempt from half-strength rule)."""
        from ..app.services.game.combat import _calculate_battle_total
        game = _combat_game(FactionName.FREMEN, FactionName.HARKONNEN)
        plan = BattlePlan(faction=FactionName.FREMEN, forces_dialed=5, spice_to_expend=0)
        total = _calculate_battle_total(game, plan, FactionName.FREMEN, FactionName.HARKONNEN)
        assert total == 5.0

    def test_basic_mode_forces_always_full_strength(self):
        """Basic mode: all forces count at full regardless of spice."""
        from ..app.services.game.combat import _calculate_battle_total
        game = _combat_game(FactionName.ATREIDES, FactionName.HARKONNEN, mode=GameMode.BASIC)
        plan = BattlePlan(faction=FactionName.ATREIDES, forces_dialed=4, spice_to_expend=0)
        total = _calculate_battle_total(game, plan, FactionName.ATREIDES, FactionName.HARKONNEN)
        assert total == 4.0

    def test_spice_to_expend_exceeds_forces_raises(self):
        """Cannot expend more spice than forces dialed."""
        from ..app.services.game.combat import submit_battle_plan
        game = _combat_game(FactionName.ATREIDES, FactionName.HARKONNEN)
        with pytest.raises(ValueError, match="Cannot expend more spice"):
            submit_battle_plan(game, "atk", forces_dialed=3, spice_to_expend=5)

    def test_spice_to_expend_exceeds_holding_raises(self):
        """Cannot expend more spice than player holds."""
        from ..app.services.game.combat import submit_battle_plan
        game = _combat_game(FactionName.ATREIDES, FactionName.HARKONNEN)
        # Give attacker only 2 spice
        updated = game.model_copy(update={
            "players": [
                game.players[0].model_copy(update={"spice": 2}),
                game.players[1],
            ]
        })
        with pytest.raises(ValueError, match="Not enough spice"):
            submit_battle_plan(updated, "atk", forces_dialed=3, spice_to_expend=3)

    def test_spice_deducted_from_both_after_battle(self):
        """Win or lose, both players pay their expended spice."""
        from ..app.services.game.combat import submit_battle_plan, declare_traitor
        game = _combat_game(FactionName.ATREIDES, FactionName.HARKONNEN)
        # Attacker expends 3 spice, defender 1 spice
        game = submit_battle_plan(game, "atk", forces_dialed=5, spice_to_expend=3)
        game = submit_battle_plan(game, "def", forces_dialed=2, spice_to_expend=1)
        game = declare_traitor(game, "atk", False)
        game = declare_traitor(game, "def", False)

        atk = next(p for p in game.players if p.id == "atk")
        def_ = next(p for p in game.players if p.id == "def")
        assert atk.spice == 7   # 10 - 3
        assert def_.spice == 9  # 10 - 1

    def test_spice_goes_to_bank_after_battle(self):
        """Expended spice flows into the Spice Bank."""
        from ..app.services.game.combat import submit_battle_plan, declare_traitor
        game = _combat_game(FactionName.ATREIDES, FactionName.HARKONNEN)
        game = submit_battle_plan(game, "atk", forces_dialed=3, spice_to_expend=2)
        game = submit_battle_plan(game, "def", forces_dialed=3, spice_to_expend=1)
        game = declare_traitor(game, "atk", False)
        game = declare_traitor(game, "def", False)
        assert game.spice_bank == 53  # 50 + 2 + 1


# ===========================================================================
# Advanced Combat: KH +2 gating
# ===========================================================================

class TestKHBonusGating:
    def _kh_game(self):
        from ..app.models.player import KwisatzHaderach
        from ..app.models.leader import Leader, LeaderStatus
        atreides = _make_player("atk", FactionName.ATREIDES, spice=10,
            forces_on_board=[ForceGroup(territory_name="Arrakeen", sector=1, regular_count=3)])
        atreides = atreides.model_copy(update={
            "kwisatz_haderach": KwisatzHaderach(is_active=True, force_losses_accumulated=7),
        })
        harkonnen = _make_player("def", FactionName.HARKONNEN, spice=10,
            forces_on_board=[ForceGroup(territory_name="Arrakeen", sector=1, regular_count=3)])
        from ..app.data.territories import TERRITORIES
        territories = {n: t.model_copy() for n, t in TERRITORIES.items()}
        return GameState(
            id="test", mode=GameMode.ADVANCED,
            players=[atreides, harkonnen],
            current_phase=GamePhase.BATTLE,
            current_player_index=0, storm_sector=5,
            territories=territories, spice_bank=50,
            active_battle=ActiveBattle(
                territory_name="Arrakeen", sector=1,
                attacker_faction=FactionName.ATREIDES,
                defender_faction=FactionName.HARKONNEN,
                attacker_prebattle_done=True, defender_prebattle_done=True,
            ),
        )

    def test_kh_adds_2_when_leader_survives(self):
        from ..app.services.game.combat import _calculate_battle_total
        game = self._kh_game()
        plan = BattlePlan(
            faction=FactionName.ATREIDES,
            forces_dialed=3, spice_to_expend=3,
            leader_id="kwisatz_haderach",
        )
        # leader_killed=False → +2 applied
        total = _calculate_battle_total(
            game, plan, FactionName.ATREIDES, FactionName.HARKONNEN,
            leader_killed=False,
        )
        assert total == 5.0  # 3 forces (full) + 2 KH

    def test_kh_bonus_suppressed_when_leader_killed(self):
        from ..app.services.game.combat import _calculate_battle_total
        game = self._kh_game()
        plan = BattlePlan(
            faction=FactionName.ATREIDES,
            forces_dialed=3, spice_to_expend=3,
            leader_id="kwisatz_haderach",
        )
        # leader_killed=True → +2 NOT applied
        total = _calculate_battle_total(
            game, plan, FactionName.ATREIDES, FactionName.HARKONNEN,
            leader_killed=True,
        )
        assert total == 3.0  # Only forces, no KH

    def test_kh_zero_forces_raises(self):
        from ..app.services.game.combat import submit_battle_plan
        game = self._kh_game()
        with pytest.raises(ValueError, match="zero forces"):
            submit_battle_plan(game, "atk", forces_dialed=0, leader_id="kwisatz_haderach")


# ===========================================================================
# Fremen sandworm riding
# ===========================================================================

class TestFremenSandwormRide:
    def _ride_game(self, ride_territory="Hagga Basin"):
        from ..app.data.territories import TERRITORIES
        # Hagga Basin sectors: [12, 13]; Cielago North: [9, 10]
        fremen = _make_player(
            "f1", FactionName.FREMEN, spice=3,
            forces_on_board=[
                ForceGroup(territory_name=ride_territory, sector=12, regular_count=4, special_count=1),
            ],
        )
        territories = {n: t.model_copy() for n, t in TERRITORIES.items()}
        return GameState(
            id="test", mode=GameMode.ADVANCED,
            players=[fremen],
            current_phase=GamePhase.SPICE_BLOW,
            current_player_index=0, storm_sector=0,
            territories=territories, spice_bank=50,
            fremen_sandworm_ride_territory=ride_territory,
        )

    def test_fremen_can_ride_to_another_territory(self):
        game = self._ride_game()
        result = fremen_sandworm_ride(game, "f1", "Cielago North", 9, regular_count=2)
        fremen = next(p for p in result.players if p.id == "f1")
        at_dest = sum(fg.regular_count for fg in fremen.forces_on_board if fg.territory_name == "Cielago North")
        assert at_dest == 2

    def test_ride_consumes_ride_flag(self):
        game = self._ride_game()
        result = fremen_sandworm_ride(game, "f1", "Cielago North", 9, regular_count=2)
        assert result.fremen_sandworm_ride_territory is None

    def test_ride_removes_forces_from_source(self):
        game = self._ride_game()
        result = fremen_sandworm_ride(game, "f1", "Cielago North", 9, regular_count=3)
        fremen = next(p for p in result.players if p.id == "f1")
        at_source = sum(fg.regular_count for fg in fremen.forces_on_board if fg.territory_name == "Hagga Basin")
        assert at_source == 1  # 4 - 3

    def test_ride_special_forces(self):
        game = self._ride_game()
        result = fremen_sandworm_ride(game, "f1", "Cielago North", 9, special_count=1)
        fremen = next(p for p in result.players if p.id == "f1")
        spec_dest = sum(fg.special_count for fg in fremen.forces_on_board if fg.territory_name == "Cielago North")
        assert spec_dest == 1

    def test_ride_cannot_go_to_same_territory(self):
        game = self._ride_game()
        with pytest.raises(ValueError, match="different territory"):
            fremen_sandworm_ride(game, "f1", "Hagga Basin", 12, regular_count=1)

    def test_ride_blocked_by_storm(self):
        game = self._ride_game()
        # Set storm to cover Cielago North sector 9
        game = game.model_copy(update={"storm_sector": 9})
        with pytest.raises(ValueError, match="storm"):
            fremen_sandworm_ride(game, "f1", "Cielago North", 9, regular_count=1)

    def test_ride_no_ride_pending_raises(self):
        game = self._ride_game()
        game = game.model_copy(update={"fremen_sandworm_ride_territory": None})
        with pytest.raises(ValueError, match="No sandworm ride"):
            fremen_sandworm_ride(game, "f1", "Cielago North", 5, regular_count=1)

    def test_ride_non_fremen_raises(self):
        atreides = _make_player("a1", FactionName.ATREIDES)
        from ..app.data.territories import TERRITORIES
        territories = {n: t.model_copy() for n, t in TERRITORIES.items()}
        game = GameState(
            id="test", mode=GameMode.ADVANCED,
            players=[atreides],
            current_phase=GamePhase.SPICE_BLOW,
            current_player_index=0, storm_sector=0,
            territories=territories, spice_bank=50,
            fremen_sandworm_ride_territory="Hagga Basin",
        )
        with pytest.raises(ValueError, match="Fremen"):
            fremen_sandworm_ride(game, "a1", "Cielago North", 5, regular_count=1)

    def test_ride_blocked_by_enemies(self):
        from ..app.data.territories import TERRITORIES
        fremen = _make_player(
            "f1", FactionName.FREMEN, spice=3,
            forces_on_board=[ForceGroup(territory_name="Hagga Basin", sector=12, regular_count=3)],
        )
        harkonnen = _make_player(
            "h1", FactionName.HARKONNEN,
            forces_on_board=[ForceGroup(territory_name="Cielago North", sector=9, regular_count=2)],
        )
        territories = {n: t.model_copy() for n, t in TERRITORIES.items()}
        game = GameState(
            id="test", mode=GameMode.ADVANCED,
            players=[fremen, harkonnen],
            current_phase=GamePhase.SPICE_BLOW,
            current_player_index=0, storm_sector=0,
            territories=territories, spice_bank=50,
            fremen_sandworm_ride_territory="Hagga Basin",
        )
        with pytest.raises(ValueError, match="occupied"):
            fremen_sandworm_ride(game, "f1", "Cielago North", 9, regular_count=1)

    def test_skip_sandworm_ride_clears_flag(self):
        game = self._ride_game()
        result = fremen_skip_sandworm_ride(game, "f1")
        assert result.fremen_sandworm_ride_territory is None

    def test_skip_without_pending_raises(self):
        game = self._ride_game()
        game = game.model_copy(update={"fremen_sandworm_ride_territory": None})
        with pytest.raises(ValueError, match="No sandworm ride"):
            fremen_skip_sandworm_ride(game, "f1")

    def test_ride_requires_advanced_mode(self):
        game = self._ride_game()
        game = game.model_copy(update={"mode": GameMode.BASIC})
        with pytest.raises(ValueError, match="Advanced"):
            fremen_sandworm_ride(game, "f1", "Cielago North", 5, regular_count=1)
