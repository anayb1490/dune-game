"""
Game setup service for the Dune board game (Avalon Hill / GF9 edition).

This service handles the full game lifecycle from lobby creation through
interactive setup to the start of turn 1:

  create_lobby()              -> GameState at LOBBY phase
  add_player_to_lobby()       -> adds a player to the lobby
  select_faction()            -> assigns a faction to a lobby player
  initialize_game()           -> LOBBY -> SETUP (traitor selection)
  process_traitor_selection() -> player picks 1 of 4 traitor cards
  process_storm_dial()        -> two players submit 0-20, storm placed
  finalize_setup()            -> SETUP -> STORM (game begins)

Legacy entry point (used by tests):
  create_game()               -> fully initialised GameState at STORM
"""

from __future__ import annotations

import random
import string
from typing import Optional

from pydantic import BaseModel

from ...data.cards import SPICE_DECK, TREACHERY_DECK
from ...data.factions import FACTION_DATA
from ...data.leaders import LEADERS, LEADERS_BY_FACTION
from ...data.territories import TERRITORIES
from ...models.card import SpiceCard, TraitorCard, TreacheryCard
from ...models.faction import FactionName
from ...models.game_state import (
    GameMode,
    GamePhase,
    GameState,
    LobbyPlayer,
    LobbyState,
    SetupState,
    SetupSubPhase,
)
from ...models.leader import Leader
from ...models.player import ForceGroup, KwisatzHaderach, Player, Prediction


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOTAL_GAME_SPICE: int = 564


# ---------------------------------------------------------------------------
# Input DTO (used by legacy create_game and tests)
# ---------------------------------------------------------------------------

class PlayerSetupConfig(BaseModel):
    player_id: str
    player_name: str
    faction: FactionName


# ---------------------------------------------------------------------------
# Lobby management
# ---------------------------------------------------------------------------

def _generate_join_code() -> str:
    """Generate a 6-character uppercase alphanumeric join code."""
    # Exclude ambiguous characters O/0/I/1
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choices(chars, k=6))


def create_lobby(
    game_id: str,
    host_player_id: str,
    host_player_name: str,
    mode: GameMode = GameMode.BASIC,
) -> GameState:
    """Create a new game in LOBBY phase with the host as the first player."""
    join_code = _generate_join_code()
    lobby_state = LobbyState(
        join_code=join_code,
        host_player_id=host_player_id,
        players=[LobbyPlayer(id=host_player_id, name=host_player_name)],
    )
    return GameState(
        id=game_id,
        mode=mode,
        players=[],
        current_phase=GamePhase.LOBBY,
        lobby_state=lobby_state,
        spice_bank=TOTAL_GAME_SPICE,
    )


def add_player_to_lobby(
    game_state: GameState,
    player_id: str,
    player_name: str,
) -> GameState:
    """Add a player to an existing lobby."""
    if game_state.current_phase != GamePhase.LOBBY:
        raise ValueError("Game is not in lobby phase.")
    if game_state.lobby_state is None:
        raise ValueError("No lobby state found.")

    lobby = game_state.lobby_state
    if len(lobby.players) >= 6:
        raise ValueError("Lobby is full (maximum 6 players).")

    if any(p.id == player_id for p in lobby.players):
        raise ValueError("Player already in lobby.")

    new_players = lobby.players + [LobbyPlayer(id=player_id, name=player_name)]
    new_lobby = lobby.model_copy(update={"players": new_players})
    return game_state.model_copy(update={"lobby_state": new_lobby})


