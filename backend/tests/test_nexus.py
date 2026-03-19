"""
Tests for the Nexus (Alliance) phase.

Covers:
  - Nexus initialisation
  - Nexus skip when Shai-Hulud not drawn
  - propose_alliance / accept_alliance
  - break_alliance
  - pass_nexus
  - Alliance victory (4 strongholds joint)
  - Territory movement/shipment constraint
"""

import pytest

from backend.app.models.faction import FactionName
from backend.app.models.game_state import GamePhase, GameState, NexusState
from backend.app.models.player import ForceGroup
from backend.app.services.game.engine import advance_phase
from backend.app.services.game.nexus import (
    accept_alliance,
    break_alliance,
    init_nexus,
    pass_nexus,
    propose_alliance,
)
from backend.app.services.game.shipment import move_forces, ship_forces


# ---------------------------------------------------------------------------
# TestInitNexus
# ---------------------------------------------------------------------------

class TestInitNexus:
    def test_creates_nexus_state(self, game_at_nexus: GameState):
        """init_nexus should set up nexus_state and enter NEXUS phase."""
        assert game_at_nexus.current_phase == GamePhase.NEXUS
        assert game_at_nexus.nexus_state is not None

    def test_first_faction_is_first_active_player(self, game_at_nexus: GameState):
        """current_faction starts at the first non-eliminated player's faction."""
        first_faction = next(
            p.faction.value for p in game_at_nexus.players if not p.is_eliminated
        )
        assert game_at_nexus.nexus_state.current_faction == first_faction

    def test_no_proposals_at_start(self, game_at_nexus: GameState):
        """No proposals should exist at the start of the Nexus."""
        assert game_at_nexus.nexus_state.proposals == {}

    def test_no_factions_done_at_start(self, game_at_nexus: GameState):
        """No factions should be marked done at the start."""
        assert game_at_nexus.nexus_state.factions_done == []

    def test_skip_when_all_eliminated(self, basic_game: GameState):
        """If every player is eliminated, nexus initialisation skips to CHOAM."""
        eliminated = basic_game.model_copy(update={
            "current_phase": GamePhase.NEXUS,
            "players": [
                p.model_copy(update={"is_eliminated": True})
                for p in basic_game.players
            ],
        })
        result = init_nexus(eliminated)
        assert result.current_phase == GamePhase.CHOAM_CHARITY
        assert result.nexus_state is None


# ---------------------------------------------------------------------------
# TestNexusSkip (nexus_triggered = False)
# ---------------------------------------------------------------------------

class TestNexusSkip:
    def test_nexus_skipped_when_not_triggered(self, basic_game: GameState):
        """
        When nexus_triggered is False, advancing from SPICE_BLOW (after resolve)
        should jump straight to CHOAM_CHARITY, bypassing NEXUS.
        """
        # Put the game into the post-resolve state: spice_blow with phase_messages
        game = basic_game.model_copy(update={
            "current_phase": GamePhase.SPICE_BLOW,
            "nexus_triggered": False,
            "phase_messages": ["Spice blow resolved."],
        })
        result = advance_phase(game)
        assert result.current_phase == GamePhase.CHOAM_CHARITY

    def test_nexus_entered_when_triggered(self, basic_game: GameState):
        """When nexus_triggered is True, advancing enters NEXUS phase."""
        game = basic_game.model_copy(update={
            "current_phase": GamePhase.SPICE_BLOW,
            "nexus_triggered": True,
            "phase_messages": ["Shai-Hulud!"],
        })
        result = advance_phase(game)
        assert result.current_phase == GamePhase.NEXUS
        assert result.nexus_state is not None


# ---------------------------------------------------------------------------
# TestProposeAlliance
# ---------------------------------------------------------------------------

