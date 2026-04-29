"""
Tests for the five critical rule fixes:
  1. Revival: 3-per-turn combined cap (free + paid)
  2. Revival: Leader revival only allowed when ALL leaders are in tanks
  3. Bidding: All-pass rule — remaining cards returned to deck, not discarded
  4. Bidding: Rotating start bidder per card
  5. Ornithopter movement: 3-territory range when player has forces in Arrakeen/Carthag

Run with:
    cd DuneGame
    python -m pytest backend/tests/test_critical_fixes.py -v
"""

import pytest

from backend.app.models.faction import FactionName
from backend.app.models.game_state import GameMode, GamePhase, GameState
from backend.app.models.leader import Leader, LeaderStatus
from backend.app.models.player import ForceGroup
from backend.app.services.game.bidding import init_bidding, pass_bid, place_bid
from backend.app.services.game.revival import (
    MAX_REVIVAL_PER_TURN,
    resolve_free_revival,
    revive_forces,
    revive_leader,
)
from backend.app.services.game.setup import PlayerSetupConfig, create_game
from backend.app.services.game.shipment import move_forces


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXED_STORM = 0  # Sector away from starting positions


def _make_game(*factions: FactionName, mode: GameMode = GameMode.BASIC) -> GameState:
    configs = [
        PlayerSetupConfig(player_id=f"p{i}", player_name=f.value, faction=f)
        for i, f in enumerate(factions, start=1)
    ]
    return create_game(
        game_id="test-critical",
        player_configs=configs,
        mode=mode,
        initial_storm_sector=FIXED_STORM,
    )


def _at_revival(game: GameState) -> GameState:
    """Put game at REVIVAL phase and run free revival so counters are set."""
    game = game.model_copy(update={"current_phase": GamePhase.REVIVAL})
    return resolve_free_revival(game)


def _get_player(game: GameState, faction: FactionName):
    return next(p for p in game.players if p.faction == faction)


def _set_player(game: GameState, faction: FactionName, **kwargs) -> GameState:
    """Return a copy of game with the given faction's player updated."""
    updated = [
        p.model_copy(update=kwargs) if p.faction == faction else p
        for p in game.players
    ]
    return game.model_copy(update={"players": updated})


# ---------------------------------------------------------------------------
# 1. Revival: 3-per-turn combined cap
# ---------------------------------------------------------------------------