def select_faction(
    game_state: GameState,
    player_id: str,
    faction: FactionName,
) -> GameState:
    """Assign a faction to a player in the lobby."""
    if game_state.current_phase != GamePhase.LOBBY:
        raise ValueError("Game is not in lobby phase.")
    if game_state.lobby_state is None:
        raise ValueError("No lobby state found.")

    lobby = game_state.lobby_state

    # Check faction not already taken
    for p in lobby.players:
        if p.faction == faction and p.id != player_id:
            raise ValueError(f"Faction {faction.value} is already taken.")

    # Find and update the player
    new_players = []
    found = False
    for p in lobby.players:
        if p.id == player_id:
            new_players.append(p.model_copy(update={"faction": faction}))
            found = True
        else:
            new_players.append(p)

    if not found:
        raise ValueError("Player not found in lobby.")

    new_lobby = lobby.model_copy(update={"players": new_players})
    return game_state.model_copy(update={"lobby_state": new_lobby})


# ---------------------------------------------------------------------------
# Game initialization (LOBBY -> SETUP)
# ---------------------------------------------------------------------------

def initialize_game(game_state: GameState) -> GameState:
    """
    Transition from LOBBY to SETUP phase.

    Builds decks, deals 4 traitor cards per player into SetupState,
    and waits for interactive traitor selection.
    """
    if game_state.current_phase != GamePhase.LOBBY:
        raise ValueError("Game must be in lobby phase to initialize.")
    if game_state.lobby_state is None:
        raise ValueError("No lobby state found.")

    lobby = game_state.lobby_state

    if len(lobby.players) < 2:
        raise ValueError("Need at least 2 players to start.")

    # Validate all players have factions
    for p in lobby.players:
        if p.faction is None:
            raise ValueError(f"Player {p.name} has not selected a faction.")

    # Validate no duplicate factions
    factions = [p.faction for p in lobby.players]
    if len(factions) != len(set(factions)):
        raise ValueError("Each faction may only be chosen by one player.")

    mode = game_state.mode

    # Build decks
    treachery_deck = _build_treachery_deck(mode)
    spice_deck = _build_spice_deck()
    territories = {name: t.model_copy() for name, t in TERRITORIES.items()}

    # Build traitor pool and deal 4 to each player
    active_factions = set(factions)
    traitor_pool = _build_traitor_pool(active_factions)

    traitor_hands_dealt: dict[str, list[TraitorCard]] = {}
    for p in lobby.players:
        traitor_hands_dealt[p.id] = [traitor_pool.pop() for _ in range(4)]

    # Shuffle player order (randomize seating / turn order)
    shuffled_lobby_players = list(lobby.players)
    random.shuffle(shuffled_lobby_players)

    # Build Player objects (without traitor cards — those come after selection)
    players: list[Player] = []
    for lp in shuffled_lobby_players:
        assert lp.faction is not None
        player, treachery_deck = _build_player(lp.id, lp.name, lp.faction, mode, treachery_deck)
        players.append(player)

    # Determine storm dial players (pick 2 random players)
    dial_indices = random.sample(range(len(shuffled_lobby_players)), min(2, len(shuffled_lobby_players)))
    storm_dial_players = [shuffled_lobby_players[i].id for i in dial_indices]

    # Check if any players auto-complete traitor selection
    # (Harkonnen in Advanced mode keeps all 4)
    traitor_selections_done: list[str] = []
    for lp in shuffled_lobby_players:
        assert lp.faction is not None
        faction_data = FACTION_DATA[lp.faction]
        keep_count = faction_data.traitor_cards_to_keep if mode == GameMode.ADVANCED else 1
        if keep_count >= 4:
            # Harkonnen Advanced: auto-keep all 4
            for player in players:
                if player.id == lp.id:
                    player_idx = players.index(player)
                    players[player_idx] = player.model_copy(update={
                        "traitor_cards": traitor_hands_dealt[lp.id][:],
                    })
                    break
            traitor_selections_done.append(lp.id)

    setup_state = SetupState(
        sub_phase=SetupSubPhase.TRAITOR_SELECTION,
        traitor_hands_dealt=traitor_hands_dealt,
        traitor_selections_done=traitor_selections_done,
        storm_dial_players=storm_dial_players,
    )

    # Spice bank
    player_spice_total = sum(p.spice for p in players)
    spice_bank = TOTAL_GAME_SPICE - player_spice_total

    return GameState(
        id=game_state.id,
        mode=mode,
        players=players,
        current_turn=1,
        current_phase=GamePhase.SETUP,
        first_player_index=0,
        storm_sector=0,  # Will be set by storm dial
        last_storm_move=0,
        spice_bank=spice_bank,
        territories=territories,
        treachery_deck=treachery_deck,
        treachery_discard=[],
        spice_deck=spice_deck,
        spice_discard=[],
        lobby_state=game_state.lobby_state,  # Preserve for host identification
        setup_state=setup_state,
        bidding_state=None,
        active_battle=None,
        bg_prediction_revealed=False,
        winner=None,
        is_game_over=False,
    )


