"""
Spice Blow Phase service for the Dune board game.

Rulebook reference: p.8 — "Spice Blow and Nexus"

Each turn, a card is drawn from the Spice Deck:
  • Territory card  → place spice on that territory (additive).
  • Shai-Hulud card → sandworm attack on the last-revealed territory:
      - All spice and forces in that territory are destroyed.
      - Continue drawing until a territory card appears; place spice there.
      - A Nexus event occurs (alliance opportunity — sets nexus_triggered).
  • First turn exception: Shai-Hulud cards are set aside and reshuffled
    back into the deck after the Spice Blow phase.

Entry point:
    resolve_spice_blow(game_state) -> GameState
"""

from __future__ import annotations

import random

from ...models.card import SpiceCard, SpiceCardType
from ...models.game_state import GamePhase, GameState
from ...models.player import Player


def resolve_spice_blow(game_state: GameState) -> GameState:
    """
    Execute the Spice Blow Phase and return the updated GameState.

    Returns
    -------
    GameState with:
      - Spice placed on territory (if territory card drawn and not in storm)
      - Shai-Hulud effects applied (if worm drawn, and not first turn)
      - Spice bank reduced by amount placed
      - Spice deck / discard updated
      - current_phase advanced to CHOAM_CHARITY
    """
    spice_deck = list(game_state.spice_deck)
    spice_discard = list(game_state.spice_discard)
    territories = {n: t.model_copy() for n, t in game_state.territories.items()}
    players = list(game_state.players)
    spice_bank = game_state.spice_bank
    storm_sector = game_state.storm_sector
    is_first_turn = game_state.current_turn == 1
    shai_hulud_drawn = False  # Track whether a Nexus event should trigger

    # Cards set aside during first-turn Shai-Hulud suppression
    set_aside: list[SpiceCard] = []

    # Ensure we have cards to draw
    if not spice_deck:
        spice_deck = _reshuffle_discard(spice_discard)
        spice_discard = []

    if not spice_deck:
        # No cards at all — skip phase
        return game_state.model_copy(update={
            "current_phase": GamePhase.CHOAM_CHARITY,
        })

    # Draw the top card
    card = spice_deck.pop(0)

    if card.card_type == SpiceCardType.TERRITORY:
        # Place spice on the territory (if not blocked by storm)
        territories, spice_bank = _place_spice(
            territories, card, storm_sector, spice_bank
        )
        spice_discard.append(card)

    elif card.card_type == SpiceCardType.SHAI_HULUD:
        if is_first_turn:
            # First turn: set aside Shai-Hulud, draw again until territory
            set_aside.append(card)
            territories, spice_deck, spice_discard, set_aside, spice_bank = (
                _draw_until_territory(
                    territories, spice_deck, spice_discard, set_aside,
                    is_first_turn=True,
                    storm_sector=storm_sector,
                    spice_bank=spice_bank,
                )
            )
        else:
            # Sandworm attack — and a Nexus event occurs!
            shai_hulud_drawn = True
            spice_discard.append(card)
            players, territories, spice_bank = _shai_hulud_attack(
                players, territories, spice_discard, spice_bank
            )
            # Draw until a territory card appears, placing spice there
            territories, spice_deck, spice_discard, _, spice_bank = (
                _draw_until_territory(
                    territories, spice_deck, spice_discard, [],
                    is_first_turn=False,
                    storm_sector=storm_sector,
                    spice_bank=spice_bank,
                )
            )

    # First turn: reshuffle set-aside Shai-Hulud cards back into the deck
    if set_aside:
        spice_deck.extend(set_aside)
        random.shuffle(spice_deck)

    return game_state.model_copy(update={
        "spice_deck": spice_deck,
        "spice_discard": spice_discard,
        "territories": territories,
        "players": players,
        "spice_bank": spice_bank,
        "current_phase": GamePhase.CHOAM_CHARITY,
        "nexus_triggered": shai_hulud_drawn,
    })


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _place_spice(
    territories: dict[str, object],
    card: SpiceCard,
    storm_sector: int,
    spice_bank: int,
) -> tuple[dict[str, object], int]:
    """Add the card's spice amount to the named territory (additive).

    Spice is NOT placed if the territory is in the current storm sector.
    The amount placed is capped by the available spice in the bank.
    Returns (territories, updated_spice_bank).
    """
    name = card.territory_name
    if name and name in territories:
        t = territories[name]
        # Storm check: if the storm is sitting on any of this territory's
        # sectors, the spice blow is lost — no spice is placed.
        if storm_sector in t.sectors:
            return territories, spice_bank

        amount = card.spice_amount or 0
        # Cap at available spice in the bank
        amount = min(amount, spice_bank)
        if amount > 0:
            territories[name] = t.model_copy(update={
                "current_spice": t.current_spice + amount,
            })
            spice_bank -= amount
    return territories, spice_bank


def _reshuffle_discard(discard: list[SpiceCard]) -> list[SpiceCard]:
    """Shuffle the discard pile into a fresh deck."""
    deck = list(discard)
    random.shuffle(deck)
    return deck


