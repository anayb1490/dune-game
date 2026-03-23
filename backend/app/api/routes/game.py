"""
Game REST API endpoints.

Includes lobby management, setup phase actions, and in-game actions.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

from ...models.game_state import GamePhase, GameState
from ...schemas.game import (
    CreateGameRequest,
    CreateGameResponse,
    CreateLobbyRequest,
    CreateLobbyResponse,
    GameActionRequest,
    GameActionType,
    JoinLobbyRequest,
    JoinLobbyResponse,
    SelectFactionRequest,
)
from ...services.game.bidding import place_bid, pass_bid
from ...services.game.combat import declare_traitor, submit_battle_plan
from ...services.game.engine import advance_phase
from ...services.game.nexus import (
    propose_alliance, accept_alliance, break_alliance, pass_nexus,
)
from ...services.game.revival import resolve_free_revival, revive_forces, revive_leader
from ...services.game.shipment import ship_forces, move_forces
from ...services.game.setup import (
    PlayerSetupConfig,
    add_player_to_lobby,
    create_game,
    create_lobby,
    initialize_game,
    process_storm_dial,
    process_traitor_selection,
    select_faction,
)
from ...services.game.state_filter import filter_state_for_player
from ...websocket.manager import manager


# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------

games: dict[str, GameState] = {}

# join_code -> game_id lookup
games_by_code: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/games",
    tags=["games"],
)


# ---------------------------------------------------------------------------
# POST /api/games/lobby — Create a new lobby
# ---------------------------------------------------------------------------

@router.post("/lobby", response_model=CreateLobbyResponse, status_code=201)
async def create_new_lobby(request: CreateLobbyRequest) -> CreateLobbyResponse:
    """Create a new game lobby. Returns game_id and join_code."""
    game_id = str(uuid.uuid4())

    game_state = create_lobby(
        game_id=game_id,
        host_player_id=request.host_player_id,
        host_player_name=request.host_player_name,
        mode=request.mode,
    )

    games[game_id] = game_state
    join_code = game_state.lobby_state.join_code
    games_by_code[join_code] = game_id

    return CreateLobbyResponse(game_id=game_id, join_code=join_code)


# ---------------------------------------------------------------------------
# POST /api/games/lobby/join — Join an existing lobby
# ---------------------------------------------------------------------------

@router.post("/lobby/join", response_model=JoinLobbyResponse)
async def join_lobby(request: JoinLobbyRequest) -> JoinLobbyResponse:
    """Join a lobby using a join code."""
    code = request.join_code.upper()
    if code not in games_by_code:
        raise HTTPException(status_code=404, detail="Invalid join code.")

    game_id = games_by_code[code]
    game_state = _get_game_or_404(game_id)

    try:
        game_state = add_player_to_lobby(
            game_state, request.player_id, request.player_name
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    games[game_id] = game_state
    await manager.broadcast(game_id, game_state)

    return JoinLobbyResponse(game_id=game_id)


# ---------------------------------------------------------------------------
# POST /api/games/{game_id}/faction — Select a faction in the lobby
# ---------------------------------------------------------------------------

@router.post("/{game_id}/faction")
async def select_player_faction(game_id: str, request: SelectFactionRequest) -> dict:
    """Choose a faction while in the lobby."""
    game_state = _get_game_or_404(game_id)

    try:
        game_state = select_faction(game_state, request.player_id, request.faction)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    games[game_id] = game_state
    await manager.broadcast(game_id, game_state)

    return game_state.model_dump(mode="json")


# ---------------------------------------------------------------------------
# POST /api/games — Legacy: create with pre-assigned players
# ---------------------------------------------------------------------------

@router.post("", response_model=CreateGameResponse, status_code=201)
async def create_new_game(request: CreateGameRequest) -> CreateGameResponse:
    """Legacy endpoint: create a game with pre-assigned players."""
    game_id = str(uuid.uuid4())

    player_configs = [
        PlayerSetupConfig(
            player_id=p.player_id,
            player_name=p.player_name,
            faction=p.faction,
        )
        for p in request.players
    ]

    game_state = create_game(
        game_id=game_id,
        player_configs=player_configs,
        mode=request.mode,
    )

    games[game_id] = game_state
    return CreateGameResponse(game_id=game_id)


# ---------------------------------------------------------------------------
# GET /api/games/{game_id} — Get current game state
# ---------------------------------------------------------------------------

@router.get("/{game_id}")
async def get_game(game_id: str, player_id: str | None = None) -> dict:
    """
    Fetch the current state of a game.
    If player_id is provided, the state is filtered to hide other players' secrets.
    """
    game_state = _get_game_or_404(game_id)
    state_dict = game_state.model_dump(mode="json")

    if player_id:
        state_dict = filter_state_for_player(state_dict, player_id)

    return state_dict


# ---------------------------------------------------------------------------
# POST /api/games/{game_id}/start — Start the game
# ---------------------------------------------------------------------------

@router.post("/{game_id}/start")
async def start_game(game_id: str, player_id: str | None = None) -> dict:
    """
    Start the game. In lobby mode, transitions to SETUP phase.
    In legacy mode (already at STORM), runs automated phases.
    """
    game_state = _get_game_or_404(game_id)

    if game_state.is_game_over:
        raise HTTPException(status_code=400, detail="Game is already over")

    try:
        if game_state.current_phase.value == "lobby":
            # Validate host
            if game_state.lobby_state and player_id:
                if player_id != game_state.lobby_state.host_player_id:
                    raise HTTPException(
                        status_code=403, detail="Only the host can start the game."
                    )
            game_state = initialize_game(game_state)
        else:
            # Legacy path: game already at STORM, nothing to do.
            # The host will advance automated phases manually.
            pass
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    games[game_id] = game_state
    await manager.broadcast(game_id, game_state)

    return game_state.model_dump(mode="json")


# ---------------------------------------------------------------------------
# POST /api/games/{game_id}/action — Perform a game action
# ---------------------------------------------------------------------------

# Automated phases resolved server-side — only the host can advance these.
_AUTOMATED_PHASES = {
    GamePhase.STORM,
    GamePhase.SPICE_BLOW,
    GamePhase.CHOAM_CHARITY,
    GamePhase.SPICE_COLLECTION,
    GamePhase.MENTAT_PAUSE,
}


@router.post("/{game_id}/action")
async def perform_action(game_id: str, action: GameActionRequest) -> dict:
    """Handle all game actions via the action_type envelope pattern."""
    game_state = _get_game_or_404(game_id)

    if game_state.is_game_over:
        raise HTTPException(status_code=400, detail="Game is already over")

    prev_phase = game_state.current_phase
    prev_player_idx = game_state.current_player_index

    try:
        match action.action_type:
            case GameActionType.ADVANCE_PHASE:
                # Automated phases: only the host can advance.
                # Interactive phases: only the current turn player.
                if game_state.current_phase in _AUTOMATED_PHASES:
                    _validate_is_host(game_state, action.player_id)
                else:
                    _validate_is_current_turn_player(game_state, action.player_id)
                game_state = advance_phase(game_state)
                logger.info(
                    "ADVANCE_PHASE by %s: %s[idx=%d] -> %s[idx=%d] msgs=%d",
                    action.player_id,
                    prev_phase.value, prev_player_idx,
                    game_state.current_phase.value, game_state.current_player_index,
                    len(game_state.phase_messages),
                )

            case GameActionType.PLACE_BID:
                amount = action.payload.get("amount", 0)
                game_state = place_bid(game_state, action.player_id, amount)

            case GameActionType.PASS_BID:
                game_state = pass_bid(game_state, action.player_id)

            case GameActionType.SELECT_TRAITOR:
                card_id = action.payload.get("traitor_card_id", "")
                game_state = process_traitor_selection(
                    game_state, action.player_id, card_id
                )

            case GameActionType.SUBMIT_STORM_DIAL:
                number = action.payload.get("number", 0)
                game_state = process_storm_dial(
                    game_state, action.player_id, number
                )
                # Don't auto-advance — let storm phase be visible

            case GameActionType.REVIVE_FORCES:
                _validate_is_current_turn_player(game_state, action.player_id)
                count = action.payload.get("count", 0)
                game_state = revive_forces(game_state, action.player_id, count)

            case GameActionType.REVIVE_LEADER:
                _validate_is_current_turn_player(game_state, action.player_id)
                leader_id = action.payload.get("leader_id", "")
                game_state = revive_leader(game_state, action.player_id, leader_id)

            case GameActionType.SHIP_FORCES:
                _validate_is_current_turn_player(game_state, action.player_id)
                game_state = ship_forces(
                    game_state,
                    action.player_id,
                    action.payload.get("territory_name", ""),
                    action.payload.get("sector", 0),
                    action.payload.get("count", 0),
                    action.payload.get("special_count", 0),
                )

            case GameActionType.MOVE_FORCES:
                _validate_is_current_turn_player(game_state, action.player_id)
                game_state = move_forces(
                    game_state,
                    action.player_id,
                    action.payload.get("from_territory", ""),
                    action.payload.get("from_sector", 0),
                    action.payload.get("to_territory", ""),
                    action.payload.get("to_sector", 0),
                    action.payload.get("regular_count", 0),
                    action.payload.get("special_count", 0),
                )

            case GameActionType.SUBMIT_BATTLE_PLAN:
                game_state = submit_battle_plan(
                    game_state,
                    action.player_id,
                    action.payload.get("forces_dialed", 0),
                    action.payload.get("leader_id"),
                    action.payload.get("weapon_card_id"),
                    action.payload.get("defense_card_id"),
                )

            case GameActionType.DECLARE_TRAITOR:
                game_state = declare_traitor(
                    game_state,
                    action.player_id,
                    bool(action.payload.get("call_traitor", False)),
                )

            case GameActionType.PROPOSE_ALLIANCE:
                _validate_is_current_turn_player(game_state, action.player_id)
                target = action.payload.get("target_faction", "")
                game_state = propose_alliance(game_state, action.player_id, target)

            case GameActionType.ACCEPT_ALLIANCE:
                target = action.payload.get("proposer_faction", "")
                game_state = accept_alliance(game_state, action.player_id, target)

            case GameActionType.BREAK_ALLIANCE:
                game_state = break_alliance(game_state, action.player_id)

            case GameActionType.PASS_NEXUS:
                _validate_is_current_turn_player(game_state, action.player_id)
                game_state = pass_nexus(game_state, action.player_id)

            case _:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown action type: {action.action_type}",
                )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Apply free revival exactly once — only when first entering the Revival phase
    # (not when a player advances within Revival to give the next player their turn).
    if game_state.current_phase == GamePhase.REVIVAL and prev_phase != GamePhase.REVIVAL:
        game_state = resolve_free_revival(game_state)

    games[game_id] = game_state
    await manager.broadcast(game_id, game_state)

    return game_state.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_game_or_404(game_id: str) -> GameState:
    if game_id not in games:
        raise HTTPException(
            status_code=404,
            detail=f"Game not found: {game_id}",
        )
    return games[game_id]


def _validate_is_host(game_state: GameState, player_id: str) -> None:
    """Only the lobby host may advance automated phases.

    Falls back to the first player in the list when lobby_state is absent
    (legacy games created without going through the lobby).
    """
    host_id: str | None = None
    if game_state.lobby_state:
        host_id = game_state.lobby_state.host_player_id
    elif game_state.players:
        host_id = game_state.players[0].id

    if host_id and host_id != player_id:
        raise ValueError("Only the host can advance automated phases.")


def _validate_is_current_turn_player(game_state: GameState, player_id: str) -> None:
    """
    Check that the acting player is the one whose turn it is.
    In interactive phases, only the current turn player can advance
    or take phase-specific actions.
    """
    if not game_state.players:
        return

    current_idx = game_state.current_player_index
    if current_idx < len(game_state.players):
        current_player = game_state.players[current_idx]
        if current_player.id != player_id:
            raise ValueError(
                f"It's {current_player.name}'s turn, not yours."
            )
