"""
FactionHandler — abstract base class for faction-specific game logic.

Each of the six factions has a concrete subclass that overrides only the
hooks relevant to that faction. The game engine calls these hooks at the
appropriate point in each phase without needing to know which faction it
is dealing with.

Default implementations represent the standard rule that most factions follow,
so subclasses only override where their rules differ.
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....models.card import TreacheryCard
    from ....models.faction import FactionData, FactionName
    from ....models.game_state import BattlePlan, GameState
    from ....models.leader import Leader
    from ....models.player import Player


class FactionHandler(ABC):
    """
    Abstract base class for all faction handlers.

    Each handler is a stateless singleton — it holds no game state of its own.
    All state is passed in via the GameState (and Player) arguments on each call.
    """

    # =========================================================================
    # STORM PHASE
    # =========================================================================

    def get_storm_move_options(self, game_state: GameState) -> list[int]:
        """
        Returns the valid storm movement distances for this faction to choose from.
        Standard rule: the top two Storm Deck cards are revealed and the first
        player picks one. Only the Fremen handler overrides this.
        """
        return []  # Empty means: use standard Storm Deck draw; no faction choice

    def is_immune_to_storm(self) -> bool:
        """
        Returns True if this faction's forces are never destroyed by the storm.
        Only Fremen override this.
        """
        return False

    # =========================================================================
    # SPICE BLOW PHASE
    # =========================================================================

    def is_immune_to_shai_hulud(self) -> bool:
        """
        Returns True if this faction's forces survive sandworm attacks.
        Standard rule: False. Only Fremen override this (always True).
        """
        return False

    def on_shai_hulud(self, game_state: GameState, territory: str) -> GameState:
        """
        Called when a Shai-Hulud card is revealed and a sandworm attacks
        a territory containing spice. Standard rule: all spice is removed.
        Fremen override this to be immune and may use the worm for movement.
        """
        return game_state

    # =========================================================================
    # CHOAM CHARITY PHASE
    # =========================================================================

    def get_choam_charity(self, player: Player, game_state: GameState) -> int:
        """
        Returns the spice this faction receives during CHOAM Charity.
        Standard rule: factions with 0 spice receive 2; factions with 1 receive 1.
        Bene Gesserit (Advanced) always receive 2 regardless of spice held.
        """
        if player.spice == 0:
            return 2
        if player.spice == 1:
            return 1
        return 0

    # =========================================================================
    # BIDDING PHASE
    # =========================================================================

    def on_card_revealed_for_bid(
        self, card: TreacheryCard, player: Player, game_state: GameState
    ) -> TreacheryCard | None:
        """
        Called before each Treachery Card goes up for auction.
        Standard rule: no special knowledge. Returns None.
        Atreides override this to receive the card details before bidding.
        """
        return None

    def on_card_purchased(
        self, card: TreacheryCard, player: Player, game_state: GameState
    ) -> list[TreacheryCard]:
        """
        Called when this faction successfully buys a Treachery Card.
        Returns a list of any additional cards this faction should receive.
        Standard rule: no additional cards. Returns [].
        Harkonnen (Advanced) override this to draw one extra card.
        """
        return []

    def get_max_treachery_cards(self, player: Player, game_state: GameState) -> int:
        """
        Returns the maximum number of Treachery Cards this faction may hold.
        Standard rule: 4. Harkonnen (Advanced): 8.
        """
        from ....data.factions import FACTION_DATA
        return FACTION_DATA[player.faction].max_treachery_cards

    # =========================================================================
    # REVIVAL PHASE
    # =========================================================================

    def get_free_revival_count(self, player: Player, game_state: GameState) -> int:
        """
        Returns how many forces this faction revives for free this turn.
        Standard rule: faction's fixed free_revival_per_turn value.
        """
        from ....data.factions import FACTION_DATA
        return FACTION_DATA[player.faction].free_revival_per_turn

    def get_traitor_cards_to_keep(self, player: Player, game_state: GameState) -> int:
        """
        Returns how many traitor cards this faction keeps at game start.
        Standard rule: 1. Harkonnen (Advanced): 4.
        """
        from ....data.factions import FACTION_DATA
        return FACTION_DATA[player.faction].traitor_cards_to_keep

    # =========================================================================
    # SHIPMENT & MOVEMENT PHASE
    # =========================================================================

    def calculate_shipment_cost(
        self,
        forces: int,
        territory: str,
        player: Player,
        game_state: GameState,
    ) -> int:
        """
        Returns the spice cost to ship `forces` forces to `territory`.
        Standard rule: 1 spice per force shipped from reserve.
        Fremen (Advanced): free to Polar Sink, half price elsewhere.
        Guild (Advanced): has additional shipment options.
        """
        return forces

    def get_max_movement_distance(self, player: Player, game_state: GameState) -> int:
        """
        Returns the maximum number of territory moves per turn.
        Standard rule: 1. Fremen (Advanced): 2.
        """
        return 1

    def can_ship_outside_shipment_phase(
        self, player: Player, game_state: GameState
    ) -> bool:
        """
        Returns True if this faction may ship forces outside the Shipment Phase.
        Standard rule: False. Spacing Guild (Advanced): True.
        """
        return False

    def on_other_faction_ships(
        self,
        shipping_player: Player,
        cost: int,
        player: Player,
        game_state: GameState,
    ) -> GameState:
        """
        Called when another faction ships forces, after the cost is paid.
        Standard rule: no effect.
        Emperor (Advanced): receives the shipment fee directly.
        """
        return game_state

    # =========================================================================
    # BATTLE PHASE
    # =========================================================================

    def get_special_force_strength(
        self, against_faction: FactionName, game_state: GameState
    ) -> int:
        """
        Returns how many regular forces each of this faction's special forces
        counts as in battle against `against_faction`.
        Standard rule: 2. Emperor's Sardaukar count as 1 vs Fremen.
        """
        return 2

    def on_battle_forces_lost(
        self, forces_lost: int, player: Player, game_state: GameState
    ) -> GameState:
        """
        Called after this faction loses forces in a battle resolution.
        Standard rule: no effect.
        Atreides (Advanced): accumulates losses toward Kwisatz Haderach activation.
        """
        return game_state

    def on_leader_killed(
        self, leader: Leader, killed_by: FactionName, player: Player, game_state: GameState
    ) -> GameState:
        """
        Called when one of this faction's leaders is killed in battle.
        Standard rule: leader goes to Tleilaxu Tanks.
        Harkonnen (Advanced): may capture the opponent's leader instead.
        """
        return game_state

    def can_use_leader(
        self, leader: Leader, player: Player, game_state: GameState
    ) -> bool:
        """
        Returns True if this faction may use the given leader in battle.
        Standard rule: leader must be AVAILABLE and belong to this faction.
        Harkonnen (Advanced): may also use captured enemy leaders.
        """
        from ....models.leader import LeaderStatus
        return (
            leader.status == LeaderStatus.AVAILABLE
            and leader.faction == player.faction
        )

    # =========================================================================
    # MENTAT PAUSE
    # =========================================================================

    def check_alternate_victory(
        self, player: Player, game_state: GameState
    ) -> bool:
        """
        Called during Mentat Pause to check faction-specific win conditions.
        Standard rule: no alternate win condition; returns False.
        Bene Gesserit (Advanced): checks Prediction win condition.
        Spacing Guild (Advanced): wins if no winner by end of turn 8.
        """
        return False
