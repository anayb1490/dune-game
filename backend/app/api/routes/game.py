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
from ...services.game.bg_actions import (
    trigger_bg_free_shipment,
    flip_advisors_to_fighters,
    flip_fighters_to_advisors,
)
from ...services.game.guild_actions import guild_cross_ship, guild_ship_to_reserves
from ...services.game.prebattle import (
    issue_voice,
    acknowledge_voice,
    ask_prescience,
    reveal_prescience_value,
    done_prebattle,
)
from ...services.game.fremen_actions import (
    fremen_sandworm_ride,
    fremen_skip_sandworm_ride,
)
from ...services.game.special_cards import (
    play_karama_block,
    play_karama_faction_power,
    play_tleilaxu_ghola,
    play_family_atomics,
    play_hajr,
    play_weather_control,
    play_truthtrance,
)
from ...models.faction import FactionName
from ...services.game.setup import (
    PlayerSetupConfig,
    add_player_to_lobby,
    create_game,
    create_lobby,
    initialize_game,
    process_atreides_prescience,
    process_bg_prediction,
    process_fremen_placement,
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
                    action.payload.get("special_forces_dialed", 0),
                    action.payload.get("spice_to_expend", 0),
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

            case GameActionType.BG_PREDICTION:
                faction_str = action.payload.get("predicted_faction", "")
                turn = action.payload.get("predicted_turn", 1)
                predicted_faction = FactionName(faction_str)
                game_state = process_bg_prediction(game_state, action.player_id, predicted_faction, turn)

            case GameActionType.FREMEN_PLACEMENT:
                placements = action.payload.get("placements", [])
                game_state = process_fremen_placement(game_state, action.player_id, placements)

            case GameActionType.ATREIDES_PRESCIENCE:
                game_state = process_atreides_prescience(game_state, action.player_id)

            # ------------------------------------------------------------------
            # Faction ability actions
            # ------------------------------------------------------------------

            case GameActionType.ACK_MOVEMENT_PRESCIENCE:
                # Atreides (or their ally) acknowledges they've seen the movement prescience reveal.
                # Sets atreides_movement_prescience_seen=True.
                p = _get_player_or_400(game_state, action.player_id)
                atreides_player = next(
                    (pl for pl in game_state.players if pl.faction == FactionName.ATREIDES),
                    None,
                )
                if atreides_player is None:
                    raise ValueError("No Atreides player in this game")
                allowed = p.faction == FactionName.ATREIDES or (
                    game_state.mode.value == "advanced" and atreides_player.ally == p.faction
                )
                if not allowed:
                    raise ValueError("Only Atreides (or their ally) can acknowledge movement prescience")
                game_state = game_state.model_copy(update={"atreides_movement_prescience_seen": True})

            case GameActionType.BG_FREE_SHIP:
                game_state = trigger_bg_free_shipment(
                    game_state,
                    action.player_id,
                    action.payload.get("territory_name", ""),
                    action.payload.get("sector", 0),
                    bool(action.payload.get("as_advisor", False)),
                )

            case GameActionType.PASS_BG_FREE_SHIP:
                # BG declines their free out-of-turn shipment — clear the pending flag
                player_obj = next(
                    (p for p in game_state.players if p.id == action.player_id), None
                )
                if player_obj is None or player_obj.faction.value != "bene_gesserit":
                    raise ValueError("Only Bene Gesserit can pass the free ship")
                game_state = game_state.model_copy(update={
                    "bg_free_ship_pending": False,
                    "bg_free_ship_last_territory": None,
                })

            case GameActionType.FLIP_ADVISORS_TO_FIGHTERS:
                game_state = flip_advisors_to_fighters(
                    game_state,
                    action.player_id,
                    action.payload.get("territory_name", ""),
                )

            case GameActionType.FLIP_FIGHTERS_TO_ADVISORS:
                game_state = flip_fighters_to_advisors(
                    game_state,
                    action.player_id,
                    action.payload.get("territory_name", ""),
                )

            case GameActionType.GUILD_CROSS_SHIP:
                game_state = guild_cross_ship(
                    game_state,
                    action.player_id,
                    action.payload.get("from_territory", ""),
                    action.payload.get("from_sector", 0),
                    action.payload.get("to_territory", ""),
                    action.payload.get("to_sector", 0),
                    action.payload.get("regular_count", 0),
                    action.payload.get("special_count", 0),
                )

            case GameActionType.GUILD_SHIP_TO_RESERVES:
                game_state = guild_ship_to_reserves(
                    game_state,
                    action.player_id,
                    action.payload.get("from_territory", ""),
                    action.payload.get("from_sector", 0),
                    action.payload.get("regular_count", 0),
                    action.payload.get("special_count", 0),
                )

            case GameActionType.ISSUE_VOICE:
                target_str = action.payload.get("target_faction", "")
                target_faction = FactionName(target_str)
                game_state = issue_voice(
                    game_state,
                    action.player_id,
                    target_faction,
                    action.payload.get("command", ""),
                    action.payload.get("card_type", ""),
                )

            case GameActionType.ACKNOWLEDGE_VOICE:
                game_state = acknowledge_voice(game_state, action.player_id)

            case GameActionType.ASK_PRESCIENCE:
                game_state = ask_prescience(
                    game_state,
                    action.player_id,
                    action.payload.get("element", ""),
                )

            case GameActionType.REVEAL_PRESCIENCE:
                game_state = reveal_prescience_value(
                    game_state,
                    action.player_id,
                    action.payload.get("revealed_value", ""),
                )

            case GameActionType.DONE_PREBATTLE:
                game_state = done_prebattle(game_state, action.player_id)

            case GameActionType.FREMEN_SANDWORM_RIDE:
                game_state = fremen_sandworm_ride(
                    game_state,
                    action.player_id,
                    action.payload.get("to_territory", ""),
                    action.payload.get("to_sector", 0),
                    action.payload.get("regular_count", 0),
                    action.payload.get("special_count", 0),
                )

            case GameActionType.FREMEN_SKIP_SANDWORM_RIDE:
                game_state = fremen_skip_sandworm_ride(game_state, action.player_id)

            # ------------------------------------------------------------------
            # Special treachery card actions
            # ------------------------------------------------------------------

            case GameActionType.PLAY_KARAMA_BLOCK:
                target_str = action.payload.get("target_faction", "")
                target = FactionName(target_str)
                game_state = play_karama_block(game_state, action.player_id, target)

            case GameActionType.PLAY_KARAMA_POWER:
                game_state = play_karama_faction_power(
                    game_state, action.player_id, action.payload
                )

            case GameActionType.PLAY_TLEILAXU_GHOLA:
                game_state = play_tleilaxu_ghola(
                    game_state,
                    action.player_id,
                    leader_id=action.payload.get("leader_id"),
                    force_count=int(action.payload.get("force_count", 0)),
                )

            case GameActionType.PLAY_FAMILY_ATOMICS:
                game_state = play_family_atomics(game_state, action.player_id)

            case GameActionType.PLAY_HAJR:
                game_state = play_hajr(game_state, action.player_id)

            case GameActionType.PLAY_WEATHER_CONTROL:
                sectors = int(action.payload.get("sectors", 0))
                game_state = play_weather_control(game_state, action.player_id, sectors)

            case GameActionType.PLAY_TRUTHTRANCE:
                target_raw = action.payload.get("target_faction", "")
                target = FactionName(target_raw)
                question = action.payload.get("question", "")
                game_state = play_truthtrance(game_state, action.player_id, target, question)

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

    Special case: in the Nexus phase the active player is tracked by
    nexus_state.current_faction (not current_player_index), because each
    player acts in sequence without the index being updated between factions.
    """
    if not game_state.players:
        return

    # Nexus: determine the current player from nexus_state.current_faction
    if (game_state.current_phase == GamePhase.NEXUS
            and game_state.nexus_state is not None):
        current_faction = game_state.nexus_state.current_faction
        current_player = next(
            (p for p in game_state.players if p.faction.value == current_faction),
            None,
        )
        if current_player and current_player.id != player_id:
            raise ValueError(
                f"It's {current_player.name}'s Nexus turn, not yours."
            )
        return

    current_idx = game_state.current_player_index
    if current_idx < len(game_state.players):
        current_player = game_state.players[current_idx]
        if current_player.id != player_id:
            raise ValueError(
                f"It's {current_player.name}'s turn, not yours."
            )


def _get_player_or_400(game_state: GameState, player_id: str):
    """Look up a player by ID; raises ValueError (caught → 400) if not found."""
    for p in game_state.players:
        if p.id == player_id:
            return p
    raise ValueError(f"Player not found: {player_id}")
