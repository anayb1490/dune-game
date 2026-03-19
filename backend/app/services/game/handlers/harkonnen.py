from __future__ import annotations

from typing import TYPE_CHECKING

from .base import FactionHandler

if TYPE_CHECKING:
    from ....models.card import TreacheryCard
    from ....models.game_state import GameState
    from ....models.leader import Leader
    from ....models.faction import FactionName
    from ....models.player import Player


class HarkonnenHandler(FactionHandler):
    """
    House Harkonnen faction handler.

    Basic:    EXTRA_TREACHERY_CARDS — always receives 2 cards at game start.
    Advanced: CAPTURE_LEADERS — keeps all 4 traitor cards; draws 1 extra
              Treachery Card whenever they win an auction; may hold up to 8
              cards; may use captured enemy leaders in their own battles.
    """

    # -------------------------------------------------------------------------
    # Bidding Phase
    # -------------------------------------------------------------------------

    def on_card_purchased(
        self, card: TreacheryCard, player: Player, game_state: GameState
    ) -> list[TreacheryCard]:
        """
        Advanced: after winning a Treachery Card at auction, Harkonnen
        immediately draws one additional card from the top of the deck.
        The engine uses the returned list to deal those extra cards.
        """
        if game_state.mode.value != "advanced":
            return []

        if not game_state.treachery_deck:
            return []

        # Return the top card of the deck as the bonus draw
        return [game_state.treachery_deck[0]]

    # -------------------------------------------------------------------------
    # Battle Phase
    # -------------------------------------------------------------------------

    def on_leader_killed(
        self,
        leader: Leader,
        killed_by: FactionName,
        player: Player,
        game_state: GameState,
    ) -> GameState:
        """
        Advanced: when an enemy leader is killed fighting against Harkonnen,
        Harkonnen may capture that leader. The captured leader's status is set
        to CAPTURED and their captured_by field is set to Harkonnen.
        The captured leader can then be used by Harkonnen in future battles.
        Standard tanks placement is skipped for captured leaders.
        """
        if game_state.mode.value != "advanced":
            return game_state

        from ....models.leader import LeaderStatus

        # Only capture enemy leaders (not Harkonnen's own leaders)
        if leader.faction == player.faction:
            return game_state

        updated_leader = leader.model_copy(
            update={
                "status": LeaderStatus.CAPTURED,
                "captured_by": player.faction,
            }
        )
        # Update the leader on its owning player
        updated_players = []
        for p in game_state.players:
            updated_leaders = [
                updated_leader if ldr.id == leader.id else ldr
                for ldr in p.leaders
            ]
            updated_players.append(p.model_copy(update={"leaders": updated_leaders}))

        return game_state.model_copy(update={"players": updated_players})

    def can_use_leader(
        self, leader: Leader, player: Player, game_state: GameState
    ) -> bool:
        """
        Advanced: Harkonnen may use any leader they have captured, in addition
        to their own available leaders.
        """
        from ....models.leader import LeaderStatus
        from ....models.faction import FactionName

        if leader.status == LeaderStatus.AVAILABLE and leader.faction == player.faction:
            return True

        if (
            game_state.mode.value == "advanced"
            and leader.status == LeaderStatus.CAPTURED
            and leader.captured_by == FactionName.HARKONNEN
        ):
            return True

        return False
