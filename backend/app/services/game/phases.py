"""
Phase utilities and CHOAM Charity service for the Dune board game.

Contains:
  • PHASE_SEQUENCE — canonical order of the 9 game phases
  • next_phase()   — look up the phase that follows a given one
  • AUTOMATED_PHASES — set of phases that resolve without player input
  • resolve_choam_charity() — CHOAM Charity Phase service

Rulebook reference: p.7–8 — "CHOAM Charity"
  Any player with 0 or 1 spice may call "CHOAM Charity" to bring their
  total up to 2.  Bene Gesserit (Advanced) always receive 2 regardless
  of current holdings.
"""

from __future__ import annotations

from ...models.game_state import GamePhase, GameState
from ...models.player import Player
from .handlers.registry import get_handler


# ---------------------------------------------------------------------------
# Phase sequence
# ---------------------------------------------------------------------------

PHASE_SEQUENCE: list[GamePhase] = [
    GamePhase.STORM,
    GamePhase.SPICE_BLOW,
    GamePhase.NEXUS,
    GamePhase.CHOAM_CHARITY,
    GamePhase.BIDDING,
    GamePhase.REVIVAL,
    GamePhase.SHIPMENT_AND_MOVEMENT,
    GamePhase.BATTLE,
    GamePhase.SPICE_COLLECTION,
    GamePhase.MENTAT_PAUSE,
]

# Phases that run_automated_phases() will fast-forward through.
# This is intentionally limited to SPICE_COLLECTION so the test helper
# doesn't loop through every phase. The full set of host-only automated
# phases is defined in the game routes.
AUTOMATED_PHASES: set[GamePhase] = {
    GamePhase.SPICE_COLLECTION,
}


def next_phase(current: GamePhase) -> GamePhase:
    """
    Return the phase that follows `current` in the sequence.

    After MENTAT_PAUSE the sequence wraps back to STORM (start of
    the next turn), but the caller is responsible for incrementing
    the turn counter — this function only returns the next phase enum.
    """
    idx = PHASE_SEQUENCE.index(current)
    return PHASE_SEQUENCE[(idx + 1) % len(PHASE_SEQUENCE)]


# ---------------------------------------------------------------------------
# CHOAM Charity Phase
# ---------------------------------------------------------------------------

def resolve_choam_charity(game_state: GameState) -> GameState:
    """
    Execute the CHOAM Charity Phase and return the updated GameState.

    For each player (in seating order):
      - Ask the faction handler how much charity they receive.
      - Standard rule: 0 spice → receive 2, 1 spice → receive 1, else 0.
      - Bene Gesserit (Advanced): always receive 2.
      - Deduct the charity from the spice bank.

    Returns GameState with:
      - Player spice updated
      - Spice bank reduced
      - current_phase advanced to BIDDING
    """
    updated_players: list[Player] = []
    spice_bank = game_state.spice_bank

    for player in game_state.players:
        handler = get_handler(player.faction)
        charity = handler.get_choam_charity(player, game_state)

        if charity > 0 and spice_bank >= charity:
            updated_players.append(player.model_copy(update={
                "spice": player.spice + charity,
            }))
            spice_bank -= charity
        elif charity > 0 and spice_bank > 0:
            # Bank doesn't have enough — give what remains
            updated_players.append(player.model_copy(update={
                "spice": player.spice + spice_bank,
            }))
            spice_bank = 0
        else:
            updated_players.append(player)

    return game_state.model_copy(update={
        "players": updated_players,
        "spice_bank": spice_bank,
        "current_phase": GamePhase.BIDDING,
    })
