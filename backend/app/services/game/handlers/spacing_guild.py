from __future__ import annotations

from typing import TYPE_CHECKING

from .base import FactionHandler

if TYPE_CHECKING:
    from ....models.game_state import GameState
    from ....models.player import Player

# The Guild wins if no other faction has won by the end of this turn
GUILD_ALTERNATE_VICTORY_TURN = 8


class SpacingGuildHandler(FactionHandler):
    """
    Spacing Guild faction handler.

    Basic:    CONTROLS_SHIPMENT — all factions must ship through the Guild;
              Guild receives all shipment fees (routed to spice bank in Basic).
    Advanced: SHIP_ANYTIME — may ship forces during any phase, not just the
              Shipment Phase. Alternate win condition: wins if no other
              faction wins by the end of turn 8.
    """

    # -------------------------------------------------------------------------
    # Shipment & Movement Phase
    # -------------------------------------------------------------------------

    def can_ship_outside_shipment_phase(
        self, player: Player, game_state: GameState
    ) -> bool:
        """
        Advanced: the Guild may ship forces at any point during any phase.
        """
        return game_state.mode.value == "advanced"

    # -------------------------------------------------------------------------
    # Mentat Pause
    # -------------------------------------------------------------------------

    def check_alternate_victory(
        self, player: Player, game_state: GameState
    ) -> bool:
        """
        Advanced: the Guild wins if no other faction has achieved victory
        by the end of turn 8. This is checked during Mentat Pause after
        all other win conditions have been evaluated.
        """
        if game_state.mode.value != "advanced":
            return False

        if game_state.current_turn < GUILD_ALTERNATE_VICTORY_TURN:
            return False

        # Guild wins only if no other faction has won
        return game_state.winner is None
