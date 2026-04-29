"""
Tests for the Dune Game REST API.

=== How API Testing Works ===

Instead of starting a real server and making HTTP requests with curl,
FastAPI provides a TestClient that simulates requests in memory.
It's fast, reliable, and doesn't need a running server.

TestClient uses the same interface as the `requests` library:
    response = client.post("/api/games", json={...})
    response = client.get("/api/games/abc123")

The response object has:
    response.status_code → 200, 201, 404, etc.
    response.json()      → parsed JSON body as a Python dict

Run with:
    cd DuneGame
    pip install httpx  # Required by FastAPI's TestClient
    python -m pytest backend/tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.api.routes.game import games  # the in-memory store
from backend.app.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """
    Create a fresh test client for each test.

    We also clear the in-memory game store so tests don't affect
    each other. This is important — tests should be independent.
    """
    games.clear()
    return TestClient(app)


@pytest.fixture
def two_player_body() -> dict:
    """Standard request body for creating a 2-player game."""
    return {
        "players": [
            {"player_id": "p1", "player_name": "Paul", "faction": "atreides"},
            {"player_id": "p2", "player_name": "Vladimir", "faction": "harkonnen"},
        ],
        "mode": "basic",
    }


@pytest.fixture
def game_id(client: TestClient, two_player_body: dict) -> str:
    """Create a game and return its ID (for tests that need an existing game)."""
    resp = client.post("/api/games", json=two_player_body)
    return resp.json()["game_id"]


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealthCheck:

    def test_health_returns_ok(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/games — Create Game
# ---------------------------------------------------------------------------

class TestCreateGame:
    """Test game creation endpoint."""

    def test_create_returns_201(self, client: TestClient, two_player_body: dict):
        """Successful creation should return HTTP 201 (Created)."""
        resp = client.post("/api/games", json=two_player_body)
        assert resp.status_code == 201

    def test_create_returns_game_id(self, client: TestClient, two_player_body: dict):
        """Response should include a game_id string."""
        resp = client.post("/api/games", json=two_player_body)
        data = resp.json()
        assert "game_id" in data
        assert isinstance(data["game_id"], str)
        assert len(data["game_id"]) > 0

    def test_create_stores_game(self, client: TestClient, two_player_body: dict):
        """After creation, the game should exist in the store."""
        resp = client.post("/api/games", json=two_player_body)
        game_id = resp.json()["game_id"]
        assert game_id in games

    def test_create_with_invalid_faction_returns_422(self, client: TestClient):
        """
        Sending an invalid faction should return 422 (Validation Error).
        FastAPI + Pydantic handle this automatically — we don't write
        any validation code ourselves!
        """
        body = {
            "players": [
                {"player_id": "p1", "player_name": "Paul", "faction": "jedi"},
                {"player_id": "p2", "player_name": "Vlad", "faction": "harkonnen"},
            ],
            "mode": "basic",
        }
        resp = client.post("/api/games", json=body)
        assert resp.status_code == 422

    def test_create_with_one_player_returns_422(self, client: TestClient):
        """Need at least 2 players."""
        body = {
            "players": [
                {"player_id": "p1", "player_name": "Paul", "faction": "atreides"},
            ],
            "mode": "basic",
        }
        resp = client.post("/api/games", json=body)
        assert resp.status_code == 422

    def test_create_six_player_game(self, client: TestClient):
        """Full 6-player game should work."""
        body = {
            "players": [
                {"player_id": "p1", "player_name": "Paul", "faction": "atreides"},
                {"player_id": "p2", "player_name": "Vladimir", "faction": "harkonnen"},
                {"player_id": "p3", "player_name": "Gaius", "faction": "bene_gesserit"},
                {"player_id": "p4", "player_name": "Stilgar", "faction": "fremen"},
                {"player_id": "p5", "player_name": "Edric", "faction": "spacing_guild"},
                {"player_id": "p6", "player_name": "Shaddam", "faction": "emperor"},
            ],
            "mode": "advanced",
        }
        resp = client.post("/api/games", json=body)
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# GET /api/games/{game_id} — Get Game State
# ---------------------------------------------------------------------------

class TestGetGame:
    """Test fetching game state."""

    def test_get_existing_game(self, client: TestClient, game_id: str):
        """Should return the full game state as JSON."""
        resp = client.get(f"/api/games/{game_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == game_id
        assert data["current_phase"] == "storm"
        assert data["current_turn"] == 1

    def test_get_includes_players(self, client: TestClient, game_id: str):
        resp = client.get(f"/api/games/{game_id}")
        data = resp.json()
        assert len(data["players"]) == 2
        factions = {p["faction"] for p in data["players"]}
        assert factions == {"atreides", "harkonnen"}

    def test_get_nonexistent_returns_404(self, client: TestClient):
        """Requesting a game that doesn't exist should return 404."""
        resp = client.get("/api/games/nonexistent-id")
        assert resp.status_code == 404

    def test_404_has_detail_message(self, client: TestClient):
        resp = client.get("/api/games/bad-id")
        assert resp.status_code == 404
        assert "detail" in resp.json()


# ---------------------------------------------------------------------------
# POST /api/games/{game_id}/start — Start Game
# ---------------------------------------------------------------------------

class TestStartGame:
    """Test running the automated opening phases."""

    def test_start_begins_at_storm(self, client: TestClient, game_id: str):
        """Starting a legacy game should land at Storm (first phase)."""
        resp = client.post(f"/api/games/{game_id}/start")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_phase"] == "storm"

    def test_start_storm_initial_state(self, client: TestClient, game_id: str):
        resp = client.post(f"/api/games/{game_id}/start")
        data = resp.json()
        assert data["current_player_index"] == 0

    def test_start_nonexistent_returns_404(self, client: TestClient):
        resp = client.post("/api/games/fake-id/start")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/games/{game_id}/action — Perform Action
