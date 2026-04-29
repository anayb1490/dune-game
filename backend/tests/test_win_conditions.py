"""
Tests for all win conditions in the Dune board game engine.

Win condition priority order (highest to lowest):
  1. Bene Gesserit Prediction (Advanced) — wins instead of the predicted faction
  2. Fremen Special Victory (Advanced)   — control the 3 Fremen sietchs, no ally
  3. Standard Stronghold Victory         — 3 solo or 4 allied
  4. Spacing Guild Alternate Victory (Advanced) — wins at turn 10 if no one else did
  5. Turn limit with no victor           — game ends, winner = None

Run with:
    cd DuneGame
    python -m pytest backend/tests/test_win_conditions.py -v
"""

import pytest

from backend.app.models.faction import FactionName
from backend.app.models.game_state import GameMode, GamePhase, GameState
from backend.app.models.player import ForceGroup, Prediction
from backend.app.services.game.engine import MAX_TURNS, advance_phase, advance_turn
from backend.app.services.game.setup import PlayerSetupConfig, create_game


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXED_STORM = 0  # Sector away from any starting forces


def _make_game(*factions: FactionName, mode: GameMode = GameMode.ADVANCED) -> GameState:
    configs = [
        PlayerSetupConfig(player_id=f"p{i}", player_name=f.value, faction=f)
        for i, f in enumerate(factions, start=1)
    ]
    return create_game(
        game_id="test-win",
        player_configs=configs,
        mode=mode,
        initial_storm_sector=FIXED_STORM,
    )


def _at_mentat(game: GameState) -> GameState:
    """Return a copy of `game` at MENTAT_PAUSE with no existing phase_messages."""
    return game.model_copy(update={
        "current_phase": GamePhase.MENTAT_PAUSE,
        "phase_messages": [],
    })


def _give_strongholds(game: GameState, faction: FactionName, strongholds: list[str]) -> GameState:
    """
    Place one token for `faction` in each listed stronghold, removing all
    other forces from those territories (ensures uncontested control).
    """
    new_players = []
    for p in game.players:
        # Strip forces from the target strongholds
        kept = [fg for fg in p.forces_on_board if fg.territory_name not in strongholds]
        if p.faction == faction:
            # Add one token per stronghold
            added = [
                ForceGroup(territory_name=sh, sector=0, regular_count=1)
                for sh in strongholds
            ]
            new_players.append(p.model_copy(update={"forces_on_board": kept + added}))
        else:
            new_players.append(p.model_copy(update={"forces_on_board": kept}))
    return game.model_copy(update={"players": new_players})


# ---------------------------------------------------------------------------
# Standard Stronghold Victory
# ---------------------------------------------------------------------------

