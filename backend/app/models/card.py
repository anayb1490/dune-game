from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .faction import FactionName


# =============================================================================
# Treachery Deck
# =============================================================================

class TreacheryCardType(str, Enum):
    WEAPON = "weapon"
    DEFENSE = "defense"
    WORTHLESS = "worthless"
    SPECIAL = "special"


class WeaponType(str, Enum):
    POISON = "poison"           # Countered only by a Snooper defense
    PROJECTILE = "projectile"   # Countered only by a Shield defense
    LASGUN = "lasgun"           # Kills both leaders outright; triggers explosion
                                # if a Shield is also played — kills all forces


class DefenseType(str, Enum):
    SNOOPER = "snooper"     # Blocks poison weapons
    SHIELD = "shield"       # Blocks projectile weapons; triggers lasgun explosion


class SpecialCardType(str, Enum):
    KARAMA = "karama"                       # Cancel any faction's special advantage (once)
    CHEAP_HERO = "cheap_hero"               # Stand-in leader with strength 0
    CHEAP_HEROINE = "cheap_heroine"         # Stand-in leader with strength 0
    TRUTHTRANCE = "truthtrance"             # Force opponent to answer yes/no truthfully
    WEATHER_CONTROL = "weather_control"     # Alter storm movement (0-10 sectors)
    FAMILY_ATOMICS = "family_atomics"       # Destroy Shield Wall permanently
    HAJR = "hajr"                           # Take an extra movement
    TLEILAXU_GHOLA = "tleilaxu_ghola"       # Revive one dead leader or up to 5 forces


class TreacheryCard(BaseModel):
    """
    A card from the 33-card Treachery Deck.
    Each player bids for these during the Bidding Phase and plays them
    secretly as part of their Battle Plan.
    """
    id: str
    name: str
    card_type: TreacheryCardType

    # Populated only when card_type == WEAPON
    weapon_type: Optional[WeaponType] = None

    # Populated only when card_type == DEFENSE
    defense_type: Optional[DefenseType] = None

    # Populated only when card_type == SPECIAL
    special_type: Optional[SpecialCardType] = None

    # Some cards (Truthtrance, Weather Control, etc.) are Advanced-only
    is_advanced: bool = False


# =============================================================================
# Spice Deck
# =============================================================================

class SpiceCardType(str, Enum):
    TERRITORY = "territory"     # Reveals a spice blow on a named territory
    SHAI_HULUD = "shai_hulud"   # Triggers sandworm event / Nexus


class SpiceCard(BaseModel):
    """
    A card from the 21-card Spice Deck.
    Two cards are revealed each Spice Blow Phase (Advanced) or one (Basic).
    Shai-Hulud cards trigger sandworm attacks or a Nexus event.
    """
    id: str
    name: str
    card_type: SpiceCardType

    # Populated only when card_type == TERRITORY
    territory_name: Optional[str] = None
    spice_amount: Optional[int] = Field(
        default=None,
        ge=1,
        description="Spice placed on the territory when this card is revealed."
    )


# =============================================================================
# Traitor Deck
# =============================================================================

class TraitorCard(BaseModel):
    """
    One of the 30 Traitor cards — one per leader across all factions.
    Each player is dealt 4 at the start; most keep 1 face-down.
    Harkonnen (Advanced) keeps all 4.
    A traitor card lets you call your opponent's leader a traitor in battle,
    negating all their forces and Battle Plan.
    """
    id: str
    leader_id: str      # Matches Leader.id
    leader_name: str    # Display name, denormalised for convenience
    faction: FactionName
    leader_strength: int = Field(default=0, ge=0, le=7, description="Fighting strength of the leader")


# =============================================================================
# Bene Gesserit Prediction Deck (Advanced)
# =============================================================================

class PredictionCardType(str, Enum):
    FACTION = "faction"     # One of the 6 faction cards
    TURN = "turn"           # One of turn numbers 1–10


class PredictionCard(BaseModel):
    """
    Advanced: Bene Gesserit secretly predicts which faction wins on which turn.
    Two cards are chosen at game start — one faction, one turn — and revealed
    at Mentat Pause if the predicted condition has been met for an instant BG win.
    """
    id: str
    card_type: PredictionCardType

    # Populated only when card_type == FACTION
    faction: Optional[FactionName] = None

    # Populated only when card_type == TURN
    turn: Optional[int] = Field(default=None, ge=1, le=10)


# =============================================================================
# Alliance Deck
# =============================================================================

class AllianceCard(BaseModel):
    """
    One of the 6 Alliance cards — one per faction.
    Handed to an ally to signal a formal alliance; returned if the alliance ends.
    """
    id: str
    faction: FactionName