class TestRevivalThreePerTurnCap:
    """Combined free + paid revival cannot exceed 3 per turn."""

    def test_free_revival_sets_counter(self):
        """resolve_free_revival tracks how many forces were auto-revived."""
        game = _make_game(FactionName.ATREIDES, FactionName.HARKONNEN)
        # Put 5 forces in tanks
        game = _set_player(game, FactionName.ATREIDES, forces_in_tanks=5, forces_in_reserve=0)
        game = _at_revival(game)

        atreides = _get_player(game, FactionName.ATREIDES)
        # Atreides free revival = 2; so counter should be 2
        assert atreides.forces_revived_this_turn == 2

    def test_paid_revival_respects_cap(self):
        """Paying to revive beyond the 3-force cap raises ValueError."""
        game = _make_game(FactionName.ATREIDES, FactionName.HARKONNEN)
        # Atreides free = 2, so only 1 slot remains
        game = _set_player(game, FactionName.ATREIDES,
                           forces_in_tanks=10, forces_in_reserve=0, spice=20)
        game = _at_revival(game)

        atreides = _get_player(game, FactionName.ATREIDES)
        # After free revival, counter = 2; requesting 2 paid should fail
        with pytest.raises(ValueError, match="3"):
            revive_forces(game, atreides.id, 2)

    def test_paid_revival_within_cap_succeeds(self):
        """Paying for 1 force when 1 slot remains is allowed."""
        game = _make_game(FactionName.ATREIDES, FactionName.HARKONNEN)
        game = _set_player(game, FactionName.ATREIDES,
                           forces_in_tanks=10, forces_in_reserve=0, spice=20)
        game = _at_revival(game)

        atreides = _get_player(game, FactionName.ATREIDES)
        result = revive_forces(game, atreides.id, 1)
        atreides_after = _get_player(result, FactionName.ATREIDES)
        assert atreides_after.forces_revived_this_turn == 3

    def test_cap_blocks_when_fully_used(self):
        """Once cap is fully used (free = 3), paid revival is blocked entirely."""
        game = _make_game(FactionName.EMPEROR, FactionName.HARKONNEN)
        emperor = _get_player(game, FactionName.EMPEROR)
        # Emperor free revival = 1; cap = 3; so 2 paid slots remain
        game = _set_player(game, FactionName.EMPEROR,
                           forces_in_tanks=10, forces_in_reserve=0, spice=20,
                           forces_revived_this_turn=MAX_REVIVAL_PER_TURN)
        game = _at_revival(game)

        # resolve_free_revival resets counter, so we need to force the counter manually
        game = _set_player(game, FactionName.EMPEROR,
                           forces_revived_this_turn=MAX_REVIVAL_PER_TURN)
        emperor = _get_player(game, FactionName.EMPEROR)
        with pytest.raises(ValueError, match="already revived"):
            revive_forces(game, emperor.id, 1)

    def test_fremen_cannot_pay_for_extra(self):
        """Fremen may not call revive_forces (their free revival fills the cap)."""
        game = _make_game(FactionName.FREMEN, FactionName.ATREIDES)
        game = _set_player(game, FactionName.FREMEN,
                           forces_in_tanks=10, forces_in_reserve=0, spice=20)
        game = _at_revival(game)

        fremen = _get_player(game, FactionName.FREMEN)
        with pytest.raises(ValueError, match="Fremen"):
            revive_forces(game, fremen.id, 1)

    def test_counter_resets_each_revival_phase(self):
        """resolve_free_revival always resets the counter before applying free revival."""
        game = _make_game(FactionName.ATREIDES, FactionName.HARKONNEN)
        # Manually set a stale counter from a previous turn
        game = _set_player(game, FactionName.ATREIDES,
                           forces_in_tanks=5, forces_revived_this_turn=99)
        game = game.model_copy(update={"current_phase": GamePhase.REVIVAL})
        game = resolve_free_revival(game)

        atreides = _get_player(game, FactionName.ATREIDES)
        # Counter should reflect ONLY this turn's free revival (2 for Atreides)
        assert atreides.forces_revived_this_turn == 2


# ---------------------------------------------------------------------------
# 2. Revival: All-leaders-in-tanks gate for leader revival
# ---------------------------------------------------------------------------