class TestProposeAlliance:
    def test_proposal_is_recorded(self, game_at_nexus: GameState):
        """Proposing an alliance records the proposal and advances turn."""
        p1 = game_at_nexus.players[0]   # atreides
        p2 = game_at_nexus.players[1]   # harkonnen

        result = propose_alliance(game_at_nexus, p1.id, p2.faction.value)

        ns = result.nexus_state
        assert ns is not None
        assert ns.proposals.get(p1.faction.value) == p2.faction.value
        assert p1.faction.value in ns.factions_done

    def test_mutual_proposal_forms_alliance(self, game_at_nexus: GameState):
        """If both factions propose to each other, the alliance forms immediately."""
        p1 = game_at_nexus.players[0]   # atreides
        p2 = game_at_nexus.players[1]   # harkonnen

        # atreides proposes to harkonnen → recorded, harkonnen's turn
        state = propose_alliance(game_at_nexus, p1.id, p2.faction.value)

        # Simulate harkonnen turn — advance nexus so it's harkonnen's turn
        # (propose already advanced for us if the two differ)
        assert state.nexus_state.current_faction == p2.faction.value

        # harkonnen proposes back → mutual → alliance forms
        result = propose_alliance(state, p2.id, p1.faction.value)

        atreides_player = next(p for p in result.players if p.faction == FactionName.ATREIDES)
        harkonnen_player = next(p for p in result.players if p.faction == FactionName.HARKONNEN)
        assert atreides_player.ally == FactionName.HARKONNEN
        assert harkonnen_player.ally == FactionName.ATREIDES

    def test_cannot_propose_to_self(self, game_at_nexus: GameState):
        p1 = game_at_nexus.players[0]
        with pytest.raises(ValueError, match="yourself"):
            propose_alliance(game_at_nexus, p1.id, p1.faction.value)

    def test_cannot_propose_when_already_allied(self, game_at_nexus: GameState):
        """A player who is already allied cannot propose a new alliance."""
        p1 = game_at_nexus.players[0]
        p2 = game_at_nexus.players[1]
        # Give p1 an existing ally
        updated = game_at_nexus.model_copy(update={
            "players": [
                p1.model_copy(update={"ally": p2.faction}) if p.id == p1.id else p
                for p in game_at_nexus.players
            ]
        })
        with pytest.raises(ValueError, match="already has an ally"):
            propose_alliance(updated, p1.id, p2.faction.value)

    def test_cannot_propose_to_already_allied_faction(self, game_at_nexus: GameState):
        """Cannot propose to a faction that already has an ally."""
        p1 = game_at_nexus.players[0]   # atreides — current turn
        p2 = game_at_nexus.players[1]   # harkonnen

        # Give p2 an existing ally (pretend)
        # In 2-player game p2's ally must be a non-existent faction — just mark directly
        updated = game_at_nexus.model_copy(update={
            "players": [
                p2.model_copy(update={"ally": FactionName.FREMEN}) if p.id == p2.id else p
                for p in game_at_nexus.players
            ]
        })
        with pytest.raises(ValueError, match="already allied"):
            propose_alliance(updated, p1.id, p2.faction.value)

    def test_wrong_turn_raises(self, game_at_nexus: GameState):
        """Only the current-turn player can propose."""
        p2 = game_at_nexus.players[1]   # not their turn
        p1 = game_at_nexus.players[0]
        with pytest.raises(ValueError, match="Not .* turn"):
            propose_alliance(game_at_nexus, p2.id, p1.faction.value)


# ---------------------------------------------------------------------------
# TestAcceptAlliance
# ---------------------------------------------------------------------------

