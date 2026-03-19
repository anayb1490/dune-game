"""
Tests for backend.app.services.game.spice — Spice Blow Phase service.

Run with:
    cd DuneGame
    python -m pytest backend/tests/test_spice.py -v
"""

import pytest

from backend.app.models.card import SpiceCard, SpiceCardType
from backend.app.models.faction import FactionName
from backend.app.models.game_state import GamePhase, GameState
from backend.app.models.player import ForceGroup
from backend.app.services.game.spice import resolve_spice_blow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CARD_COUNTER = 0


def _territory_card(name: str, amount: int) -> SpiceCard:
    global _CARD_COUNTER
    _CARD_COUNTER += 1
    return SpiceCard(
        id=f"test_territory_{_CARD_COUNTER}",
        name=name,
        card_type=SpiceCardType.TERRITORY,
        territory_name=name,
        spice_amount=amount,
    )


def _worm_card() -> SpiceCard:
    global _CARD_COUNTER
    _CARD_COUNTER += 1
    return SpiceCard(
        id=f"test_worm_{_CARD_COUNTER}",
        name="Shai-Hulud",
        card_type=SpiceCardType.SHAI_HULUD,
    )


class TestSpicePlacement:
    """Territory cards add spice to the named territory."""

    def test_territory_card_places_spice(self, game_at_spice_blow: GameState):
        card = _territory_card("Hagga Basin", 6)
        game = game_at_spice_blow.model_copy(update={
            "spice_deck": [card],
            "spice_discard": [],
        })

        result = resolve_spice_blow(game)
        assert result.territories["Hagga Basin"].current_spice == 6

    def test_spice_is_additive(self, game_at_spice_blow: GameState):
        """Drawing the same territory twice should stack spice."""
        card1 = _territory_card("The Great Flat", 10)
        card2 = _territory_card("The Great Flat", 10)
        game = game_at_spice_blow.model_copy(update={
            "spice_deck": [card1],
            "spice_discard": [],
        })

        result = resolve_spice_blow(game)
        # First draw places 10
        assert result.territories["The Great Flat"].current_spice == 10

        # Simulate a second spice blow on the result
        result2 = result.model_copy(update={
            "spice_deck": [card2],
            "current_phase": GamePhase.SPICE_BLOW,
        })
        result2 = resolve_spice_blow(result2)
        assert result2.territories["The Great Flat"].current_spice == 20

    def test_card_moves_to_discard(self, game_at_spice_blow: GameState):
        card = _territory_card("Red Chasm", 8)
        game = game_at_spice_blow.model_copy(update={
            "spice_deck": [card],
            "spice_discard": [],
        })

        result = resolve_spice_blow(game)
        assert len(result.spice_deck) == 0
        assert len(result.spice_discard) == 1
        assert result.spice_discard[0].territory_name == "Red Chasm"

    def test_advances_to_choam_charity(self, game_at_spice_blow: GameState):
        card = _territory_card("Meridian", 6)
        game = game_at_spice_blow.model_copy(update={
            "spice_deck": [card],
            "spice_discard": [],
        })

        result = resolve_spice_blow(game)
        assert result.current_phase == GamePhase.CHOAM_CHARITY


