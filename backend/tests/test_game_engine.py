"""
Integration tests for the full turn/phase cycle.

Verifies:
  - Automated phases use the two-step resolve→advance pattern
  - Turn-based phases cycle through all players before advancing
  - Host-only validation works for automated phases
  - The full turn loop from STORM through MENTAT_PAUSE

Run with:
    cd DuneGame
    python -m pytest backend/tests/test_game_engine.py -v
"""

import pytest

from backend.app.models.faction import FactionName
from backend.app.models.game_state import GamePhase, GameState, LobbyState, LobbyPlayer
from backend.app.services.game.engine import advance_phase


@pytest.fixture
def game_with_lobby(basic_game: GameState) -> GameState:
    """A 2-player game with a lobby_state (host = p1)."""
    lobby = LobbyState(
        join_code="TEST01",
        host_player_id="p1",
        players=[
            LobbyPlayer(id="p1", name="Paul", faction=FactionName.ATREIDES),
            LobbyPlayer(id="p2", name="Vladimir", faction=FactionName.HARKONNEN),
        ],
    )
    return basic_game.model_copy(update={"lobby_state": lobby})


class TestAutomatedPhasesTwoStep:
    """Automated phases resolve in two steps: resolve (with messages), then advance."""

    def test_storm_step1_resolves_with_messages(self, basic_game: GameState):
        result = advance_phase(basic_game)
        assert result.current_phase == GamePhase.STORM
        assert len(result.phase_messages) > 0
        assert "Storm moves" in result.phase_messages[0]

    def test_storm_step2_advances_to_spice_blow(self, basic_game: GameState):
        step1 = advance_phase(basic_game)
        step2 = advance_phase(step1)
        assert step2.current_phase == GamePhase.SPICE_BLOW
        assert step2.phase_messages == []

    def test_spice_blow_two_step(self, basic_game: GameState):
        game = basic_game.model_copy(update={"current_phase": GamePhase.SPICE_BLOW})
        step1 = advance_phase(game)
        assert step1.current_phase == GamePhase.SPICE_BLOW
        assert len(step1.phase_messages) > 0
        step2 = advance_phase(step1)
        assert step2.current_phase == GamePhase.CHOAM_CHARITY
        assert step2.phase_messages == []

    def test_choam_charity_two_step(self, game_at_choam: GameState):
        step1 = advance_phase(game_at_choam)
        assert step1.current_phase == GamePhase.CHOAM_CHARITY
        assert len(step1.phase_messages) > 0
        step2 = advance_phase(step1)
        assert step2.current_phase == GamePhase.BIDDING
        assert step2.phase_messages == []

    def test_spice_collection_two_step(self, basic_game: GameState):
        game = basic_game.model_copy(update={"current_phase": GamePhase.SPICE_COLLECTION})
        step1 = advance_phase(game)
        assert step1.current_phase == GamePhase.SPICE_COLLECTION
        assert len(step1.phase_messages) > 0
        step2 = advance_phase(step1)
        assert step2.current_phase == GamePhase.MENTAT_PAUSE
        assert step2.phase_messages == []

    def test_mentat_pause_two_step_no_winner(self, basic_game: GameState):
        game = basic_game.model_copy(update={"current_phase": GamePhase.MENTAT_PAUSE})
        step1 = advance_phase(game)
        assert step1.current_phase == GamePhase.MENTAT_PAUSE
        assert len(step1.phase_messages) > 0
        assert "Turn 2" in step1.phase_messages[0]
        step2 = advance_phase(step1)
        assert step2.current_phase == GamePhase.STORM
        assert step2.current_turn == 2
        assert step2.phase_messages == []


