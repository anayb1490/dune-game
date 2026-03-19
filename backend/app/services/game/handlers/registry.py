"""
Handler registry — maps each FactionName to its singleton FactionHandler.

Usage:
    from backend.app.services.game.handlers.registry import get_handler

    handler = get_handler(player.faction)
    cost = handler.calculate_shipment_cost(forces, territory, player, game_state)
"""

from ....models.faction import FactionName
from .atreides import AtreidesHandler
from .bene_gesserit import BeneGesseritHandler
from .base import FactionHandler
from .emperor import EmperorHandler
from .fremen import FremenHandler
from .harkonnen import HarkonnenHandler
from .spacing_guild import SpacingGuildHandler

# Singleton instances — handlers are stateless so one instance per faction suffices
_REGISTRY: dict[FactionName, FactionHandler] = {
    FactionName.ATREIDES:      AtreidesHandler(),
    FactionName.HARKONNEN:     HarkonnenHandler(),
    FactionName.BENE_GESSERIT: BeneGesseritHandler(),
    FactionName.FREMEN:        FremenHandler(),
    FactionName.SPACING_GUILD: SpacingGuildHandler(),
    FactionName.EMPEROR:       EmperorHandler(),
}


def get_handler(faction: FactionName) -> FactionHandler:
    """
    Returns the FactionHandler for the given faction.
    Raises KeyError if the faction has no registered handler.
    """
    return _REGISTRY[faction]