class TestAcceptAlliance:
    def _state_with_pending_proposal(self, game_at_nexus: GameState) -> GameState:
        """Helper: atreides proposes to harkonnen → returns state at harkonnen's turn."""
        p1 = game_at_nexus.players[0]   # atreides
        p2 = game_at_nexus.players[1]   # harkonnen
        return propose_alliance(game_at_nexus, p1.id, p2.faction.value)

    def test_accept_forms_alliance(self, game_at_nexus: GameState):
        state = self._state_with_pending_proposal(game_at_nexus)
        p2 = next(p for p in state.players if p.faction == FactionName.HARKONNEN)
        p1_faction = FactionName.ATREIDES

        result = accept_alliance(state, p2.id, p1_faction.value)

        atreides = next(p for p in result.players if p.faction == FactionName.ATREIDES)
        harkonnen = next(p for p in result.players if p.faction == FactionName.HARKONNEN)
        assert atreides.ally == FactionName.HARKONNEN
        assert harkonnen.ally == FactionName.ATREIDES

    def test_accept_clears_proposal(self, game_at_nexus: GameState):
        """After acceptance, the pending proposal should be removed."""
        state = self._state_with_pending_proposal(game_at_nexus)
        p2 = next(p for p in state.players if p.faction == FactionName.HARKONNEN)
        result = accept_alliance(state, p2.id, FactionName.ATREIDES.value)
        assert result.nexus_state is None or "atreides" not in (result.nexus_state.proposals if result.nexus_state else {})

    def test_accept_nonexistent_proposal_raises(self, game_at_nexus: GameState):
        """Accepting a proposal that doesn't exist should fail."""
        # It's atreides' turn — skip to harkonnen by passing
        p1 = game_at_nexus.players[0]
        state = pass_nexus(game_at_nexus, p1.id)
        # Nexus might be over in 2-player. Re-init and only test the error.
        # Use 6-player nexus via direct validation
        p2 = game_at_nexus.players[1]
        # Force nexus to harkonnen's turn directly
        updated = game_at_nexus.model_copy(update={
            "nexus_state": game_at_nexus.nexus_state.model_copy(update={
                "current_faction": p2.faction.value,
            })
        })
        with pytest.raises(ValueError, match="No pending proposal"):
            accept_alliance(updated, p2.id, FactionName.ATREIDES.value)


# ---------------------------------------------------------------------------
# TestBreakAlliance
# ---------------------------------------------------------------------------

class TestBreakAlliance:
    def test_break_clears_both_ally_fields(self, game_at_nexus: GameState):
        """Breaking an alliance clears ally on both players."""
        p1 = game_at_nexus.players[0]   # atreides
        p2 = game_at_nexus.players[1]   # harkonnen

        # Give them an alliance
        allied = game_at_nexus.model_copy(update={
            "players": [
                p1.model_copy(update={"ally": p2.faction}),
                p2.model_copy(update={"ally": p1.faction}),
            ]
        })

        result = break_alliance(allied, p1.id)

        for p in result.players:
            assert p.ally is None

    def test_break_does_not_end_turn(self, game_at_nexus: GameState):
        """
        After breaking, the player's faction should still be current_faction —
        they can still propose or pass.
        """
        p1 = game_at_nexus.players[0]
        p2 = game_at_nexus.players[1]

        allied = game_at_nexus.model_copy(update={
            "players": [
                p1.model_copy(update={"ally": p2.faction}),
                p2.model_copy(update={"ally": p1.faction}),
            ]
        })

        result = break_alliance(allied, p1.id)
        # Turn has NOT advanced
        assert result.nexus_state is not None
        assert result.nexus_state.current_faction == p1.faction.value

    def test_break_without_ally_raises(self, game_at_nexus: GameState):
        p1 = game_at_nexus.players[0]
        with pytest.raises(ValueError, match="no alliance"):
            break_alliance(game_at_nexus, p1.id)

    def test_break_logged(self, game_at_nexus: GameState):
        """Broken alliances are recorded in game_log."""
        p1 = game_at_nexus.players[0]
        p2 = game_at_nexus.players[1]
        allied = game_at_nexus.model_copy(update={
            "players": [
                p1.model_copy(update={"ally": p2.faction}),
                p2.model_copy(update={"ally": p1.faction}),
            ]
        })
        result = break_alliance(allied, p1.id)
        assert any("breaks alliance" in entry for entry in result.game_log)