# ---------------------------------------------------------------------------

class TestPerformAction:
    """Test the generic action endpoint."""

    @staticmethod
    def _advance_all_players(client, game_id):
        """Advance through all players in the current phase (turn-based)."""
        resp = client.get(f"/api/games/{game_id}")
        state = resp.json()
        num_players = len(state["players"])
        for _ in range(num_players):
            resp = client.get(f"/api/games/{game_id}")
            state = resp.json()
            current_idx = state.get("current_player_index", 0)
            player_id = state["players"][current_idx]["id"]
            resp = client.post(f"/api/games/{game_id}/action", json={
                "player_id": player_id,
                "action_type": "advance_phase",
            })
        return resp

    @staticmethod
    def _advance_to_bidding(client, game_id):
        """Advance through Storm, Spice Blow, and CHOAM Charity to reach Bidding."""
        for phase in ("storm", "spice_blow", "choam_charity"):
            resp = client.get(f"/api/games/{game_id}")
            state = resp.json()
            assert state["current_phase"] == phase
            TestPerformAction._advance_all_players(client, game_id)

    @staticmethod
    def _pass_all_bids(client, game_id):
        """Pass all bids to clear bidding."""
        for _ in range(20):
            resp = client.get(f"/api/games/{game_id}")
            state = resp.json()
            if state["current_phase"] != "bidding" or state.get("bidding_state") is None:
                break
            bidder = state["bidding_state"]["current_bidder"]
            bid_player = next(
                p for p in state["players"] if p["faction"] == bidder
            )
            client.post(f"/api/games/{game_id}/action", json={
                "player_id": bid_player["id"],
                "action_type": "pass_bid",
            })

    def test_advance_phase_from_bidding(self, client: TestClient, game_id: str):
        """After starting, advance through early phases, pass bids, then advance → Revival."""
        client.post(f"/api/games/{game_id}/start")

        # Advance through Storm, Spice Blow, CHOAM Charity (each cycles through all players)
        self._advance_to_bidding(client, game_id)
        self._pass_all_bids(client, game_id)

        # Bidding should be done — now advance to Revival
        resp = client.get(f"/api/games/{game_id}")
        state = resp.json()
        current_idx = state.get("current_player_index", 0)
        player_id = state["players"][current_idx]["id"]
        resp = client.post(f"/api/games/{game_id}/action", json={
            "player_id": player_id,
            "action_type": "advance_phase",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_phase"] == "revival"

    def test_advance_through_all_interactive_phases(
        self, client: TestClient, game_id: str
    ):
        """Keep advancing — should cycle through all phases to next turn."""
        client.post(f"/api/games/{game_id}/start")

        # Advance through the early phases first
        self._advance_to_bidding(client, game_id)
        self._pass_all_bids(client, game_id)

        # Now advance through remaining phases.
        phases_seen = []
        for _ in range(80):
            resp = client.get(f"/api/games/{game_id}")
            state = resp.json()
            phase = state["current_phase"]

            # Handle nexus — all players must pass (or act) before advance_phase works
            if phase == "nexus":
                ns = state.get("nexus_state")
                if ns is not None:
                    current_faction = ns.get("current_faction")
                    faction_player = next(
                        (p for p in state["players"] if p["faction"] == current_faction),
                        None,
                    )
                    if faction_player:
                        client.post(f"/api/games/{game_id}/action", json={
                            "player_id": faction_player["id"],
                            "action_type": "pass_nexus",
                        })
                    phases_seen.append("nexus")
                    continue  # Re-check state next iteration

            # Determine the right player to advance
            current_idx = state.get("current_player_index", 0)
            player_id = state["players"][current_idx]["id"] if state["players"] else "p1"

            resp = client.post(f"/api/games/{game_id}/action", json={
                "player_id": player_id,
                "action_type": "advance_phase",
            })
            new_phase = resp.json()["current_phase"]
            phases_seen.append(new_phase)

            # Handle bidding — pass all bids
            if new_phase == "bidding":
                bs = resp.json().get("bidding_state")
                if bs is not None:
                    self._pass_all_bids(client, game_id)
                break  # Reached bidding in next turn — success

        # Should end up back at Bidding (turn 2)
        assert phases_seen[-1] == "bidding"

    def test_action_on_nonexistent_game_returns_404(self, client: TestClient):
        resp = client.post("/api/games/fake/action", json={
            "player_id": "p1",
            "action_type": "advance_phase",
        })
        assert resp.status_code == 404

    def test_invalid_action_body_returns_422(self, client: TestClient, game_id: str):
        """Sending gibberish action_type should fail validation."""
        resp = client.post(f"/api/games/{game_id}/action", json={
            "player_id": "p1",
            "action_type": "do_a_backflip",
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

class TestWebSocket:
    """Test WebSocket connection."""

    def test_connect_and_receive_ack(self, client: TestClient, game_id: str):
        """
        Connect to a game's WebSocket, send a message, get an ack back.

        TestClient provides a context manager for WebSocket testing.
        The 'with' block simulates the full WebSocket lifecycle:
        connect → exchange messages → disconnect.
        """
        with client.websocket_connect(f"/ws/{game_id}/p1") as ws:
            ws.send_text("hello")
            data = ws.receive_json()
            assert data["type"] == "ack"

    def test_connect_to_nonexistent_game(self, client: TestClient):
        """WebSocket connections to unknown game IDs should still work.
        (The connection manager just creates a new room.)"""
        with client.websocket_connect("/ws/unknown-game/test-player") as ws:
            ws.send_text("ping")
            data = ws.receive_json()
            assert data["type"] == "ack"
