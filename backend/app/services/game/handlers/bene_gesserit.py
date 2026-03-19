from __future__ import annotations

from typing import TYPE_CHECKING

from .base import FactionHandler

if TYPE_CHECKING:
    from ....models.game_state import GameState
    from ....models.player import Player


class BeneGesseritHandler(FactionHandler):
    """
    Bene Gesserit faction handler.

    Basic:    No unique basic abilities.
    Advanced: PREDICTION — secret alternate instant win condition.
              ADVISORS — dual-mode Advisor/Fighter tokens.
              Always receives 2 spice CHOAM Charity regardless of spice held.
    """

    # -------------------------------------------------------------------------
    # CHOAM Charity Phase
    # -------------------------------------------------------------------------

    def get_choam_charity(self, player: Player, game_state: GameState) -> int:
        """
        Advanced: Bene Gesserit always receive 2 spice CHOAM Charity,
        regardless of how much spice they currently hold.
        Basic: falls back to standard rules (2 if 0 spice, 1 if 1 spice).
        """
        if game_state.mode.value == "advanced":
            return 2
        return super().get_choam_charity(player, game_state)

    # -------------------------------------------------------------------------
    # Mentat Pause
    # -------------------------------------------------------------------------

    def check_alternate_victory(
        self, player: Player, game_state: GameState
    ) -> bool:
        """
        Advanced: BG wins instantly if, at Mentat Pause, the faction they
        predicted controls the number of strongholds required to win, AND
        it is the turn they predicted.

        The win is checked even if another faction would also win normally —
        BG prediction takes precedence.
        """
        if game_state.mode.value != "advanced":
            return False

        if player.prediction is None:
            return False

        prediction = player.prediction
        if prediction.faction is None or prediction.turn is None:
            return False

        if game_state.current_turn != prediction.turn:
            return False

        # Find the predicted faction's player and count their stronghold control
        predicted_player = next(
            (p for p in game_state.players if p.faction == prediction.faction),
            None,
        )
        if predicted_player is None or predicted_player.is_eliminated:
            return False

        strongholds_controlled = _count_strongholds_controlled(
            predicted_player, game_state
        )

        # Standard win requires 3 strongholds (solo) or 4 (with ally)
        win_threshold = 4 if predicted_player.ally is not None else 3
        return strongholds_controlled >= win_threshold


def _count_strongholds_controlled(player: Player, game_state: GameState) -> int:
    """
    Returns the number of stronghold territories where the given player
    has at least one force present (and no enemy forces).
    """
    from ....models.territory import TerritoryType

    controlled = 0
    for name, territory in game_state.territories.items():
        if territory.territory_type != TerritoryType.STRONGHOLD:
            continue

        # Check if this player has forces here
        player_forces = sum(
            fg.regular_count + fg.special_count
            for fg in player.forces_on_board
            if fg.territory_name == name and not fg.is_advisor
        )
        if player_forces == 0:
            continue

        # Check no enemy forces present
        enemy_present = any(
            p.faction != player.faction
            and any(
                fg.territory_name == name
                and (fg.regular_count + fg.special_count) > 0
                and not fg.is_advisor
                for fg in p.forces_on_board
            )
            for p in game_state.players
        )
        if not enemy_present:
            controlled += 1

    return controlled
