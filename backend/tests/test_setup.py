"""
Tests for backend.app.services.game.setup.create_game().

Run with:
    cd DuneGame
    python -m pytest backend/tests/test_setup.py -v
"""

import pytest

from backend.app.data.factions import FACTION_DATA
from backend.app.data.territories import TERRITORIES
from backend.app.models.faction import FactionName
from backend.app.models.game_state import GameMode, GamePhase, GameState
from backend.app.models.player import KwisatzHaderach, Prediction
from backend.app.services.game.setup import (
    TOTAL_GAME_SPICE,
    PlayerSetupConfig,
    create_game,
)


# =========================================================================
# Validation
# =========================================================================

class TestValidation:
    """create_game must reject invalid player configurations."""

    def test_too_few_players(self):
        configs = [
            PlayerSetupConfig(player_id="p1", player_name="Solo", faction=FactionName.ATREIDES),
        ]
        with pytest.raises(ValueError, match="at least 2"):
            create_game("g1", configs, GameMode.BASIC)

    def test_too_many_players(self):
        factions = list(FactionName)
        configs = [
            PlayerSetupConfig(player_id=f"p{i}", player_name=f"Player{i}", faction=f)
            for i, f in enumerate(factions)
        ]
        # Add a 7th player by duplicating Atreides — should fail on count before
        # it fails on duplicate, but both are caught.
        configs.append(
            PlayerSetupConfig(player_id="p7", player_name="Extra", faction=FactionName.ATREIDES)
        )
        with pytest.raises(ValueError):
            create_game("g1", configs, GameMode.BASIC)

    def test_duplicate_factions(self):
        configs = [
            PlayerSetupConfig(player_id="p1", player_name="Paul", faction=FactionName.ATREIDES),
            PlayerSetupConfig(player_id="p2", player_name="Thufir", faction=FactionName.ATREIDES),
        ]
        with pytest.raises(ValueError, match="only be chosen by one"):
            create_game("g1", configs, GameMode.BASIC)


# =========================================================================
# GameState structure
# =========================================================================

class TestGameStateStructure:
    """Basic sanity checks on the returned GameState."""

    def test_returns_game_state(self, basic_game: GameState):
        assert isinstance(basic_game, GameState)

    def test_game_id_and_mode(self, basic_game: GameState, advanced_game: GameState):
        assert basic_game.id == "test-basic"
        assert basic_game.mode == GameMode.BASIC
        assert advanced_game.id == "test-advanced"
        assert advanced_game.mode == GameMode.ADVANCED

    def test_starts_at_turn_1_storm_phase(self, basic_game: GameState):
        assert basic_game.current_turn == 1
        assert basic_game.current_phase == GamePhase.STORM

    def test_storm_sector_in_range(self, two_player_configs):
        """When no sector is provided, the random choice must be 0–17."""
        game = create_game("g1", two_player_configs, GameMode.BASIC)
        assert 0 <= game.storm_sector <= 17

    def test_explicit_storm_sector(self, two_player_configs):
        game = create_game("g1", two_player_configs, GameMode.BASIC, initial_storm_sector=14)
        assert game.storm_sector == 14

    def test_game_not_over(self, basic_game: GameState):
        assert basic_game.is_game_over is False
        assert basic_game.winner is None


# =========================================================================
# Player initialization
# =========================================================================

