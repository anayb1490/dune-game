"""
Tests for major faction ability implementations:
  - Atreides Movement Prescience (engine injection)
  - BG Free Shipment + Advisor flip mechanics
  - Guild Cross-shipment + Back-to-reserves
  - BG Voice (pre-battle)
  - Atreides Battle Prescience (pre-battle)
  - done_prebattle / pre-battle sequencing
"""

from __future__ import annotations

import pytest

from ..app.models.faction import FactionName
from ..app.models.game_state import (
    ActiveBattle,
    GameMode,
    GamePhase,
    GameState,
)
from ..app.models.player import ForceGroup, Player
from ..app.services.game.bg_actions import (
    flip_advisors_to_fighters,
    flip_fighters_to_advisors,
    trigger_bg_free_shipment,
)
from ..app.services.game.guild_actions import guild_cross_ship, guild_ship_to_reserves
from ..app.services.game.prebattle import (
    acknowledge_voice,
    ask_prescience,
    done_prebattle,
    issue_voice,
    reveal_prescience_value,
)


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

def _make_player(
    pid: str,
    name: str,
    faction: FactionName,
    spice: int = 10,
    forces_on_board=None,
    forces_in_reserve: int = 10,
    special_forces_in_reserve: int = 0,
) -> Player:
    return Player(
        id=pid,
        name=name,
        faction=faction,
        spice=spice,
        forces_on_board=forces_on_board or [],
        forces_in_reserve=forces_in_reserve,
        special_forces_in_reserve=special_forces_in_reserve,
    )


def _make_territory_dict(territory_module):
    """Return the full territory dict from the data module."""
    from ..app.data.territories import TERRITORIES
    return {name: t.model_copy() for name, t in TERRITORIES.items()}


def _base_game(
    players: list[Player],
    mode: GameMode = GameMode.BASIC,
    phase: GamePhase = GamePhase.SHIPMENT_AND_MOVEMENT,
    storm_sector: int = 5,
) -> GameState:
    from ..app.data.territories import TERRITORIES
    territories = {name: t.model_copy() for name, t in TERRITORIES.items()}
    return GameState(
        id="test",
        mode=mode,
        players=players,
        current_phase=phase,
        current_player_index=0,
        storm_sector=storm_sector,
        territories=territories,
        spice_bank=100,
    )


def _active_battle(
    attacker: FactionName,
    defender: FactionName,
    attacker_done: bool = False,
    defender_done: bool = False,
) -> ActiveBattle:
    return ActiveBattle(
        territory_name="Arrakeen",
        sector=1,
        attacker_faction=attacker,
        defender_faction=defender,
        attacker_prebattle_done=attacker_done,
        defender_prebattle_done=defender_done,
    )


# ===========================================================================
# Atreides Movement Prescience (engine injection)
# ===========================================================================