# ---------------------------------------------------------------------------
# TestPassNexus
# ---------------------------------------------------------------------------

class TestPassNexus:
    def test_pass_advances_to_next_player(self, six_player_nexus: GameState):
        """Passing advances the turn to the next faction."""
        ns = six_player_nexus.nexus_state
        first_faction = ns.current_faction
        first_player = next(
            p for p in six_player_nexus.players if p.faction.value == first_faction
        )

        result = pass_nexus(six_player_nexus, first_player.id)

        assert result.nexus_state is not None
        assert result.nexus_state.current_faction != first_faction
        assert first_faction in result.nexus_state.factions_done

    def test_all_pass_ends_nexus(self, game_at_nexus: GameState):
        """When all players pass, the Nexus ends and CHOAM_CHARITY begins."""
        state = game_at_nexus
        for player in state.players:
            if not player.is_eliminated:
                # Force it to be this player's turn
                state = state.model_copy(update={
                    "nexus_state": state.nexus_state.model_copy(update={
                        "current_faction": player.faction.value,
                    })
                })
                state = pass_nexus(state, player.id)
                if state.current_phase == GamePhase.CHOAM_CHARITY:
                    break

        assert state.current_phase == GamePhase.CHOAM_CHARITY
        assert state.nexus_state is None

    def test_pass_marks_faction_done(self, game_at_nexus: GameState):
        p1 = game_at_nexus.players[0]
        result = pass_nexus(game_at_nexus, p1.id)
        if result.nexus_state is not None:
            assert p1.faction.value in result.nexus_state.factions_done

    def test_wrong_turn_raises(self, game_at_nexus: GameState):
        p2 = game_at_nexus.players[1]
        with pytest.raises(ValueError, match="Not .* turn"):
            pass_nexus(game_at_nexus, p2.id)


# ---------------------------------------------------------------------------
# TestAllianceVictory
# ---------------------------------------------------------------------------