# ---------------------------------------------------------------------------
# Traitor selection (interactive)
# ---------------------------------------------------------------------------

def process_traitor_selection(
    game_state: GameState,
    player_id: str,
    traitor_card_id: str,
) -> GameState:
    """Player selects one traitor card from their dealt hand of 4."""
    if game_state.current_phase != GamePhase.SETUP:
        raise ValueError("Game is not in setup phase.")
    if game_state.setup_state is None:
        raise ValueError("No setup state found.")
    if game_state.setup_state.sub_phase != SetupSubPhase.TRAITOR_SELECTION:
        raise ValueError("Not in traitor selection sub-phase.")

    setup = game_state.setup_state

    if player_id in setup.traitor_selections_done:
        raise ValueError("Player has already selected a traitor.")

    if player_id not in setup.traitor_hands_dealt:
        raise ValueError("Player not found in traitor hands.")

    hand = setup.traitor_hands_dealt[player_id]
    chosen = None
    for card in hand:
        if card.id == traitor_card_id:
            chosen = card
            break

    if chosen is None:
        raise ValueError(f"Card {traitor_card_id} not in player's dealt hand.")

    # Update the player's traitor_cards
    new_players = []
    for p in game_state.players:
        if p.id == player_id:
            new_players.append(p.model_copy(update={"traitor_cards": [chosen]}))
        else:
            new_players.append(p)

    new_selections_done = setup.traitor_selections_done + [player_id]
    new_setup = setup.model_copy(update={
        "traitor_selections_done": new_selections_done,
    })

    new_state = game_state.model_copy(update={
        "players": new_players,
        "setup_state": new_setup,
    })

    # Check if all players are done — advance to storm dial
    if len(new_selections_done) == len(game_state.players):
        new_setup = new_setup.model_copy(update={
            "sub_phase": SetupSubPhase.STORM_DIAL,
        })
        new_state = new_state.model_copy(update={"setup_state": new_setup})

    return new_state


# ---------------------------------------------------------------------------
# Storm dial (interactive)
# ---------------------------------------------------------------------------

def _next_setup_sub_phase(
    game_state: GameState,
    after: "SetupSubPhase | None" = None,
) -> "SetupSubPhase | None":
    """
    Return the first required optional setup sub-phase that comes after `after`,
    or None if setup should be finalised.

    Order: BG_PREDICTION → FREMEN_PLACEMENT → ATREIDES_PRESCIENCE
    Each is only included when the relevant faction/mode combination is present.
    """
    is_advanced = game_state.mode == GameMode.ADVANCED
    factions = {p.faction for p in game_state.players}

    ordered: list[SetupSubPhase] = []
    if FactionName.BENE_GESSERIT in factions and is_advanced:
        ordered.append(SetupSubPhase.BG_PREDICTION)
    if FactionName.FREMEN in factions:
        ordered.append(SetupSubPhase.FREMEN_PLACEMENT)
    if FactionName.ATREIDES in factions and is_advanced:
        ordered.append(SetupSubPhase.ATREIDES_PRESCIENCE)

    if after is None:
        return ordered[0] if ordered else None
    try:
        idx = ordered.index(after)
        return ordered[idx + 1] if idx + 1 < len(ordered) else None
    except ValueError:
        return ordered[0] if ordered else None