class TestAtreidesMovementPrescience:
    def _make_spice_card(self):
        from ..app.models.game_state import SpiceCard
        return SpiceCard(
            id="sc1",
            name="Hagga Basin",
            card_type="territory",
            territory_name="Hagga Basin",
            spice_amount=6,
        )

    def test_injected_when_atreides_present_advanced(self):
        """Prescience card is injected at shipment phase start in Advanced mode."""
        from ..app.services.game.engine import _inject_atreides_movement_prescience
        card = self._make_spice_card()
        atreides = _make_player("a1", "Atreides", FactionName.ATREIDES)
        game = _base_game([atreides], mode=GameMode.ADVANCED)
        game = game.model_copy(update={"spice_deck": [card]})

        result = _inject_atreides_movement_prescience(game)
        assert result.atreides_movement_prescience is not None
        assert result.atreides_movement_prescience["territory_name"] == "Hagga Basin"
        assert result.atreides_movement_prescience_seen is False

    def test_not_injected_in_basic_mode(self):
        """No injection in Basic mode."""
        from ..app.services.game.engine import _inject_atreides_movement_prescience
        card = self._make_spice_card()
        atreides = _make_player("a1", "Atreides", FactionName.ATREIDES)
        game = _base_game([atreides], mode=GameMode.BASIC)
        game = game.model_copy(update={"spice_deck": [card]})

        result = _inject_atreides_movement_prescience(game)
        assert result.atreides_movement_prescience is None

    def test_not_injected_without_atreides_player(self):
        """No injection if Atreides is not in the game."""
        from ..app.services.game.engine import _inject_atreides_movement_prescience
        card = self._make_spice_card()
        guild = _make_player("g1", "Guild", FactionName.SPACING_GUILD)
        game = _base_game([guild], mode=GameMode.ADVANCED)
        game = game.model_copy(update={"spice_deck": [card]})

        result = _inject_atreides_movement_prescience(game)
        assert result.atreides_movement_prescience is None

    def test_not_injected_with_empty_spice_deck(self):
        """No injection if the spice deck is empty."""
        from ..app.services.game.engine import _inject_atreides_movement_prescience
        atreides = _make_player("a1", "Atreides", FactionName.ATREIDES)
        game = _base_game([atreides], mode=GameMode.ADVANCED)
        game = game.model_copy(update={"spice_deck": []})

        result = _inject_atreides_movement_prescience(game)
        assert result.atreides_movement_prescience is None


# ===========================================================================
# BG Free Shipment
# ===========================================================================

