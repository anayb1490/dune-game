"""
End-to-end integration tests for the complete game flow.

Tests the EXACT HTTP flow a real game goes through:
  lobby -> join -> factions -> start -> setup -> STORM -> phase cycle

Uses the FastAPI TestClient to simulate real API calls.

Run with:
    cd DuneGame
    python -m pytest backend/tests/test_e2e_flow.py -v
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api.routes.game import games, games_by_code


@pytest.fixture(autouse=True)
def clear_game_stores():
    """Clear in-memory stores before and after each test."""
    games.clear()
    games_by_code.clear()
    yield
    games.clear()
    games_by_code.clear()


client = TestClient(app)


class TestFullLobbyToGameFlow:
    """Test the complete flow from lobby creation to gameplay."""

    def _create_and_start_game(self):
        """Helper: create lobby, join, pick factions, go through setup, arrive at STORM."""

        # Step 1: Host creates a lobby
        resp = client.post("/api/games/lobby", json={
            "host_player_id": "host1",
            "host_player_name": "Paul",
            "mode": "basic",
        })
        assert resp.status_code == 201
        data = resp.json()
        game_id = data["game_id"]
        join_code = data["join_code"]

        # Step 2: Second player joins
        resp = client.post("/api/games/lobby/join", json={
            "player_id": "player2",
            "player_name": "Vladimir",
            "join_code": join_code,
        })
        assert resp.status_code == 200
        assert resp.json()["game_id"] == game_id

        # Step 3: Both players select factions
        resp = client.post(f"/api/games/{game_id}/faction", json={
            "player_id": "host1",
            "faction": "atreides",
        })
        assert resp.status_code == 200

        resp = client.post(f"/api/games/{game_id}/faction", json={
            "player_id": "player2",
            "faction": "harkonnen",
        })
        assert resp.status_code == 200

        # Step 4: Host starts the game
        resp = client.post(f"/api/games/{game_id}/start?player_id=host1")
        assert resp.status_code == 200
        state = resp.json()
        assert state["current_phase"] == "setup"
        assert state["setup_state"]["sub_phase"] == "traitor_selection"

        # Step 5: Both players select traitors
        for pid in ["host1", "player2"]:
            resp = client.get(f"/api/games/{game_id}?player_id={pid}")
            player_state = resp.json()
            setup = player_state["setup_state"]
            hand = setup["traitor_hands_dealt"].get(pid, [])
            if hand:
                traitor_id = hand[0]["id"]
                resp = client.post(f"/api/games/{game_id}/action", json={
                    "player_id": pid,
                    "action_type": "select_traitor",
                    "payload": {"traitor_card_id": traitor_id},
                })
                assert resp.status_code == 200

        # Check we're now at storm dial
        resp = client.get(f"/api/games/{game_id}?player_id=host1")
        state = resp.json()
        # After traitor selection, might be at storm_dial or already at storm
        if state["current_phase"] == "setup":
            assert state["setup_state"]["sub_phase"] == "storm_dial"

            # Step 6: Storm dial players submit numbers
            dial_players = state["setup_state"]["storm_dial_players"]
            for pid in dial_players:
                resp = client.post(f"/api/games/{game_id}/action", json={
                    "player_id": pid,
                    "action_type": "submit_storm_dial",
                    "payload": {"number": 5},
                })
                assert resp.status_code == 200

        # Step 7: Verify we're at STORM phase
        resp = client.get(f"/api/games/{game_id}?player_id=host1")
        state = resp.json()
        assert state["current_phase"] == "storm", (
            f"Expected STORM but got {state['current_phase']}"
        )
        assert state["phase_messages"] == [] or state.get("phase_messages") is None or state["phase_messages"] == []

        return game_id

    def test_game_starts_at_storm(self):
        """After setup, the game should be at the STORM phase."""
        game_id = self._create_and_start_game()
        resp = client.get(f"/api/games/{game_id}?player_id=host1")
        state = resp.json()
        assert state["current_phase"] == "storm"

    def test_storm_resolve_then_advance(self):
        """STORM: first click resolves (messages), second click advances to SPICE_BLOW."""
        game_id = self._create_and_start_game()

        # Verify we have lobby_state preserved (for host detection)
        resp = client.get(f"/api/games/{game_id}?player_id=host1")
        state = resp.json()
        assert state.get("lobby_state") is not None, "lobby_state should be preserved"
        assert state["lobby_state"]["host_player_id"] == "host1"

        # Click 1: resolve storm
        resp = client.post(f"/api/games/{game_id}/action", json={
            "player_id": "host1",
            "action_type": "advance_phase",
            "payload": {},
        })
        assert resp.status_code == 200
        state = resp.json()
        assert state["current_phase"] == "storm", "Should still be at STORM after resolving"
        assert len(state["phase_messages"]) > 0, "Should have phase messages after resolve"
        assert "Storm moves" in state["phase_messages"][0]

        # Click 2: advance to spice blow
        resp = client.post(f"/api/games/{game_id}/action", json={
            "player_id": "host1",
            "action_type": "advance_phase",
            "payload": {},
        })
        assert resp.status_code == 200
        state = resp.json()
        assert state["current_phase"] == "spice_blow", "Should advance to SPICE_BLOW"
        assert state["phase_messages"] == [], "Messages should be cleared"

    def test_all_automated_phases_require_two_clicks(self):
        """Each automated phase requires 2 clicks (resolve + advance) by the host."""
        game_id = self._create_and_start_game()

        expected_phases = [
            ("storm", "spice_blow"),
            ("spice_blow", "choam_charity"),
            ("choam_charity", "bidding"),
        ]

        for current, next_expected in expected_phases:
            # Verify starting phase
            resp = client.get(f"/api/games/{game_id}?player_id=host1")
            state = resp.json()
            assert state["current_phase"] == current, (
                f"Expected to be at {current} but at {state['current_phase']}"
            )

            # Click 1: resolve (stay on same phase, get messages)
            resp = client.post(f"/api/games/{game_id}/action", json={
                "player_id": "host1",
                "action_type": "advance_phase",
                "payload": {},
            })
            assert resp.status_code == 200
            state = resp.json()
            assert state["current_phase"] == current, (
                f"Should still be at {current} after resolve, got {state['current_phase']}"
            )
            assert len(state["phase_messages"]) > 0, (
                f"Should have messages after resolving {current}"
            )

            # Click 2: advance to next phase
            resp = client.post(f"/api/games/{game_id}/action", json={
                "player_id": "host1",
                "action_type": "advance_phase",
                "payload": {},
            })
            assert resp.status_code == 200
            state = resp.json()
            assert state["current_phase"] == next_expected, (
                f"Should advance from {current} to {next_expected}, got {state['current_phase']}"
            )
            assert state["phase_messages"] == [], (
                f"Messages should be cleared after advancing from {current}"
            )

    def test_non_host_cannot_advance_automated_phase(self):
        """Only the host can advance automated phases."""
        game_id = self._create_and_start_game()

        # Non-host player tries to advance
        resp = client.post(f"/api/games/{game_id}/action", json={
            "player_id": "player2",
            "action_type": "advance_phase",
            "payload": {},
        })
        assert resp.status_code == 400
        assert "host" in resp.json()["detail"].lower()

    def _skip_bidding(self, game_id: str):
        """Helper: pass on all bids until bidding is complete."""
        for _ in range(100):  # Safety limit
            resp = client.get(f"/api/games/{game_id}?player_id=host1")
            state = resp.json()

            if state["current_phase"] != "bidding":
                return state

            bidding = state.get("bidding_state")
            if bidding is None:
                # Bidding resolved — advance_phase will skip past bidding
                current_idx = state["current_player_index"]
                pid = state["players"][current_idx]["id"]
                resp = client.post(f"/api/games/{game_id}/action", json={
                    "player_id": pid,
                    "action_type": "advance_phase",
                    "payload": {},
                })
                return resp.json()

            # current_bidder is a faction name (e.g., "atreides"), not a player index
            current_bidder_faction = bidding.get("current_bidder")
            if current_bidder_faction is None:
                # No eligible bidders — advance past bidding
                current_idx = state["current_player_index"]
                pid = state["players"][current_idx]["id"]
                resp = client.post(f"/api/games/{game_id}/action", json={
                    "player_id": pid,
                    "action_type": "advance_phase",
                    "payload": {},
                })
                return resp.json()

            # Find the player with this faction
            bidder_id = None
            for p in state["players"]:
                if p["faction"] == current_bidder_faction:
                    bidder_id = p["id"]
                    break

            if bidder_id is None:
                break

            resp = client.post(f"/api/games/{game_id}/action", json={
                "player_id": bidder_id,
                "action_type": "pass_bid",
                "payload": {},
            })
            if resp.status_code != 200:
                break

        # Shouldn't reach here
        resp = client.get(f"/api/games/{game_id}?player_id=host1")
        return resp.json()

    def test_revival_cycles_through_players(self):
        """In REVIVAL, each player gets a turn before advancing to the next phase."""
        game_id = self._create_and_start_game()

        # Fast-forward to REVIVAL by advancing through automated phases
        for _ in range(3):  # Storm, Spice Blow, CHOAM Charity (2 clicks each)
            client.post(f"/api/games/{game_id}/action", json={
                "player_id": "host1",
                "action_type": "advance_phase",
                "payload": {},
            })
            client.post(f"/api/games/{game_id}/action", json={
                "player_id": "host1",
                "action_type": "advance_phase",
                "payload": {},
            })

        # Skip bidding
        state = self._skip_bidding(game_id)
        assert state["current_phase"] == "revival", (
            f"Expected revival, got {state['current_phase']}"
        )

        # Now test player cycling in REVIVAL
        players = state["players"]
        assert len(players) == 2

        # Player at index 0 should be able to advance (End Turn)
        first_player_id = players[0]["id"]
        assert state["current_player_index"] == 0

        # First player clicks "End Turn"
        resp = client.post(f"/api/games/{game_id}/action", json={
            "player_id": first_player_id,
            "action_type": "advance_phase",
            "payload": {},
        })
        assert resp.status_code == 200
        state = resp.json()
        assert state["current_phase"] == "revival", "Should still be in REVIVAL"
        assert state["current_player_index"] == 1, "Should be second player's turn"

        # Second player clicks "End Phase"
        second_player_id = players[1]["id"]
        resp = client.post(f"/api/games/{game_id}/action", json={
            "player_id": second_player_id,
            "action_type": "advance_phase",
            "payload": {},
        })
        assert resp.status_code == 200
        state = resp.json()
        assert state["current_phase"] == "shipment_and_movement", (
            f"Should advance to SHIPMENT, got {state['current_phase']}"
        )
        assert state["current_player_index"] == 0

    def test_wrong_player_cannot_advance_turn(self):
        """In turn-based phases, only the current player can advance."""
        game_id = self._create_and_start_game()

        # Fast-forward through automated phases
        for _ in range(3):
            client.post(f"/api/games/{game_id}/action", json={
                "player_id": "host1",
                "action_type": "advance_phase",
                "payload": {},
            })
            client.post(f"/api/games/{game_id}/action", json={
                "player_id": "host1",
                "action_type": "advance_phase",
                "payload": {},
            })

        # Skip bidding
        state = self._skip_bidding(game_id)
        assert state["current_phase"] == "revival", (
            f"Expected revival, got {state['current_phase']}"
        )

        players = state["players"]
        first_player_id = players[0]["id"]
        second_player_id = players[1]["id"]

        # The player who is NOT at current_player_index should fail
        wrong_player_id = second_player_id if state["current_player_index"] == 0 else first_player_id
        resp = client.post(f"/api/games/{game_id}/action", json={
            "player_id": wrong_player_id,
            "action_type": "advance_phase",
            "payload": {},
        })
        assert resp.status_code == 400
        assert "turn" in resp.json()["detail"].lower()