def _transition_to_sub_phase(
    game_state: GameState,
    new_setup: "SetupState",
    sub_phase: "SetupSubPhase",
    storm_sector: int,
) -> GameState:
    """Transition setup_state to `sub_phase`, injecting any needed data."""
    updates: dict = {"sub_phase": sub_phase}

    if sub_phase == SetupSubPhase.ATREIDES_PRESCIENCE:
        # Store top 5 cards as plain dicts so Atreides can study them
        preview = [c.model_dump() for c in game_state.treachery_deck[:5]]
        updates["atreides_prescience_cards"] = preview

    updated_setup = new_setup.model_copy(update=updates)
    return game_state.model_copy(update={
        "setup_state": updated_setup,
        "storm_sector": storm_sector,
    })


def process_storm_dial(
    game_state: GameState,
    player_id: str,
    number: int,
) -> GameState:
    """One of two designated players submits their storm dial number (0-20)."""
    if game_state.current_phase != GamePhase.SETUP:
        raise ValueError("Game is not in setup phase.")
    if game_state.setup_state is None:
        raise ValueError("No setup state found.")
    if game_state.setup_state.sub_phase != SetupSubPhase.STORM_DIAL:
        raise ValueError("Not in storm dial sub-phase.")

    setup = game_state.setup_state

    if player_id not in setup.storm_dial_players:
        raise ValueError("Player is not a designated storm dial player.")

    if player_id in setup.storm_dial_submissions:
        raise ValueError("Player has already submitted a storm dial number.")

    if not 0 <= number <= 20:
        raise ValueError("Storm dial number must be between 0 and 20.")

    new_submissions = {**setup.storm_dial_submissions, player_id: number}
    new_setup = setup.model_copy(update={"storm_dial_submissions": new_submissions})
    new_state = game_state.model_copy(update={"setup_state": new_setup})

    # If both players have submitted, determine next sub-phase
    if len(new_submissions) == 2:
        total = sum(new_submissions.values())
        storm_sector = total % 18
        new_state = new_state.model_copy(update={"storm_sector": storm_sector})

        next_phase = _next_setup_sub_phase(new_state, after=None)
        if next_phase is not None:
            return _transition_to_sub_phase(new_state, new_setup, next_phase, storm_sector)
        return finalize_setup(new_state, storm_sector)

    return new_state


# ---------------------------------------------------------------------------
# BG Prediction (interactive, Advanced only)
# ---------------------------------------------------------------------------

def process_bg_prediction(
    game_state: GameState,
    player_id: str,
    predicted_faction: FactionName,
    predicted_turn: int,
) -> GameState:
    """Bene Gesserit player secretly records their prediction."""
    if game_state.current_phase != GamePhase.SETUP:
        raise ValueError("Game is not in setup phase.")
    if game_state.setup_state is None:
        raise ValueError("No setup state found.")
    if game_state.setup_state.sub_phase != SetupSubPhase.BG_PREDICTION:
        raise ValueError("Not in BG prediction sub-phase.")

    # Validate it's the BG player
    bg_player = next((p for p in game_state.players if p.faction == FactionName.BENE_GESSERIT), None)
    if bg_player is None:
        raise ValueError("No Bene Gesserit player in this game.")
    if bg_player.id != player_id:
        raise ValueError("Only the Bene Gesserit player can make a prediction.")

    if not 1 <= predicted_turn <= 10:
        raise ValueError("Predicted turn must be between 1 and 10.")
    if predicted_faction == FactionName.BENE_GESSERIT:
        raise ValueError("Bene Gesserit cannot predict themselves to win.")
    # Ensure predicted faction is in the game
    active_factions = {p.faction for p in game_state.players}
    if predicted_faction not in active_factions:
        raise ValueError(f"Faction {predicted_faction.value} is not in this game.")

    # Update the BG player's prediction
    new_prediction = Prediction(faction=predicted_faction, turn=predicted_turn, is_revealed=False)
    new_players = [
        p.model_copy(update={"prediction": new_prediction}) if p.faction == FactionName.BENE_GESSERIT else p
        for p in game_state.players
    ]

    # Advance to the next setup sub-phase or finalize
    new_state = game_state.model_copy(update={"players": new_players})
    next_phase = _next_setup_sub_phase(new_state, after=SetupSubPhase.BG_PREDICTION)
    if next_phase is not None:
        assert new_state.setup_state is not None
        return _transition_to_sub_phase(
            new_state, new_state.setup_state, next_phase, new_state.storm_sector
        )
    return finalize_setup(new_state, new_state.storm_sector)