class TestBGFreeShipment:
    """
    Tests for trigger_bg_free_shipment.

    As of the out-of-turn trigger implementation, the game state must have
    bg_free_ship_pending=True (set by ship_forces when a non-BG faction ships).
    Tests set this flag directly to isolate the free-ship logic.
    """

    def test_basic_ships_to_polar_sink(self):
        bg = _make_player("bg1", "BG", FactionName.BENE_GESSERIT, forces_in_reserve=5)
        game = _base_game([bg], mode=GameMode.BASIC).model_copy(update={
            "bg_free_ship_pending": True,
            "bg_free_ship_last_territory": "Hagga Basin",
        })

        result = trigger_bg_free_shipment(game, "bg1", "Polar Sink", 1)
        bg_after = next(p for p in result.players if p.id == "bg1")
        assert bg_after.forces_in_reserve == 4
        board_total = sum(fg.regular_count for fg in bg_after.forces_on_board)
        assert board_total == 1
        # Flag cleared after use
        assert result.bg_free_ship_pending is False

    def test_basic_cannot_ship_to_non_polar_sink(self):
        bg = _make_player("bg1", "BG", FactionName.BENE_GESSERIT, forces_in_reserve=5)
        game = _base_game([bg], mode=GameMode.BASIC).model_copy(update={
            "bg_free_ship_pending": True,
            "bg_free_ship_last_territory": "Hagga Basin",
        })

        with pytest.raises(ValueError, match="Polar Sink"):
            trigger_bg_free_shipment(game, "bg1", "Arrakeen", 1)

    def test_non_bg_cannot_use_ability(self):
        harkonnen = _make_player("h1", "Harkonnen", FactionName.HARKONNEN, forces_in_reserve=5)
        game = _base_game([harkonnen], mode=GameMode.ADVANCED).model_copy(update={
            "bg_free_ship_pending": True,
        })

        with pytest.raises(ValueError, match="Bene Gesserit"):
            trigger_bg_free_shipment(game, "h1", "Polar Sink", 0)

    def test_no_pending_raises(self):
        """Calling trigger without another faction having shipped should fail."""
        bg = _make_player("bg1", "BG", FactionName.BENE_GESSERIT, forces_in_reserve=5)
        game = _base_game([bg], mode=GameMode.BASIC)  # bg_free_ship_pending defaults False

        with pytest.raises(ValueError, match="pending"):
            trigger_bg_free_shipment(game, "bg1", "Polar Sink", 0)

    def test_no_reserve_forces_raises(self):
        bg = _make_player("bg1", "BG", FactionName.BENE_GESSERIT, forces_in_reserve=0)
        game = _base_game([bg], mode=GameMode.BASIC).model_copy(update={
            "bg_free_ship_pending": True,
            "bg_free_ship_last_territory": "Hagga Basin",
        })

        with pytest.raises(ValueError, match="No forces in reserve"):
            trigger_bg_free_shipment(game, "bg1", "Polar Sink", 0)

    def test_advanced_can_ship_as_fighter(self):
        bg = _make_player("bg1", "BG", FactionName.BENE_GESSERIT, forces_in_reserve=5)
        game = _base_game([bg], mode=GameMode.ADVANCED).model_copy(update={
            "bg_free_ship_pending": True,
            "bg_free_ship_last_territory": "Arrakeen",
        })

        result = trigger_bg_free_shipment(game, "bg1", "Arrakeen", 1, as_advisor=False)
        bg_after = next(p for p in result.players if p.id == "bg1")
        fighters = [fg for fg in bg_after.forces_on_board if not fg.is_advisor]
        assert sum(fg.regular_count for fg in fighters) == 1

    def test_advanced_as_advisor_in_occupied_territory(self):
        bg = _make_player("bg1", "BG", FactionName.BENE_GESSERIT, forces_in_reserve=5)
        atreides = _make_player(
            "a1", "Atreides", FactionName.ATREIDES,
            forces_on_board=[ForceGroup(territory_name="Arrakeen", sector=1, regular_count=2)],
        )
        game = _base_game([bg, atreides], mode=GameMode.ADVANCED).model_copy(update={
            "bg_free_ship_pending": True,
            "bg_free_ship_last_territory": "Arrakeen",
        })

        result = trigger_bg_free_shipment(game, "bg1", "Arrakeen", 1, as_advisor=True)
        bg_after = next(p for p in result.players if p.id == "bg1")
        advisors = [fg for fg in bg_after.forces_on_board if fg.is_advisor]
        assert sum(fg.regular_count for fg in advisors) == 1

    def test_advanced_as_advisor_in_unoccupied_becomes_fighter(self):
        bg = _make_player("bg1", "BG", FactionName.BENE_GESSERIT, forces_in_reserve=5)
        game = _base_game([bg], mode=GameMode.ADVANCED).model_copy(update={
            "bg_free_ship_pending": True,
            "bg_free_ship_last_territory": "Arrakeen",
        })

        # Arrakeen is unoccupied — force should land as fighter despite as_advisor=True
        result = trigger_bg_free_shipment(game, "bg1", "Arrakeen", 1, as_advisor=True)
        bg_after = next(p for p in result.players if p.id == "bg1")
        advisors = [fg for fg in bg_after.forces_on_board if fg.is_advisor]
        fighters = [fg for fg in bg_after.forces_on_board if not fg.is_advisor]
        assert sum(fg.regular_count for fg in advisors) == 0
        assert sum(fg.regular_count for fg in fighters) == 1

    def test_advanced_cannot_ship_to_wrong_territory(self):
        """Advanced BG may only ship to the triggering territory or Polar Sink."""
        bg = _make_player("bg1", "BG", FactionName.BENE_GESSERIT, forces_in_reserve=5)
        game = _base_game([bg], mode=GameMode.ADVANCED).model_copy(update={
            "bg_free_ship_pending": True,
            "bg_free_ship_last_territory": "Arrakeen",  # triggered by Arrakeen
        })

        with pytest.raises(ValueError, match="Arrakeen"):
            trigger_bg_free_shipment(game, "bg1", "Carthag", 5, as_advisor=False)


# ===========================================================================
# BG Advisor flip mechanics
# ===========================================================================

