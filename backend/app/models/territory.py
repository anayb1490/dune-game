from enum import Enum

from pydantic import BaseModel, Field


class TerritoryType(str, Enum):
    SAND = "sand"           # Open desert; subject to storm and sandworm
    ROCK = "rock"           # Sheltered; storm does not affect forces here
    STRONGHOLD = "stronghold"  # Rock territory that counts for victory condition
    POLAR_SINK = "polar_sink"  # Central region; immune to storm, free haven


class Territory(BaseModel):
    """
    Represents a single named territory on the Arrakeen board.

    Static fields define the board geography and never change.
    The only mutable runtime field is `current_spice`, which fluctuates
    as spice is blown, collected, and consumed.

    Force occupancy is NOT stored here — it lives on each Player's
    `forces_on_board` list as ForceGroup objects. This keeps territory
    models lean and avoids deeply nested mutable state.

    Adjacency between territories is stored in a separate static data
    structure (see services/game/board_data.py) to avoid circular references.
    """

    name: str

    territory_type: TerritoryType

    sectors: list[int] = Field(
        description="Sector indices (0–17) this territory spans. "
                    "Used to determine which forces are caught by the storm."
    )

    # Spice blow
    has_spice_blow: bool = Field(
        default=False,
        description="Whether this territory appears on a Spice Deck card."
    )
    spice_blow_amount: int = Field(
        default=0,
        description="Spice placed here when its Spice Deck card is revealed."
    )

    # Storm exception — True for Imperial Basin only.
    # Imperial Basin is sand but the rules explicitly state that forces there
    # are NOT destroyed when the storm passes through (rulebook p.7).
    storm_exception: bool = Field(
        default=False,
        description="If True, forces here are never destroyed by the storm even "
                    "though the territory_type is SAND. Currently applies only to "
                    "Imperial Basin."
    )

    # Runtime state
    current_spice: int = Field(
        default=0,
        ge=0,
        description="Spice currently present on this territory."
    )

    # Derived flags
    @property
    def is_stronghold(self) -> bool:
        return self.territory_type == TerritoryType.STRONGHOLD

    @property
    def is_protected_from_storm(self) -> bool:
        """
        Returns True if forces here are never destroyed by the storm.
        Covers rock, stronghold, and polar sink types by default.
        Also True for Imperial Basin (sand, but explicitly storm-exempt per rules).
        """
        if self.storm_exception:
            return True
        return self.territory_type in (
            TerritoryType.ROCK,
            TerritoryType.STRONGHOLD,
            TerritoryType.POLAR_SINK,
        )

    @property
    def is_sand(self) -> bool:
        return self.territory_type == TerritoryType.SAND