class TestStrongholdVictory:

    def test_solo_3_strongholds_wins(self):
        """A faction controlling 3 uncontested strongholds wins."""
        from backend.app.data.territories import STRONGHOLD_NAMES
        shs = list(STRONGHOLD_NAMES)[:3]
        game = _make_game(FactionName.ATREIDES, FactionName.HARKONNEN, mode=GameMode.BASIC)
        game = _give_strongholds(game, FactionName.ATREIDES, shs)
        game = _at_mentat(game)

        result = advance_phase(game)

        assert result.is_game_over is True
        assert result.winner == FactionName.ATREIDES
        assert result.ally_winner is None
        assert len(result.phase_messages) > 0
        assert "wins" in result.phase_messages[0].lower()

    def test_solo_2_strongholds_does_not_win(self):
        """2 strongholds is not enough to win solo."""
        from backend.app.data.territories import STRONGHOLD_NAMES
        shs = list(STRONGHOLD_NAMES)[:2]
        game = _make_game(FactionName.ATREIDES, FactionName.HARKONNEN, mode=GameMode.BASIC)
        game = _give_strongholds(game, FactionName.ATREIDES, shs)
        game = _at_mentat(game)

        result = advance_phase(game)

        assert result.is_game_over is False

    def test_contested_stronghold_does_not_count(self):
        """A stronghold with enemy forces present is not controlled."""
        from backend.app.data.territories import STRONGHOLD_NAMES
        shs = list(STRONGHOLD_NAMES)[:3]
        game = _make_game(FactionName.ATREIDES, FactionName.HARKONNEN, mode=GameMode.BASIC)

        # Give Atreides 3 strongholds, but put Harkonnen in one of them too
        game = _give_strongholds(game, FactionName.ATREIDES, shs)
        new_players = []
        for p in game.players:
            if p.faction == FactionName.HARKONNEN:
                contested = ForceGroup(territory_name=shs[0], sector=0, regular_count=1)
                new_players.append(p.model_copy(update={
                    "forces_on_board": p.forces_on_board + [contested]
                }))
            else:
                new_players.append(p)
        game = game.model_copy(update={"players": new_players})
        game = _at_mentat(game)

        result = advance_phase(game)

        # Atreides effectively controls only 2 uncontested strongholds — no win
        assert result.is_game_over is False

    def test_allied_4_strongholds_wins(self):
        """An alliance controlling 4 strongholds combined wins."""
        from backend.app.data.territories import STRONGHOLD_NAMES
        shs = list(STRONGHOLD_NAMES)[:4]
        game = _make_game(FactionName.ATREIDES, FactionName.HARKONNEN, mode=GameMode.BASIC)

        # Form the alliance
        new_players = [
            p.model_copy(update={"ally": FactionName.HARKONNEN})
            if p.faction == FactionName.ATREIDES
            else p.model_copy(update={"ally": FactionName.ATREIDES})
            for p in game.players
        ]
        game = game.model_copy(update={"players": new_players})

        # Atreides takes 2, Harkonnen takes 2
        game = _give_strongholds(game, FactionName.ATREIDES, shs[:2])
        game = _give_strongholds(game, FactionName.HARKONNEN, shs[2:4])
        game = _at_mentat(game)

        result = advance_phase(game)

        assert result.is_game_over is True
        assert result.winner in (FactionName.ATREIDES, FactionName.HARKONNEN)
        assert result.ally_winner in (FactionName.ATREIDES, FactionName.HARKONNEN)
        assert result.winner != result.ally_winner
        assert "together" in result.phase_messages[0].lower() or "alliance" in result.phase_messages[0].lower()

    def test_allied_3_strongholds_does_not_win(self):
        """An alliance needs 4 strongholds — 3 is not enough."""
        from backend.app.data.territories import STRONGHOLD_NAMES
        shs = list(STRONGHOLD_NAMES)[:3]
        game = _make_game(FactionName.ATREIDES, FactionName.HARKONNEN, mode=GameMode.BASIC)

        new_players = [
            p.model_copy(update={"ally": FactionName.HARKONNEN})
            if p.faction == FactionName.ATREIDES
            else p.model_copy(update={"ally": FactionName.ATREIDES})
            for p in game.players
        ]
        game = game.model_copy(update={"players": new_players})
        game = _give_strongholds(game, FactionName.ATREIDES, shs[:2])
        game = _give_strongholds(game, FactionName.HARKONNEN, shs[2:3])
        game = _at_mentat(game)

        result = advance_phase(game)
        assert result.is_game_over is False

    def test_win_message_includes_winner_name(self):
        """Victory phase_messages should name the winning faction."""
        from backend.app.data.territories import STRONGHOLD_NAMES
        shs = list(STRONGHOLD_NAMES)[:3]
        game = _make_game(FactionName.ATREIDES, FactionName.HARKONNEN, mode=GameMode.BASIC)
        game = _give_strongholds(game, FactionName.ATREIDES, shs)
        game = _at_mentat(game)

        result = advance_phase(game)
        assert "Atreides" in result.phase_messages[0]


# ---------------------------------------------------------------------------
# Fremen Special Victory
# ---------------------------------------------------------------------------

