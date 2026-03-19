"""
WebSocket Connection Manager.

Manages WebSocket connections grouped by game_id, with per-player tracking
so that each player receives a filtered view of the game state (hiding
other players' secret information).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import WebSocket

from ..models.game_state import GameState
from ..services.game.state_filter import filter_state_for_player


logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Tracks WebSocket connections grouped by game_id.

    Each connection is a (player_id, WebSocket) pair so we can send
    per-player filtered state during broadcast.
    """

    def __init__(self) -> None:
        # game_id -> list of (player_id, websocket) tuples
        self._rooms: dict[str, list[tuple[str, WebSocket]]] = {}

    async def connect(self, game_id: str, player_id: str, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection and add it to the game's room."""
        await websocket.accept()

        if game_id not in self._rooms:
            self._rooms[game_id] = []
        self._rooms[game_id].append((player_id, websocket))

        logger.info(
            "WebSocket connected: game=%s player=%s (now %d in room)",
            game_id,
            player_id,
            len(self._rooms[game_id]),
        )

    def disconnect(self, game_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket from its game room."""
        if game_id in self._rooms:
            self._rooms[game_id] = [
                (pid, ws) for pid, ws in self._rooms[game_id] if ws is not websocket
            ]
            if not self._rooms[game_id]:
                del self._rooms[game_id]

        logger.info("WebSocket disconnected: game=%s", game_id)

    async def broadcast(self, game_id: str, game_state: GameState) -> None:
        """
        Send the game state to ALL players in a game room.

        Each player receives a filtered view that hides other players'
        secret information (traitor cards, treachery hand, etc.).
        """
        if game_id not in self._rooms:
            return

        full_state = game_state.model_dump(mode="json")
        stale_connections: list[WebSocket] = []

        for player_id, websocket in self._rooms[game_id]:
            try:
                filtered = filter_state_for_player(full_state, player_id)
                await websocket.send_text(json.dumps(filtered))
            except Exception:
                stale_connections.append(websocket)

        for ws in stale_connections:
            self.disconnect(game_id, ws)

    async def send_personal(
        self, websocket: WebSocket, data: dict[str, Any]
    ) -> None:
        """Send a message to one specific player."""
        await websocket.send_text(json.dumps(data))

    def get_connection_count(self, game_id: str) -> int:
        """How many clients are connected to a specific game."""
        return len(self._rooms.get(game_id, []))


# Singleton instance
manager = ConnectionManager()