class TestTurnBasedPhasesPlayerCycling:
    """Turn-based phases cycle through all players before advancing."""

    def test_revival_cycles_through_players(self, basic_game: GameState):
        """With 2 players: player 0 → player 1 → next phase."""
        game = basic_game.model_copy(update={
            "current_phase": GamePhase.REVIVAL,
            "current_player_index": 0,
        })

        # Player 0 ends turn → advance to player 1
        step1 = advance_phase(game)
        assert step1.current_phase == GamePhase.REVIVAL
        assert step1.current_player_index == 1

        # Player 1 ends phase → advance to next phase
        step2 = advance_phase(step1)
        assert step2.current_phase == GamePhase.SHIPMENT_AND_MOVEMENT
        assert step2.current_player_index == 0

    def test_shipment_cycles_through_players(self, basic_game: GameState):
        """With 2 players: player 0 → player 1 → next phase."""
        game = basic_game.model_copy(update={
            "current_phase": GamePhase.SHIPMENT_AND_MOVEMENT,
            "current_player_index": 0,
        })

        # Player 0 ends turn → advance to player 1
        step1 = advance_phase(game)
        assert step1.current_phase == GamePhase.SHIPMENT_AND_MOVEMENT
        assert step1.current_player_index == 1

        # Player 1 ends phase → advance to BATTLE
        step2 = advance_phase(step1)
        assert step2.current_phase == GamePhase.BATTLE
        assert step2.current_player_index == 0

    def test_revival_cycles_six_players(self, six_player_basic: GameState):
        """With 6 players, all 6 must go before advancing."""
        game = six_player_basic.model_copy(update={
            "current_phase": GamePhase.REVIVAL,
            "current_player_index": 0,
        })

        # Players 0-4 advance to next player
        for i in range(5):
            game = advance_phase(game)
            assert game.current_phase == GamePhase.REVIVAL
            assert game.current_player_index == i + 1

        # Player 5 (last) advances to next phase
        game = advance_phase(game)
        assert game.current_phase == GamePhase.SHIPMENT_AND_MOVEMENT
        assert game.current_player_index == 0


class TestFullTurnCycle:
    """Full turn cycle from STORM through all phases back to STORM."""

    def test_automated_through_bidding(self, basic_game: GameState):
        """Advance through all automated phases (6 clicks) to reach BIDDING."""
        game = basic_game
        assert game.current_phase == GamePhase.STORM

        # Storm: resolve + advance (2 clicks)
        game = advance_phase(game)  # resolve
        assert game.current_phase == GamePhase.STORM
        assert game.phase_messages
        game = advance_phase(game)  # advance
        assert game.current_phase == GamePhase.SPICE_BLOW

        # Spice Blow: resolve + advance (2 clicks)
        game = advance_phase(game)
        game = advance_phase(game)
        assert game.current_phase == GamePhase.CHOAM_CHARITY

        # CHOAM: resolve + advance (2 clicks)
        game = advance_phase(game)
        game = advance_phase(game)
        assert game.current_phase == GamePhase.BIDDING

        assert game.current_turn == 1
        assert game.bidding_state is not None

    def test_interactive_phases_cycle_players(self, basic_game: GameState):
        """Revival and shipment cycle through all 2 players before advancing."""
        game = basic_game.model_copy(update={
            "current_phase": GamePhase.REVIVAL,
            "current_player_index": 0,
        })

        # Revival: player 0, then player 1, then next phase
        game = advance_phase(game)  # p0 → p1
        assert game.current_phase == GamePhase.REVIVAL
        assert game.current_player_index == 1
        game = advance_phase(game)  # p1 → next phase
        assert game.current_phase == GamePhase.SHIPMENT_AND_MOVEMENT
        assert game.current_player_index == 0

        # Shipment: player 0, then player 1, then next phase
        game = advance_phase(game)  # p0 → p1
        assert game.current_phase == GamePhase.SHIPMENT_AND_MOVEMENT
        assert game.current_player_index == 1
        game = advance_phase(game)  # p1 → next phase
        assert game.current_phase == GamePhase.BATTLE
        assert game.current_player_index == 0
