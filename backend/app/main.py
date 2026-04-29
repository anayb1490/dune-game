"""
Dune Board Game — FastAPI Application Entry Point.

=== How a Web Server Works ===

When you run:
    uvicorn backend.app.main:app --reload --port 8000

Here's what happens:
  1. Uvicorn (the server) loads this file and finds the `app` object
  2. It starts listening on port 8000 for incoming connections
  3. When a browser/client sends a request to http://localhost:8000/...,
     Uvicorn passes it to FastAPI
  4. FastAPI matches the URL to the right endpoint function and calls it
  5. The function returns data, FastAPI converts it to JSON, sends it back

The --reload flag means "watch for file changes and restart automatically."
Great for development — save a file, server restarts, changes are live.

=== What This File Does ===

This is the "assembly point" where we:
  1. Create the FastAPI app
  2. Add CORS middleware (so the React frontend can talk to us)
  3. Mount our REST API routes
  4. Set up the WebSocket endpoint
"""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .api.routes.game import router as game_router
from .api.routes.rules import router as rules_router
from .core.config import ALLOWED_ORIGINS, API_PREFIX, APP_TITLE, APP_VERSION
from .websocket.manager import manager


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Create the FastAPI application
# ---------------------------------------------------------------------------
#
# Think of `app` as the receptionist for our server.
# Every HTTP request and WebSocket connection comes here first.
# It checks the URL, finds the matching handler, and dispatches the request.

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=(
        "API for a multiplayer implementation of the classic Dune board game. "
        "Supports REST endpoints for game management and WebSocket connections "
        "for real-time game state updates."
    ),
)


# ---------------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------------
#
# Middleware is code that runs on EVERY request, before your endpoint
# function is called. Think of it as a "security guard at the door."
#
# CORSMiddleware does this on every request:
#   1. Checks: "Where did this request come from?" (the Origin header)
#   2. Compares it to our ALLOWED_ORIGINS list
#   3. If it's allowed, adds headers to the response saying "this is ok"
#   4. If not allowed, the browser will block the response
#
# allow_credentials=True  → lets the browser send cookies
# allow_methods=["*"]     → allows GET, POST, PUT, DELETE, etc.
# allow_headers=["*"]     → allows any request headers

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Mount REST API routes
# ---------------------------------------------------------------------------
#
# include_router() takes the router we defined in game.py and "mounts"
# it onto our app with the /api prefix.
#
# So the router's routes become:
#   POST /api/games          → create_new_game()
#   GET  /api/games/{id}     → get_game()
#   POST /api/games/{id}/start   → start_game()
#   POST /api/games/{id}/action  → perform_action()

app.include_router(game_router, prefix=API_PREFIX)
app.include_router(rules_router, prefix=API_PREFIX)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------
#
# This is fundamentally different from the REST endpoints above.
#
# REST = short-lived:  request → response → done, connection closes
# WebSocket = long-lived: connection opens → messages flow both ways → eventually closes
#
# The lifecycle of a WebSocket connection:
#
#   1. Browser connects:
#      const ws = new WebSocket("ws://localhost:8000/ws/game-abc123")
#
#   2. Server accepts (in our connect() method):
#      await manager.connect(game_id, websocket)
#
#   3. Messages flow freely:
#      - Server → Client: game state updates (via manager.broadcast)
#      - Client → Server: player actions (received in the while loop below)
#
#   4. Someone disconnects:
#      - Browser closes tab → WebSocketDisconnect exception
#      - We clean up in the except block
#
# Note the URL pattern: /ws/{game_id}
# The "ws://" protocol (instead of "http://") tells the browser
# "this is a WebSocket connection, not a regular HTTP request."

@app.websocket("/ws/{game_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, player_id: str):
    """
    WebSocket endpoint for real-time game updates.

    Each player connects with their player_id so the server can send
    per-player filtered state (hiding other players' secrets).
    """
    await manager.connect(game_id, player_id, websocket)

    try:
        # This loop runs forever until the client disconnects.
        # websocket.receive_text() BLOCKS (waits) until the client
        # sends a message. This is how WebSockets work — the connection
        # stays open and we just wait for data.
        while True:
            data = await websocket.receive_text()

            # For now, we just log messages from the client.
            # Later, we could process game actions here as an
            # alternative to the REST /action endpoint.
            logger.info(
                "WebSocket message from game=%s: %s",
                game_id,
                data[:200],  # Truncate for safety
            )

            # Echo back an acknowledgment
            await manager.send_personal(
                websocket,
                {"type": "ack", "message": "Message received"},
            )

    except WebSocketDisconnect:
        # This exception fires when the client closes the connection
        # (e.g., closes browser tab, navigates away, loses internet).
        # It's not an error — it's the normal way WebSocket connections end.
        manager.disconnect(game_id, websocket)
        logger.info("Client disconnected from game=%s", game_id)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
#
# A simple endpoint that returns "ok" — useful for checking if the server
# is running. Load balancers and monitoring tools use this to verify
# the server is alive.

@app.get("/health")
async def health_check():
    return {"status": "ok"}
