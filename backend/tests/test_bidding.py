"""
Tests for backend.app.services.game.bidding — Bidding Phase service.

Run with:
    cd DuneGame
    python -m pytest backend/tests/test_bidding.py -v
"""

import pytest

from backend.app.models.faction import FactionName
from backend.app.models.game_state import GamePhase, GameState
from backend.app.services.game.bidding import (
    init_bidding,
    pass_bid,
    place_bid,
)


class TestInitBidding:
    """init_bidding sets up the auction correctly."""

    def test_creates_bidding_state(self, game_at_bidding: GameState):
        """After init, bidding_state should exist."""
        assert game_at_bidding.bidding_state is not None

    def test_phase_is_bidding(self, game_at_bidding: GameState):
        assert game_at_bidding.current_phase == GamePhase.BIDDING

    def test_deals_correct_number_of_cards(self, game_at_bidding: GameState):
        """2-player game → 2 cards up for bid."""
        bs = game_at_bidding.bidding_state
        assert len(bs.cards_up_for_bid) == 2

    def test_cards_removed_from_deck(self, game_at_bidding: GameState):
        """Cards dealt for auction should no longer be in the treachery deck."""
        bs = game_at_bidding.bidding_state
        auction_ids = {c.id for c in bs.cards_up_for_bid}
        deck_ids = {c.id for c in game_at_bidding.treachery_deck}
        assert auction_ids.isdisjoint(deck_ids)

    def test_first_bidder_is_set(self, game_at_bidding: GameState):
        """current_bidder should be set to a faction."""
        bs = game_at_bidding.bidding_state
        assert bs.current_bidder is not None

    def test_starts_at_card_0(self, game_at_bidding: GameState):
        bs = game_at_bidding.bidding_state
        assert bs.current_card_index == 0
        assert bs.current_high_bid == 0
        assert bs.current_high_bidder is None
        assert bs.factions_passed == []


class TestPlaceBid:
    """Placing a bid updates the auction state."""

    def test_bid_updates_high_bidder(self, game_at_bidding: GameState):
        bs = game_at_bidding.bidding_state
        bidder = next(
            p for p in game_at_bidding.players
            if p.faction == bs.current_bidder
        )
        result = place_bid(game_at_bidding, bidder.id, 1)
        assert result.bidding_state.current_high_bidder == bidder.faction
        assert result.bidding_state.current_high_bid == 1

    def test_bid_advances_to_next_bidder(self, game_at_bidding: GameState):
        bs = game_at_bidding.bidding_state
        first_bidder = bs.current_bidder
        bidder = next(
            p for p in game_at_bidding.players
            if p.faction == first_bidder
        )
        result = place_bid(game_at_bidding, bidder.id, 1)
        # Next bidder should be different
        assert result.bidding_state.current_bidder != first_bidder

    def test_cannot_bid_more_than_spice(self, game_at_bidding: GameState):
        bs = game_at_bidding.bidding_state
        bidder = next(
            p for p in game_at_bidding.players
            if p.faction == bs.current_bidder
        )
        with pytest.raises(ValueError, match="spice"):
            place_bid(game_at_bidding, bidder.id, bidder.spice + 1)

    def test_cannot_bid_lower_than_current(self, game_at_bidding: GameState):
        bs = game_at_bidding.bidding_state
        bidder = next(
            p for p in game_at_bidding.players
            if p.faction == bs.current_bidder
        )
        # Place first bid of 3
        state = place_bid(game_at_bidding, bidder.id, 3)
        # Other player tries to bid 2 (lower)
        next_bidder = next(
            p for p in state.players
            if p.faction == state.bidding_state.current_bidder
        )
        with pytest.raises(ValueError, match="higher"):
            place_bid(state, next_bidder.id, 2)

    def test_wrong_player_cannot_bid(self, game_at_bidding: GameState):
        """Only the current_bidder can place a bid."""
        bs = game_at_bidding.bidding_state
        wrong_player = next(
            p for p in game_at_bidding.players
            if p.faction != bs.current_bidder
        )
        with pytest.raises(ValueError, match="turn"):
            place_bid(game_at_bidding, wrong_player.id, 1)


class TestPassBid:
    """Passing on a bid."""

    def test_pass_adds_to_factions_passed(self, game_at_bidding: GameState):
        bs = game_at_bidding.bidding_state
        bidder = next(
            p for p in game_at_bidding.players
            if p.faction == bs.current_bidder
        )
        result = pass_bid(game_at_bidding, bidder.id)
        assert bidder.faction in result.bidding_state.factions_passed

    def test_all_pass_no_bids_discards_card(self, game_at_bidding: GameState):
        """If everyone passes without bidding, card should be discarded."""
        # Both players pass
        bs = game_at_bidding.bidding_state
        p1 = next(p for p in game_at_bidding.players if p.faction == bs.current_bidder)
        state = pass_bid(game_at_bidding, p1.id)

        bs2 = state.bidding_state
        p2 = next(p for p in state.players if p.faction == bs2.current_bidder)
        state = pass_bid(state, p2.id)

        # Card should have moved to discard or next auction started
        if state.bidding_state is not None:
            # Moved to next card
            assert state.bidding_state.current_card_index == 1
        else:
            # If only 1 card was up, bidding ended
            assert state.current_phase != GamePhase.BIDDING