class TestBGAdvisorFlips:
    def _bg_with_advisors(self, territory: str = "Arrakeen", sector: int = 1) -> tuple[Player, GameState]:
        bg = _make_player(
            "bg1", "BG", FactionName.BENE_GESSERIT,
            forces_on_board=[
                ForceGroup(territory_name=territory, sector=sector, regular_count=2, is_advisor=True),
            ],
        )
        game = _base_game([bg], mode=GameMode.ADVANCED)
        return bg, game

    def _bg_with_fighters(self, territory: str = "Arrakeen", sector: int = 1) -> tuple[Player, GameState]:
        bg = _make_player(
            "bg1", "BG", FactionName.BENE_GESSERIT,
            forces_on_board=[
                ForceGroup(territory_name=territory, sector=sector, regular_count=3, is_advisor=False),
            ],
        )
        game = _base_game([bg], mode=GameMode.ADVANCED)
        return bg, game

    def test_flip_advisors_to_fighters(self):
        _, game = self._bg_with_advisors()
        result = flip_advisors_to_fighters(game, "bg1", "Arrakeen")
        bg_after = next(p for p in result.players if p.id == "bg1")
        fighters = [fg for fg in bg_after.forces_on_board if not fg.is_advisor]
        advisors = [fg for fg in bg_after.forces_on_board if fg.is_advisor]
        assert sum(fg.regular_count for fg in fighters) == 2
        assert sum(fg.regular_count for fg in advisors) == 0

    def test_flip_fighters_to_advisors(self):
        _, game = self._bg_with_fighters()
        result = flip_fighters_to_advisors(game, "bg1", "Arrakeen")
        bg_after = next(p for p in result.players if p.id == "bg1")
        fighters = [fg for fg in bg_after.forces_on_board if not fg.is_advisor]
        advisors = [fg for fg in bg_after.forces_on_board if fg.is_advisor]
        assert sum(fg.regular_count for fg in fighters) == 0
        assert sum(fg.regular_count for fg in advisors) == 3

    def test_flip_advisors_to_fighters_merges_with_existing_fighters(self):
        bg = _make_player(
            "bg1", "BG", FactionName.BENE_GESSERIT,
            forces_on_board=[
                ForceGroup(territory_name="Arrakeen", sector=1, regular_count=2, is_advisor=True),
                ForceGroup(territory_name="Arrakeen", sector=1, regular_count=1, is_advisor=False),
            ],
        )
        game = _base_game([bg], mode=GameMode.ADVANCED)
        result = flip_advisors_to_fighters(game, "bg1", "Arrakeen")
        bg_after = next(p for p in result.players if p.id == "bg1")
        fighters = [fg for fg in bg_after.forces_on_board if not fg.is_advisor]
        assert sum(fg.regular_count for fg in fighters) == 3

    def test_flip_advisors_requires_advanced_mode(self):
        bg = _make_player(
            "bg1", "BG", FactionName.BENE_GESSERIT,
            forces_on_board=[
                ForceGroup(territory_name="Arrakeen", sector=1, regular_count=1, is_advisor=True),
            ],
        )
        game = _base_game([bg], mode=GameMode.BASIC)
        with pytest.raises(ValueError, match="Advanced"):
            flip_advisors_to_fighters(game, "bg1", "Arrakeen")

    def test_flip_fighters_to_advisors_requires_advanced_mode(self):
        bg = _make_player(
            "bg1", "BG", FactionName.BENE_GESSERIT,
            forces_on_board=[
                ForceGroup(territory_name="Arrakeen", sector=1, regular_count=1, is_advisor=False),
            ],
        )
        game = _base_game([bg], mode=GameMode.BASIC)
        with pytest.raises(ValueError, match="Advanced"):
            flip_fighters_to_advisors(game, "bg1", "Arrakeen")

    def test_flip_advisors_no_advisors_raises(self):
        _, game = self._bg_with_fighters()
        with pytest.raises(ValueError, match="No advisors"):
            flip_advisors_to_fighters(game, "bg1", "Arrakeen")

    def test_flip_fighters_no_fighters_raises(self):
        _, game = self._bg_with_advisors()
        with pytest.raises(ValueError, match="No fighters"):
            flip_fighters_to_advisors(game, "bg1", "Arrakeen")