class TestShaiHulud:
    """Shai-Hulud (sandworm) card effects."""

    def test_worm_destroys_spice_on_last_territory(self, game_at_spice_blow: GameState):
        """Worm should destroy spice on the last-revealed territory."""
        prev_territory = _territory_card("Hagga Basin", 6)
        worm = _worm_card()
        next_territory = _territory_card("Red Chasm", 8)

        # Set up: Hagga Basin already in discard (last revealed), spice on it
        territories = {
            n: t.model_copy() for n, t in game_at_spice_blow.territories.items()
        }
        territories["Hagga Basin"] = territories["Hagga Basin"].model_copy(
            update={"current_spice": 6}
        )

        game = game_at_spice_blow.model_copy(update={
            "spice_deck": [worm, next_territory],
            "spice_discard": [prev_territory],
            "territories": territories,
            "current_turn": 2,  # Not first turn
        })

        result = resolve_spice_blow(game)
        # Hagga Basin spice destroyed by worm
        assert result.territories["Hagga Basin"].current_spice == 0
        # Red Chasm gets new spice
        assert result.territories["Red Chasm"].current_spice == 8

    def test_worm_destroys_forces(self, game_at_spice_blow: GameState):
        """Worm should destroy forces in the last-revealed territory."""
        prev_territory = _territory_card("The Great Flat", 10)
        worm = _worm_card()
        next_territory = _territory_card("Meridian", 6)

        # Place Atreides forces in The Great Flat
        atreides = next(
            p for p in game_at_spice_blow.players
            if p.faction == FactionName.ATREIDES
        )
        new_forces = list(atreides.forces_on_board) + [
            ForceGroup(
                territory_name="The Great Flat",
                sector=13,
                regular_count=4,
            ),
        ]
        updated_atreides = atreides.model_copy(update={
            "forces_on_board": new_forces,
            "forces_in_reserve": atreides.forces_in_reserve - 4,
        })
        players = [
            updated_atreides if p.faction == FactionName.ATREIDES else p
            for p in game_at_spice_blow.players
        ]

        game = game_at_spice_blow.model_copy(update={
            "spice_deck": [worm, next_territory],
            "spice_discard": [prev_territory],
            "players": players,
            "current_turn": 2,
        })

        result = resolve_spice_blow(game)
        atreides_after = next(
            p for p in result.players if p.faction == FactionName.ATREIDES
        )
        great_flat = [
            fg for fg in atreides_after.forces_on_board
            if fg.territory_name == "The Great Flat"
        ]
        assert len(great_flat) == 0
        assert atreides_after.forces_in_tanks == 4

    def test_worm_draws_until_territory(self, game_at_spice_blow: GameState):
        """After worm, keep drawing past more worms until territory found."""
        prev_territory = _territory_card("Hagga Basin", 6)
        worm1 = _worm_card()
        worm2 = _worm_card()
        territory = _territory_card("Meridian", 6)

        game = game_at_spice_blow.model_copy(update={
            "spice_deck": [worm1, worm2, territory],
            "spice_discard": [prev_territory],
            "current_turn": 2,
        })

        result = resolve_spice_blow(game)
        assert result.territories["Meridian"].current_spice == 6
        # All 3 drawn cards + prev should be in discard
        assert len(result.spice_discard) == 4


class TestFirstTurnException:
    """On the first turn, Shai-Hulud cards are set aside and reshuffled."""

    def test_first_turn_worm_set_aside(self, game_at_spice_blow: GameState):
        """Worm on first turn should not destroy anything."""
        worm = _worm_card()
        territory = _territory_card("Hagga Basin", 6)

        # Place some spice on a territory that would normally be attacked
        territories = {
            n: t.model_copy() for n, t in game_at_spice_blow.territories.items()
        }
        territories["Red Chasm"] = territories["Red Chasm"].model_copy(
            update={"current_spice": 8}
        )

        game = game_at_spice_blow.model_copy(update={
            "spice_deck": [worm, territory],
            "spice_discard": [_territory_card("Red Chasm", 8)],
            "territories": territories,
            "current_turn": 1,  # First turn!
        })

        result = resolve_spice_blow(game)
        # Red Chasm spice should NOT be destroyed
        assert result.territories["Red Chasm"].current_spice == 8
        # Hagga Basin should get its spice
        assert result.territories["Hagga Basin"].current_spice == 6

    def test_first_turn_worm_reshuffled_into_deck(self, game_at_spice_blow: GameState):
        """Set-aside worm cards get reshuffled back into the deck."""
        worm = _worm_card()
        territory = _territory_card("Meridian", 6)

        game = game_at_spice_blow.model_copy(update={
            "spice_deck": [worm, territory],
            "spice_discard": [],
            "current_turn": 1,
        })

        result = resolve_spice_blow(game)
        # The worm should be back in the deck (reshuffled)
        assert len(result.spice_deck) == 1
        assert result.spice_deck[0].card_type == SpiceCardType.SHAI_HULUD


