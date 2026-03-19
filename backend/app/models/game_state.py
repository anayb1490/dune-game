from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .card import TreacheryCard, SpiceCard, TraitorCard
from .faction import FactionName
from .player import Player
from .territory import Territory


# =============================================================================
# Enums
# =============================================================================

class GamePhase(str, Enum):
    """All game phases, including pre-game lobby and setup."""
    LOBBY = "lobby"
    SETUP = "setup"
    STORM = "storm"
    SPICE_BLOW = "spice_blow"
    NEXUS = "nexus"
    CHOAM_CHARITY = "choam_charity"
    BIDDING = "bidding"
    REVIVAL = "revival"
    SHIPMENT_AND_MOVEMENT = "shipment_and_movement"
    BATTLE = "battle"
    SPICE_COLLECTION = "spice_collection"
    MENTAT_PAUSE = "mentat_pause"


class GameMode(str, Enum):
    BASIC = "basic"
    ADVANCED = "advanced"


class SetupSubPhase(str, Enum):
    TRAITOR_SELECTION = "traitor_selection"
    STORM_DIAL = "storm_dial"


# =============================================================================
# Battle sub-models
# =============================================================================

class BattlePlan(BaseModel):
    """
    A player's secret Battle Plan, submitted simultaneously by both combatants
    before resolution.

    Forces dialed: the number of forces the player chooses to commit to combat.
    These are lost regardless of the outcome — the winner keeps the remainder,
    the loser loses all remaining forces in that territory too.

    Advanced: `spice_to_expend` allows a player to boost their total strength
    by 1 per spice spent (up to the number of forces they dialed).
    """
    faction: FactionName
    forces_dialed: int = Field(ge=0)

    # Leader: exactly one of leader_id or cheap_hero must be set
    leader_id: Optional[str] = Field(
        default=None,
        description="ID of the leader disc being used. None if using a Cheap Hero."
    )
    cheap_hero: bool = Field(
        default=False,
        description="True if a Cheap Hero/Heroine card is played instead of a leader."
    )

    # How many of forces_dialed are special forces (Sardaukar / Fedaykin)
    special_forces_dialed: int = Field(
        default=0,
        ge=0,
        description="Number of special forces included in forces_dialed. "
                    "Used to calculate correct battle strength via handler."
    )

    # Optional Treachery Cards
    weapon_card: Optional[TreacheryCard] = None
    defense_card: Optional[TreacheryCard] = None

    # Advanced only — 0 in Basic game
    spice_to_expend: int = Field(
        default=0,
        ge=0,
        description="Advanced: spice spent to increase battle total (1 per spice, "
                    "up to the number of forces dialed)."
    )


class ActiveBattle(BaseModel):
    """
    The context of a battle currently in progress during the Battle Phase.
    Exists on GameState only while a battle is being resolved; set to None
    once the battle concludes and forces / leaders have been updated.
    """
    territory_name: str
    sector: int = Field(ge=0, le=17)
    attacker_faction: FactionName
    defender_faction: FactionName

    # Plans are hidden (None) until both players have submitted
    attacker_plan: Optional[BattlePlan] = None
    defender_plan: Optional[BattlePlan] = None

    is_resolved: bool = False


# =============================================================================
# Bidding sub-model
# =============================================================================

class LobbyPlayer(BaseModel):
    """A player in the lobby who may not have chosen a faction yet."""
    id: str
    name: str
    faction: Optional[FactionName] = None


class LobbyState(BaseModel):
    """Pre-game lobby where players join and pick factions."""
    join_code: str
    host_player_id: str
    players: list[LobbyPlayer] = Field(default_factory=list)


class SetupState(BaseModel):
    """Interactive setup steps after the host starts the game."""
    sub_phase: SetupSubPhase = SetupSubPhase.TRAITOR_SELECTION

    # Traitor selection: player_id -> their 4 dealt traitor cards
    traitor_hands_dealt: dict[str, list[TraitorCard]] = Field(default_factory=dict)
    # Player IDs that have submitted their traitor pick
    traitor_selections_done: list[str] = Field(default_factory=list)

    # Storm dial: player_id -> submitted number (0-20)
    storm_dial_submissions: dict[str, int] = Field(default_factory=dict)
    # The two player IDs designated for the storm dial
    storm_dial_players: list[str] = Field(default_factory=list)