# ---------------------------------------------------------------------------
# Fremen Placement (interactive)
# ---------------------------------------------------------------------------

def process_fremen_placement(
    game_state: GameState,
    player_id: str,
    placements: list[dict],  # [{"territory": str, "sector": int, "regular_count": int, "special_count": int}, ...]
) -> GameState:
    """Fremen player redistributes starting forces to any unoccupied territories."""
    if game_state.current_phase != GamePhase.SETUP:
        raise ValueError("Game is not in setup phase.")
    if game_state.setup_state is None:
        raise ValueError("No setup state found.")
    if game_state.setup_state.sub_phase != SetupSubPhase.FREMEN_PLACEMENT:
        raise ValueError("Not in Fremen placement sub-phase.")

    fremen_player = next((p for p in game_state.players if p.faction == FactionName.FREMEN), None)
    if fremen_player is None:
        raise ValueError("No Fremen player in this game.")
    if fremen_player.id != player_id:
        raise ValueError("Only the Fremen player can place their forces.")

    # Count current Fremen forces on board
    total_regular = sum(fg.regular_count for fg in fremen_player.forces_on_board)
    total_special = sum(fg.special_count for fg in fremen_player.forces_on_board)

    # Validate placements sum matches
    placement_regular = sum(p.get("regular_count", 0) for p in placements)
    placement_special = sum(p.get("special_count", 0) for p in placements)

    if placement_regular != total_regular:
        raise ValueError(f"Must place exactly {total_regular} regular forces (got {placement_regular}).")
    if placement_special != total_special:
        raise ValueError(f"Must place exactly {total_special} special forces (got {placement_special}).")

    # Validate territories exist and aren't occupied by enemies
    occupied_by_others: set[str] = set()
    for p in game_state.players:
        if p.faction != FactionName.FREMEN:
            for fg in p.forces_on_board:
                occupied_by_others.add(fg.territory_name)

    new_force_groups: list[ForceGroup] = []
    for pl in placements:
        territory = pl.get("territory", "")
        if territory not in game_state.territories:
            raise ValueError(f"Territory '{territory}' does not exist.")
        if territory in occupied_by_others:
            raise ValueError(f"Territory '{territory}' is occupied by another faction.")
        reg = pl.get("regular_count", 0)
        spec = pl.get("special_count", 0)
        if reg < 0 or spec < 0:
            raise ValueError("Force counts cannot be negative.")
        if reg + spec == 0:
            continue  # Skip empty placements

        t = game_state.territories[territory]
        sector = pl.get("sector", t.sectors[0] if t.sectors else 0)
        new_force_groups.append(ForceGroup(
            territory_name=territory,
            sector=sector,
            regular_count=reg,
            special_count=spec,
        ))

    new_players = [
        p.model_copy(update={"forces_on_board": new_force_groups}) if p.faction == FactionName.FREMEN else p
        for p in game_state.players
    ]
    new_state = game_state.model_copy(update={"players": new_players})
    next_phase = _next_setup_sub_phase(new_state, after=SetupSubPhase.FREMEN_PLACEMENT)
    if next_phase is not None:
        assert new_state.setup_state is not None
        return _transition_to_sub_phase(
            new_state, new_state.setup_state, next_phase, new_state.storm_sector
        )
    return finalize_setup(new_state, new_state.storm_sector)