# ===========================================================================
# Guild Cross-shipment
# ===========================================================================

class TestGuildCrossShip:
    def _guild_game(self) -> tuple[Player, GameState]:
        guild = _make_player(
            "g1", "Guild", FactionName.SPACING_GUILD,
            spice=10,
            forces_on_board=[
                ForceGroup(territory_name="Arrakeen", sector=1, regular_count=4),
            ],
        )
        game = _base_game([guild])
        return guild, game

    def test_cross_ship_moves_forces(self):
        _, game = self._guild_game()
        result = guild_cross_ship(game, "g1", "Arrakeen", 1, "Carthag", 17, regular_count=2)
        guild_after = next(p for p in result.players if p.id == "g1")
        arrakeen_forces = sum(
            fg.regular_count for fg in guild_after.forces_on_board
            if fg.territory_name == "Arrakeen"
        )
        carthag_forces = sum(
            fg.regular_count for fg in guild_after.forces_on_board
            if fg.territory_name == "Carthag"
        )
        assert arrakeen_forces == 2
        assert carthag_forces == 2

    def test_cross_ship_costs_half_rounded_up(self):
        _, game = self._guild_game()
        result = guild_cross_ship(game, "g1", "Arrakeen", 1, "Carthag", 17, regular_count=3)
        guild_after = next(p for p in result.players if p.id == "g1")
        # 3 forces → normal cost 3 → half = ceil(3/2) = 2
        assert guild_after.spice == 10 - 2

    def test_cross_ship_spice_goes_to_bank(self):
        _, game = self._guild_game()
        result = guild_cross_ship(game, "g1", "Arrakeen", 1, "Carthag", 17, regular_count=3)
        assert result.spice_bank == game.spice_bank + 2

    def test_cross_ship_insufficient_spice_raises(self):
        guild = _make_player(
            "g1", "Guild", FactionName.SPACING_GUILD,
            spice=0,
            forces_on_board=[
                ForceGroup(territory_name="Arrakeen", sector=1, regular_count=4),
            ],
        )
        game = _base_game([guild])
        with pytest.raises(ValueError, match="spice"):
            guild_cross_ship(game, "g1", "Arrakeen", 1, "Carthag", 17, regular_count=2)

    def test_cross_ship_insufficient_forces_raises(self):
        _, game = self._guild_game()
        with pytest.raises(ValueError, match="regular forces"):
            guild_cross_ship(game, "g1", "Arrakeen", 1, "Carthag", 17, regular_count=10)

    def test_non_guild_cannot_cross_ship(self):
        atreides = _make_player(
            "a1", "Atreides", FactionName.ATREIDES,
            forces_on_board=[ForceGroup(territory_name="Arrakeen", sector=1, regular_count=2)],
        )
        game = _base_game([atreides])
        with pytest.raises(ValueError, match="Spacing Guild"):
            guild_cross_ship(game, "a1", "Arrakeen", 1, "Carthag", 17, regular_count=1)

    def test_cross_ship_zero_forces_raises(self):
        _, game = self._guild_game()
        with pytest.raises(ValueError, match="at least 1"):
            guild_cross_ship(game, "g1", "Arrakeen", 3, "Carthag", 3, regular_count=0)


# ===========================================================================
# Guild Ship-to-reserves
# ===========================================================================

