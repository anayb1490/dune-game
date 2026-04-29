"""
Bidding Phase service for the Dune board game.

The Bidding Phase is an auction: Treachery Cards from the deck are sold
one at a time to the highest bidder. Players spend spice to buy weapons,
defenses, and special cards that they'll use in battle.

Rulebook clarifications implemented here:
  - ROTATING START: Each card's auction opens with the next eligible player
    to the right of whoever opened the previous card's bidding. (p.8)
  - ALL-PASS RULE: If all eligible players pass on a card with no bids
    placed, ALL remaining unsold cards are returned to the top of the
    Treachery Deck and the Bidding Phase ends immediately. (p.8)

Entry points:
    init_bidding(game_state) -> GameState
    place_bid(game_state, player_id, amount) -> GameState
    pass_bid(game_state, player_id) -> GameState
"""

from __future__ import annotations

from ...models.card import TreacheryCard
from ...models.faction import FactionName
from ...models.game_state import BiddingState, GamePhase, GameState
from ...models.player import Player
from .handlers.registry import get_handler
from .phases import next_phase


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_bidding(game_state: GameState) -> GameState:
    """
    Set up the Bidding Phase: draw cards from the treachery deck and
    prepare the first auction.

    How many cards? One per player who has room in their hand.
    (If a player already holds the maximum number of cards, they can't
    bid and don't get a card dealt for them.)
    """
    eligible_players = _get_eligible_players(game_state)

    if not eligible_players or not game_state.treachery_deck:
        # No one can bid or no cards left — skip bidding entirely.
        # Reset current_player_index so the Revival phase starts at player 0.
        return game_state.model_copy(update={
            "current_phase": next_phase(GamePhase.BIDDING),
            "bidding_state": None,
            "current_player_index": 0,
        })

    # Draw N cards (one per eligible player, but never more than the deck has)
    num_cards = min(len(eligible_players), len(game_state.treachery_deck))
    cards_for_auction = game_state.treachery_deck[:num_cards]
    remaining_deck = game_state.treachery_deck[num_cards:]

    # Find the first eligible bidder (first player in turn order)
    first_bidder = _get_first_eligible_bidder(game_state)

    # Atreides prescience: reveal the first card to Atreides
    prescience_card_id = _get_prescience_card_id(game_state, cards_for_auction[0])

    bidding_state = BiddingState(
        cards_up_for_bid=cards_for_auction,
        current_card_index=0,
        current_high_bidder=None,
        current_high_bid=0,
        current_bidder=first_bidder,
        opening_bidder=first_bidder,
        factions_passed=[],
        atreides_prescience_card_id=prescience_card_id,
    )

    return game_state.model_copy(update={
        "current_phase": GamePhase.BIDDING,
        "bidding_state": bidding_state,
        "treachery_deck": remaining_deck,
    })


def place_bid(game_state: GameState, player_id: str, amount: int) -> GameState:
    """
    A player places a bid on the current card.

    Validates:
      - It's this player's turn to bid
      - The bid is higher than the current high bid
      - The player has enough spice
      - The player has room in their hand

    After placing, advances to the next bidder. If all others have passed,
    resolves the auction immediately.
    """
    bs = game_state.bidding_state
    if bs is None:
        raise ValueError("No active bidding phase")

    player = _get_player(game_state, player_id)

    # Validation
    if player.faction != bs.current_bidder:
        raise ValueError(
            f"Not {player.faction.value}'s turn to bid "
            f"(waiting for {bs.current_bidder.value})"
        )

    if amount <= bs.current_high_bid:
        raise ValueError(
            f"Bid of {amount} must be higher than current high bid of {bs.current_high_bid}"
        )

    # Allied spice may be used: bidder can spend up to own + ally's spice
    ally_player = next(
        (p for p in game_state.players if p.faction == player.ally),
        None,
    ) if player.ally else None
    ally_spice = ally_player.spice if ally_player else 0
    if amount > player.spice + ally_spice:
        raise ValueError(
            f"{player.faction.value} has {player.spice} spice "
            f"(ally has {ally_spice}) but tried to bid {amount}"
        )

    handler = get_handler(player.faction)
    max_cards = handler.get_max_treachery_cards(player, game_state)
    if len(player.treachery_hand) >= max_cards:
        raise ValueError(f"{player.faction.value}'s hand is full ({max_cards} cards)")

    # Update bidding state with the new high bid
    updated_bs = bs.model_copy(update={
        "current_high_bidder": player.faction,
        "current_high_bid": amount,
    })

    updated_state = game_state.model_copy(update={"bidding_state": updated_bs})

    # Advance to next bidder — if everyone else has passed, resolve
    return _advance_to_next_bidder(updated_state)