class BiddingState(BaseModel):
    """
    Tracks the state of the Bidding Phase across multiple card auctions.
    Each turn, a number of Treachery Cards equal to the number of players
    are auctioned one at a time.
    """
    cards_up_for_bid: list[TreacheryCard] = Field(default_factory=list)
    current_card_index: int = 0
    current_high_bidder: Optional[FactionName] = None
    current_high_bid: int = 0

    # Whose turn is it to bid? (faction name of the active bidder)
    current_bidder: Optional[FactionName] = None

    # Tracks which factions have passed on the current card
    factions_passed: list[FactionName] = Field(default_factory=list)

    # Atreides prescience: ID of the card currently visible to Atreides (Advanced)
    atreides_prescience_card_id: Optional[str] = None


class NexusState(BaseModel):
    """
    Tracks the state of the Nexus (alliance opportunity) phase.

    Triggered when Shai-Hulud is drawn (not first turn). Each player in
    turn order may propose an alliance, accept a pending proposal, break
    their current alliance, or pass. When all players are done the Nexus
    ends and the game advances to CHOAM Charity.
    """
    # Pending proposals: proposer_faction_value -> target_faction_value
    # Uses str keys because Pydantic dict keys must be str-serialisable.
    proposals: dict[str, str] = Field(default_factory=dict)

    # Factions that have completed their nexus turn (proposed, accepted, or passed)
    factions_done: list[str] = Field(default_factory=list)

    # The faction whose turn it is to act
    current_faction: Optional[str] = None


# =============================================================================
# GameState
# =============================================================================

class GameState(BaseModel):
    """
    The complete, authoritative state of a single Dune game session.
    This is the root object serialised to/from the server and broadcast
    to all connected players via WebSocket.

    Sensitive fields (opponent battle plans, traitor cards) are filtered
    per-player before sending in the schema layer.
    """
    id: str
    mode: GameMode

    # Players — ordered by seating position (determines turn order)
    players: list[Player]

    # Turn and phase
    current_turn: int = Field(default=1, ge=1, le=10)
    current_phase: GamePhase = GamePhase.STORM
    first_player_index: int = Field(
        default=0,
        description="Index into `players` of the faction that acts first this turn."
    )
    current_player_index: int = Field(
        default=0,
        description="Index into `players` of the faction currently taking their turn "
                    "in interactive phases (Revival, Shipment, etc.)."
    )

    # Storm
    storm_sector: int = Field(
        default=0,
        ge=0,
        le=17,
        description="Current position of the storm (sector index, 0–17). "
                    "Advances clockwise each turn."
    )
    last_storm_move: int = Field(
        default=0,
        ge=0,
        description="How many sectors the storm moved last turn (recorded for reference)."
    )

    # Spice bank — total spice not currently held by any player or territory
    spice_bank: int = Field(default=0, ge=0)

    # Board: territory name -> Territory
    territories: dict[str, Territory] = Field(default_factory=dict)

    # Decks
    treachery_deck: list[TreacheryCard] = Field(default_factory=list)
    treachery_discard: list[TreacheryCard] = Field(default_factory=list)
    spice_deck: list[SpiceCard] = Field(default_factory=list)
    spice_discard: list[SpiceCard] = Field(default_factory=list)

    # Active sub-states (None when that phase is not in progress)
    lobby_state: Optional[LobbyState] = None
    setup_state: Optional[SetupState] = None
    bidding_state: Optional[BiddingState] = None
    nexus_state: Optional[NexusState] = None
    active_battle: Optional[ActiveBattle] = None

    # Nexus trigger — set by spice blow when Shai-Hulud is drawn (not first turn)
    nexus_triggered: bool = False

    # Advanced: Bene Gesserit prediction
    # The Prediction is also stored on the BG Player, but mirrored here so
    # the game engine can check the win condition without searching players.
    bg_prediction_revealed: bool = False

    # Phase messages — populated when automated phases resolve so players
    # can see what happened before the host advances to the next phase.
    phase_messages: list[str] = Field(default_factory=list)

    # Cumulative event log — all phase messages appended over game history.
    # Capped at 60 entries server-side. Public; not filtered per-player.
    game_log: list[str] = Field(default_factory=list)

    # Win condition
    winner: Optional[FactionName] = None
    is_game_over: bool = False