class TestGuildShipToReserves:
    def _guild_game(self) -> tuple[Player, GameState]:
        guild = _make_player(
            "g1", "Guild", FactionName.SPACING_GUILD,
            spice=10,
            forces_in_reserve=3,
            forces_on_board=[
                ForceGroup(territory_name="Sietch Tabr", sector=13, regular_count=4),
            ],
        )
        game = _base_game([guild])
        return guild, game

    def test_ship_to_reserves_removes_from_board(self):
        _, game = self._guild_game()
        result = guild_ship_to_reserves(game, "g1", "Sietch Tabr", 13, regular_count=2)
        guild_after = next(p for p in result.players if p.id == "g1")
        on_board = sum(fg.regular_count for fg in guild_after.forces_on_board)
        assert on_board == 2

    def test_ship_to_reserves_adds_to_reserve(self):
        _, game = self._guild_game()
        result = guild_ship_to_reserves(game, "g1", "Sietch Tabr", 13, regular_count=2)
        guild_after = next(p for p in result.players if p.id == "g1")
        assert guild_after.forces_in_reserve == 3 + 2

    def test_ship_to_reserves_cost_1_per_2_rounded_up(self):
        _, game = self._guild_game()
        # 3 forces → ceil(3/2) = 2
        result = guild_ship_to_reserves(game, "g1", "Sietch Tabr", 13, regular_count=3)
        guild_after = next(p for p in result.players if p.id == "g1")
        assert guild_after.spice == 10 - 2

    def test_ship_to_reserves_spice_to_bank(self):
        _, game = self._guild_game()
        result = guild_ship_to_reserves(game, "g1", "Sietch Tabr", 13, regular_count=3)
        assert result.spice_bank == game.spice_bank + 2

    def test_non_guild_cannot_use(self):
        fremen = _make_player(
            "f1", "Fremen", FactionName.FREMEN,
            forces_on_board=[ForceGroup(territory_name="Sietch Tabr", sector=13, regular_count=3)],
        )
        game = _base_game([fremen])
        with pytest.raises(ValueError, match="Spacing Guild"):
            guild_ship_to_reserves(game, "f1", "Sietch Tabr", 13, regular_count=2)

    def test_zero_forces_raises(self):
        _, game = self._guild_game()
        with pytest.raises(ValueError, match="at least 1"):
            guild_ship_to_reserves(game, "g1", "Sietch Tabr", 13, regular_count=0)


# ===========================================================================
# BG Voice (pre-battle)
# ===========================================================================

class TestBGVoice:
    def _voice_game(self):
        bg = _make_player("bg1", "BG", FactionName.BENE_GESSERIT)
        harkonnen = _make_player("h1", "Harkonnen", FactionName.HARKONNEN)
        game = _base_game([bg, harkonnen], phase=GamePhase.BATTLE)
        ab = _active_battle(FactionName.BENE_GESSERIT, FactionName.HARKONNEN)
        return game.model_copy(update={"active_battle": ab})

    def test_bg_can_issue_voice(self):
        game = self._voice_game()
        result = issue_voice(game, "bg1", FactionName.HARKONNEN, "not_play", "shield")
        assert result.active_battle.voice_command == {"command": "not_play", "card_type": "shield"}
        assert result.active_battle.voice_target_faction == FactionName.HARKONNEN
        assert result.active_battle.voice_acknowledged is False

    def test_voice_marks_issuer_done(self):
        game = self._voice_game()
        result = issue_voice(game, "bg1", FactionName.HARKONNEN, "play", "poison_weapon")
        # BG is attacker
        assert result.active_battle.attacker_prebattle_done is True
        assert result.active_battle.defender_prebattle_done is False

    def test_voice_cannot_target_self(self):
        game = self._voice_game()
        with pytest.raises(ValueError, match="Cannot Voice your own faction"):
            issue_voice(game, "bg1", FactionName.BENE_GESSERIT, "play", "shield")

    def test_non_bg_cannot_voice(self):
        game = self._voice_game()
        with pytest.raises(ValueError, match="Bene Gesserit"):
            issue_voice(game, "h1", FactionName.BENE_GESSERIT, "play", "shield")

    def test_invalid_command_raises(self):
        game = self._voice_game()
        with pytest.raises(ValueError, match="Invalid command"):
            issue_voice(game, "bg1", FactionName.HARKONNEN, "maybe", "shield")

    def test_invalid_card_type_raises(self):
        game = self._voice_game()
        with pytest.raises(ValueError, match="Invalid card type"):
            issue_voice(game, "bg1", FactionName.HARKONNEN, "play", "mystery_card")

    def test_voice_only_once_per_battle(self):
        game = self._voice_game()
        game = issue_voice(game, "bg1", FactionName.HARKONNEN, "play", "shield")
        with pytest.raises(ValueError, match="already been issued"):
            issue_voice(game, "bg1", FactionName.HARKONNEN, "not_play", "snooper")

    def test_acknowledge_voice_marks_target_done(self):
        game = self._voice_game()
        game = issue_voice(game, "bg1", FactionName.HARKONNEN, "not_play", "shield")
        result = acknowledge_voice(game, "h1")
        assert result.active_battle.voice_acknowledged is True
        assert result.active_battle.defender_prebattle_done is True

    def test_wrong_player_cannot_acknowledge(self):
        game = self._voice_game()
        game = issue_voice(game, "bg1", FactionName.HARKONNEN, "not_play", "shield")
        with pytest.raises(ValueError, match="Voice target"):
            acknowledge_voice(game, "bg1")

    def test_acknowledge_without_voice_raises(self):
        game = self._voice_game()
        with pytest.raises(ValueError, match="No Voice command"):
            acknowledge_voice(game, "h1")


