"""
Spice Blow Phase service for the Dune board game.

Rulebook reference:
  p.8  — "Spice Blow and Nexus" (Basic)
  p.9  — "Double Spice Blow" (Advanced Phase 2)
  p.9  — "Increased Spice Flow" (Advanced Spice Collection)

BASIC SPICE BLOW
  • Territory card  → place spice on that territory (additive).
  • Shai-Hulud card → sandworm attack on last-revealed territory; forces (except
                      Fremen) and all spice destroyed. Draw again until territory.
                      A Nexus occurs. Fremen may ride the worm afterwards.
  • First-turn exception: Shai-Hulud cards set aside and reshuffled.

ADVANCED DOUBLE SPICE BLOW
  Draw TWO cards, using separate A and B discard piles.
  First draw uses pile A; second draw uses pile B.
  Each draw follows the same Shai-Hulud / Territory rules independently.

ADVANCED INCREASED SPICE FLOW
  During Spice Collection each occupant of Carthag or Arrakeen collects +2 spice;
  the occupant of Tuek's Sietch collects +1 spice — regardless of territory spice.

ADVISOR EXCLUSION
  BG Advisors (is_advisor=True) never collect spice (Basic or Advanced).
"""

from __future__ import annotations

import random

from ...models.card import SpiceCard, SpiceCardType
from ...models.game_state import GamePhase, GameState
from ...models.player import Player


# ---------------------------------------------------------------------------
# Increased Spice Flow constants (Advanced Spice Collection)
# ---------------------------------------------------------------------------

_INCREASED_FLOW: dict[str, int] = {
    "Carthag": 2,
    "Arrakeen": 2,
    "Tuek's Sietch": 1,
}


# ---------------------------------------------------------------------------
# Public entry point — Spice Blow Phase
# ---------------------------------------------------------------------------

def resolve_spice_blow(game_state: GameState) -> GameState:
    """
    Execute the Spice Blow Phase and return the updated GameState.

    Advanced mode draws two cards (Double Spice Blow) with separate A/B
    discard piles.  Basic mode draws one card using the standard discard.
    In both modes, the phase advances to CHOAM_CHARITY when done.
    """
    if game_state.mode.value == "advanced":
        return _resolve_double_spice_blow(game_state)
    return _resolve_single_spice_blow(game_state)


# ---------------------------------------------------------------------------
# Spice Collection helpers
# ---------------------------------------------------------------------------

