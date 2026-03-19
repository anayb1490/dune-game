from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FactionName(str, Enum):
    ATREIDES = "atreides"
    HARKONNEN = "harkonnen"
    BENE_GESSERIT = "bene_gesserit"
    FREMEN = "fremen"
    SPACING_GUILD = "spacing_guild"
    EMPEROR = "emperor"


class FactionAbility(str, Enum):
    """
    Named abilities a faction may possess.
    Abilities are split into two sets on FactionData: `basic_abilities`
    (available in both game modes) and `advanced_abilities` (Advanced only).

    The FactionHandler for each faction implements the actual game logic
    triggered by these abilities; this enum is purely declarative data used
    for rules display, client rendering, and quick membership checks.
    """

    # -- Basic abilities -------------------------------------------------------

    # Atreides: may look at each Treachery Card before it is bid on
    PRESCIENCE = "prescience"

    # Harkonnen: receives 2 Treachery Cards at game start; buys 1 extra
    #            card whenever they purchase one at auction
    EXTRA_TREACHERY_CARDS = "extra_treachery_cards"

    # Emperor: receives all spice paid by other factions for shipment
    RECEIVES_SHIPMENT_FEES = "receives_shipment_fees"

    # Spacing Guild: no faction may ship forces without Guild consent
    CONTROLS_SHIPMENT = "controls_shipment"

    # -- Advanced abilities ----------------------------------------------------

    # Atreides: Kwisatz Haderach token unlocks after 7 cumulative force losses
    KWISATZ_HADERACH = "kwisatz_haderach"

    # Harkonnen: may hold up to 8 Treachery Cards; keeps all 4 dealt traitor
    #            cards; may capture defeated enemy leaders for own use
    CAPTURE_LEADERS = "capture_leaders"

    # Bene Gesserit: alternate instant win condition via secret Prediction
    PREDICTION = "prediction"

    # Bene Gesserit: forces placed as non-combatant Advisors that can flip
    #                to Fighters when their co-occupying ally enters combat
    ADVISORS = "advisors"

    # Fremen: forces immune to sandworm attacks; may use sandworms to move
    SANDWORM_RIDER = "sandworm_rider"

    # Fremen: may ship any number of forces to Polar Sink for free each turn
    FREE_POLAR_SINK_SHIPMENT = "free_polar_sink_shipment"

    # Fremen: ships all other forces at half the normal spice cost
    HALF_PRICE_SHIPMENT = "half_price_shipment"

    # Spacing Guild: may ship forces at any point during any phase (not just
    #                the Shipment Phase); has additional shipment options
    SHIP_ANYTIME = "ship_anytime"

    # Emperor: 5 Sardaukar special forces (count as 2 except vs Fremen)
    SARDAUKAR = "sardaukar"

    # Fremen: 3 Fedaykin special forces (always count as 2)
    FEDAYKIN = "fedaykin"


class SpecialForceInfo(BaseModel):
    """Describes a faction's elite unit type (Advanced game only)."""
    name: str
    combat_strength: int = Field(
        default=2,
        description="How many regular forces this unit counts as in battle. "
                    "Sardaukar vs Fremen exception is handled in EmperorHandler."
    )


class StartingPosition(BaseModel):
    """A faction's initial force placement on the board at game start."""
    territory: str
    regular_forces: int = 0
    special_forces: int = 0  # Advanced only


class FactionData(BaseModel):
    """
    Static reference data for a faction. This never changes during a game.
    All mutable runtime state lives on the Player model.
    All faction-specific game logic lives in the corresponding FactionHandler.
    """
    name: FactionName
    display_name: str
    starting_spice: int

    # Forces
    total_regular_forces: int
    starting_reserve: int = Field(description="Forces held off-board at game start")
    starting_positions: list[StartingPosition] = Field(
        default_factory=list,
        description="On-board force placements at game start"
    )
    free_revival_per_turn: int = Field(
        description="Forces revived for free each Revival Phase"
    )

    # Treachery hand limits
    max_treachery_cards: int = Field(
        default=4,
        description="Max cards in hand. Harkonnen (Advanced) may hold up to 8."
    )
    starting_treachery_cards: int = Field(
        default=1,
        description="Cards dealt at game start. Harkonnen always receives 2."
    )
    traitor_cards_to_keep: int = Field(
        default=1,
        description="How many traitor cards this faction keeps at game start. "
                    "Harkonnen (Advanced) keeps all 4."
    )

    # Special forces (Advanced only)
    special_force_info: Optional[SpecialForceInfo] = None
    total_special_forces: int = 0

    # Abilities — split by game mode
    basic_abilities: set[FactionAbility] = Field(
        default_factory=set,
        description="Abilities available in both Basic and Advanced game modes."
    )
    advanced_abilities: set[FactionAbility] = Field(
        default_factory=set,
        description="Abilities available in Advanced game mode only."
    )

    def has_ability(self, ability: FactionAbility, advanced: bool = False) -> bool:
        """
        Returns True if this faction possesses the given ability.
        Pass advanced=True to also check advanced_abilities.
        """
        if ability in self.basic_abilities:
            return True
        if advanced and ability in self.advanced_abilities:
            return True
        return False