def _draw_until_territory(
    territories: dict[str, object],
    spice_deck: list[SpiceCard],
    spice_discard: list[SpiceCard],
    set_aside: list[SpiceCard],
    is_first_turn: bool,
    storm_sector: int,
    spice_bank: int,
) -> tuple[dict[str, object], list[SpiceCard], list[SpiceCard], list[SpiceCard], int]:
    """
    Keep drawing from the spice deck until a territory card is found.
    Shai-Hulud cards drawn along the way are either set aside (first turn)
    or discarded (later turns). The territory card is placed and discarded.

    Returns (territories, spice_deck, spice_discard, set_aside, spice_bank).
    """
    while spice_deck:
        card = spice_deck.pop(0)

        if card.card_type == SpiceCardType.TERRITORY:
            territories, spice_bank = _place_spice(
                territories, card, storm_sector, spice_bank
            )
            spice_discard.append(card)
            break

        # Another Shai-Hulud
        if is_first_turn:
            set_aside.append(card)
        else:
            spice_discard.append(card)

    return territories, spice_deck, spice_discard, set_aside, spice_bank


def apply_spice_collection_effects(game_state: GameState) -> GameState:
    """
    Apply Spice Collection effects without advancing the phase.

    Each player collects spice from territories where they have forces.
    Each force in a territory with spice collects 2 spice (or 3 for special forces),
    up to the amount available on that territory.

    Per the rules: each force token collects 2 spice. Players collect from
    territories where only they have forces (no sharing with opponents).

    The phase stays at SPICE_COLLECTION so players can see the results
    before advancing.
    """
    territories = {n: t.model_copy() for n, t in game_state.territories.items()}
    updated_players = list(game_state.players)

    # Build a map of territory -> [(player_index, force_count)]
    territory_collectors: dict[str, list[tuple[int, int]]] = {}
    for i, player in enumerate(updated_players):
        if player.is_eliminated:
            continue
        for fg in player.forces_on_board:
            total = (fg.regular_count or 0) + (fg.special_count or 0)
            if total > 0:
                if fg.territory_name not in territory_collectors:
                    territory_collectors[fg.territory_name] = []
                # Merge same player in same territory
                existing = None
                for entry in territory_collectors[fg.territory_name]:
                    if entry[0] == i:
                        existing = entry
                        break
                if existing:
                    idx = territory_collectors[fg.territory_name].index(existing)
                    territory_collectors[fg.territory_name][idx] = (i, existing[1] + total)
                else:
                    territory_collectors[fg.territory_name].append((i, total))

    # Collect spice
    spice_gains = [0] * len(updated_players)

    for terr_name, collectors in territory_collectors.items():
        t = territories.get(terr_name)
        if not t or t.current_spice <= 0:
            continue

        available = t.current_spice
        # Each force collects 2 spice, up to what's available
        for player_idx, force_count in collectors:
            can_collect = min(force_count * 2, available)
            if can_collect > 0:
                spice_gains[player_idx] += can_collect
                available -= can_collect
            if available <= 0:
                break

        territories[terr_name] = t.model_copy(update={
            "current_spice": available,
        })

    # Apply spice gains to players
    final_players = []
    for i, player in enumerate(updated_players):
        if spice_gains[i] > 0:
            final_players.append(player.model_copy(update={
                "spice": player.spice + spice_gains[i],
            }))
        else:
            final_players.append(player)

    return game_state.model_copy(update={
        "players": final_players,
        "territories": territories,
    })


def resolve_spice_collection(game_state: GameState) -> GameState:
    """
    Legacy wrapper: apply effects and advance phase in one step.
    Used by tests via run_automated_phases().
    """
    from .phases import next_phase

    resolved = apply_spice_collection_effects(game_state)
    return resolved.model_copy(update={
        "current_phase": next_phase(game_state.current_phase),
    })


def _shai_hulud_attack(
    players: list[Player],
    territories: dict[str, object],
    spice_discard: list[SpiceCard],
    spice_bank: int,
) -> tuple[list[Player], dict[str, object], int]:
    """
    Sandworm attack: destroy all spice and forces in the territory that
    was most recently revealed (i.e. the most recent *territory* card in
    the discard pile, ignoring Shai-Hulud cards on top).

    Forces destroyed by the worm go to the Tleilaxu Tanks.
    Destroyed spice returns to the spice bank.

    Returns (updated_players, territories, spice_bank).
    """
    # Find the last territory card in the discard pile
    target_name: str | None = None
    for card in reversed(spice_discard):
        if card.card_type == SpiceCardType.TERRITORY and card.territory_name:
            target_name = card.territory_name
            break

    if target_name is None:
        # No previous territory card — nothing to attack
        return players, territories, spice_bank

    # Destroy spice on the territory — return it to the bank
    if target_name in territories:
        t = territories[target_name]
        spice_bank += t.current_spice
        territories[target_name] = t.model_copy(update={"current_spice": 0})

    # Destroy forces in the territory (all players, all sectors)
    # Fremen are immune to Shai-Hulud — their forces survive.
    from .handlers.registry import get_handler

    updated_players: list[Player] = []
    for player in players:
        handler = get_handler(player.faction)
        if handler.is_immune_to_shai_hulud():
            # This faction (Fremen) is immune to sandworm attacks
            updated_players.append(player)
            continue

        surviving = []
        regular_killed = 0
        special_killed = 0

        for fg in player.forces_on_board:
            if fg.territory_name == target_name:
                regular_killed += fg.regular_count
                special_killed += fg.special_count
            else:
                surviving.append(fg)

        if regular_killed == 0 and special_killed == 0:
            updated_players.append(player)
        else:
            updated_players.append(player.model_copy(update={
                "forces_on_board": surviving,
                "forces_in_tanks": player.forces_in_tanks + regular_killed,
                "special_forces_in_tanks": (
                    player.special_forces_in_tanks + special_killed
                ),
            }))

    return updated_players, territories, spice_bank