# ---------------------------------------------------------------------------
# Atreides Prescience (interactive, Advanced only)
# ---------------------------------------------------------------------------

def process_atreides_prescience(
    game_state: GameState,
    player_id: str,
) -> GameState:
    """
    Atreides player acknowledges that they have viewed the top treachery cards.
    This advances setup to the next sub-phase (or finalizes if none remain).
    """
    if game_state.current_phase != GamePhase.SETUP:
        raise ValueError("Game is not in setup phase.")
    if game_state.setup_state is None:
        raise ValueError("No setup state found.")
    if game_state.setup_state.sub_phase != SetupSubPhase.ATREIDES_PRESCIENCE:
        raise ValueError("Not in Atreides prescience sub-phase.")

    atreides_player = next(
        (p for p in game_state.players if p.faction == FactionName.ATREIDES), None
    )
    if atreides_player is None:
        raise ValueError("No Atreides player in this game.")
    if atreides_player.id != player_id:
        raise ValueError("Only the Atreides player can acknowledge prescience.")

    # ATREIDES_PRESCIENCE is always the last optional sub-phase
    return finalize_setup(game_state, game_state.storm_sector)


# ---------------------------------------------------------------------------
# Finalize setup (SETUP -> STORM)
# ---------------------------------------------------------------------------

def finalize_setup(game_state: GameState, storm_sector: int) -> GameState:
    """Complete setup and transition to the first game turn."""
    return game_state.model_copy(update={
        "current_phase": GamePhase.STORM,
        "storm_sector": storm_sector,
        "setup_state": None,
    })


# ---------------------------------------------------------------------------
# Legacy entry point (backward-compatible with existing tests)
# ---------------------------------------------------------------------------

