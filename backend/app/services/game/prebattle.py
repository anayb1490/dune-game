"""
Pre-battle faction abilities for the Dune board game.

Two abilities resolve BEFORE battle plans are submitted:
  1. BG VOICE (Basic): BG commands opponent to play/not play a card type.
     Format:  {"command": "play"|"not_play",
               "card_type": "poison_weapon"|"projectile_weapon"|"lasgun"|
                            "snooper"|"shield"|"worthless"|"cheap_hero"}
     The target must comply if possible; if they cannot they may do as they wish.
     Advanced: BG may also Voice their ally's opponent.
     Rulebook (p.13): Voice must resolve BEFORE Atreides prescience.

  2. ATREIDES BATTLE PRESCIENCE (Basic): Before plans are submitted, Atreides
     asks their opponent to reveal ONE element of their battle plan:
       "leader", "weapon", "defense", or "number"
     If asked about weapon/defense and opponent has none, they say so.
     Atreides may only ask about one element (cannot ask again if none).
     Rulebook (p.12): resolves AFTER Voice.

Sequence for a battle involving BG or Atreides:
  1. BG (if present) may issue a Voice command.  (or pass)
  2. Target of Voice acknowledges (they are informed).
  3. Atreides (if present) asks for one element.  (or pass)
  4. Opponent reveals that element.
  5. Plans are submitted.

Each faction does ONE pre-battle action per battle, then marks done.
Non-BG/non-Atreides factions simply call done_prebattle to pass.

Entry points:
    issue_voice(game_state, bg_player_id, target_faction, command, card_type)
    acknowledge_voice(game_state, target_player_id)
    ask_prescience(game_state, atreides_player_id, element)
    reveal_prescience(game_state, target_player_id)
    done_prebattle(game_state, player_id)
"""

from __future__ import annotations

from ...models.faction import FactionName
from ...models.game_state import ActiveBattle, GameState
from ...models.player import Player

# Valid Voice card types
VALID_VOICE_CARD_TYPES = frozenset({
    "poison_weapon",
    "projectile_weapon",
    "lasgun",
    "snooper",
    "shield",
    "worthless",
    "cheap_hero",
})

# Valid prescience elements
VALID_PRESCIENCE_ELEMENTS = frozenset({"leader", "weapon", "defense", "number"})


# ---------------------------------------------------------------------------
# BG Voice
# ---------------------------------------------------------------------------

def issue_voice(
    game_state: GameState,
    bg_player_id: str,
    target_faction: FactionName,
    command: str,
    card_type: str,
) -> GameState:
    """
    BG (or their ally, in Advanced) issues a Voice command to target_faction
    before battle plans are submitted.

    command: "play" or "not_play"
    card_type: one of VALID_VOICE_CARD_TYPES
    """
    ab = game_state.active_battle
    if ab is None:
        raise ValueError("No active battle")

    if ab.prebattle_complete:
        raise ValueError("Pre-battle phase is already complete")

    player = _get_player(game_state, bg_player_id)

    # Only BG (or their ally in Advanced) can Voice
    if player.faction != FactionName.BENE_GESSERIT:
        # Advanced: BG ally may also voice the ally's opponent
        bg_player = next(
            (p for p in game_state.players if p.faction == FactionName.BENE_GESSERIT),
            None,
        )
        if (game_state.mode.value == "advanced"
                and bg_player
                and bg_player.ally == player.faction):
            pass  # Ally of BG can Voice
        else:
            raise ValueError("Only Bene Gesserit (or their ally in Advanced) can use Voice")

    # Validate target is in this battle
    if target_faction not in (ab.attacker_faction, ab.defender_faction):
        raise ValueError(f"{target_faction.value} is not in this battle")

    if target_faction == player.faction:
        raise ValueError("Cannot Voice your own faction")

    if command not in ("play", "not_play"):
        raise ValueError(f"Invalid command '{command}': must be 'play' or 'not_play'")

    if card_type not in VALID_VOICE_CARD_TYPES:
        raise ValueError(
            f"Invalid card type '{card_type}'. Valid types: {sorted(VALID_VOICE_CARD_TYPES)}"
        )

    # Voice can only be issued once per battle
    if ab.voice_command is not None:
        raise ValueError("Voice has already been issued for this battle")

    # Determine which faction is BG's (the issuer's)
    issuer_faction = player.faction

    # Mark the issuer's side as done (Voice was their pre-battle action)
    is_attacker = issuer_faction == ab.attacker_faction
    updated_ab = ab.model_copy(update={
        "voice_command": {"command": command, "card_type": card_type},
        "voice_target_faction": target_faction,
        "voice_acknowledged": False,
        "attacker_prebattle_done": ab.attacker_prebattle_done or is_attacker,
        "defender_prebattle_done": ab.defender_prebattle_done or (not is_attacker),
    })

    return game_state.model_copy(update={"active_battle": updated_ab})


def acknowledge_voice(
    game_state: GameState,
    target_player_id: str,
) -> GameState:
    """
    The Voice target acknowledges the command.
    After acknowledgement the target's pre-battle action slot is consumed.
    Pre-battle completes if both sides are done.
    """
    ab = game_state.active_battle
    if ab is None:
        raise ValueError("No active battle")

    if ab.voice_command is None:
        raise ValueError("No Voice command to acknowledge")

    player = _get_player(game_state, target_player_id)

    if player.faction != ab.voice_target_faction:
        raise ValueError(
            f"Only {ab.voice_target_faction.value} (the Voice target) can acknowledge"
        )

    is_attacker = player.faction == ab.attacker_faction
    updated_ab = ab.model_copy(update={
        "voice_acknowledged": True,
        "attacker_prebattle_done": ab.attacker_prebattle_done or is_attacker,
        "defender_prebattle_done": ab.defender_prebattle_done or (not is_attacker),
    })

    return game_state.model_copy(update={"active_battle": updated_ab})


