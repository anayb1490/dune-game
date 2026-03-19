"""
Tests for backend.app.services.game.phases — CHOAM Charity + phase utilities.

Run with:
    cd DuneGame
    python -m pytest backend/tests/test_phases.py -v
"""

import pytest

from backend.app.models.faction import FactionName
from backend.app.models.game_state import GamePhase, GameState
from backend.app.services.game.phases import (
    AUTOMATED_PHASES,
    PHASE_SEQUENCE,
    next_phase,
    resolve_choam_charity,
)


class TestPhaseSequence:
    """Verify the canonical phase ordering."""

    def test_sequence_length(self):
        assert len(PHASE_SEQUENCE) == 10  # includes NEXUS

    def test_storm_is_first(self):
        assert PHASE_SEQUENCE[0] == GamePhase.STORM

    def test_mentat_pause_is_last(self):
        assert PHASE_SEQUENCE[-1] == GamePhase.MENTAT_PAUSE

    def test_next_phase_advances(self):
        assert next_phase(GamePhase.STORM) == GamePhase.SPICE_BLOW
        assert next_phase(GamePhase.SPICE_BLOW) == GamePhase.NEXUS   # NEXUS between Spice Blow and CHOAM
        assert next_phase(GamePhase.NEXUS) == GamePhase.CHOAM_CHARITY
        assert next_phase(GamePhase.CHOAM_CHARITY) == GamePhase.BIDDING

    def test_next_phase_wraps(self):
        """After MENTAT_PAUSE, wraps back to STORM."""
        assert next_phase(GamePhase.MENTAT_PAUSE) == GamePhase.STORM

    def test_automated_phases_set(self):
        """Only SPICE_COLLECTION is fully automated (no player cycling)."""
        assert GamePhase.STORM not in AUTOMATED_PHASES
        assert GamePhase.SPICE_BLOW not in AUTOMATED_PHASES
        assert GamePhase.CHOAM_CHARITY not in AUTOMATED_PHASES
        assert GamePhase.SPICE_COLLECTION in AUTOMATED_PHASES
        assert GamePhase.BIDDING not in AUTOMATED_PHASES
        assert GamePhase.BATTLE not in AUTOMATED_PHASES


class TestCHOAMCharity:
    """Verify CHOAM Charity gives spice to broke players."""

    def test_broke_player_gets_2(self, game_at_choam: GameState):
        """A player with 0 spice should receive 2."""
        result = resolve_choam_charity(game_at_choam)
        fremen = next(p for p in result.players if p.faction == FactionName.FREMEN)
        assert fremen.spice == 2

    def test_player_with_1_gets_1(self, game_at_choam: GameState):
        """A player with 1 spice should receive 1 (total = 2)."""
        result = resolve_choam_charity(game_at_choam)
        bg = next(p for p in result.players if p.faction == FactionName.BENE_GESSERIT)
        assert bg.spice == 2

    def test_wealthy_player_gets_nothing(self, game_at_choam: GameState):
        """A player with >= 2 spice should get 0 charity."""
        # Atreides starts with 10 spice (Basic mode)
        result = resolve_choam_charity(game_at_choam)
        atreides = next(p for p in result.players if p.faction == FactionName.ATREIDES)
        atreides_before = next(
            p for p in game_at_choam.players if p.faction == FactionName.ATREIDES
        )
        assert atreides.spice == atreides_before.spice

    def test_spice_bank_decreases(self, game_at_choam: GameState):
        """Charity comes from the spice bank."""
        result = resolve_choam_charity(game_at_choam)
        # Fremen got 2, BG got 1 → bank decreased by 3
        assert result.spice_bank == game_at_choam.spice_bank - 3

    def test_advances_to_bidding(self, game_at_choam: GameState):
        result = resolve_choam_charity(game_at_choam)
        assert result.current_phase == GamePhase.BIDDING

    def test_empty_bank_gives_partial(self, game_at_choam: GameState):
        """If the bank has less than needed, give what's left."""
        game = game_at_choam.model_copy(update={"spice_bank": 1})

        result = resolve_choam_charity(game)
        # First broke player in order should get the 1 remaining spice
        total_charity_given = sum(
            p2.spice - p1.spice
            for p1, p2 in zip(game.players, result.players)
        )
        assert total_charity_given == 1
        assert result.spice_bank == 0

    def test_no_charity_needed(self, six_player_basic: GameState):
        """If all players have >= 2, no charity is given."""
        game = six_player_basic.model_copy(update={
            "current_phase": GamePhase.CHOAM_CHARITY,
        })
        bank_before = game.spice_bank

        result = resolve_choam_charity(game)
        assert result.spice_bank == bank_before