class TestFremenSpecialVictory:
    FREMEN_SIETCHS = ["Sietch Tabr", "Habbanya Sietch", "Tuek's Sietch"]

    def test_fremen_win_with_3_sietchs_no_ally(self):
        """Fremen win their special victory (Advanced) controlling the 3 Fremen sietchs."""
        game = _make_game(FactionName.FREMEN, FactionName.ATREIDES, mode=GameMode.ADVANCED)
        game = _give_strongholds(game, FactionName.FREMEN, self.FREMEN_SIETCHS)
        game = _at_mentat(game)

        result = advance_phase(game)

        assert result.is_game_over is True
        assert result.winner == FactionName.FREMEN
        assert result.ally_winner is None
        assert "Fremen" in result.phase_messages[0]

    def test_fremen_no_special_win_with_ally(self):
        """
        Fremen special victory is forfeited if they have an ally.
        When Fremen are allied, only the standard 4-stronghold alliance check applies.
        Clear all non-Fremen stronghold forces so the alliance has exactly 3 strongholds —
        not enough to win via the standard alliance check either.
        """
        from backend.app.data.territories import STRONGHOLD_NAMES
        game = _make_game(FactionName.FREMEN, FactionName.ATREIDES, mode=GameMode.ADVANCED)

        # Give Fremen the 3 sietchs, and strip all forces from every other stronghold
        # so the alliance can't reach 4 uncontested strongholds
        all_sh = list(STRONGHOLD_NAMES)
        new_players = []
        for p in game.players:
            # Remove all forces from strongholds
            no_sh = [fg for fg in p.forces_on_board if fg.territory_name not in all_sh]
            if p.faction == FactionName.FREMEN:
                added = [
                    ForceGroup(territory_name=sh, sector=0, regular_count=1)
                    for sh in self.FREMEN_SIETCHS
                ]
                new_players.append(p.model_copy(update={"forces_on_board": no_sh + added}))
            else:
                new_players.append(p.model_copy(update={"forces_on_board": no_sh}))
        game = game.model_copy(update={"players": new_players})

        # Give Fremen an ally
        new_players2 = [
            p.model_copy(update={"ally": FactionName.ATREIDES})
            if p.faction == FactionName.FREMEN
            else p.model_copy(update={"ally": FactionName.FREMEN})
            for p in game.players
        ]
        game = game.model_copy(update={"players": new_players2})
        game = _at_mentat(game)

        result = advance_phase(game)

        # Fremen special check skipped (has ally).
        # Alliance has only 3 strongholds (< 4 needed) → no win
        assert result.is_game_over is False

    def test_fremen_no_special_win_in_basic_mode(self):
        """Fremen special victory only exists in Advanced mode."""
        game = _make_game(FactionName.FREMEN, FactionName.ATREIDES, mode=GameMode.BASIC)
        game = _give_strongholds(game, FactionName.FREMEN, self.FREMEN_SIETCHS)
        game = _at_mentat(game)

        result = advance_phase(game)

        # Standard win condition: Fremen control 3 strongholds — wins via normal check
        assert result.is_game_over is True
        assert result.winner == FactionName.FREMEN

    def test_fremen_special_victory_takes_priority_over_other_faction(self):
        """
        If both Fremen (special) and another faction (standard) would win
        simultaneously, Fremen's special victory takes precedence.
        """
        from backend.app.data.territories import STRONGHOLD_NAMES
        other_shs = [s for s in STRONGHOLD_NAMES if s not in self.FREMEN_SIETCHS][:3]

        game = _make_game(FactionName.FREMEN, FactionName.ATREIDES, mode=GameMode.ADVANCED)
        game = _give_strongholds(game, FactionName.FREMEN, self.FREMEN_SIETCHS)
        game = _give_strongholds(game, FactionName.ATREIDES, other_shs)
        game = _at_mentat(game)

        result = advance_phase(game)

        # Fremen special check runs before standard stronghold check
        assert result.is_game_over is True
        assert result.winner == FactionName.FREMEN

    def test_fremen_needs_all_3_sietchs(self):
        """Fremen must control all 3 sietchs — 2 is not enough."""
        game = _make_game(FactionName.FREMEN, FactionName.ATREIDES, mode=GameMode.ADVANCED)
        game = _give_strongholds(game, FactionName.FREMEN, self.FREMEN_SIETCHS[:2])
        game = _at_mentat(game)

        result = advance_phase(game)
        assert result.is_game_over is False