# ---------------------------------------------------------------------------
# Atreides Battle Prescience
# ---------------------------------------------------------------------------

def ask_prescience(
    game_state: GameState,
    atreides_player_id: str,
    element: str,
) -> GameState:
    """
    Atreides asks their opponent to reveal one element of their battle plan.
    element: "leader" | "weapon" | "defense" | "number"

    May also be used by Atreides' ally (Advanced).
    """
    ab = game_state.active_battle
    if ab is None:
        raise ValueError("No active battle")

    if ab.prebattle_complete:
        raise ValueError("Pre-battle phase is already complete")

    player = _get_player(game_state, atreides_player_id)

    # Only Atreides (or ally in Advanced) can ask prescience
    if player.faction != FactionName.ATREIDES:
        atreides_player = next(
            (p for p in game_state.players if p.faction == FactionName.ATREIDES),
            None,
        )
        if (game_state.mode.value == "advanced"
                and atreides_player
                and atreides_player.ally == player.faction):
            pass
        else:
            raise ValueError("Only Atreides (or their ally in Advanced) can use Prescience")

    if player.faction not in (ab.attacker_faction, ab.defender_faction):
        raise ValueError(f"{player.faction.value} is not in this battle")

    if element not in VALID_PRESCIENCE_ELEMENTS:
        raise ValueError(
            f"Invalid element '{element}'. Valid: {sorted(VALID_PRESCIENCE_ELEMENTS)}"
        )

    if ab.prescience_element_asked is not None:
        raise ValueError("Prescience has already been used for this battle")

    is_attacker = player.faction == ab.attacker_faction
    # The target is the opponent
    target_faction = ab.defender_faction if is_attacker else ab.attacker_faction

    updated_ab = ab.model_copy(update={
        "prescience_element_asked": element,
        "atreides_faction": player.faction,
        "attacker_prebattle_done": ab.attacker_prebattle_done or is_attacker,
        "defender_prebattle_done": ab.defender_prebattle_done or (not is_attacker),
    })

    return game_state.model_copy(update={"active_battle": updated_ab})


def reveal_prescience(
    game_state: GameState,
    target_player_id: str,
) -> GameState:
    """
    The prescience target reveals the requested element of their (planned) battle plan.

    Since plans haven't been submitted yet, the player states what they INTEND to play.
    The engine records the revealed value; the UI shows it to Atreides only.
    The target must answer honestly — the honour system / rule enforcement is trusting.

    The payload for reveal comes from the frontend via the action handler.
    This function receives the revealed_value string (e.g. "Duncan Idaho", "poison",
    "no weapon", "3") and stores it on the ActiveBattle.
    """
    # Note: this is called from the route handler with the revealed_value from payload.
    # See the route: REVEAL_PRESCIENCE action passes revealed_value.
    raise NotImplementedError(
        "Call reveal_prescience_value(game_state, target_player_id, revealed_value) instead"
    )


def reveal_prescience_value(
    game_state: GameState,
    target_player_id: str,
    revealed_value: str,
) -> GameState:
    """
    The prescience target reveals the requested element.
    revealed_value: a string description (e.g. "none", "Duncan Idaho", "4", "shield").
    """
    ab = game_state.active_battle
    if ab is None:
        raise ValueError("No active battle")

    if ab.prescience_element_asked is None:
        raise ValueError("No prescience question has been asked")

    player = _get_player(game_state, target_player_id)

    # Target is the opponent of Atreides' side
    atreides_faction = ab.atreides_faction
    if atreides_faction is None:
        raise ValueError("No Atreides faction tracked for this battle")

    atreides_is_attacker = atreides_faction == ab.attacker_faction
    expected_target = ab.defender_faction if atreides_is_attacker else ab.attacker_faction

    if player.faction != expected_target:
        raise ValueError(
            f"Only {expected_target.value} (the prescience target) can reveal"
        )

    is_attacker = player.faction == ab.attacker_faction
    updated_ab = ab.model_copy(update={
        "prescience_revealed_value": revealed_value,
        "attacker_prebattle_done": ab.attacker_prebattle_done or is_attacker,
        "defender_prebattle_done": ab.defender_prebattle_done or (not is_attacker),
    })

    return game_state.model_copy(update={"active_battle": updated_ab})


# ---------------------------------------------------------------------------
# Pass / done
# ---------------------------------------------------------------------------

def done_prebattle(
    game_state: GameState,
    player_id: str,
) -> GameState:
    """
    A player has no pre-battle ability to use (or chooses not to use it).
    Marks their side as done in the pre-battle phase.
    """
    ab = game_state.active_battle
    if ab is None:
        raise ValueError("No active battle")

    player = _get_player(game_state, player_id)

    if player.faction not in (ab.attacker_faction, ab.defender_faction):
        raise ValueError(f"{player.faction.value} is not in this battle")

    is_attacker = player.faction == ab.attacker_faction

    updated_ab = ab.model_copy(update={
        "attacker_prebattle_done": ab.attacker_prebattle_done or is_attacker,
        "defender_prebattle_done": ab.defender_prebattle_done or (not is_attacker),
    })

    return game_state.model_copy(update={"active_battle": updated_ab})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_player(game_state: GameState, player_id: str) -> Player:
    for p in game_state.players:
        if p.id == player_id:
            return p
    raise ValueError(f"Player not found: {player_id}")