def apply_spice_collection_effects(game_state: GameState) -> GameState:
    """
    Apply Spice Collection effects without advancing the phase.

    Each force (non-advisor) in a territory with spice collects 2 spice,
    up to the spice available on that territory.  Special forces also count
    as 1 force for collection purposes.

    Advanced Increased Spice Flow: after standard collection, occupants of
    Carthag (+2), Arrakeen (+2) and Tuek's Sietch (+1) each receive a bonus
    directly from the Spice Bank — even when those territories have no spice.
    """
    territories = {n: t.model_copy() for n, t in game_state.territories.items()}
    updated_players = list(game_state.players)
    spice_bank = game_state.spice_bank

    # Build territory -> [(player_index, force_count)] — exclude advisors
    territory_collectors: dict[str, list[tuple[int, int]]] = {}
    for i, player in enumerate(updated_players):
        if player.is_eliminated:
            continue
        for fg in player.forces_on_board:
            if fg.is_advisor:
                continue  # BG Advisors never collect spice
            total = (fg.regular_count or 0) + (fg.special_count or 0)
            if total > 0:
                if fg.territory_name not in territory_collectors:
                    territory_collectors[fg.territory_name] = []
                existing = next(
                    (e for e in territory_collectors[fg.territory_name] if e[0] == i),
                    None,
                )
                if existing:
                    idx = territory_collectors[fg.territory_name].index(existing)
                    territory_collectors[fg.territory_name][idx] = (i, existing[1] + total)
                else:
                    territory_collectors[fg.territory_name].append((i, total))

    # Standard spice collection (2 spice per force, up to territory supply)
    spice_gains = [0] * len(updated_players)
    for terr_name, collectors in territory_collectors.items():
        t = territories.get(terr_name)
        if not t or t.current_spice <= 0:
            continue
        available = t.current_spice
        for player_idx, force_count in collectors:
            can_collect = min(force_count * 2, available)
            if can_collect > 0:
                spice_gains[player_idx] += can_collect
                available -= can_collect
            if available <= 0:
                break
        territories[terr_name] = t.model_copy(update={"current_spice": available})

    # Advanced: Increased Spice Flow bonuses (paid from Spice Bank)
    if game_state.mode.value == "advanced":
        for i, player in enumerate(updated_players):
            if player.is_eliminated:
                continue
            for terr_name, bonus in _INCREASED_FLOW.items():
                has_fighters = any(
                    fg.territory_name == terr_name
                    and not fg.is_advisor
                    and (fg.regular_count + fg.special_count) > 0
                    for fg in player.forces_on_board
                )
                if has_fighters:
                    actual = min(bonus, spice_bank)
                    spice_gains[i] += actual
                    spice_bank -= actual

    # Apply gains
    final_players = [
        p.model_copy(update={"spice": p.spice + spice_gains[i]})
        if spice_gains[i] > 0 else p
        for i, p in enumerate(updated_players)
    ]

    return game_state.model_copy(update={
        "players": final_players,
        "territories": territories,
        "spice_bank": spice_bank,
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


# ---------------------------------------------------------------------------
# Single blow (Basic mode)
# ---------------------------------------------------------------------------

def _resolve_single_spice_blow(game_state: GameState) -> GameState:
    spice_deck = list(game_state.spice_deck)
    spice_discard = list(game_state.spice_discard)
    territories = {n: t.model_copy() for n, t in game_state.territories.items()}
    players = list(game_state.players)
    spice_bank = game_state.spice_bank
    storm_sector = game_state.storm_sector
    is_first_turn = game_state.current_turn == 1
    shai_hulud_drawn = False
    set_aside: list[SpiceCard] = []
    sandworm_territory: str | None = None

    if not spice_deck:
        spice_deck = _reshuffle_discard(spice_discard)
        spice_discard = []
    if not spice_deck:
        return game_state.model_copy(update={"current_phase": GamePhase.CHOAM_CHARITY})

    card = spice_deck.pop(0)

    if card.card_type == SpiceCardType.TERRITORY:
        territories, spice_bank = _place_spice(territories, card, storm_sector, spice_bank)
        spice_discard.append(card)

    elif card.card_type == SpiceCardType.SHAI_HULUD:
        if is_first_turn:
            set_aside.append(card)
            territories, spice_deck, spice_discard, set_aside, spice_bank = _draw_until_territory(
                territories, spice_deck, spice_discard, set_aside,
                is_first_turn=True, storm_sector=storm_sector, spice_bank=spice_bank,
            )
        else:
            shai_hulud_drawn = True
            spice_discard.append(card)
            sandworm_territory = _last_territory_in_discard(spice_discard)
            players, territories, spice_bank = _shai_hulud_attack(
                players, territories, spice_discard, spice_bank
            )
            territories, spice_deck, spice_discard, _, spice_bank = _draw_until_territory(
                territories, spice_deck, spice_discard, [],
                is_first_turn=False, storm_sector=storm_sector, spice_bank=spice_bank,
            )

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
        "fremen_sandworm_ride_territory": sandworm_territory,
    })


# ---------------------------------------------------------------------------
# Double blow (Advanced mode)
# ---------------------------------------------------------------------------

def _resolve_double_spice_blow(game_state: GameState) -> GameState:
    """
    Advanced Double Spice Blow: draw two cards using separate A and B
    discard piles.  Shai-Hulud on each draw attacks the last territory
    in that draw's own discard pile.

    A Nexus is triggered if either draw produces a Shai-Hulud (on turn > 1).
    Sandworm ride is tracked from whichever draw last triggered a worm.
    """
    spice_deck = list(game_state.spice_deck)
    discard_a = list(game_state.spice_discard_a)
    discard_b = list(game_state.spice_discard_b)
    territories = {n: t.model_copy() for n, t in game_state.territories.items()}
    players = list(game_state.players)
    spice_bank = game_state.spice_bank
    storm_sector = game_state.storm_sector
    is_first_turn = game_state.current_turn == 1
    nexus = False
    sandworm_territory: str | None = None

    # Reshuffle entire combined discard into deck if exhausted
    if not spice_deck:
        combined = discard_a + discard_b + list(game_state.spice_discard)
        spice_deck = _reshuffle_discard(combined)
        discard_a = []
        discard_b = []
    if not spice_deck:
        return game_state.model_copy(update={"current_phase": GamePhase.CHOAM_CHARITY})

    # --- First draw (pile A) ---
    spice_deck, discard_a, territories, players, spice_bank, worm_a, worm_terr_a = (
        _do_one_blow(
            spice_deck, discard_a, territories, players, spice_bank,
            storm_sector, is_first_turn,
        )
    )
    if worm_a:
        nexus = True
        sandworm_territory = worm_terr_a

    # --- Second draw (pile B) ---
    if spice_deck:
        spice_deck, discard_b, territories, players, spice_bank, worm_b, worm_terr_b = (
            _do_one_blow(
                spice_deck, discard_b, territories, players, spice_bank,
                storm_sector, is_first_turn,
            )
        )
        if worm_b:
            nexus = True
            sandworm_territory = worm_terr_b

    return game_state.model_copy(update={
        "spice_deck": spice_deck,
        "spice_discard_a": discard_a,
        "spice_discard_b": discard_b,
        "territories": territories,
        "players": players,
        "spice_bank": spice_bank,
        "current_phase": GamePhase.CHOAM_CHARITY,
        "nexus_triggered": nexus,
        "fremen_sandworm_ride_territory": sandworm_territory,
    })