class TestPlayerInit:
    """Verify each player is correctly set up from FactionData."""

    def test_correct_player_count(self, basic_game: GameState, six_player_basic: GameState):
        assert len(basic_game.players) == 2
        assert len(six_player_basic.players) == 6

    def test_player_factions_match(self, six_player_basic: GameState):
        factions = {p.faction for p in six_player_basic.players}
        assert factions == set(FactionName)

    def test_starting_spice(self, six_player_basic: GameState):
        for player in six_player_basic.players:
            expected = FACTION_DATA[player.faction].starting_spice
            assert player.spice == expected, (
                f"{player.faction.value} should start with {expected} spice, got {player.spice}"
            )

    def test_five_leaders_per_player(self, six_player_basic: GameState):
        for player in six_player_basic.players:
            assert len(player.leaders) == 5, (
                f"{player.faction.value} should have 5 leaders, got {len(player.leaders)}"
            )

    def test_leader_factions_correct(self, six_player_basic: GameState):
        """Each player's leaders must belong to their own faction."""
        for player in six_player_basic.players:
            for leader in player.leaders:
                assert leader.faction == player.faction

    def test_starting_treachery_hand(self, six_player_basic: GameState):
        for player in six_player_basic.players:
            expected = FACTION_DATA[player.faction].starting_treachery_cards
            assert len(player.treachery_hand) == expected, (
                f"{player.faction.value} should start with {expected} treachery card(s), "
                f"got {len(player.treachery_hand)}"
            )

    def test_traitor_cards_basic(self, six_player_basic: GameState):
        """In Basic mode, every faction keeps exactly 1 traitor card."""
        for player in six_player_basic.players:
            assert len(player.traitor_cards) == 1, (
                f"{player.faction.value} (Basic) should keep 1 traitor, "
                f"got {len(player.traitor_cards)}"
            )

    def test_traitor_cards_advanced_harkonnen(self, six_player_advanced: GameState):
        """In Advanced mode, Harkonnen keeps all 4 traitor cards."""
        for player in six_player_advanced.players:
            if player.faction == FactionName.HARKONNEN:
                assert len(player.traitor_cards) == 4
            else:
                assert len(player.traitor_cards) == 1

    def test_forces_on_board(self, six_player_basic: GameState):
        """Starting forces match FACTION_DATA.starting_positions."""
        for player in six_player_basic.players:
            fd = FACTION_DATA[player.faction]
            expected_groups = len(fd.starting_positions)
            assert len(player.forces_on_board) == expected_groups, (
                f"{player.faction.value}: expected {expected_groups} force groups, "
                f"got {len(player.forces_on_board)}"
            )
            for pos, group in zip(fd.starting_positions, player.forces_on_board):
                assert group.territory_name == pos.territory
                assert group.regular_count == pos.regular_forces

    def test_forces_in_reserve(self, six_player_basic: GameState):
        """Reserve count matches FACTION_DATA.starting_reserve."""
        for player in six_player_basic.players:
            expected = FACTION_DATA[player.faction].starting_reserve
            assert player.forces_in_reserve == expected, (
                f"{player.faction.value}: expected {expected} in reserve, "
                f"got {player.forces_in_reserve}"
            )

    def test_special_forces_in_reserve(self, six_player_advanced: GameState):
        """Special forces in reserve match FACTION_DATA.total_special_forces."""
        for player in six_player_advanced.players:
            expected = FACTION_DATA[player.faction].total_special_forces
            assert player.special_forces_in_reserve == expected, (
                f"{player.faction.value}: expected {expected} special in reserve, "
                f"got {player.special_forces_in_reserve}"
            )

    def test_no_forces_in_tanks(self, basic_game: GameState):
        """No one starts with forces in the tanks."""
        for player in basic_game.players:
            assert player.forces_in_tanks == 0
            assert player.special_forces_in_tanks == 0

    def test_no_ally_at_start(self, basic_game: GameState):
        for player in basic_game.players:
            assert player.ally is None

    def test_not_eliminated(self, basic_game: GameState):
        for player in basic_game.players:
            assert player.is_eliminated is False


# =========================================================================
# Deck state
# =========================================================================

class TestDeckState:
    """Verify deck sizes after initial dealing."""

    def test_treachery_deck_size_basic(self, six_player_basic: GameState):
        """Basic deck starts at 27 (no advanced cards). 6 players dealt 1 each
        (except Harkonnen who gets 2) = 7 cards dealt, 20 remaining."""
        dealt = sum(len(p.treachery_hand) for p in six_player_basic.players)
        remaining = len(six_player_basic.treachery_deck)
        assert dealt + remaining == 27  # 33 - 6 advanced = 27

    def test_treachery_deck_size_advanced(self, six_player_advanced: GameState):
        """Advanced deck has all 33. Same dealing: 7 dealt, 26 remaining."""
        dealt = sum(len(p.treachery_hand) for p in six_player_advanced.players)
        remaining = len(six_player_advanced.treachery_deck)
        assert dealt + remaining == 33

    def test_no_advanced_cards_in_basic_deck(self, six_player_basic: GameState):
        """No is_advanced cards should appear anywhere in a Basic game."""
        all_cards = list(six_player_basic.treachery_deck)
        for p in six_player_basic.players:
            all_cards.extend(p.treachery_hand)
        for card in all_cards:
            assert card.is_advanced is False, (
                f"Advanced card '{card.name}' found in Basic game"
            )

    def test_spice_deck_size(self, basic_game: GameState):
        """Spice Deck always has 26 cards (20 territory + 6 Shai-Hulud)."""
        assert len(basic_game.spice_deck) == 26

    def test_treachery_discard_empty(self, basic_game: GameState):
        assert len(basic_game.treachery_discard) == 0

    def test_spice_discard_empty(self, basic_game: GameState):
        assert len(basic_game.spice_discard) == 0

    def test_no_duplicate_treachery_ids(self, six_player_advanced: GameState):
        """Every treachery card should have a unique ID."""
        all_cards = list(six_player_advanced.treachery_deck)
        for p in six_player_advanced.players:
            all_cards.extend(p.treachery_hand)
        ids = [c.id for c in all_cards]
        assert len(ids) == len(set(ids)), "Duplicate treachery card IDs found"

    def test_no_duplicate_spice_ids(self, basic_game: GameState):
        ids = [c.id for c in basic_game.spice_deck]
        assert len(ids) == len(set(ids)), "Duplicate spice card IDs found"