class TestDeckExhaustion:
    """Edge cases around empty or nearly-empty decks."""

    def test_empty_deck_reshuffles_discard(self, game_at_spice_blow: GameState):
        """If deck is empty, reshuffle discard pile into deck before drawing."""
        discard_card = _territory_card("The Great Flat", 10)
        game = game_at_spice_blow.model_copy(update={
            "spice_deck": [],
            "spice_discard": [discard_card],
        })

        result = resolve_spice_blow(game)
        # Should have drawn the reshuffled card and placed spice
        assert result.territories["The Great Flat"].current_spice == 10

    def test_completely_empty_skips_phase(self, game_at_spice_blow: GameState):
        """If both deck and discard are empty, skip to CHOAM_CHARITY."""
        game = game_at_spice_blow.model_copy(update={
            "spice_deck": [],
            "spice_discard": [],
        })

        result = resolve_spice_blow(game)
        assert result.current_phase == GamePhase.CHOAM_CHARITY


class TestStormBlocking:
    """Spice is not placed if the territory is in the storm sector."""

    def test_storm_blocks_spice_placement(self, game_at_spice_blow: GameState):
        """Territory in storm sector should receive no spice."""
        # Storm is at sector 5; Imperial Basin has sectors [4, 5] — blocked
        card = _territory_card("Imperial Basin", 4)
        game = game_at_spice_blow.model_copy(update={
            "spice_deck": [card],
            "spice_discard": [],
            "storm_sector": 5,
        })

        result = resolve_spice_blow(game)
        assert result.territories["Imperial Basin"].current_spice == 0
        # Card still goes to discard
        assert len(result.spice_discard) == 1

    def test_storm_does_not_block_other_territory(self, game_at_spice_blow: GameState):
        """Territory NOT in storm sector should receive spice normally."""
        # Storm is at sector 5; Hagga Basin has sectors [7, 8] — not blocked
        card = _territory_card("Hagga Basin", 6)
        game = game_at_spice_blow.model_copy(update={
            "spice_deck": [card],
            "spice_discard": [],
            "storm_sector": 5,
        })

        result = resolve_spice_blow(game)
        assert result.territories["Hagga Basin"].current_spice == 6


class TestSpiceBank:
    """Spice placed on territories comes from the bank."""

    def test_spice_deducted_from_bank(self, game_at_spice_blow: GameState):
        """Placing spice should reduce the spice bank."""
        card = _territory_card("Red Chasm", 8)
        initial_bank = game_at_spice_blow.spice_bank
        game = game_at_spice_blow.model_copy(update={
            "spice_deck": [card],
            "spice_discard": [],
        })

        result = resolve_spice_blow(game)
        assert result.spice_bank == initial_bank - 8

    def test_spice_capped_at_bank(self, game_at_spice_blow: GameState):
        """If bank has less spice than the card amount, only place what's left."""
        card = _territory_card("The Great Flat", 10)
        game = game_at_spice_blow.model_copy(update={
            "spice_deck": [card],
            "spice_discard": [],
            "spice_bank": 3,  # Only 3 left in bank
        })

        result = resolve_spice_blow(game)
        assert result.territories["The Great Flat"].current_spice == 3
        assert result.spice_bank == 0

    def test_shai_hulud_returns_spice_to_bank(self, game_at_spice_blow: GameState):
        """Destroyed spice should go back to the bank."""
        prev_territory = _territory_card("Hagga Basin", 6)
        worm = _worm_card()
        next_territory = _territory_card("Red Chasm", 8)

        territories = {
            n: t.model_copy() for n, t in game_at_spice_blow.territories.items()
        }
        territories["Hagga Basin"] = territories["Hagga Basin"].model_copy(
            update={"current_spice": 6}
        )

        initial_bank = game_at_spice_blow.spice_bank
        game = game_at_spice_blow.model_copy(update={
            "spice_deck": [worm, next_territory],
            "spice_discard": [prev_territory],
            "territories": territories,
            "current_turn": 2,
        })

        result = resolve_spice_blow(game)
        # Bank should get +6 (destroyed) then -8 (placed on Red Chasm)
        assert result.spice_bank == initial_bank + 6 - 8