def create_game(
    game_id: str,
    player_configs: list[PlayerSetupConfig],
    mode: GameMode,
    initial_storm_sector: Optional[int] = None,
) -> GameState:
    """
    Create and return a fully initialised GameState, ready for turn 1.
    This is the original all-in-one function, kept for backward compatibility.
    """
    _validate_configs(player_configs)

    territories = {name: t.model_copy() for name, t in TERRITORIES.items()}
    treachery_deck = _build_treachery_deck(mode)
    spice_deck = _build_spice_deck()

    active_factions = {cfg.faction for cfg in player_configs}
    traitor_pool = _build_traitor_pool(active_factions)

    players, treachery_deck = _init_players_legacy(
        player_configs, mode, traitor_pool, treachery_deck
    )

    if initial_storm_sector is None:
        initial_storm_sector = random.randint(0, 17)

    player_spice_total = sum(p.spice for p in players)
    spice_bank = TOTAL_GAME_SPICE - player_spice_total

    return GameState(
        id=game_id,
        mode=mode,
        players=players,
        current_turn=1,
        current_phase=GamePhase.STORM,
        first_player_index=0,
        storm_sector=initial_storm_sector,
        last_storm_move=0,
        spice_bank=spice_bank,
        territories=territories,
        treachery_deck=treachery_deck,
        treachery_discard=[],
        spice_deck=spice_deck,
        spice_discard=[],
        bidding_state=None,
        active_battle=None,
        bg_prediction_revealed=False,
        winner=None,
        is_game_over=False,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _validate_configs(player_configs: list[PlayerSetupConfig]) -> None:
    if len(player_configs) < 2:
        raise ValueError("Dune requires at least 2 players.")
    if len(player_configs) > 6:
        raise ValueError("Dune supports a maximum of 6 players.")
    factions = [cfg.faction for cfg in player_configs]
    if len(factions) != len(set(factions)):
        raise ValueError("Each faction may only be chosen by one player.")


def _build_treachery_deck(mode: GameMode) -> list[TreacheryCard]:
    if mode == GameMode.BASIC:
        cards = [c.model_copy() for c in TREACHERY_DECK if not c.is_advanced]
    else:
        cards = [c.model_copy() for c in TREACHERY_DECK]
    random.shuffle(cards)
    return cards


def _build_spice_deck() -> list[SpiceCard]:
    deck = [c.model_copy() for c in SPICE_DECK]
    random.shuffle(deck)
    return deck


def _build_traitor_pool(active_factions: set[FactionName]) -> list[TraitorCard]:
    pool: list[TraitorCard] = []
    for faction in active_factions:
        for leader in LEADERS_BY_FACTION[faction]:
            pool.append(TraitorCard(
                id=f"traitor_{leader.id}",
                leader_id=leader.id,
                leader_name=leader.name,
                faction=faction,
                leader_strength=leader.strength,
            ))
    random.shuffle(pool)
    return pool


def _build_player(
    player_id: str,
    player_name: str,
    faction: FactionName,
    mode: GameMode,
    treachery_deck: list[TreacheryCard],
) -> tuple[Player, list[TreacheryCard]]:
    """Build a single Player object (without traitor cards)."""
    faction_data = FACTION_DATA[faction]

    forces_on_board: list[ForceGroup] = []
    for pos in faction_data.starting_positions:
        territory = TERRITORIES.get(pos.territory)
        sector = territory.sectors[0] if territory else 0
        forces_on_board.append(ForceGroup(
            territory_name=pos.territory,
            sector=sector,
            regular_count=pos.regular_forces,
            special_count=pos.special_forces,
        ))

    starting_hand: list[TreacheryCard] = []
    for _ in range(faction_data.starting_treachery_cards):
        if treachery_deck:
            starting_hand.append(treachery_deck.pop(0))

    leaders: list[Leader] = [
        l.model_copy() for l in LEADERS_BY_FACTION[faction]
    ]

    kwisatz_haderach = (
        KwisatzHaderach()
        if faction == FactionName.ATREIDES and mode == GameMode.ADVANCED
        else None
    )
    prediction = (
        Prediction()
        if faction == FactionName.BENE_GESSERIT and mode == GameMode.ADVANCED
        else None
    )

    player = Player(
        id=player_id,
        name=player_name,
        faction=faction,
        spice=faction_data.starting_spice,
        treachery_hand=starting_hand,
        traitor_cards=[],  # Set during traitor selection
        forces_on_board=forces_on_board,
        forces_in_reserve=faction_data.starting_reserve,
        forces_in_tanks=0,
        special_forces_in_reserve=faction_data.total_special_forces,
        special_forces_in_tanks=0,
        leaders=leaders,
        ally=None,
        is_eliminated=False,
        kwisatz_haderach=kwisatz_haderach,
        prediction=prediction,
    )
    return player, treachery_deck


def _init_players_legacy(
    player_configs: list[PlayerSetupConfig],
    mode: GameMode,
    traitor_pool: list[TraitorCard],
    treachery_deck: list[TreacheryCard],
) -> tuple[list[Player], list[TreacheryCard]]:
    """Legacy: builds players with auto-selected traitors."""
    traitor_hands: dict[str, list[TraitorCard]] = {}
    for cfg in player_configs:
        traitor_hands[cfg.player_id] = [traitor_pool.pop() for _ in range(4)]

    players: list[Player] = []
    for cfg in player_configs:
        faction_data = FACTION_DATA[cfg.faction]
        raw_hand = traitor_hands[cfg.player_id]
        keep_count = (
            faction_data.traitor_cards_to_keep
            if mode == GameMode.ADVANCED
            else 1
        )
        sorted_hand = sorted(
            raw_hand,
            key=lambda c: _leader_strength(c.leader_id),
            reverse=True,
        )
        kept_traitors = sorted_hand[:keep_count]

        player, treachery_deck = _build_player(
            cfg.player_id, cfg.player_name, cfg.faction, mode, treachery_deck
        )
        player = player.model_copy(update={"traitor_cards": kept_traitors})
        players.append(player)

    return players, treachery_deck


def _leader_strength(leader_id: str) -> int:
    leader = LEADERS.get(leader_id)
    return leader.strength if leader else 0