# =========================================================================
# Spice bank
# =========================================================================

class TestSpiceBank:

    def test_spice_bank_calculation(self, six_player_basic: GameState):
        """Spice bank = total game spice - sum of player starting spice."""
        player_spice = sum(p.spice for p in six_player_basic.players)
        assert six_player_basic.spice_bank == TOTAL_GAME_SPICE - player_spice

    def test_spice_bank_positive(self, six_player_basic: GameState):
        assert six_player_basic.spice_bank > 0


# =========================================================================
# Advanced-mode specifics
# =========================================================================

class TestAdvancedMode:

    def test_atreides_kwisatz_haderach_init(self, six_player_advanced: GameState):
        atreides = next(p for p in six_player_advanced.players if p.faction == FactionName.ATREIDES)
        assert atreides.kwisatz_haderach is not None
        assert isinstance(atreides.kwisatz_haderach, KwisatzHaderach)
        assert atreides.kwisatz_haderach.is_active is False
        assert atreides.kwisatz_haderach.force_losses_accumulated == 0
        assert atreides.kwisatz_haderach.territory is None

    def test_bg_prediction_init(self, six_player_advanced: GameState):
        bg = next(p for p in six_player_advanced.players if p.faction == FactionName.BENE_GESSERIT)
        assert bg.prediction is not None
        assert isinstance(bg.prediction, Prediction)
        assert bg.prediction.faction is None
        assert bg.prediction.turn is None
        assert bg.prediction.is_revealed is False

    def test_no_advanced_state_in_basic(self, six_player_basic: GameState):
        """Basic mode: no Kwisatz Haderach or Prediction on any player."""
        for player in six_player_basic.players:
            assert player.kwisatz_haderach is None, (
                f"{player.faction.value} should not have KH in Basic mode"
            )
            assert player.prediction is None, (
                f"{player.faction.value} should not have Prediction in Basic mode"
            )

    def test_non_atreides_no_kh(self, six_player_advanced: GameState):
        for player in six_player_advanced.players:
            if player.faction != FactionName.ATREIDES:
                assert player.kwisatz_haderach is None

    def test_non_bg_no_prediction(self, six_player_advanced: GameState):
        for player in six_player_advanced.players:
            if player.faction != FactionName.BENE_GESSERIT:
                assert player.prediction is None


# =========================================================================
# Territory map
# =========================================================================

class TestTerritoryMap:

    def test_all_territories_present(self, basic_game: GameState):
        assert len(basic_game.territories) == len(TERRITORIES)

    def test_territory_names_match(self, basic_game: GameState):
        assert set(basic_game.territories.keys()) == set(TERRITORIES.keys())

    def test_territories_start_with_zero_spice(self, basic_game: GameState):
        for name, territory in basic_game.territories.items():
            assert territory.current_spice == 0, (
                f"Territory '{name}' should start with 0 spice, got {territory.current_spice}"
            )

    def test_imperial_basin_storm_exception(self, basic_game: GameState):
        ib = basic_game.territories["Imperial Basin"]
        assert ib.storm_exception is True
        assert ib.is_protected_from_storm is True

    def test_stronghold_count(self, basic_game: GameState):
        strongholds = [t for t in basic_game.territories.values() if t.is_stronghold]
        assert len(strongholds) == 5

    def test_territory_immutability(self, basic_game: GameState):
        """Mutating a territory in the game state should NOT mutate the
        module-level TERRITORIES constant (deep copy check)."""
        basic_game.territories["Imperial Basin"].current_spice = 99
        assert TERRITORIES["Imperial Basin"].current_spice == 0


# =========================================================================
# Traitor card integrity
# =========================================================================

class TestTraitorCards:

    def test_traitor_cards_from_active_factions_only(self, six_player_basic: GameState):
        """All traitor cards held by players should reference leaders from
        factions that are actually in the game."""
        active_factions = {p.faction for p in six_player_basic.players}
        for player in six_player_basic.players:
            for tc in player.traitor_cards:
                assert tc.faction in active_factions, (
                    f"Traitor card for {tc.leader_name} ({tc.faction.value}) "
                    f"but that faction is not in the game"
                )

    def test_no_duplicate_traitor_ids(self, six_player_basic: GameState):
        """No two players should hold the same traitor card."""
        all_ids: list[str] = []
        for player in six_player_basic.players:
            all_ids.extend(tc.id for tc in player.traitor_cards)
        assert len(all_ids) == len(set(all_ids)), "Duplicate traitor card IDs found"

    def test_two_player_traitor_pool_size(self, two_player_configs):
        """With 2 factions (10 leaders), we deal 4 to each = 8 used, 2 left over.
        Each player should have valid cards."""
        game = create_game("g1", two_player_configs, GameMode.BASIC, initial_storm_sector=0)
        total_traitors = sum(len(p.traitor_cards) for p in game.players)
        assert total_traitors == 2  # 1 kept per player in Basic
