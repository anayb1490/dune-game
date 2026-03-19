from __future__ import annotations

from typing import TYPE_CHECKING

from .base import FactionHandler

if TYPE_CHECKING:
    from ....models.card import TreacheryCard
    from ....models.game_state import GameState
    from ....models.player import Player


class AtreidesHandler(FactionHandler):
    """
    House Atreides faction handler.

    Basic:    PRESCIENCE — sees each Treachery Card before it is bid on.
    Advanced: KWISATZ_HADERACH — after 7 cumulative force losses the KH
              token activates as a leader with +2 bonus strength.
    """

    # -------------------------------------------------------------------------
    # Bidding Phase
    # -------------------------------------------------------------------------

    def on_card_revealed_for_bid(
        self, card: TreacheryCard, player: Player, game_state: GameState
    ) -> TreacheryCard | None:
        """
        Returns the card so the engine can reveal its full details to the
        Atreides player before bidding opens. Other players are notified
        that Atreides has looked, but do not see the card contents.
        """
        return card

    # -------------------------------------------------------------------------
    # Battle Phase
    # -------------------------------------------------------------------------

    def on_battle_forces_lost(
        self, forces_lost: int, player: Player, game_state: GameState
    ) -> GameState:
        """
        Advanced: accumulates force losses toward KH activation (threshold: 7).
        Once losses reach 7 the KH becomes active. If the KH is subsequently
        killed, the counter resets and he becomes unavailable until 7 more
        losses accumulate.
        """
        if game_state.mode.value != "advanced" or player.kwisatz_haderach is None:
            return game_state

        kh = player.kwisatz_haderach
        new_total = kh.force_losses_accumulated + forces_lost
        updated_kh = kh.model_copy(
            update={
                "force_losses_accumulated": new_total,
                "is_active": new_total >= 7,
            }
        )
        updated_player = player.model_copy(update={"kwisatz_haderach": updated_kh})
        updated_players = [
            updated_player if p.faction == player.faction else p
            for p in game_state.players
        ]
        return game_state.model_copy(update={"players": updated_players})
