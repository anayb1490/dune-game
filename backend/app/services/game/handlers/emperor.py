from __future__ import annotations

from typing import TYPE_CHECKING

from .base import FactionHandler

if TYPE_CHECKING:
    from ....models.faction import FactionName
    from ....models.game_state import GameState
    from ....models.player import Player


class EmperorHandler(FactionHandler):
    """
    The Emperor faction handler.

    Basic:    RECEIVES_SHIPMENT_FEES — collects all spice paid by other
              factions for shipment (goes to spice bank in Basic; Emperor
              receives it directly in Advanced).
    Advanced: SARDAUKAR — 5 special forces. Each counts as 2 regular forces
              in battle against all factions except Fremen, against whom
              Sardaukar count as only 1.
    """

    # -------------------------------------------------------------------------
    # Shipment & Movement Phase
    # -------------------------------------------------------------------------

    def on_other_faction_ships(
        self,
        shipping_player: Player,
        cost: int,
        player: Player,
        game_state: GameState,
    ) -> GameState:
        """
        Advanced: the Emperor receives the shipment fee directly from the
        faction that is shipping, rather than it going to the spice bank.
        The spice transfer itself is handled by the engine; this hook
        signals that the Emperor should be the recipient.
        """
        if game_state.mode.value != "advanced":
            return game_state

        updated_emperor = player.model_copy(update={"spice": player.spice + cost})
        updated_players = [
            updated_emperor if p.faction == player.faction else p
            for p in game_state.players
        ]
        return game_state.model_copy(update={"players": updated_players})

    # -------------------------------------------------------------------------
    # Battle Phase
    # -------------------------------------------------------------------------

    def get_special_force_strength(
        self, against_faction: FactionName, game_state: GameState
    ) -> int:
        """
        Advanced: Sardaukar count as 2 regular forces in battle against all
        factions except the Fremen, against whom they count as only 1.
        The Fremen's desert fighting expertise neutralises the Sardaukar edge.
        """
        if game_state.mode.value != "advanced":
            return 2

        from ....models.faction import FactionName as FN
        if against_faction == FN.FREMEN:
            return 1

        return 2