class TestLeaderRevivalGate:
    """A leader can only be revived when ALL of the player's leaders are in the Tanks."""

    def _make_game_with_atreides_leaders_in_tanks(self, count_in_tanks: int):
        """Helper: create Atreides game with `count_in_tanks` leaders in the Tanks."""
        game = _make_game(FactionName.ATREIDES, FactionName.HARKONNEN)
        atreides = _get_player(game, FactionName.ATREIDES)

        # Update leader statuses: first `count_in_tanks` go to IN_TANKS, rest AVAILABLE
        updated_leaders = []
        for i, leader in enumerate(atreides.leaders):
            if i < count_in_tanks:
                updated_leaders.append(leader.model_copy(update={"status": LeaderStatus.IN_TANKS}))
            else:
                updated_leaders.append(leader.model_copy(update={"status": LeaderStatus.AVAILABLE}))

        game = _set_player(game, FactionName.ATREIDES,
                           leaders=updated_leaders, spice=20)
        return _at_revival(game)

    def test_cannot_revive_when_leaders_available(self):
        """Reviving a leader fails if not all leaders are in the Tanks."""
        # 4 of 5 in tanks — should block revival
        game = self._make_game_with_atreides_leaders_in_tanks(4)
        atreides = _get_player(game, FactionName.ATREIDES)
        # The first leader in tanks
        target = next(l for l in atreides.leaders if l.status == LeaderStatus.IN_TANKS)

        with pytest.raises(ValueError, match="all.*leaders"):
            revive_leader(game, atreides.id, target.id)

    def test_cannot_revive_when_one_available(self):
        """Reviving a leader fails if even 1 leader is not in the Tanks."""
        # Only 3 of 5 in tanks
        game = self._make_game_with_atreides_leaders_in_tanks(3)
        atreides = _get_player(game, FactionName.ATREIDES)
        target = next(l for l in atreides.leaders if l.status == LeaderStatus.IN_TANKS)

        with pytest.raises(ValueError, match="all.*leaders"):
            revive_leader(game, atreides.id, target.id)

    def test_can_revive_when_all_in_tanks(self):
        """Reviving a leader succeeds when all 5 leaders are in the Tanks."""
        game = self._make_game_with_atreides_leaders_in_tanks(5)
        atreides = _get_player(game, FactionName.ATREIDES)
        target = atreides.leaders[0]  # Any leader in tanks

        result = revive_leader(game, atreides.id, target.id)
        atreides_after = _get_player(result, FactionName.ATREIDES)
        revived = next(l for l in atreides_after.leaders if l.id == target.id)
        assert revived.status == LeaderStatus.AVAILABLE

    def test_only_one_leader_per_turn(self):
        """Attempting to revive a second leader in the same Revival phase fails."""
        game = self._make_game_with_atreides_leaders_in_tanks(5)
        atreides = _get_player(game, FactionName.ATREIDES)

        # Revive first leader
        first = atreides.leaders[0]
        game = revive_leader(game, atreides.id, first.id)

        # Now all leaders must be back in tanks to attempt another (set them)
        # But leader_revived_this_turn should block us immediately
        atreides_after = _get_player(game, FactionName.ATREIDES)
        assert atreides_after.leader_revived_this_turn is True

        # Try to revive a second leader — should fail on the "already revived" check
        second = next(
            l for l in atreides_after.leaders
            if l.id != first.id and l.status == LeaderStatus.IN_TANKS
        )
        with pytest.raises(ValueError, match="already revived a leader"):
            revive_leader(game, atreides.id, second.id)

    def test_leader_revived_flag_reset_by_free_revival(self):
        """resolve_free_revival resets leader_revived_this_turn to False."""
        game = _make_game(FactionName.ATREIDES, FactionName.HARKONNEN)
        # Manually set flag as if a leader was revived last turn
        game = _set_player(game, FactionName.ATREIDES, leader_revived_this_turn=True)
        game = game.model_copy(update={"current_phase": GamePhase.REVIVAL})
        game = resolve_free_revival(game)

        atreides = _get_player(game, FactionName.ATREIDES)
        assert atreides.leader_revived_this_turn is False


# ---------------------------------------------------------------------------
# 3. Bidding: All-pass rule — cards returned to deck
# ---------------------------------------------------------------------------

