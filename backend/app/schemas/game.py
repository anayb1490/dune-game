"""
API request / response schemas.

Schemas control what the client sends to us and what we send back.
They are separate from internal models so we can filter hidden info.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from ..models.faction import FactionName
from ..models.game_state import GameMode


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class PlayerConfig(BaseModel):
    """Legacy: used by the old create_game endpoint."""
    player_id: str
    player_name: str
    faction: FactionName


class CreateGameRequest(BaseModel):
    """Legacy: POST /api/games — create a game with pre-assigned players."""
    players: list[PlayerConfig] = Field(min_length=2, max_length=6)
    mode: GameMode = Field(default=GameMode.BASIC)


class CreateLobbyRequest(BaseModel):
    """POST /api/games/lobby — create a new lobby."""
    host_player_id: str
    host_player_name: str
    mode: GameMode = Field(default=GameMode.BASIC)


class JoinLobbyRequest(BaseModel):
    """POST /api/games/lobby/join — join an existing lobby by code."""
    player_id: str
    player_name: str
    join_code: str


class SelectFactionRequest(BaseModel):
    """POST /api/games/{game_id}/faction — choose a faction in the lobby."""
    player_id: str
    faction: FactionName


class GameActionType(str, Enum):
    ADVANCE_PHASE = "advance_phase"
    PLACE_BID = "place_bid"
    PASS_BID = "pass_bid"
    SELECT_TRAITOR = "select_traitor"
    SUBMIT_STORM_DIAL = "submit_storm_dial"
    REVIVE_FORCES = "revive_forces"
    REVIVE_LEADER = "revive_leader"
    SHIP_FORCES = "ship_forces"
    MOVE_FORCES = "move_forces"
    SUBMIT_BATTLE_PLAN = "submit_battle_plan"
    # Alliance / Nexus actions
    PROPOSE_ALLIANCE = "propose_alliance"
    ACCEPT_ALLIANCE = "accept_alliance"
    BREAK_ALLIANCE = "break_alliance"
    PASS_NEXUS = "pass_nexus"


class GameActionRequest(BaseModel):
    """POST /api/games/{game_id}/action — perform a game action."""
    player_id: str
    action_type: GameActionType
    payload: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class CreateGameResponse(BaseModel):
    game_id: str
    message: str = "Game created successfully"


class CreateLobbyResponse(BaseModel):
    game_id: str
    join_code: str


class JoinLobbyResponse(BaseModel):
    game_id: str


class ErrorResponse(BaseModel):
    detail: str
