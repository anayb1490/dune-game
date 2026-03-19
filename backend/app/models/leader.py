from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .faction import FactionName


class LeaderStatus(str, Enum):
    AVAILABLE = "available"             # In the player's leader pool; can be used in battle
    IN_TANKS = "in_tanks"               # Killed once; in Tleilaxu Tanks; can be revived
    FACE_DOWN_IN_TANKS = "face_down_in_tanks"  # Killed a second time in the same turn;
                                               # cannot be revived until face-up leaders
                                               # are cleared from the Tanks first
    CAPTURED = "captured"               # Advanced (Harkonnen only): leader is held by
                                        # Harkonnen and may be used in their battles


class Leader(BaseModel):
    """
    A leader disc belonging to one of the six factions.
    Each faction has exactly 5 leaders; their fighting strength contributes
    to the total Battle Plan value alongside dialed forces.

    Leaders move between statuses throughout the game:
      - Start AVAILABLE in their owner's pool.
      - Move to IN_TANKS when killed in battle.
      - Move to FACE_DOWN_IN_TANKS if killed a second time in the same turn
        (rare; prevents immediate revival).
      - Revive back to AVAILABLE during the Revival Phase (or for free if
        within the faction's free revival allowance).
      - Advanced (Harkonnen): enemy leaders can be CAPTURED and used by
        Harkonnen in their own battles.
    """
    id: str = Field(description="Unique identifier, e.g. 'atreides_duncan_idaho'")
    name: str
    faction: FactionName
    strength: int = Field(ge=1, le=7, description="Fighting strength (1–7)")
    status: LeaderStatus = LeaderStatus.AVAILABLE

    # Advanced: if CAPTURED, which faction is holding this leader
    captured_by: Optional[FactionName] = Field(
        default=None,
        description="Advanced (Harkonnen): the faction currently holding this leader."
    )

    # Advanced (Atreides): Kwisatz Haderach may be used as a leader;
    # flagged here so the battle service can apply the +2 strength bonus
    # when the KH is active and deployed to the same territory.
    is_kwisatz_haderach: bool = Field(
        default=False,
        description="True only for the Atreides Kwisatz Haderach token (Advanced)."
    )
