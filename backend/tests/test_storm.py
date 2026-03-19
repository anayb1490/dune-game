"""
Tests for backend.app.services.game.storm — Storm Phase service.

Run with:
    cd DuneGame
    python -m pytest backend/tests/test_storm.py -v
"""

import pytest

from backend.app.models.faction import FactionName
from backend.app.models.game_state import GamePhase, GameState
from backend.app.models.player import ForceGroup
from backend.app.services.game.storm import resolve_storm


class TestStormMovement:
    """Verify the storm moves counterclockwise and records its move."""

    def test_storm_moves_counterclockwise(self, basic_game: GameState):
        result = resolve_storm(basic_game, storm_move=3)
        # Storm at sector 5, move 3 counterclockwise: (5 - 3) % 18 = 2
        assert result.storm_sector == 2

    def test_storm_wraps_around(self, basic_game: GameState):
        result = resolve_storm(basic_game, storm_move=7)
        # Storm at sector 5, move 7: (5 - 7) % 18 = 16
        assert result.storm_sector == 16

    def test_storm_move_recorded(self, basic_game: GameState):
        result = resolve_storm(basic_game, storm_move=4)
        assert result.last_storm_move == 4

    def test_storm_zero_move(self, basic_game: GameState):
        result = resolve_storm(basic_game, storm_move=0)
        assert result.storm_sector == 5  # Unchanged
        assert result.last_storm_move == 0

    def test_advances_to_spice_blow(self, basic_game: GameState):
        result = resolve_storm(basic_game, storm_move=2)
        assert result.current_phase == GamePhase.SPICE_BLOW

    def test_random_storm_in_range(self, basic_game: GameState):
        """Without explicit move, storm should move 2–6 sectors."""
        result = resolve_storm(basic_game)
        move = result.last_storm_move
        assert 2 <= move <= 6


class TestStormDamage:
    """Verify forces are destroyed in swept sand sectors."""

    def test_forces_killed_in_swept_sand(self, game_with_forces_in_sand: GameState):
        """Forces at sector 13 (The Great Flat, sand) should be destroyed
        when the storm sweeps through sector 13."""
        # Storm at 15, move 3: sweeps 14, 13, 12. Sector 13 is hit.
        result = resolve_storm(game_with_forces_in_sand, storm_move=3)
        atreides = next(p for p in result.players if p.faction == FactionName.ATREIDES)

        # The Great Flat forces should be gone from the board
        great_flat_groups = [
            fg for fg in atreides.forces_on_board
            if fg.territory_name == "The Great Flat"
        ]
        assert len(great_flat_groups) == 0

        # Those 5 forces should be in the tanks
        assert atreides.forces_in_tanks == 5

    def test_forces_safe_in_stronghold(self, six_player_basic: GameState):
        """Atreides start in Arrakeen (stronghold, sector 3).
        Even if the storm sweeps sector 3, forces survive."""
        # Place storm so it sweeps through sector 3
        game = six_player_basic.model_copy(update={"storm_sector": 5})
        result = resolve_storm(game, storm_move=3)  # Sweeps 4, 3, 2
        atreides = next(p for p in result.players if p.faction == FactionName.ATREIDES)

        arrakeen_forces = [
            fg for fg in atreides.forces_on_board
            if fg.territory_name == "Arrakeen"
        ]
        assert len(arrakeen_forces) == 1
        assert arrakeen_forces[0].regular_count == 10

    def test_fremen_immune_to_storm(self, game_with_forces_in_sand: GameState):
        """Fremen forces are never destroyed by the storm."""
        # Place Fremen forces in the same sand sector
        fremen = next(
            p for p in game_with_forces_in_sand.players
            if p.faction == FactionName.FREMEN
        )
        new_forces = list(fremen.forces_on_board) + [
            ForceGroup(
                territory_name="The Great Flat",
                sector=13,
                regular_count=3,
            ),
        ]
        updated_fremen = fremen.model_copy(update={"forces_on_board": new_forces})
        players = [
            updated_fremen if p.faction == FactionName.FREMEN else p
            for p in game_with_forces_in_sand.players
        ]
        game = game_with_forces_in_sand.model_copy(update={"players": players})

        result = resolve_storm(game, storm_move=3)  # Sweeps 14, 13, 12
        fremen_after = next(p for p in result.players if p.faction == FactionName.FREMEN)

        great_flat_groups = [
            fg for fg in fremen_after.forces_on_board
            if fg.territory_name == "The Great Flat"
        ]
        assert len(great_flat_groups) == 1
        assert great_flat_groups[0].regular_count == 3

    def test_imperial_basin_protected(self, six_player_basic: GameState):
        """Imperial Basin is sand but storm_exception=True — forces survive."""
        # Place a player's forces in Imperial Basin
        atreides = next(p for p in six_player_basic.players if p.faction == FactionName.ATREIDES)
        new_forces = list(atreides.forces_on_board) + [
            ForceGroup(
                territory_name="Imperial Basin",
                sector=5,
                regular_count=3,
            ),
        ]
        updated = atreides.model_copy(update={
            "forces_on_board": new_forces,
            "forces_in_reserve": atreides.forces_in_reserve - 3,
        })
        players = [updated if p.faction == FactionName.ATREIDES else p for p in six_player_basic.players]
        game = six_player_basic.model_copy(update={
            "players": players,
            "storm_sector": 7,
        })

        result = resolve_storm(game, storm_move=3)  # Sweeps 6, 5, 4
        atreides_after = next(p for p in result.players if p.faction == FactionName.ATREIDES)
        ib_groups = [fg for fg in atreides_after.forces_on_board if fg.territory_name == "Imperial Basin"]
        assert len(ib_groups) == 1
        assert ib_groups[0].regular_count == 3

    def test_forces_not_in_swept_sector_survive(self, game_with_forces_in_sand: GameState):
        """Forces in sector 13 are safe if storm only sweeps sectors 14, 15, 16."""
        # Storm at 17, move 3: sweeps 16, 15, 14 — sector 13 NOT hit
        game = game_with_forces_in_sand.model_copy(update={"storm_sector": 17})
        result = resolve_storm(game, storm_move=3)
        atreides = next(p for p in result.players if p.faction == FactionName.ATREIDES)
        great_flat = [fg for fg in atreides.forces_on_board if fg.territory_name == "The Great Flat"]
        assert len(great_flat) == 1
        assert great_flat[0].regular_count == 5

    def test_no_damage_zero_move(self, game_with_forces_in_sand: GameState):
        """A storm move of 0 sweeps no sectors."""
        result = resolve_storm(game_with_forces_in_sand, storm_move=0)
        atreides = next(p for p in result.players if p.faction == FactionName.ATREIDES)
        assert atreides.forces_in_tanks == 0