class TestAllianceVictory:
    """Alliance needs 4 strongholds; solo faction needs 3."""

    def _give_strongholds(self, game_state: GameState, faction: FactionName, names: list[str]) -> GameState:
        """Helper: place the faction's forces in the given strongholds."""
        player = next(p for p in game_state.players if p.faction == faction)
        new_forces = list(player.forces_on_board)
        for sh_name in names:
            territory = game_state.territories[sh_name]
            sector = territory.sectors[0]
            # Only add if not already there
            if not any(fg.territory_name == sh_name for fg in new_forces):
                new_forces.append(ForceGroup(
                    territory_name=sh_name,
                    sector=sector,
                    regular_count=1,
                    special_count=0,
                ))
        updated_player = player.model_copy(update={"forces_on_board": new_forces})
        return game_state.model_copy(update={
            "players": [
                updated_player if p.faction == faction else p
                for p in game_state.players
            ]
        })

    def test_solo_wins_with_3_strongholds(self, basic_game: GameState):
        """An unallied faction controlling 3 strongholds triggers victory."""
        from backend.app.services.game.engine import _check_stronghold_victory

        game = self._give_strongholds(
            basic_game, FactionName.ATREIDES,
            ["Arrakeen", "Sietch Tabr", "Tuek's Sietch"],
        )
        game = game.model_copy(update={"current_phase": GamePhase.MENTAT_PAUSE})
        winner = _check_stronghold_victory(game)
        assert winner == FactionName.ATREIDES

    def test_solo_does_not_win_with_2_strongholds(self, basic_game: GameState):
        from backend.app.services.game.engine import _check_stronghold_victory

        game = self._give_strongholds(
            basic_game, FactionName.ATREIDES,
            ["Arrakeen", "Sietch Tabr"],
        )
        game = game.model_copy(update={"current_phase": GamePhase.MENTAT_PAUSE})
        assert _check_stronghold_victory(game) is None

    def test_alliance_needs_4_strongholds(self, basic_game: GameState):
        """An allied pair needs 4 combined strongholds to win."""
        from backend.app.services.game.engine import _check_stronghold_victory

        # Atreides starts in Arrakeen (1), Harkonnen starts in Carthag (1).
        # Add Tuek's Sietch to Harkonnen only → combined total = 3, not enough.
        game = self._give_strongholds(
            basic_game, FactionName.HARKONNEN,
            ["Tuek's Sietch"],
        )
        # Set up alliance
        game = game.model_copy(update={
            "players": [
                p.model_copy(update={"ally": FactionName.HARKONNEN})
                if p.faction == FactionName.ATREIDES
                else p.model_copy(update={"ally": FactionName.ATREIDES})
                if p.faction == FactionName.HARKONNEN
                else p
                for p in game.players
            ],
            "current_phase": GamePhase.MENTAT_PAUSE,
        })
        # Arrakeen + Carthag + Tuek's Sietch = 3 total — not enough (need 4)
        assert _check_stronghold_victory(game) is None

    def test_alliance_wins_with_4_strongholds(self, basic_game: GameState):
        """Allied pair with 4 combined strongholds wins."""
        from backend.app.services.game.engine import _check_stronghold_victory

        game = self._give_strongholds(
            basic_game, FactionName.ATREIDES,
            ["Arrakeen", "Sietch Tabr", "Habbanya Sietch"],
        )
        game = self._give_strongholds(
            game, FactionName.HARKONNEN,
            ["Tuek's Sietch"],
        )
        game = game.model_copy(update={
            "players": [
                p.model_copy(update={"ally": FactionName.HARKONNEN})
                if p.faction == FactionName.ATREIDES
                else p.model_copy(update={"ally": FactionName.ATREIDES})
                if p.faction == FactionName.HARKONNEN
                else p
                for p in game.players
            ],
            "current_phase": GamePhase.MENTAT_PAUSE,
        })
        winner = _check_stronghold_victory(game)
        # Either ally can be returned as the winner
        assert winner in (FactionName.ATREIDES, FactionName.HARKONNEN)


# ---------------------------------------------------------------------------
# TestAllianceTerritoryConstraint
# ---------------------------------------------------------------------------