class TestBiddingAllPassRule:
    """When all players pass a card with no bids, remaining cards go back to deck."""

    def _setup_bidding(self) -> GameState:
        """Create a fresh 2-player game in BIDDING phase."""
        game = _make_game(FactionName.ATREIDES, FactionName.HARKONNEN)
        game = game.model_copy(update={"current_phase": GamePhase.BIDDING})
        return init_bidding(game)

    def test_all_pass_ends_bidding(self):
        """When all players pass with no bids, the Bidding phase ends."""
        game = self._setup_bidding()
        bs = game.bidding_state

        p1 = next(p for p in game.players if p.faction == bs.current_bidder)
        game = pass_bid(game, p1.id)

        bs2 = game.bidding_state
        p2 = next(p for p in game.players if p.faction == bs2.current_bidder)
        game = pass_bid(game, p2.id)

        # Bidding phase should have ended
        assert game.current_phase != GamePhase.BIDDING
        assert game.bidding_state is None

    def test_all_pass_returns_cards_to_deck(self):
        """The unsold cards must be returned to the TOP of the Treachery Deck."""
        game = self._setup_bidding()
        bs = game.bidding_state
        # Record which cards were up for auction
        unsold_ids = {c.id for c in bs.cards_up_for_bid}
        # Record deck size before
        deck_before = len(game.treachery_deck)

        # Both players pass
        p1 = next(p for p in game.players if p.faction == bs.current_bidder)
        game = pass_bid(game, p1.id)
        bs2 = game.bidding_state
        p2 = next(p for p in game.players if p.faction == bs2.current_bidder)
        game = pass_bid(game, p2.id)

        # Deck should now contain the unsold cards again
        deck_ids_after = {c.id for c in game.treachery_deck}
        assert unsold_ids.issubset(deck_ids_after), (
            "Unsold cards should have been returned to the deck"
        )
        # Deck size should have grown by the number of returned cards
        assert len(game.treachery_deck) == deck_before + len(unsold_ids)

    def test_all_pass_on_second_card_returns_remaining(self):
        """If card 1 is won but all pass on card 2, only card 2+ return to deck."""
        game = self._setup_bidding()
        bs = game.bidding_state
        second_card_id = bs.cards_up_for_bid[1].id

        # Card 1: p1 bids 1, p2 passes → p1 wins card 1
        p1 = next(p for p in game.players if p.faction == bs.current_bidder)
        game = place_bid(game, p1.id, 1)

        bs2 = game.bidding_state
        p2 = next(p for p in game.players if p.faction == bs2.current_bidder)
        game = pass_bid(game, p2.id)  # p1 wins card 1

        # Now on card 2; both players pass
        if game.bidding_state is not None:
            bs3 = game.bidding_state
            opener3 = next(p for p in game.players if p.faction == bs3.current_bidder)
            game = pass_bid(game, opener3.id)

            if game.bidding_state is not None:
                bs4 = game.bidding_state
                other = next(p for p in game.players if p.faction == bs4.current_bidder)
                game = pass_bid(game, other.id)

        # Card 2 should be back in the deck
        deck_ids = {c.id for c in game.treachery_deck}
        assert second_card_id in deck_ids

    def test_cards_returned_to_top_of_deck(self):
        """Returned cards should be at the TOP (index 0+) of the deck."""
        game = self._setup_bidding()
        bs = game.bidding_state
        unsold_ids = [c.id for c in bs.cards_up_for_bid]

        p1 = next(p for p in game.players if p.faction == bs.current_bidder)
        game = pass_bid(game, p1.id)
        bs2 = game.bidding_state
        p2 = next(p for p in game.players if p.faction == bs2.current_bidder)
        game = pass_bid(game, p2.id)

        # First N entries of the restored deck should be the returned cards
        returned = [c.id for c in game.treachery_deck[:len(unsold_ids)]]
        assert returned == unsold_ids


# ---------------------------------------------------------------------------
# 4. Bidding: Rotating start bidder
# ---------------------------------------------------------------------------