class TestAuctionResolution:
    """Winning an auction awards the card and transfers spice."""

    def test_winner_gets_card(self, game_at_bidding: GameState):
        """After one player bids and the other passes, winner gets the card."""
        bs = game_at_bidding.bidding_state
        card_up = bs.cards_up_for_bid[0]

        # Player 1 bids 1
        p1 = next(p for p in game_at_bidding.players if p.faction == bs.current_bidder)
        state = place_bid(game_at_bidding, p1.id, 1)

        # Player 2 passes → player 1 wins
        bs2 = state.bidding_state
        p2 = next(p for p in state.players if p.faction == bs2.current_bidder)
        state = pass_bid(state, p2.id)

        # Player 1 should now have the card
        winner = next(p for p in state.players if p.faction == p1.faction)
        card_ids = [c.id for c in winner.treachery_hand]
        assert card_up.id in card_ids

    def test_winner_pays_spice(self, game_at_bidding: GameState):
        bs = game_at_bidding.bidding_state
        p1 = next(p for p in game_at_bidding.players if p.faction == bs.current_bidder)
        original_spice = p1.spice

        state = place_bid(game_at_bidding, p1.id, 3)
        bs2 = state.bidding_state
        p2 = next(p for p in state.players if p.faction == bs2.current_bidder)
        state = pass_bid(state, p2.id)

        winner = next(p for p in state.players if p.faction == p1.faction)
        assert winner.spice == original_spice - 3

    def test_spice_goes_to_bank_without_emperor(self, game_at_bidding: GameState):
        """In a 2-player game (no Emperor), bid spice goes to the spice bank."""
        bank_before = game_at_bidding.spice_bank
        bs = game_at_bidding.bidding_state

        p1 = next(p for p in game_at_bidding.players if p.faction == bs.current_bidder)
        state = place_bid(game_at_bidding, p1.id, 3)

        bs2 = state.bidding_state
        p2 = next(p for p in state.players if p.faction == bs2.current_bidder)
        state = pass_bid(state, p2.id)

        assert state.spice_bank == bank_before + 3

    def test_spice_goes_to_emperor(self, game_at_bidding_6p: GameState):
        """In a 6-player game, non-Emperor bids go to the Emperor."""
        game = game_at_bidding_6p
        bs = game.bidding_state
        if bs is None:
            pytest.skip("No bidding state (empty deck)")

        # Find a non-Emperor bidder
        emperor_before = next(
            p for p in game.players if p.faction == FactionName.EMPEROR
        )

        # Ensure current bidder is not Emperor; if they are, pass and get next
        if bs.current_bidder == FactionName.EMPEROR:
            emp = next(p for p in game.players if p.faction == FactionName.EMPEROR)
            game = pass_bid(game, emp.id)
            bs = game.bidding_state

        bidder = next(p for p in game.players if p.faction == bs.current_bidder)
        state = place_bid(game, bidder.id, 2)

        # Have everyone else pass so bidder wins
        for _ in range(10):  # safety cap
            bs2 = state.bidding_state
            if bs2 is None:
                break
            if bs2.current_card_index != bs.current_card_index:
                break  # auction resolved, moved to next card
            curr = next(p for p in state.players if p.faction == bs2.current_bidder)
            state = pass_bid(state, curr.id)

        emperor_after = next(
            p for p in state.players if p.faction == FactionName.EMPEROR
        )
        assert emperor_after.spice == emperor_before.spice + 2


class TestBiddingCompletion:
    """After all cards are auctioned, bidding ends."""

    def test_bidding_ends_after_all_cards(self, game_at_bidding: GameState):
        """Resolving all auctions should advance past Bidding."""
        state = game_at_bidding

        # Resolve all auctions by having everyone pass on every card
        for _ in range(20):  # safety cap
            bs = state.bidding_state
            if bs is None:
                break
            bidder = next(
                p for p in state.players if p.faction == bs.current_bidder
            )
            state = pass_bid(state, bidder.id)

        assert state.bidding_state is None
        assert state.current_phase == GamePhase.REVIVAL

    def test_bidding_state_cleaned_up(self, game_at_bidding: GameState):
        """After bidding ends, bidding_state should be None."""
        state = game_at_bidding
        for _ in range(20):
            bs = state.bidding_state
            if bs is None:
                break
            bidder = next(
                p for p in state.players if p.faction == bs.current_bidder
            )
            state = pass_bid(state, bidder.id)

        assert state.bidding_state is None
