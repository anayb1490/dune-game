from typing import Optional

from pydantic import BaseModel, Field

from .card import TreacheryCard, TraitorCard, PredictionCard
from .faction import FactionName
from .leader import Leader


# =============================================================================
# Force placement
# =============================================================================

class ForceGroup(BaseModel):
    """
    A stack of forces belonging to one player, occupying a specific sector
    within a territory.

    A single player may have multiple ForceGroups in the same territory if
    their forces are spread across different sectors — this matters for storm
    resolution, which sweeps forces in specific sectors only.

    Special forces (Sardaukar / Fedaykin) are tracked separately from regular
    forces because they have different combat strength and revival costs.

    Advanced (Bene Gesserit): the `is_advisor` flag distinguishes Advisor tokens
    (non-combatant observers that do not trigger or participate in battles) from
    Fighter tokens. An Advisor stack and a Fighter stack in the same sector are
    represented as two separate ForceGroup entries.
    """
    territory_name: str
    sector: int = Field(ge=0, le=17)
    regular_count: int = Field(default=0, ge=0)
    special_count: int = Field(
        default=0,
        ge=0,
        description="Advanced: Sardaukar (Emperor), Fedaykin (Fremen), or BG fighters."
    )
    is_advisor: bool = Field(
        default=False,
        description="Advanced (Bene Gesserit only): True if these forces are in "
                    "Advisor mode and cannot participate in combat."
    )


# =============================================================================
# Faction-specific Advanced sub-models
# =============================================================================

class KwisatzHaderach(BaseModel):
    """
    Advanced (Atreides only): tracks the state of the Kwisatz Haderach.

    The KH token becomes available after the Atreides have accumulated
    7 or more total force losses across any battles. Once available, the
    Atreides player may deploy him to a territory as a leader with +2 bonus
    strength. He is removed (and the counter resets) if he is ever killed
    in battle.
    """
    is_active: bool = False
    force_losses_accumulated: int = Field(
        default=0,
        ge=0,
        description="Cumulative Atreides force losses. KH activates at 7."
    )
    territory: Optional[str] = Field(
        default=None,
        description="Territory where the KH is currently deployed, if active."
    )


class Prediction(BaseModel):
    """
    Advanced (Bene Gesserit only): the BG player's secret win-condition.

    At game start the BG player secretly chooses one Faction card and one
    Turn card. If, at any Mentat Pause, the predicted faction controls
    the required number of strongholds AND it is the predicted turn, the
    BG player wins immediately — even if another faction would also win.
    """
    faction: Optional[FactionName] = None
    turn: Optional[int] = Field(default=None, ge=1, le=10)
    is_revealed: bool = False


# =============================================================================
# Player
# =============================================================================

class Player(BaseModel):
    """
    All mutable runtime state for a single player during a game.

    Static faction data (starting positions, ability flags, etc.) is stored
    separately in FactionData and looked up by `faction` when needed.
    """
    id: str
    name: str
    faction: FactionName

    # Spice
    spice: int = Field(default=0, ge=0)

    # Treachery hand
    # Most factions: max 4 cards. Harkonnen (Advanced): max 8.
    treachery_hand: list[TreacheryCard] = Field(default_factory=list)

    # Traitor cards
    # Most factions keep 1 face-down traitor card.
    # Harkonnen (Advanced) keeps all 4 dealt to them.
    traitor_cards: list[TraitorCard] = Field(default_factory=list)

    # Forces on the board
    forces_on_board: list[ForceGroup] = Field(default_factory=list)

    # Forces off the board
    forces_in_reserve: int = Field(default=0, ge=0)
    forces_in_tanks: int = Field(
        default=0,
        ge=0,
        description="Regular forces in the Tleilaxu Tanks awaiting revival."
    )

    # Advanced: special forces (Sardaukar / Fedaykin / BG fighters)
    special_forces_in_reserve: int = Field(default=0, ge=0)
    special_forces_in_tanks: int = Field(default=0, ge=0)

    # Leaders
    leaders: list[Leader] = Field(default_factory=list)

    # Alliance
    ally: Optional[FactionName] = Field(
        default=None,
        description="The faction this player is currently allied with, if any."
    )

    # Status
    is_eliminated: bool = False
    moves_this_turn: int = Field(
        default=0,
        ge=0,
        description="Number of moves made this Shipment & Movement turn. "
                    "Standard: max 1. Fremen (Advanced): max 2."
    )
    forces_revived_this_turn: int = Field(
        default=0,
        ge=0,
        description="Total forces (free + paid) revived this Revival phase. "
                    "Combined cap is 3 per turn."
    )
    leader_revived_this_turn: bool = Field(
        default=False,
        description="Whether this player has already revived a leader this Revival phase. "
                    "Only one leader may be revived per turn."
    )

    # -------------------------------------------------------------------------
    # Faction-specific Advanced state
    # -------------------------------------------------------------------------

    # Atreides only — None for all other factions
    kwisatz_haderach: Optional[KwisatzHaderach] = None

    # Bene Gesserit only — None for all other factions
    # Also stored by reference on GameState for efficient win-condition checking.
    prediction: Optional[Prediction] = None