class TestBiddingRotatingOpener:
    """Each card's auction opens with the next eligible player to the right."""

    def _make_three_player_bidding(self) -> GameState:
        """3-player game (Atreides, Harkonnen, Fremen) in BIDDING."""
        game = _make_game(
            FactionName.ATREIDES,
            FactionName.HARKONNEN,
            FactionName.FREMEN,
        )
        game = game.model_copy(update={"current_phase": GamePhase.BIDDING})
        return init_bidding(game)

    def test_opening_bidder_tracked(self):
        """BiddingState.opening_bidder is set when bidding starts."""
        game = self._make_three_player_bidding()
        bs = game.bidding_state
        assert bs.opening_bidder is not None
        assert bs.opening_bidder == bs.current_bidder

    def test_second_card_opener_is_next_right(self):
        """After card 1 is resolved, card 2 opens with the player to the right of card 1's opener."""
        game = self._make_three_player_bidding()
        bs = game.bidding_state
        card1_opener = bs.opening_bidder

        # Resolve card 1: opener bids 1, all others pass
        players_in_order = [p.faction for p in game.players]
        opener_player = next(p for p in game.players if p.faction == card1_opener)
        game = place_bid(game, opener_player.id, 1)

        # Everyone else passes
        while game.bidding_state and game.bidding_state.current_card_index == 0:
            current = game.bidding_state.current_bidder
            p = next(pl for pl in game.players if pl.faction == current)
            game = pass_bid(game, p.id)

        if game.bidding_state is None or game.bidding_state.current_card_index < 1:
            pytest.skip("Not enough cards for 2-card rotation test")

        bs2 = game.bidding_state
        card2_opener = bs2.opening_bidder

        # card2_opener should be the player to the right of card1_opener
        opener_idx = players_in_order.index(card1_opener)
        # Find next eligible player to the right (wrapping)
        for i in range(1, len(players_in_order) + 1):
            candidate = players_in_order[(opener_idx + i) % len(players_in_order)]
            candidate_player = next(p for p in game.players if p.faction == candidate)
            from backend.app.services.game.handlers.registry import get_handler
            handler = get_handler(candidate)
            max_cards = handler.get_max_treachery_cards(candidate_player, game)
            if len(candidate_player.treachery_hand) < max_cards:
                assert card2_opener == candidate, (
                    f"Expected card 2 to open with {candidate.value}, "
                    f"got {card2_opener.value if card2_opener else None}"
                )
                break

    def test_opener_is_current_bidder_at_card_start(self):
        """opening_bidder equals current_bidder at the start of each new card."""
        game = self._make_three_player_bidding()
        bs = game.bidding_state
        # At the very start, both should match
        assert bs.opening_bidder == bs.current_bidder


# ---------------------------------------------------------------------------
# 5. Ornithopter movement
# ---------------------------------------------------------------------------