# ---------------------------------------------------------------------------
# Bene Gesserit Prediction Victory
# ---------------------------------------------------------------------------

class TestBGPredictionVictory:

    def _bg_game_with_prediction(self, predicted_faction: FactionName, predicted_turn: int):
        """Helper: 3-player Advanced game with BG's prediction set."""
        game = _make_game(
            FactionName.BENE_GESSERIT,
            FactionName.ATREIDES,
            FactionName.FREMEN,
            mode=GameMode.ADVANCED,
        )
        prediction = Prediction(faction=predicted_faction, turn=predicted_turn)
        new_players = [
            p.model_copy(update={"prediction": prediction})
            if p.faction == FactionName.BENE_GESSERIT
            else p
            for p in game.players
        ]
        return game.model_copy(update={"players": new_players})

    def test_bg_wins_when_prediction_matches(self):
        """BG wins when predicted faction wins on predicted turn."""
        from backend.app.data.territories import STRONGHOLD_NAMES
        shs = list(STRONGHOLD_NAMES)[:3]

        game = self._bg_game_with_prediction(FactionName.ATREIDES, predicted_turn=3)
        game = game.model_copy(update={"current_turn": 3})
        game = _give_strongholds(game, FactionName.ATREIDES, shs)
        game = _at_mentat(game)

        result = advance_phase(game)

        assert result.is_game_over is True
        assert result.winner == FactionName.BENE_GESSERIT
        assert result.bg_prediction_revealed is True
        assert "Bene Gesserit" in result.phase_messages[0]
        assert "prediction" in result.phase_messages[0].lower()

    def test_bg_wins_before_predicted_faction(self):
        """BG prediction takes precedence — BG wins even though Atreides would normally win."""
        from backend.app.data.territories import STRONGHOLD_NAMES
        shs = list(STRONGHOLD_NAMES)[:3]

        game = self._bg_game_with_prediction(FactionName.ATREIDES, predicted_turn=1)
        game = _give_strongholds(game, FactionName.ATREIDES, shs)
        game = _at_mentat(game)

        result = advance_phase(game)

        assert result.winner == FactionName.BENE_GESSERIT  # Not Atreides

    def test_bg_does_not_win_wrong_turn(self):
        """BG prediction fails if the turn doesn't match, even if faction wins."""
        from backend.app.data.territories import STRONGHOLD_NAMES
        shs = list(STRONGHOLD_NAMES)[:3]

        game = self._bg_game_with_prediction(FactionName.ATREIDES, predicted_turn=5)
        game = game.model_copy(update={"current_turn": 3})
        game = _give_strongholds(game, FactionName.ATREIDES, shs)
        game = _at_mentat(game)

        result = advance_phase(game)

        # Atreides wins normally since BG prediction turn doesn't match
        assert result.winner == FactionName.ATREIDES

    def test_bg_does_not_win_wrong_faction(self):
        """BG prediction fails if a different faction wins."""
        from backend.app.data.territories import STRONGHOLD_NAMES
        shs = list(STRONGHOLD_NAMES)[:3]

        # BG predicted Atreides, but Fremen wins
        game = self._bg_game_with_prediction(FactionName.ATREIDES, predicted_turn=1)
        game = _give_strongholds(game, FactionName.FREMEN, shs)
        game = _at_mentat(game)

        result = advance_phase(game)

        assert result.winner == FactionName.FREMEN
        assert result.winner != FactionName.BENE_GESSERIT

    def test_bg_prediction_not_active_in_basic_mode(self):
        """BG prediction win condition only applies in Advanced mode."""
        game = _make_game(
            FactionName.BENE_GESSERIT, FactionName.ATREIDES, mode=GameMode.BASIC
        )
        from backend.app.data.territories import STRONGHOLD_NAMES
        shs = list(STRONGHOLD_NAMES)[:3]
        game = _give_strongholds(game, FactionName.ATREIDES, shs)
        game = _at_mentat(game)

        result = advance_phase(game)

        # No BG prediction in Basic — Atreides wins normally
        assert result.winner == FactionName.ATREIDES


