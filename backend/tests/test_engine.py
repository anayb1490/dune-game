"""
Tests for backend.app.services.game.engine — Game engine state machine.

Run with:
    cd DuneGame
    python -m pytest backend/tests/test_engine.py -v
"""

import pytest

from backend.app.models.faction import FactionName
from backend.app.models.game_state import GamePhase, GameState
from backend.app.services.game.engine import (
    MAX_TURNS,
    advance_phase,
    advance_turn,
    run_automated_phases,
)


class TestAdvancePhase:
    """advance_phase() uses a two-step pattern for automated phases:
    1. First call: resolve effects, populate phase_messages, stay on phase.
    2. Second call: clear messages, advance to next phase.
    """

    @staticmethod
    def _resolve_and_advance(game_state: GameState) -> GameState:
        """Two advances: resolve (step 1) then advance (step 2)."""
        result = advance_phase(game_state)   # resolve
        result = advance_phase(result)        # advance
        return result

    def test_storm_resolves_then_advances(self, basic_game: GameState):
        """Storm phase: first advance resolves with messages, second advances to SPICE_BLOW."""
        assert basic_game.current_phase == GamePhase.STORM
        # Step 1: resolve — stays on STORM with messages
        result = advance_phase(basic_game)
        assert result.current_phase == GamePhase.STORM
        assert result.current_player_index == 0
        assert len(result.phase_messages) > 0
        # Step 2: advance to SPICE_BLOW
        result = advance_phase(result)
        assert result.current_phase == GamePhase.SPICE_BLOW
        assert result.phase_messages == []

    def test_spice_blow_resolves_then_advances(self, game_at_spice_blow: GameState):
        result = self._resolve_and_advance(game_at_spice_blow)
        assert result.current_phase == GamePhase.CHOAM_CHARITY

    def test_choam_resolves_then_advances(self, game_at_choam: GameState):
        result = self._resolve_and_advance(game_at_choam)
        assert result.current_phase == GamePhase.BIDDING

    def test_bidding_skips(self, basic_game: GameState):
        """Interactive phases just advance the phase marker."""
        game = basic_game.model_copy(update={
            "current_phase": GamePhase.BIDDING,
        })
        result = advance_phase(game)
        assert result.current_phase == GamePhase.REVIVAL

    def test_battle_skips(self, basic_game: GameState):
        game = basic_game.model_copy(update={
            "current_phase": GamePhase.BATTLE,
        })
        result = advance_phase(game)
        assert result.current_phase == GamePhase.SPICE_COLLECTION

    def test_mentat_pause_generates_messages_then_advances_turn(self, basic_game: GameState):
        """MENTAT_PAUSE: first advance generates messages, second advances the turn."""
        game = basic_game.model_copy(update={
            "current_phase": GamePhase.MENTAT_PAUSE,
        })
        # Step 1: resolve — stays on MENTAT_PAUSE with messages
        result = advance_phase(game)
        assert result.current_phase == GamePhase.MENTAT_PAUSE
        assert len(result.phase_messages) > 0
        # Step 2: advance to next turn
        result = advance_phase(result)
        assert result.current_turn == 2
        assert result.current_phase == GamePhase.STORM
        assert result.phase_messages == []


class TestRunAutomatedPhases:
    """run_automated_phases() loops until hitting a non-automated phase."""

    def test_storm_not_auto_advanced(self, basic_game: GameState):
        """STORM is not in the test-helper AUTOMATED_PHASES set."""
        assert basic_game.current_phase == GamePhase.STORM
        result = run_automated_phases(basic_game)
        assert result.current_phase == GamePhase.STORM

    def test_already_at_interactive_does_nothing(self, basic_game: GameState):
        """If already at an interactive phase, returns immediately."""
        game = basic_game.model_copy(update={
            "current_phase": GamePhase.BIDDING,
        })
        result = run_automated_phases(game)
        assert result.current_phase == GamePhase.BIDDING

    def test_spice_collection_resolves_to_mentat(self, basic_game: GameState):
        """SPICE_COLLECTION is automated — should resolve to MENTAT_PAUSE."""
        game = basic_game.model_copy(update={
            "current_phase": GamePhase.SPICE_COLLECTION,
        })
        result = run_automated_phases(game)
        assert result.current_phase == GamePhase.MENTAT_PAUSE

    def test_stops_on_game_over(self, basic_game: GameState):
        """If game is already over, returns immediately."""
        game = basic_game.model_copy(update={
            "is_game_over": True,
        })
        result = run_automated_phases(game)
        assert result.is_game_over is True


class TestAdvanceTurn:
    """advance_turn() increments the turn counter and resets to STORM."""

    def test_increments_turn(self, basic_game: GameState):
        result = advance_turn(basic_game)
        assert result.current_turn == 2

    def test_resets_to_storm(self, basic_game: GameState):
        game = basic_game.model_copy(update={
            "current_phase": GamePhase.MENTAT_PAUSE,
        })
        result = advance_turn(game)
        assert result.current_phase == GamePhase.STORM

    def test_turn_limit_ends_game(self, basic_game: GameState):
        """After turn 10, the game should be over."""
        game = basic_game.model_copy(update={
            "current_turn": MAX_TURNS,
        })
        result = advance_turn(game)
        assert result.is_game_over is True

    def test_turn_9_continues(self, basic_game: GameState):
        """Turn 9 should advance to turn 10 normally."""
        game = basic_game.model_copy(update={
            "current_turn": 9,
        })
        result = advance_turn(game)
        assert result.current_turn == 10
        assert result.is_game_over is False

    def test_guild_wins_on_turn_limit(self, six_player_advanced: GameState):
        """Spacing Guild should win when the turn limit is reached in Advanced mode."""
        game = six_player_advanced.model_copy(update={
            "current_turn": MAX_TURNS,
        })
        result = advance_turn(game)
        assert result.is_game_over is True
        # Guild's alternate victory: wins if no other faction has won by turn 10
        assert result.winner == FactionName.SPACING_GUILD


class TestFullTurnLoop:
    """Integration: manually advancing through automated phases using two-step pattern."""

    def test_full_manual_sequence(self, basic_game: GameState):
        """Advance through Storm, Spice, CHOAM (2 steps each) → reach BIDDING."""
        result = basic_game

        # Advance through Storm (resolve + advance = 2 calls)
        result = advance_phase(result)  # resolve
        assert result.current_phase == GamePhase.STORM
        assert len(result.phase_messages) > 0
        result = advance_phase(result)  # advance
        assert result.current_phase == GamePhase.SPICE_BLOW

        # Advance through Spice Blow (2 calls)
        result = advance_phase(result)  # resolve
        assert result.current_phase == GamePhase.SPICE_BLOW
        result = advance_phase(result)  # advance
        assert result.current_phase == GamePhase.CHOAM_CHARITY

        # Advance through CHOAM Charity (2 calls)
        result = advance_phase(result)  # resolve
        assert result.current_phase == GamePhase.CHOAM_CHARITY
        result = advance_phase(result)  # advance
        assert result.current_phase == GamePhase.BIDDING

        # Storm should have moved
        assert result.last_storm_move is not None
        assert result.last_storm_move >= 2

        # Turn should still be 1
        assert result.current_turn == 1