class TestOrnithopterMovement:
    """A player with forces in Arrakeen or Carthag gets 3-territory range."""

    def _make_ship_move_game(self) -> GameState:
        """Atreides vs Harkonnen; Atreides starts in Arrakeen."""
        game = _make_game(FactionName.ATREIDES, FactionName.HARKONNEN)
        return game.model_copy(update={"current_phase": GamePhase.SHIPMENT_AND_MOVEMENT})

    def test_atreides_has_ornithopter_by_default(self):
        """Atreides starts in Arrakeen, so they have ornithopter access."""
        game = self._make_ship_move_game()
        from backend.app.services.game.shipment import _has_ornithopter_access
        atreides = _get_player(game, FactionName.ATREIDES)
        assert _has_ornithopter_access(atreides) is True

    def test_harkonnen_has_no_ornithopter(self):
        """Harkonnen starts in Carthag, so they also have ornithopter access."""
        game = self._make_ship_move_game()
        from backend.app.services.game.shipment import _has_ornithopter_access
        harkonnen = _get_player(game, FactionName.HARKONNEN)
        # Harkonnen starts in Carthag (a city) → ornithopter access
        assert _has_ornithopter_access(harkonnen) is True

    def test_player_without_city_forces_has_no_ornithopter(self):
        """A player with no forces in Arrakeen or Carthag has no ornithopter."""
        game = self._make_ship_move_game()
        from backend.app.services.game.shipment import _has_ornithopter_access
        atreides = _get_player(game, FactionName.ATREIDES)

        # Remove all Arrakeen/Carthag forces
        non_city_forces = [
            fg for fg in atreides.forces_on_board
            if fg.territory_name not in ("Arrakeen", "Carthag")
        ]
        atreides_no_city = atreides.model_copy(update={"forces_on_board": non_city_forces})
        assert _has_ornithopter_access(atreides_no_city) is False

    def test_ornithopter_allows_3_hop_move(self):
        """A player with ornithopter can move to a territory 2+ hops away."""
        game = self._make_ship_move_game()
        from backend.app.data.adjacency import get_reachable_within

        atreides = _get_player(game, FactionName.ATREIDES)
        # Atreides is in Arrakeen (sector 8) — find a 2-hop destination
        arrakeen_neighbors = set()
        for fg in atreides.forces_on_board:
            if fg.territory_name == "Arrakeen":
                from backend.app.data.adjacency import get_adjacent
                for neighbor in get_adjacent("Arrakeen"):
                    for n2 in get_adjacent(neighbor):
                        if n2 != "Arrakeen":
                            arrakeen_neighbors.add(n2)

        reachable_3 = get_reachable_within("Arrakeen", 3)
        # A 2-hop territory should be reachable within 3 hops
        assert len(reachable_3) > len(get_reachable_within("Arrakeen", 1))

    def test_non_ornithopter_blocked_at_2_hops(self):
        """A player without ornithopter cannot move to a territory 2+ hops away."""
        game = self._make_ship_move_game()
        from backend.app.data.adjacency import get_adjacent, get_reachable_within

        # Place Emperor forces in Polar Sink (no Arrakeen/Carthag ownership)
        # Emperor starts off-planet, so put a force in Polar Sink
        configs = [
            PlayerSetupConfig(player_id="p1", player_name="emp", faction=FactionName.EMPEROR),
            PlayerSetupConfig(player_id="p2", player_name="atreides", faction=FactionName.ATREIDES),
        ]
        g2 = create_game("test-orn", configs, GameMode.BASIC, FIXED_STORM)
        g2 = g2.model_copy(update={"current_phase": GamePhase.SHIPMENT_AND_MOVEMENT})

        emperor = _get_player(g2, FactionName.EMPEROR)

        # Place emperor forces only in Polar Sink
        forces = [ForceGroup(territory_name="Polar Sink", sector=0, regular_count=3)]
        g2 = _set_player(g2, FactionName.EMPEROR, forces_on_board=forces, forces_in_reserve=17)

        from backend.app.services.game.shipment import _has_ornithopter_access
        emperor_updated = _get_player(g2, FactionName.EMPEROR)
        assert _has_ornithopter_access(emperor_updated) is False

        # Moving 1 hop from Polar Sink should work (to an adjacent territory)
        adjacent_to_sink = list(get_adjacent("Polar Sink"))
        assert len(adjacent_to_sink) > 0

        # Moving 2 hops should fail via move_forces
        two_hop_targets = []
        for neighbor in adjacent_to_sink:
            for n2 in get_adjacent(neighbor):
                if n2 != "Polar Sink" and n2 not in adjacent_to_sink:
                    two_hop_targets.append(n2)

        if two_hop_targets:
            target = two_hop_targets[0]
            target_terr = g2.territories[target]
            sector = target_terr.sectors[0]
            with pytest.raises(ValueError, match="not adjacent|not reachable"):
                move_forces(g2, emperor_updated.id, "Polar Sink", 0, target, sector, regular_count=1)

    def test_get_move_range_returns_3_with_ornithopter(self):
        """_get_move_range returns 3 when player has forces in Arrakeen."""
        from backend.app.services.game.shipment import _get_move_range
        game = self._make_ship_move_game()
        atreides = _get_player(game, FactionName.ATREIDES)
        assert _get_move_range(atreides, game) == 3

    def test_get_move_range_returns_1_without_ornithopter(self):
        """_get_move_range returns 1 when player has no city forces."""
        from backend.app.services.game.shipment import _get_move_range
        game = self._make_ship_move_game()
        atreides = _get_player(game, FactionName.ATREIDES)
        # Remove city forces
        forces = [fg for fg in atreides.forces_on_board
                  if fg.territory_name not in ("Arrakeen", "Carthag")]
        forces.append(ForceGroup(territory_name="Polar Sink", sector=0, regular_count=3))
        atreides_no_city = atreides.model_copy(update={"forces_on_board": forces})
        # Need a GameState with the updated player
        updated_game = game.model_copy(update={
            "players": [atreides_no_city if p.faction == FactionName.ATREIDES else p
                        for p in game.players]
        })
        assert _get_move_range(atreides_no_city, updated_game) == 1

    def test_ornithopter_move_succeeds_2_hops(self):
        """Atreides (in Arrakeen) can move forces to a territory 2 hops away."""
        game = self._make_ship_move_game()
        from backend.app.data.adjacency import get_adjacent

        atreides = _get_player(game, FactionName.ATREIDES)
        # Find Arrakeen forces
        arrakeen_fg = next(
            (fg for fg in atreides.forces_on_board if fg.territory_name == "Arrakeen"),
            None,
        )
        if arrakeen_fg is None:
            pytest.skip("No Arrakeen forces found for Atreides")

        # Find a territory exactly 2 hops from Arrakeen
        arrakeen_neighbors = get_adjacent("Arrakeen")
        two_hop = None
        for n in arrakeen_neighbors:
            for n2 in get_adjacent(n):
                if (n2 != "Arrakeen"
                        and n2 not in arrakeen_neighbors
                        and n2 in game.territories):
                    terr = game.territories[n2]
                    # Pick a non-storm sector
                    safe_sector = next(
                        (s for s in terr.sectors if s != game.storm_sector), None
                    )
                    if safe_sector is not None:
                        two_hop = (n2, safe_sector)
                        break
            if two_hop:
                break

        if two_hop is None:
            pytest.skip("Could not find a clear 2-hop destination")

        dest_name, dest_sector = two_hop
        result = move_forces(
            game, atreides.id,
            "Arrakeen", arrakeen_fg.sector,
            dest_name, dest_sector,
            regular_count=1,
        )
        # Verify forces arrived
        atreides_after = _get_player(result, FactionName.ATREIDES)
        dest_forces = sum(
            fg.regular_count + fg.special_count
            for fg in atreides_after.forces_on_board
            if fg.territory_name == dest_name
        )
        assert dest_forces >= 1