# ===========================================================================
# Atreides Battle Prescience
# ===========================================================================

class TestAtreidesBattlePrescience:
    def _prescience_game(self):
        atreides = _make_player("a1", "Atreides", FactionName.ATREIDES)
        harkonnen = _make_player("h1", "Harkonnen", FactionName.HARKONNEN)
        game = _base_game([atreides, harkonnen], phase=GamePhase.BATTLE)
        ab = _active_battle(FactionName.ATREIDES, FactionName.HARKONNEN)
        return game.model_copy(update={"active_battle": ab})

    def test_atreides_can_ask_prescience(self):
        game = self._prescience_game()
        result = ask_prescience(game, "a1", "weapon")
        assert result.active_battle.prescience_element_asked == "weapon"
        assert result.active_battle.attacker_prebattle_done is True

    def test_invalid_element_raises(self):
        game = self._prescience_game()
        with pytest.raises(ValueError, match="Invalid element"):
            ask_prescience(game, "a1", "lucky_charm")

    def test_prescience_only_once_per_battle(self):
        game = self._prescience_game()
        game = ask_prescience(game, "a1", "leader")
        with pytest.raises(ValueError, match="already been used"):
            ask_prescience(game, "a1", "weapon")

    def test_non_atreides_cannot_ask(self):
        game = self._prescience_game()
        with pytest.raises(ValueError, match="Atreides"):
            ask_prescience(game, "h1", "leader")

    def test_reveal_prescience_value(self):
        game = self._prescience_game()
        game = ask_prescience(game, "a1", "leader")
        result = reveal_prescience_value(game, "h1", "Feyd-Rautha Harkonnen")
        assert result.active_battle.prescience_revealed_value == "Feyd-Rautha Harkonnen"
        assert result.active_battle.defender_prebattle_done is True

    def test_reveal_without_question_raises(self):
        game = self._prescience_game()
        with pytest.raises(ValueError, match="No prescience question"):
            reveal_prescience_value(game, "h1", "Feyd-Rautha Harkonnen")

    def test_wrong_player_cannot_reveal(self):
        game = self._prescience_game()
        game = ask_prescience(game, "a1", "leader")
        with pytest.raises(ValueError, match="prescience target"):
            reveal_prescience_value(game, "a1", "some leader")


# ===========================================================================
# done_prebattle (pass pre-battle action)
# ===========================================================================