# ---------------------------------------------------------------------------
# Spacing Guild Alternate Victory
# ---------------------------------------------------------------------------

class TestGuildAlternateVictory:

    def test_guild_wins_at_turn_10_no_other_winner(self):
        """Guild wins at turn 10 in Advanced mode if no faction controls strongholds."""
        game = _make_game(
            FactionName.SPACING_GUILD, FactionName.ATREIDES, mode=GameMode.ADVANCED
        )
        game = game.model_copy(update={"current_turn": MAX_TURNS})
        game = _at_mentat(game)

        result = advance_phase(game)

        assert result.is_game_over is True
        assert result.winner == FactionName.SPACING_GUILD
        assert "Guild" in result.phase_messages[0]

    def test_guild_does_not_win_before_turn_10(self):
        """Guild alternate victory only triggers at turn 10."""
        game = _make_game(
            FactionName.SPACING_GUILD, FactionName.ATREIDES, mode=GameMode.ADVANCED
        )
        game = game.model_copy(update={"current_turn": 8})
        game = _at_mentat(game)

        result = advance_phase(game)

        assert result.is_game_over is False

    def test_guild_does_not_win_in_basic_mode(self):
        """Guild alternate victory is Advanced-only."""
        game = _make_game(
            FactionName.SPACING_GUILD, FactionName.ATREIDES, mode=GameMode.BASIC
        )
        game = game.model_copy(update={"current_turn": MAX_TURNS})
        game = _at_mentat(game)

        result = advance_phase(game)

        # No winner (guild doesn't win in Basic, no faction has 3 strongholds)
        assert result.winner is None
        assert result.is_game_over is True

    def test_guild_does_not_win_if_faction_has_strongholds(self):
        """Standard stronghold winner takes precedence over Guild alternate victory."""
        from backend.app.data.territories import STRONGHOLD_NAMES
        shs = list(STRONGHOLD_NAMES)[:3]

        game = _make_game(
            FactionName.SPACING_GUILD, FactionName.ATREIDES, mode=GameMode.ADVANCED
        )
        game = game.model_copy(update={"current_turn": MAX_TURNS})
        game = _give_strongholds(game, FactionName.ATREIDES, shs)
        game = _at_mentat(game)

        result = advance_phase(game)

        assert result.winner == FactionName.ATREIDES  # Not Guild

    def test_guild_wins_via_advance_turn_at_limit(self):
        """advance_turn() also triggers Guild victory when game exceeds turn 10."""
        game = _make_game(
            FactionName.SPACING_GUILD, FactionName.ATREIDES, mode=GameMode.ADVANCED
        )
        game = game.model_copy(update={"current_turn": MAX_TURNS})

        result = advance_turn(game)

        assert result.is_game_over is True
        assert result.winner == FactionName.SPACING_GUILD


# ---------------------------------------------------------------------------
# No victor (turn limit, no Guild)
# ---------------------------------------------------------------------------

class TestNoVictorTurnLimit:

    def test_no_victor_when_game_ends_basic(self):
        """Basic mode: at turn 10 with no stronghold winner, game ends with no victor."""
        game = _make_game(FactionName.ATREIDES, FactionName.HARKONNEN, mode=GameMode.BASIC)
        game = game.model_copy(update={"current_turn": MAX_TURNS})
        game = _at_mentat(game)

        result = advance_phase(game)

        assert result.is_game_over is True
        assert result.winner is None

    def test_no_victor_message_generated(self):
        """A message is generated when the game ends with no winner."""
        game = _make_game(FactionName.ATREIDES, FactionName.HARKONNEN, mode=GameMode.BASIC)
        game = game.model_copy(update={"current_turn": MAX_TURNS})
        game = _at_mentat(game)

        result = advance_phase(game)
        assert len(result.phase_messages) > 0
