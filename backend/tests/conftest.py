"""
Shared fixtures for Dune game tests.

Usage:
    cd DuneGame
    python -m pytest backend/tests/ -v
"""

import pytest

from backend.app.models.card import SpiceCard, SpiceCardType
from backend.app.models.faction import FactionName
from backend.app.models.game_state import GameMode, GamePhase, GameState
from backend.app.models.player import ForceGroup
from backend.app.services.game.bidding import init_bidding
from backend.app.services.game.nexus import init_nexus
from backend.app.services.game.setup import PlayerSetupConfig, create_game


# ---------------------------------------------------------------------------
# Player configuration fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def two_player_configs() -> list[PlayerSetupConfig]:
    """Minimum viable game: Atreides vs Harkonnen."""
    return [
        PlayerSetupConfig(
            player_id="p1",
            player_name="Paul",
            faction=FactionName.ATREIDES,
        ),
        PlayerSetupConfig(
            player_id="p2",
            player_name="Vladimir",
            faction=FactionName.HARKONNEN,
        ),
    ]


@pytest.fixture
def six_player_configs() -> list[PlayerSetupConfig]:
    """Full 6-player game with all factions."""
    return [
        PlayerSetupConfig(player_id="p1", player_name="Paul",     faction=FactionName.ATREIDES),
        PlayerSetupConfig(player_id="p2", player_name="Vladimir",  faction=FactionName.HARKONNEN),
        PlayerSetupConfig(player_id="p3", player_name="Gaius",     faction=FactionName.BENE_GESSERIT),
        PlayerSetupConfig(player_id="p4", player_name="Stilgar",   faction=FactionName.FREMEN),
        PlayerSetupConfig(player_id="p5", player_name="Edric",     faction=FactionName.SPACING_GUILD),
        PlayerSetupConfig(player_id="p6", player_name="Shaddam",   faction=FactionName.EMPEROR),
    ]


# ---------------------------------------------------------------------------
# GameState fixtures (with deterministic storm for reproducibility)
# ---------------------------------------------------------------------------

FIXED_STORM_SECTOR = 5  # Arbitrary, used for deterministic tests


@pytest.fixture
def basic_game(two_player_configs: list[PlayerSetupConfig]) -> GameState:
    """A 2-player Basic-mode game with a fixed storm sector."""
    return create_game(
        game_id="test-basic",
        player_configs=two_player_configs,
        mode=GameMode.BASIC,
        initial_storm_sector=FIXED_STORM_SECTOR,
    )


@pytest.fixture
def advanced_game(two_player_configs: list[PlayerSetupConfig]) -> GameState:
    """A 2-player Advanced-mode game with a fixed storm sector."""
    return create_game(
        game_id="test-advanced",
        player_configs=two_player_configs,
        mode=GameMode.ADVANCED,
        initial_storm_sector=FIXED_STORM_SECTOR,
    )


@pytest.fixture
def six_player_basic(six_player_configs: list[PlayerSetupConfig]) -> GameState:
    """A full 6-player Basic-mode game."""
    return create_game(
        game_id="test-6p-basic",
        player_configs=six_player_configs,
        mode=GameMode.BASIC,
        initial_storm_sector=FIXED_STORM_SECTOR,
    )


@pytest.fixture
def six_player_advanced(six_player_configs: list[PlayerSetupConfig]) -> GameState:
    """A full 6-player Advanced-mode game."""
    return create_game(
        game_id="test-6p-advanced",
        player_configs=six_player_configs,
        mode=GameMode.ADVANCED,
        initial_storm_sector=FIXED_STORM_SECTOR,
    )


# ---------------------------------------------------------------------------
# Phase-specific fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def game_with_forces_in_sand(six_player_basic: GameState) -> GameState:
    """
    A game where the Atreides player has forces manually placed in a sand
    sector (sector 15, The Great Flat) so storm damage can be tested.
    Storm starts at sector 15, moving counterclockwise.
    """
    atreides = next(p for p in six_player_basic.players if p.faction == FactionName.ATREIDES)
    # Add forces in The Great Flat at sector 15 (sand, not storm-protected)
    new_forces = list(atreides.forces_on_board) + [
        ForceGroup(
            territory_name="The Great Flat",
            sector=15,
            regular_count=5,
            special_count=0,
        ),
    ]
    updated_atreides = atreides.model_copy(update={
        "forces_on_board": new_forces,
        "forces_in_reserve": atreides.forces_in_reserve - 5,
    })
    updated_players = [
        updated_atreides if p.faction == FactionName.ATREIDES else p
        for p in six_player_basic.players
    ]
    return six_player_basic.model_copy(update={
        "players": updated_players,
        "storm_sector": 17,  # Storm at sector 17, moving counterclockwise
    })


@pytest.fixture
def game_at_spice_blow(basic_game: GameState) -> GameState:
    """A game state already in the SPICE_BLOW phase."""
    return basic_game.model_copy(update={
        "current_phase": GamePhase.SPICE_BLOW,
    })


@pytest.fixture
def game_at_choam(six_player_basic: GameState) -> GameState:
    """A 6-player game in the CHOAM_CHARITY phase with one broke player."""
    # Make the Fremen player broke (0 spice)
    updated_players = []
    for p in six_player_basic.players:
        if p.faction == FactionName.FREMEN:
            updated_players.append(p.model_copy(update={"spice": 0}))
        elif p.faction == FactionName.BENE_GESSERIT:
            updated_players.append(p.model_copy(update={"spice": 1}))
        else:
            updated_players.append(p)
    return six_player_basic.model_copy(update={
        "players": updated_players,
        "current_phase": GamePhase.CHOAM_CHARITY,
    })


@pytest.fixture
def game_at_bidding(basic_game: GameState) -> GameState:
    """A 2-player game initialised into the BIDDING phase with auctions ready."""
    game = basic_game.model_copy(update={
        "current_phase": GamePhase.CHOAM_CHARITY,
    })
    # Use the real init_bidding to set up the auction properly
    from backend.app.services.game.phases import resolve_choam_charity
    game = resolve_choam_charity(game)
    return init_bidding(game)


@pytest.fixture
def game_at_nexus(basic_game: GameState) -> GameState:
    """A 2-player game initialised into the NEXUS phase (Shai-Hulud was drawn)."""
    base = basic_game.model_copy(update={
        "current_phase": GamePhase.NEXUS,
        "nexus_triggered": True,
    })
    return init_nexus(base)


@pytest.fixture
def six_player_nexus(six_player_basic: GameState) -> GameState:
    """A 6-player game initialised into the NEXUS phase."""
    base = six_player_basic.model_copy(update={
        "current_phase": GamePhase.NEXUS,
        "nexus_triggered": True,
    })
    return init_nexus(base)


@pytest.fixture
def game_at_bidding_6p(six_player_advanced: GameState) -> GameState:
    """A 6-player Advanced game in BIDDING — tests Emperor revenue + Harkonnen bonus."""
    game = six_player_advanced.model_copy(update={
        "current_phase": GamePhase.CHOAM_CHARITY,
    })
    from backend.app.services.game.phases import resolve_choam_charity
    game = resolve_choam_charity(game)
    return init_bidding(game)