def pass_bid(game_state: GameState, player_id: str) -> GameState:
    """
    A player passes (declines to bid) on the current card.

    If only one bidder remains after this pass and they hold the high bid,
    they win the auction.

    If ALL players pass with no bids placed, ALL remaining unsold cards
    (including the current one) are returned to the top of the Treachery
    Deck and the Bidding Phase ends immediately.
    """
    bs = game_state.bidding_state
    if bs is None:
        raise ValueError("No active bidding phase")

    player = _get_player(game_state, player_id)

    if player.faction != bs.current_bidder:
        raise ValueError(
            f"Not {player.faction.value}'s turn to bid "
            f"(waiting for {bs.current_bidder.value})"
        )

    # Add this faction to the passed list
    new_passed = list(bs.factions_passed) + [player.faction]
    updated_bs = bs.model_copy(update={"factions_passed": new_passed})
    updated_state = game_state.model_copy(update={"bidding_state": updated_bs})

    # Check if the auction should resolve
    eligible = _get_eligible_players(updated_state)
    non_passed = [p for p in eligible if p.faction not in new_passed]

    if len(non_passed) == 1 and updated_bs.current_high_bidder is not None:
        # One player left and there's a bid — they win
        return _resolve_current_auction(updated_state)

    if len(non_passed) == 0:
        # Everyone passed — either resolve the bid or end bidding
        if updated_bs.current_high_bidder is not None:
            return _resolve_current_auction(updated_state)
        else:
            # ALL-PASS RULE: No one bid at all — return remaining cards to deck
            return _return_cards_to_deck(updated_state)

    # More bidders remain — advance to the next one
    return _advance_to_next_bidder(updated_state)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_current_auction(game_state: GameState) -> GameState:
    """
    Award the current card to the high bidder, transfer spice, and
    either start the next auction or end the Bidding phase.
    """
    bs = game_state.bidding_state
    card = bs.cards_up_for_bid[bs.current_card_index]
    winner_faction = bs.current_high_bidder
    bid_amount = bs.current_high_bid

    # Find winner and update their hand + spice
    # If the winner can't fully cover the bid from their own spice, the
    # remainder is paid by their ally (alliance spice-sharing rule).
    winner_player = next(p for p in game_state.players if p.faction == winner_faction)
    own_payment = min(winner_player.spice, bid_amount)
    ally_payment = bid_amount - own_payment  # 0 when winner covers alone
    ally_faction = winner_player.ally  # None when no ally

    updated_players = []
    emperor_faction = None

    for p in game_state.players:
        if p.faction == winner_faction:
            # Winner: add card to hand, deduct own portion
            new_hand = list(p.treachery_hand) + [card]

            # Check for Harkonnen bonus card
            handler = get_handler(p.faction)
            bonus_cards = handler.on_card_purchased(card, p, game_state)
            new_hand.extend(bonus_cards)

            updated_players.append(p.model_copy(update={
                "treachery_hand": new_hand,
                "spice": p.spice - own_payment,
            }))
        elif ally_faction and p.faction == ally_faction and ally_payment > 0:
            # Ally covers the shortfall
            updated_players.append(p.model_copy(update={
                "spice": p.spice - ally_payment,
            }))
        else:
            updated_players.append(p)

        if p.faction == FactionName.EMPEROR:
            emperor_faction = p.faction

    # Transfer spice: to Emperor if playing, otherwise to bank
    spice_bank = game_state.spice_bank
    if emperor_faction is not None and winner_faction != FactionName.EMPEROR:
        # Emperor receives the bid spice
        updated_players = [
            p.model_copy(update={"spice": p.spice + bid_amount})
            if p.faction == FactionName.EMPEROR else p
            for p in updated_players
        ]
    else:
        # Spice goes to the bank
        spice_bank += bid_amount

    # Remove Harkonnen bonus cards from the deck
    remaining_deck = list(game_state.treachery_deck)
    handler = get_handler(winner_faction)
    bonus_cards = handler.on_card_purchased(card, winner_player, game_state)
    if bonus_cards:
        # Remove drawn cards from the deck
        bonus_ids = {c.id for c in bonus_cards}
        remaining_deck = [c for c in remaining_deck if c.id not in bonus_ids]

    updated_state = game_state.model_copy(update={
        "players": updated_players,
        "spice_bank": spice_bank,
        "treachery_deck": remaining_deck,
    })

    return _advance_to_next_card(updated_state)


def _return_cards_to_deck(game_state: GameState) -> GameState:
    """
    ALL-PASS RULE: Everyone passed on the current card with no bids.
    Return all remaining unsold cards (current card + any not yet auctioned)
    to the TOP of the Treachery Deck, then end the Bidding Phase.
    """
    bs = game_state.bidding_state
    # All cards from current_card_index onwards are unsold
    unsold_cards = list(bs.cards_up_for_bid[bs.current_card_index:])
    restored_deck = unsold_cards + list(game_state.treachery_deck)

    return game_state.model_copy(update={
        "treachery_deck": restored_deck,
        "bidding_state": None,
        "current_phase": next_phase(GamePhase.BIDDING),
        "current_player_index": 0,
    })