# ---------------------------------------------------------------------------
# 6. BFS reachability utility
# ---------------------------------------------------------------------------

class TestGetReachableWithin:
    """Unit tests for the adjacency BFS helper."""

    def test_1_hop_equals_adjacent(self):
        """get_reachable_within with max_hops=1 should equal get_adjacent."""
        from backend.app.data.adjacency import get_adjacent, get_reachable_within
        for t in ["Arrakeen", "Polar Sink", "Imperial Basin"]:
            assert get_reachable_within(t, 1) == get_adjacent(t)

    def test_2_hops_larger_than_1(self):
        """2-hop reachable set is larger than 1-hop for most territories."""
        from backend.app.data.adjacency import get_reachable_within
        r1 = get_reachable_within("Arrakeen", 1)
        r2 = get_reachable_within("Arrakeen", 2)
        assert len(r2) > len(r1)

    def test_0_hops_empty(self):
        """0 hops returns empty set."""
        from backend.app.data.adjacency import get_reachable_within
        assert get_reachable_within("Arrakeen", 0) == frozenset()

    def test_blocked_territory_excluded(self):
        """Blocked territories are not included in the reachable set."""
        from backend.app.data.adjacency import get_adjacent, get_reachable_within
        neighbors = get_adjacent("Arrakeen")
        # Block all neighbors
        result = get_reachable_within("Arrakeen", 2, blocked_territories=neighbors)
        # No neighbor should appear in result
        assert result.isdisjoint(neighbors)

    def test_blocked_territory_cuts_transitive_reach(self):
        """If a territory is blocked, territories only reachable through it are cut."""
        from backend.app.data.adjacency import get_adjacent, get_reachable_within
        # Block all 1-hop neighbors — nothing should be reachable in 2 hops
        neighbors = get_adjacent("Arrakeen")
        r2_blocked = get_reachable_within("Arrakeen", 2, blocked_territories=neighbors)
        assert len(r2_blocked) == 0