class TestAllianceTerritoryConstraint:
    """
    Allied players cannot ship or move into a territory occupied by their ally.
    Polar Sink is exempt from this rule.
    """

    def _ally_game(self, basic_game: GameState) -> tuple[GameState, str, str]:
        """
        Returns (game, atreides_player_id, harkonnen_player_id) where both are allied.
        Atreides starts in Arrakeen, Harkonnen starts in Carthag.
        """
        p1 = next(p for p in basic_game.players if p.faction == FactionName.ATREIDES)
        p2 = next(p for p in basic_game.players if p.faction == FactionName.HARKONNEN)
        game = basic_game.model_copy(update={
            "players": [
                p.model_copy(update={"ally": FactionName.HARKONNEN}) if p.faction == FactionName.ATREIDES
                else p.model_copy(update={"ally": FactionName.ATREIDES}) if p.faction == FactionName.HARKONNEN
                else p
                for p in basic_game.players
            ],
            "current_phase": GamePhase.SHIPMENT_AND_MOVEMENT,
        })
        return game, p1.id, p2.id

    def test_cannot_ship_to_ally_occupied_territory(self, basic_game: GameState):
        """Atreides cannot ship into Carthag where Harkonnen has forces."""
        game, atreides_id, _ = self._ally_game(basic_game)
        # Verify Harkonnen is in Carthag
        harkonnen = next(p for p in game.players if p.faction == FactionName.HARKONNEN)
        assert any(fg.territory_name == "Carthag" for fg in harkonnen.forces_on_board)

        with pytest.raises(ValueError, match="ally has forces"):
            ship_forces(game, atreides_id, "Carthag", 11, 1)

    def test_can_ship_to_unoccupied_territory(self, basic_game: GameState):
        """Atreides can still ship to a territory with no ally forces."""
        game, atreides_id, _ = self._ally_game(basic_game)
        # Sietch Tabr is a stronghold with no starting forces for either faction
        atreides = next(p for p in game.players if p.faction == FactionName.ATREIDES)
        assert all(fg.territory_name != "Sietch Tabr" for fg in atreides.forces_on_board)
        harkonnen = next(p for p in game.players if p.faction == FactionName.HARKONNEN)
        assert all(fg.territory_name != "Sietch Tabr" for fg in harkonnen.forces_on_board)

        # Should not raise
        result = ship_forces(game, atreides_id, "Sietch Tabr", 8, 1)
        atreides_after = next(p for p in result.players if p.faction == FactionName.ATREIDES)
        assert any(fg.territory_name == "Sietch Tabr" for fg in atreides_after.forces_on_board)

    def test_polar_sink_exempt_from_constraint(self, basic_game: GameState):
        """Polar Sink is exempt — allies may both have forces there."""
        game, atreides_id, harkonnen_id = self._ally_game(basic_game)

        # Put Harkonnen forces in Polar Sink manually
        harkonnen = next(p for p in game.players if p.faction == FactionName.HARKONNEN)
        new_forces = list(harkonnen.forces_on_board) + [
            ForceGroup(territory_name="Polar Sink", sector=0, regular_count=3)
        ]
        game = game.model_copy(update={
            "players": [
                p.model_copy(update={"forces_on_board": new_forces})
                if p.faction == FactionName.HARKONNEN else p
                for p in game.players
            ]
        })

        # Atreides can still ship to Polar Sink even though ally is there
        result = ship_forces(game, atreides_id, "Polar Sink", 0, 1)
        atreides_after = next(p for p in result.players if p.faction == FactionName.ATREIDES)
        assert any(fg.territory_name == "Polar Sink" for fg in atreides_after.forces_on_board)

    def test_cannot_move_to_ally_occupied_territory(self, basic_game: GameState):
        """Moving into an ally-occupied territory should also be blocked."""
        from backend.app.data.adjacency import ADJACENCY

        game, atreides_id, _ = self._ally_game(basic_game)

        # Carthag (sector 11) is where Harkonnen starts.
        # Find a territory adjacent to Carthag (excluding Polar Sink) and
        # place Atreides forces there so they can try to move into Carthag.
        carthag_adj = [t for t in ADJACENCY.get("Carthag", frozenset()) if t != "Polar Sink"]
        if not carthag_adj:
            pytest.skip("No non-Polar-Sink territory adjacent to Carthag found")

        adj_name = carthag_adj[0]
        adj_territory = game.territories[adj_name]
        adj_sector = adj_territory.sectors[0]

        # Place Atreides forces in the adjacent territory
        atreides = next(p for p in game.players if p.faction == FactionName.ATREIDES)
        existing = next(
            (fg for fg in atreides.forces_on_board if fg.territory_name == adj_name),
            None,
        )
        if existing is None:
            new_forces = list(atreides.forces_on_board) + [
                ForceGroup(territory_name=adj_name, sector=adj_sector, regular_count=2)
            ]
            game = game.model_copy(update={
                "players": [
                    p.model_copy(update={"forces_on_board": new_forces})
                    if p.faction == FactionName.ATREIDES else p
                    for p in game.players
                ]
            })
            from_sector = adj_sector
        else:
            from_sector = existing.sector

        # Atreides tries to move into Carthag where Harkonnen (ally) has forces
        with pytest.raises(ValueError, match="ally has forces"):
            move_forces(
                game, atreides_id,
                adj_name, from_sector,
                "Carthag", 11,
                regular_count=1,
            )