def _do_one_blow(
    spice_deck: list[SpiceCard],
    discard: list[SpiceCard],
    territories: dict,
    players: list[Player],
    spice_bank: int,
    storm_sector: int,
    is_first_turn: bool,
) -> tuple[list, list, dict, list, int, bool, str | None]:
    """
    Execute one card draw from the spice deck using the given discard pile.
    Returns (spice_deck, discard, territories, players, spice_bank, worm_triggered, worm_territory).
    """
    set_aside: list[SpiceCard] = []
    worm_triggered = False
    worm_territory: str | None = None

    if not spice_deck:
        return spice_deck, discard, territories, players, spice_bank, False, None

    card = spice_deck.pop(0)

    if card.card_type == SpiceCardType.TERRITORY:
        territories, spice_bank = _place_spice(territories, card, storm_sector, spice_bank)
        discard.append(card)

    elif card.card_type == SpiceCardType.SHAI_HULUD:
        if is_first_turn:
            set_aside.append(card)
            territories, spice_deck, discard, set_aside, spice_bank = _draw_until_territory(
                territories, spice_deck, discard, set_aside,
                is_first_turn=True, storm_sector=storm_sector, spice_bank=spice_bank,
            )
        else:
            worm_triggered = True
            discard.append(card)
            worm_territory = _last_territory_in_discard(discard)
            players, territories, spice_bank = _shai_hulud_attack(
                players, territories, discard, spice_bank
            )
            territories, spice_deck, discard, _, spice_bank = _draw_until_territory(
                territories, spice_deck, discard, [],
                is_first_turn=False, storm_sector=storm_sector, spice_bank=spice_bank,
            )

    if set_aside:
        spice_deck.extend(set_aside)
        random.shuffle(spice_deck)

    return spice_deck, discard, territories, players, spice_bank, worm_triggered, worm_territory


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _place_spice(
    territories: dict,
    card: SpiceCard,
    storm_sector: int,
    spice_bank: int,
) -> tuple[dict, int]:
    name = card.territory_name
    if name and name in territories:
        t = territories[name]
        if storm_sector in t.sectors:
            return territories, spice_bank
        amount = min(card.spice_amount or 0, spice_bank)
        if amount > 0:
            territories[name] = t.model_copy(update={"current_spice": t.current_spice + amount})
            spice_bank -= amount
    return territories, spice_bank


def _reshuffle_discard(discard: list[SpiceCard]) -> list[SpiceCard]:
    deck = list(discard)
    random.shuffle(deck)
    return deck


def _last_territory_in_discard(discard: list[SpiceCard]) -> str | None:
    """Return the territory_name of the most recent Territory card in the discard."""
    for card in reversed(discard):
        if card.card_type == SpiceCardType.TERRITORY and card.territory_name:
            return card.territory_name
    return None


def _draw_until_territory(
    territories: dict,
    spice_deck: list[SpiceCard],
    spice_discard: list[SpiceCard],
    set_aside: list[SpiceCard],
    is_first_turn: bool,
    storm_sector: int,
    spice_bank: int,
) -> tuple[dict, list, list, list, int]:
    while spice_deck:
        card = spice_deck.pop(0)
        if card.card_type == SpiceCardType.TERRITORY:
            territories, spice_bank = _place_spice(territories, card, storm_sector, spice_bank)
            spice_discard.append(card)
            break
        if is_first_turn:
            set_aside.append(card)
        else:
            spice_discard.append(card)
    return territories, spice_deck, spice_discard, set_aside, spice_bank


def _shai_hulud_attack(
    players: list[Player],
    territories: dict,
    spice_discard: list[SpiceCard],
    spice_bank: int,
) -> tuple[list[Player], dict, int]:
    """
    Sandworm attacks the last-revealed territory in the given discard pile.
    Destroys all spice there and all forces except Fremen (immune).
    """
    target_name = _last_territory_in_discard(spice_discard)
    if target_name is None:
        return players, territories, spice_bank

    if target_name in territories:
        t = territories[target_name]
        spice_bank += t.current_spice
        territories[target_name] = t.model_copy(update={"current_spice": 0})

    from .handlers.registry import get_handler

    updated_players: list[Player] = []
    for player in players:
        handler = get_handler(player.faction)
        if handler.is_immune_to_shai_hulud():
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
                "special_forces_in_tanks": player.special_forces_in_tanks + special_killed,
            }))

    return updated_players, territories, spice_bank