def _advance_to_next_card(game_state: GameState) -> GameState:
    """
    Move to the next card in the auction, or end bidding if all cards
    have been auctioned.

    The next card's opening bidder is the next eligible player to the
    right of whoever opened the current card's bidding (rotating start rule).
    """
    bs = game_state.bidding_state
    next_index = bs.current_card_index + 1

    if next_index >= len(bs.cards_up_for_bid):
        # All cards auctioned — end the Bidding phase.
        return game_state.model_copy(update={
            "bidding_state": None,
            "current_phase": next_phase(GamePhase.BIDDING),
            "current_player_index": 0,
        })

    # ROTATING START: next opener is the next eligible player to the right
    # of whoever opened the current card's auction.
    next_opener = _get_next_card_opener(game_state, bs.opening_bidder)
    next_card = bs.cards_up_for_bid[next_index]
    prescience_card_id = _get_prescience_card_id(game_state, next_card)

    new_bs = BiddingState(
        cards_up_for_bid=bs.cards_up_for_bid,
        current_card_index=next_index,
        current_high_bidder=None,
        current_high_bid=0,
        current_bidder=next_opener,
        opening_bidder=next_opener,
        factions_passed=[],
        atreides_prescience_card_id=prescience_card_id,
    )

    return game_state.model_copy(update={"bidding_state": new_bs})


def _advance_to_next_bidder(game_state: GameState) -> GameState:
    """
    Find the next eligible player in turn order who hasn't passed
    and whose hand isn't full.
    """
    bs = game_state.bidding_state
    eligible = _get_eligible_players(game_state)
    eligible_factions = [
        p.faction for p in eligible
        if p.faction not in bs.factions_passed
    ]

    if not eligible_factions:
        # No one left — resolve or return to deck
        if bs.current_high_bidder is not None:
            return _resolve_current_auction(game_state)
        return _return_cards_to_deck(game_state)

    # Find the current bidder's position and advance to the next
    current = bs.current_bidder
    all_factions = [p.faction for p in game_state.players]

    # Start from the position after the current bidder
    try:
        start_idx = all_factions.index(current) + 1
    except ValueError:
        start_idx = 0

    # Walk around the table until we find an eligible, non-passed faction
    for i in range(len(all_factions)):
        idx = (start_idx + i) % len(all_factions)
        faction = all_factions[idx]
        if faction in eligible_factions:
            updated_bs = bs.model_copy(update={"current_bidder": faction})
            return game_state.model_copy(update={"bidding_state": updated_bs})

    # Shouldn't reach here, but safety fallback
    if bs.current_high_bidder is not None:
        return _resolve_current_auction(game_state)
    return _return_cards_to_deck(game_state)


def _get_next_card_opener(
    game_state: GameState,
    prev_opener: FactionName | None,
) -> FactionName | None:
    """
    ROTATING START RULE: The opening bidder for the next card is the next
    eligible player seated to the right of whoever opened the previous card.

    If prev_opener is None or no longer eligible, fall back to the standard
    first-eligible-from-first-player logic.
    """
    eligible = _get_eligible_players(game_state)
    if not eligible:
        return None

    eligible_factions = {p.faction for p in eligible}
    all_factions = [p.faction for p in game_state.players]

    if prev_opener is None or prev_opener not in all_factions:
        # Fallback: first eligible player from first_player_index
        return _get_first_eligible_bidder(game_state)

    # Start from the position immediately to the right of prev_opener
    try:
        start_idx = all_factions.index(prev_opener) + 1
    except ValueError:
        start_idx = 0

    for i in range(len(all_factions)):
        idx = (start_idx + i) % len(all_factions)
        if all_factions[idx] in eligible_factions:
            return all_factions[idx]

    return eligible[0].faction


def _get_eligible_players(game_state: GameState) -> list[Player]:
    """
    Players who can participate in bidding: hand not full, not eliminated.
    """
    eligible = []
    for player in game_state.players:
        if player.is_eliminated:
            continue
        handler = get_handler(player.faction)
        max_cards = handler.get_max_treachery_cards(player, game_state)
        if len(player.treachery_hand) < max_cards:
            eligible.append(player)
    return eligible


def _get_first_eligible_bidder(game_state: GameState) -> FactionName | None:
    """
    The first eligible player in seating order, starting from first_player_index.
    """
    eligible = _get_eligible_players(game_state)
    if not eligible:
        return None

    eligible_factions = {p.faction for p in eligible}
    num_players = len(game_state.players)

    for i in range(num_players):
        idx = (game_state.first_player_index + i) % num_players
        faction = game_state.players[idx].faction
        if faction in eligible_factions:
            return faction

    return eligible[0].faction


def _get_prescience_card_id(game_state: GameState, card: TreacheryCard) -> str | None:
    """
    If Atreides is in the game, return the card's ID so the frontend can
    reveal it to the Atreides player. Returns None if Atreides is not playing
    or is eliminated.
    """
    atreides_player = next(
        (p for p in game_state.players
         if p.faction == FactionName.ATREIDES and not p.is_eliminated),
        None,
    )
    if atreides_player is None:
        return None

    handler = get_handler(FactionName.ATREIDES)
    revealed = handler.on_card_revealed_for_bid(card, atreides_player, game_state)
    if revealed is not None:
        return card.id
    return None


def _get_player(game_state: GameState, player_id: str) -> Player:
    """Look up a player by ID, raise ValueError if not found."""
    for player in game_state.players:
        if player.id == player_id:
            return player
    raise ValueError(f"Player not found: {player_id}")
