from __future__ import annotations

from typing import TYPE_CHECKING

from .base import FactionHandler

if TYPE_CHECKING:
    from ....models.game_state import GameState
    from ....models.player import Player

POLAR_SINK = "Polar Sink"
GREAT_FLAT = "The Great Flat"


class FremenHandler(FactionHandler):
    """
    Fremen faction handler.

    Basic:    Forces are never destroyed by sandworms or storm (inherent).
    Advanced: SANDWORM_RIDER — may use sandworms for movement.
              FREE_POLAR_SINK_SHIPMENT — ships any forces to Polar Sink free.
              FREE_GREAT_FLAT_SHIPMENT — ships any forces to The Great Flat free.
              HALF_PRICE_SHIPMENT — all other shipments at half spice cost.
              FEDAYKIN — 3 special forces, each counting as 2 in battle.
              DOUBLE_MOVEMENT — may move through 2 territories per turn.
              SPECIAL_VICTORY — wins by controlling Sietch Tabr, Habbanya Sietch,
                and Tuek's Sietch (with no allies).
    """

    # -------------------------------------------------------------------------
    # Storm Phase
    # -------------------------------------------------------------------------

    def is_immune_to_storm(self) -> bool:
        """
        Fremen forces are never destroyed by the storm, in both Basic and
        Advanced game modes.
        """
        return True

    # -------------------------------------------------------------------------
    # Spice Blow Phase
    # -------------------------------------------------------------------------

    def is_immune_to_shai_hulud(self) -> bool:
        """
        Fremen forces are never destroyed by sandworm attacks.
        This is inherent to the Fremen in both Basic and Advanced modes.
        """
        return True

    # -------------------------------------------------------------------------
    # Shipment & Movement Phase
    # -------------------------------------------------------------------------

    def calculate_shipment_cost(
        self,
        forces: int,
        territory: str,
        player: Player,
        game_state: GameState,
    ) -> int:
        """
        Advanced:
          - Shipping to Polar Sink or The Great Flat costs 0 spice.
          - All other shipments cost half the normal rate (rounded up).
        Basic: standard cost (1 spice per force).
        """
        if game_state.mode.value != "advanced":
            return forces

        if territory == POLAR_SINK or territory == GREAT_FLAT:
            return 0

        # Half price, rounded up
        return -(-forces // 2)  # ceiling division

    def get_max_movement_distance(self, player: Player, game_state: GameState) -> int:
        """
        Advanced: Fremen may move through 2 territories per turn
        instead of the standard 1.
        """
        if game_state.mode.value != "advanced":
            return 1
        return 2

    # -------------------------------------------------------------------------
    # Mentat Pause
    # -------------------------------------------------------------------------

    def check_alternate_victory(
        self, player: Player, game_state: GameState
    ) -> bool:
        """
        Advanced: Fremen win if they control Sietch Tabr, Habbanya Sietch,
        and Tuek's Sietch, AND they have no ally. This is checked before
        the normal stronghold victory, so Fremen can win even without
        controlling the standard 3 strongholds.
        """
        if game_state.mode.value != "advanced":
            return False

        # Fremen special victory requires no ally
        if player.ally is not None:
            return False

        # Must control these 3 specific strongholds
        required = {"Sietch Tabr", "Habbanya Sietch", "Tuek's Sietch"}
        controlled = set()

        for name in required:
            # Check if Fremen have forces there and no enemy does
            fremen_present = any(
                fg.territory_name == name
                and (fg.regular_count + fg.special_count) > 0
                for fg in player.forces_on_board
            )
            if not fremen_present:
                return False

            enemy_present = any(
                p.faction != player.faction
                and any(
                    fg.territory_name == name
                    and (fg.regular_count + fg.special_count) > 0
                    and not fg.is_advisor  # BG advisors don't block
                    for fg in p.forces_on_board
                )
                for p in game_state.players
                if not p.is_eliminated
            )
            if enemy_present:
                return False

            controlled.add(name)

        return controlled == required