class TestDonePrebattle:
    def _simple_game(self):
        atreides = _make_player("a1", "Atreides", FactionName.ATREIDES)
        fremen = _make_player("f1", "Fremen", FactionName.FREMEN)
        game = _base_game([atreides, fremen], phase=GamePhase.BATTLE)
        ab = _active_battle(FactionName.ATREIDES, FactionName.FREMEN)
        return game.model_copy(update={"active_battle": ab})

    def test_done_prebattle_marks_attacker_done(self):
        game = self._simple_game()
        result = done_prebattle(game, "a1")
        assert result.active_battle.attacker_prebattle_done is True
        assert result.active_battle.defender_prebattle_done is False

    def test_done_prebattle_marks_defender_done(self):
        game = self._simple_game()
        result = done_prebattle(game, "f1")
        assert result.active_battle.attacker_prebattle_done is False
        assert result.active_battle.defender_prebattle_done is True

    def test_both_done_triggers_prebattle_complete(self):
        game = self._simple_game()
        game = done_prebattle(game, "a1")
        game = done_prebattle(game, "f1")
        assert game.active_battle.prebattle_complete is True

    def test_player_not_in_battle_raises(self):
        game = self._simple_game()
        guild = _make_player("g1", "Guild", FactionName.SPACING_GUILD)
        # Add guild to players but they're not in the battle
        game = game.model_copy(update={"players": list(game.players) + [guild]})
        with pytest.raises(ValueError, match="not in this battle"):
            done_prebattle(game, "g1")

    def test_no_active_battle_raises(self):
        atreides = _make_player("a1", "Atreides", FactionName.ATREIDES)
        game = _base_game([atreides], phase=GamePhase.BATTLE)
        # no active_battle set
        with pytest.raises(ValueError, match="No active battle"):
            done_prebattle(game, "a1")


# ===========================================================================
# Pre-battle complete blocks battle plan submission
# ===========================================================================

class TestPrebattleGatesBattlePlans:
    def test_submit_plan_blocked_when_prebattle_incomplete(self):
        from ..app.services.game.combat import submit_battle_plan
        atreides = _make_player(
            "a1", "Atreides", FactionName.ATREIDES,
            forces_on_board=[ForceGroup(territory_name="Arrakeen", sector=1, regular_count=3)],
        )
        harkonnen = _make_player(
            "h1", "Harkonnen", FactionName.HARKONNEN,
            forces_on_board=[ForceGroup(territory_name="Arrakeen", sector=1, regular_count=3)],
        )
        game = _base_game([atreides, harkonnen], phase=GamePhase.BATTLE)
        ab = _active_battle(
            FactionName.ATREIDES, FactionName.HARKONNEN,
            attacker_done=False, defender_done=False,
        )
        game = game.model_copy(update={"active_battle": ab})

        with pytest.raises(ValueError, match="Pre-battle phase not yet complete"):
            submit_battle_plan(game, "a1", forces_dialed=2)

    def test_submit_plan_allowed_when_both_sides_done(self):
        from ..app.services.game.combat import submit_battle_plan
        atreides = _make_player(
            "a1", "Atreides", FactionName.ATREIDES,
            forces_on_board=[ForceGroup(territory_name="Arrakeen", sector=1, regular_count=3)],
        )
        harkonnen = _make_player(
            "h1", "Harkonnen", FactionName.HARKONNEN,
            forces_on_board=[ForceGroup(territory_name="Arrakeen", sector=1, regular_count=3)],
        )
        game = _base_game([atreides, harkonnen], phase=GamePhase.BATTLE)
        ab = _active_battle(
            FactionName.ATREIDES, FactionName.HARKONNEN,
            attacker_done=True, defender_done=True,
        )
        game = game.model_copy(update={"active_battle": ab})

        # Should not raise for the attacker
        result = submit_battle_plan(game, "a1", forces_dialed=2)
        assert result.active_battle.attacker_plan is not None
