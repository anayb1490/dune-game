"""
Tests for special treachery card actions (special_cards.py).

Covers:
  - Karama basic (block a faction)
  - Karama faction power (Atreides, Emperor, Fremen, Guild, Harkonnen, BG)
  - Tleilaxu Ghola
  - Family Atomics
  - Hajr
  - Weather Control
"""

from __future__ import annotations

import pytest

from ..app.models.card import (
    SpecialCardType,
    TreacheryCard,
    TreacheryCardType,
    WeaponType,
)
from ..app.models.faction import FactionName
from ..app.models.game_state import (
    ActiveBattle,
    BattlePlan,
    GameMode,
    GamePhase,
    GameState,
)
from ..app.models.leader import Leader, LeaderStatus
from ..app.models.player import ForceGroup, Player
from ..app.services.game.special_cards import (
    is_karama_blocked,
    play_family_atomics,
    play_hajr,
    play_karama_block,
    play_karama_faction_power,
    play_tleilaxu_ghola,
    play_weather_control,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _karama_card(cid: str = "k1") -> TreacheryCard:
    return TreacheryCard(
        id=cid, name="Karama",
        card_type=TreacheryCardType.SPECIAL,
        special_type=SpecialCardType.KARAMA,
    )


def _worthless_card(cid: str = "w1") -> TreacheryCard:
    return TreacheryCard(id=cid, name="Worthless", card_type=TreacheryCardType.WORTHLESS)


def _ghola_card(cid: str = "g1") -> TreacheryCard:
    return TreacheryCard(
        id=cid, name="Tleilaxu Ghola",
        card_type=TreacheryCardType.SPECIAL,
        special_type=SpecialCardType.TLEILAXU_GHOLA,
    )


def _atomics_card(cid: str = "fa1") -> TreacheryCard:
    return TreacheryCard(
        id=cid, name="Family Atomics",
        card_type=TreacheryCardType.SPECIAL,
        special_type=SpecialCardType.FAMILY_ATOMICS,
        is_advanced=True,
    )


def _hajr_card(cid: str = "h1") -> TreacheryCard:
    return TreacheryCard(
        id=cid, name="Hajr",
        card_type=TreacheryCardType.SPECIAL,
        special_type=SpecialCardType.HAJR,
    )


def _weather_card(cid: str = "wc1") -> TreacheryCard:
    return TreacheryCard(
        id=cid, name="Weather Control",
        card_type=TreacheryCardType.SPECIAL,
        special_type=SpecialCardType.WEATHER_CONTROL,
        is_advanced=True,
    )


def _poison_card(cid: str = "pw1") -> TreacheryCard:
    return TreacheryCard(
        id=cid, name="Poison",
        card_type=TreacheryCardType.WEAPON,
        weapon_type=WeaponType.POISON,
    )


def _make_player(
    pid: str,
    faction: FactionName,
    spice: int = 10,
    hand: list[TreacheryCard] | None = None,
    forces_in_tanks: int = 0,
    forces_in_reserve: int = 10,
    leaders: list[Leader] | None = None,
    forces_on_board: list[ForceGroup] | None = None,
) -> Player:
    return Player(
        id=pid,
        name=faction.value,
        faction=faction,
        spice=spice,
        treachery_hand=hand or [],
        forces_in_tanks=forces_in_tanks,
        forces_in_reserve=forces_in_reserve,
        leaders=leaders or [],
        forces_on_board=forces_on_board or [],
    )


def _make_leader(lid: str, name: str, strength: int = 3,
                 status: LeaderStatus = LeaderStatus.IN_TANKS) -> Leader:
    return Leader(id=lid, name=name, strength=strength, status=status,
                  faction=FactionName.ATREIDES)


def _base_game(
    players: list[Player],
    mode: GameMode = GameMode.ADVANCED,
    phase: GamePhase = GamePhase.BIDDING,
    current_turn: int = 2,
) -> GameState:
    from ..app.data.territories import TERRITORIES
    territories = {n: t.model_copy() for n, t in TERRITORIES.items()}
    return GameState(
        id="test",
        mode=mode,
        players=players,
        current_phase=phase,
        current_player_index=0,
        storm_sector=5,
        territories=territories,
        spice_bank=100,
        current_turn=current_turn,
    )


# ===========================================================================
# Karama — Basic Block
# ===========================================================================

class TestKaramaBlock:

    def test_blocks_target_faction(self):
        """Karama sets karama_blocked_faction to target for this turn."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_karama_card()])
        target = _make_player("p2", FactionName.HARKONNEN)
        game = _base_game([player, target])

        result = play_karama_block(game, "p1", FactionName.HARKONNEN)
        assert result.karama_blocked_faction == FactionName.HARKONNEN
        assert result.karama_blocked_turn == game.current_turn

    def test_card_discarded_after_use(self):
        """Karama card leaves the hand and enters treachery_discard."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_karama_card("k1")])
        target = _make_player("p2", FactionName.HARKONNEN)
        game = _base_game([player, target])

        result = play_karama_block(game, "p1", FactionName.HARKONNEN)
        atreides = next(p for p in result.players if p.id == "p1")
        assert not any(c.id == "k1" for c in atreides.treachery_hand)
        assert any(c.id == "k1" for c in result.treachery_discard)

    def test_cannot_block_own_faction(self):
        """Cannot use Karama against yourself."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_karama_card()])
        game = _base_game([player])
        with pytest.raises(ValueError, match="own faction"):
            play_karama_block(game, "p1", FactionName.ATREIDES)

    def test_no_karama_raises(self):
        """Raises if player has no Karama card."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_poison_card()])
        target = _make_player("p2", FactionName.HARKONNEN)
        game = _base_game([player, target])
        with pytest.raises(ValueError, match="No Karama"):
            play_karama_block(game, "p1", FactionName.HARKONNEN)

    def test_bg_worthless_substitution_advanced(self):
        """BG can use a Worthless card as Karama in Advanced mode."""
        player = _make_player("p1", FactionName.BENE_GESSERIT, hand=[_worthless_card("w1")])
        target = _make_player("p2", FactionName.HARKONNEN)
        game = _base_game([player, target], mode=GameMode.ADVANCED)

        result = play_karama_block(game, "p1", FactionName.HARKONNEN)
        assert result.karama_blocked_faction == FactionName.HARKONNEN
        # Worthless card should be discarded
        bg = next(p for p in result.players if p.id == "p1")
        assert len(bg.treachery_hand) == 0

    def test_bg_worthless_not_valid_in_basic(self):
        """BG Worthless substitution only works in Advanced mode."""
        player = _make_player("p1", FactionName.BENE_GESSERIT, hand=[_worthless_card("w1")])
        target = _make_player("p2", FactionName.HARKONNEN)
        game = _base_game([player, target], mode=GameMode.BASIC)
        with pytest.raises(ValueError, match="No Karama"):
            play_karama_block(game, "p1", FactionName.HARKONNEN)

    def test_is_karama_blocked_returns_true(self):
        """is_karama_blocked returns True for the blocked faction this turn."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_karama_card()])
        target = _make_player("p2", FactionName.HARKONNEN)
        game = _base_game([player, target])
        result = play_karama_block(game, "p1", FactionName.HARKONNEN)
        assert is_karama_blocked(result, FactionName.HARKONNEN) is True
        assert is_karama_blocked(result, FactionName.ATREIDES) is False

    def test_karama_block_expires_next_turn(self):
        """A Karama block from a previous turn is not active."""
        game = _base_game(
            [_make_player("p1", FactionName.ATREIDES)],
            current_turn=3,
        )
        game = game.model_copy(update={
            "karama_blocked_faction": FactionName.HARKONNEN,
            "karama_blocked_turn": 2,  # previous turn
        })
        assert is_karama_blocked(game, FactionName.HARKONNEN) is False


# ===========================================================================
# Karama — Faction Powers (Advanced)
# ===========================================================================

class TestKaramaFactionPower:

    def test_basic_mode_raises(self):
        """Faction Karama powers require Advanced mode."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_karama_card()])
        game = _base_game([player], mode=GameMode.BASIC)
        with pytest.raises(ValueError, match="Advanced mode"):
            play_karama_faction_power(game, "p1", {})

    # -- Emperor --

    def test_emperor_revives_forces(self):
        """Emperor Karama revives up to 3 forces from tanks."""
        player = _make_player(
            "p1", FactionName.EMPEROR,
            hand=[_karama_card()],
            forces_in_tanks=5,
            forces_in_reserve=2,
        )
        game = _base_game([player])
        result = play_karama_faction_power(game, "p1", {"force_count": 3})
        emp = next(p for p in result.players if p.id == "p1")
        assert emp.forces_in_tanks == 2
        assert emp.forces_in_reserve == 5

    def test_emperor_revive_too_many_raises(self):
        """Emperor Karama cannot revive more than 3 forces."""
        player = _make_player("p1", FactionName.EMPEROR, hand=[_karama_card()], forces_in_tanks=5)
        game = _base_game([player])
        with pytest.raises(ValueError, match="at most 3"):
            play_karama_faction_power(game, "p1", {"force_count": 4})

    def test_emperor_revives_leader(self):
        """Emperor Karama revives a single leader from tanks."""
        ldr = _make_leader("l1", "Zum Galis", status=LeaderStatus.IN_TANKS)
        player = _make_player("p1", FactionName.EMPEROR, hand=[_karama_card()], leaders=[ldr])
        game = _base_game([player])
        result = play_karama_faction_power(game, "p1", {"leader_id": "l1"})
        emp = next(p for p in result.players if p.id == "p1")
        revived = next(l for l in emp.leaders if l.id == "l1")
        assert revived.status == LeaderStatus.AVAILABLE

    def test_emperor_cant_choose_both(self):
        """Emperor Karama: cannot request leader AND forces simultaneously."""
        ldr = _make_leader("l1", "Zum Galis", status=LeaderStatus.IN_TANKS)
        player = _make_player(
            "p1", FactionName.EMPEROR,
            hand=[_karama_card()],
            forces_in_tanks=3,
            leaders=[ldr],
        )
        game = _base_game([player])
        with pytest.raises(ValueError, match="Choose either"):
            play_karama_faction_power(game, "p1", {"leader_id": "l1", "force_count": 2})

    # -- Guild --

    def test_guild_blocks_target_shipment(self):
        """Guild Karama blocks the target faction's shipment this turn."""
        player = _make_player("p1", FactionName.SPACING_GUILD, hand=[_karama_card()])
        target = _make_player("p2", FactionName.ATREIDES)
        game = _base_game([player, target])
        result = play_karama_faction_power(game, "p1", {"target_faction": "atreides"})
        assert result.karama_blocked_faction == FactionName.ATREIDES
        assert result.karama_blocked_turn == game.current_turn

    def test_guild_requires_target(self):
        """Guild Karama raises without target_faction."""
        player = _make_player("p1", FactionName.SPACING_GUILD, hand=[_karama_card()])
        game = _base_game([player])
        with pytest.raises(ValueError, match="target_faction is required"):
            play_karama_faction_power(game, "p1", {})

    # -- Harkonnen --

    def test_harkonnen_card_exchange(self):
        """Harkonnen Karama: 1-for-1 card exchange with another player."""
        poison = _poison_card("pw1")
        player = _make_player(
            "p1", FactionName.HARKONNEN,
            hand=[_karama_card("k1"), poison],
        )
        worthless = _worthless_card("w2")
        target = _make_player("p2", FactionName.ATREIDES, hand=[worthless])
        game = _base_game([player, target])
        result = play_karama_faction_power(game, "p1", {
            "target_faction": "atreides",
            "take_card_ids": ["w2"],
            "give_card_ids": ["pw1"],
        })
        hark = next(p for p in result.players if p.id == "p1")
        atr  = next(p for p in result.players if p.id == "p2")
        assert any(c.id == "w2" for c in hark.treachery_hand)
        assert any(c.id == "pw1" for c in atr.treachery_hand)

    def test_harkonnen_unequal_exchange_raises(self):
        """Harkonnen Karama: take/give counts must match."""
        poison = _poison_card("pw1")
        player = _make_player(
            "p1", FactionName.HARKONNEN,
            hand=[_karama_card("k1"), poison],
        )
        target = _make_player("p2", FactionName.ATREIDES, hand=[_worthless_card("w1")])
        game = _base_game([player, target])
        with pytest.raises(ValueError, match="1-for-1"):
            play_karama_faction_power(game, "p1", {
                "target_faction": "atreides",
                "take_card_ids": ["w1"],
                "give_card_ids": [],
            })

    # -- Atreides --

    def test_atreides_reveals_battle_plan(self):
        """Atreides Karama: stores opponent's plan on ActiveBattle."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_karama_card()])
        opponent = _make_player("p2", FactionName.HARKONNEN)
        defender_plan = BattlePlan(
            faction=FactionName.HARKONNEN,
            forces_dialed=3,
        )
        active_battle = ActiveBattle(
            territory_name="Arrakeen",
            sector=1,
            attacker_faction=FactionName.ATREIDES,
            defender_faction=FactionName.HARKONNEN,
            defender_plan=defender_plan,
        )
        game = _base_game([player, opponent])
        game = game.model_copy(update={"active_battle": active_battle})
        result = play_karama_faction_power(game, "p1", {"target_faction": "harkonnen"})
        assert result.active_battle.atreides_karama_revealed_faction == FactionName.HARKONNEN
        assert result.active_battle.atreides_karama_revealed_plan.forces_dialed == 3

    def test_atreides_no_plan_raises(self):
        """Atreides Karama raises if the target hasn't submitted a plan."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_karama_card()])
        opponent = _make_player("p2", FactionName.HARKONNEN)
        active_battle = ActiveBattle(
            territory_name="Arrakeen",
            sector=1,
            attacker_faction=FactionName.ATREIDES,
            defender_faction=FactionName.HARKONNEN,
        )
        game = _base_game([player, opponent])
        game = game.model_copy(update={"active_battle": active_battle})
        with pytest.raises(ValueError, match="not yet submitted"):
            play_karama_faction_power(game, "p1", {"target_faction": "harkonnen"})

    def test_atreides_no_active_battle_raises(self):
        """Atreides Karama raises outside of an active battle."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_karama_card()])
        game = _base_game([player])
        with pytest.raises(ValueError, match="active battle"):
            play_karama_faction_power(game, "p1", {"target_faction": "harkonnen"})

    # -- BG --

    def test_bg_no_unique_power_discards_card(self):
        """BG has no unique Karama power; card is simply discarded."""
        player = _make_player("p1", FactionName.BENE_GESSERIT, hand=[_karama_card("k1")])
        game = _base_game([player])
        result = play_karama_faction_power(game, "p1", {})
        bg = next(p for p in result.players if p.id == "p1")
        assert not any(c.id == "k1" for c in bg.treachery_hand)
        assert any(c.id == "k1" for c in result.treachery_discard)

    # -- Fremen --

    def test_fremen_karama_destroys_forces_and_spice(self):
        """Fremen Karama: destroys non-Fremen forces and spice in a sand territory."""
        fremen = _make_player("p1", FactionName.FREMEN, hand=[_karama_card()])
        enemy = _make_player(
            "p2", FactionName.ATREIDES,
            forces_on_board=[ForceGroup(territory_name="Hagga Basin", sector=12, regular_count=3)],
        )
        game = _base_game([fremen, enemy])
        game = game.model_copy(update={
            "territories": {
                **game.territories,
                "Hagga Basin": game.territories["Hagga Basin"].model_copy(
                    update={"current_spice": 4}
                ),
            }
        })
        result = play_karama_faction_power(game, "p1", {"territory_name": "Hagga Basin"})
        atr = next(p for p in result.players if p.id == "p2")
        assert atr.forces_in_tanks == 3
        assert not any(fg.territory_name == "Hagga Basin" for fg in atr.forces_on_board)
        assert result.territories["Hagga Basin"].current_spice == 0
        assert result.fremen_sandworm_ride_territory == "Hagga Basin"

    def test_fremen_karama_non_sand_raises(self):
        """Fremen Karama raises if territory is not sand type."""
        fremen = _make_player("p1", FactionName.FREMEN, hand=[_karama_card()])
        game = _base_game([fremen])
        with pytest.raises(ValueError, match="sand territory"):
            play_karama_faction_power(game, "p1", {"territory_name": "Arrakeen"})


# ===========================================================================
# Tleilaxu Ghola
# ===========================================================================

class TestTleilaxuGhola:

    def test_revive_leader(self):
        """Ghola revives one dead leader from tanks."""
        ldr = _make_leader("l1", "Thufir Hawat", status=LeaderStatus.IN_TANKS)
        player = _make_player("p1", FactionName.ATREIDES, hand=[_ghola_card()], leaders=[ldr])
        game = _base_game([player])
        result = play_tleilaxu_ghola(game, "p1", leader_id="l1")
        atr = next(p for p in result.players if p.id == "p1")
        revived = next(l for l in atr.leaders if l.id == "l1")
        assert revived.status == LeaderStatus.AVAILABLE

    def test_revive_forces(self):
        """Ghola revives up to 5 forces from tanks."""
        player = _make_player(
            "p1", FactionName.ATREIDES,
            hand=[_ghola_card()],
            forces_in_tanks=8,
            forces_in_reserve=2,
        )
        game = _base_game([player])
        result = play_tleilaxu_ghola(game, "p1", force_count=5)
        atr = next(p for p in result.players if p.id == "p1")
        assert atr.forces_in_tanks == 3
        assert atr.forces_in_reserve == 7

    def test_revive_too_many_forces_raises(self):
        """Ghola cannot revive more than 5 forces."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_ghola_card()], forces_in_tanks=8)
        game = _base_game([player])
        with pytest.raises(ValueError, match="at most 5"):
            play_tleilaxu_ghola(game, "p1", force_count=6)

    def test_cant_choose_both_raises(self):
        """Ghola: cannot request leader AND forces simultaneously."""
        ldr = _make_leader("l1", "Thufir Hawat", status=LeaderStatus.IN_TANKS)
        player = _make_player(
            "p1", FactionName.ATREIDES,
            hand=[_ghola_card()],
            forces_in_tanks=3,
            leaders=[ldr],
        )
        game = _base_game([player])
        with pytest.raises(ValueError, match="either"):
            play_tleilaxu_ghola(game, "p1", leader_id="l1", force_count=2)

    def test_leader_not_in_tanks_raises(self):
        """Ghola raises if the named leader is not in the tanks."""
        ldr = _make_leader("l1", "Thufir Hawat", status=LeaderStatus.AVAILABLE)
        player = _make_player("p1", FactionName.ATREIDES, hand=[_ghola_card()], leaders=[ldr])
        game = _base_game([player])
        with pytest.raises(ValueError, match="not in the Tleilaxu Tanks"):
            play_tleilaxu_ghola(game, "p1", leader_id="l1")

    def test_no_card_raises(self):
        """Ghola raises if player has no Tleilaxu Ghola card."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_karama_card()])
        game = _base_game([player])
        with pytest.raises(ValueError, match="No Tleilaxu Ghola"):
            play_tleilaxu_ghola(game, "p1", force_count=1)

    def test_card_discarded_after_use(self):
        """Ghola card is discarded after use."""
        player = _make_player(
            "p1", FactionName.ATREIDES,
            hand=[_ghola_card("g1")],
            forces_in_tanks=3,
        )
        game = _base_game([player])
        result = play_tleilaxu_ghola(game, "p1", force_count=2)
        atr = next(p for p in result.players if p.id == "p1")
        assert not any(c.id == "g1" for c in atr.treachery_hand)
        assert any(c.id == "g1" for c in result.treachery_discard)


# ===========================================================================
# Family Atomics
# ===========================================================================

class TestFamilyAtomics:

    def test_destroys_shield_wall(self):
        """Family Atomics sets shield_wall_destroyed to True."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_atomics_card()])
        game = _base_game([player])
        result = play_family_atomics(game, "p1")
        assert result.shield_wall_destroyed is True

    def test_non_fremen_forces_destroyed(self):
        """Non-Fremen forces in the Shield Wall are sent to tanks."""
        enemy = _make_player(
            "p2", FactionName.HARKONNEN,
            forces_on_board=[ForceGroup(
                territory_name="Shield Wall", sector=4, regular_count=4
            )],
        )
        player = _make_player("p1", FactionName.ATREIDES, hand=[_atomics_card()])
        game = _base_game([player, enemy])
        result = play_family_atomics(game, "p1")
        hark = next(p for p in result.players if p.id == "p2")
        assert hark.forces_in_tanks == 4
        assert not any(fg.territory_name == "Shield Wall" for fg in hark.forces_on_board)

    def test_fremen_survive(self):
        """Fremen forces in the Shield Wall survive Family Atomics."""
        fremen = _make_player(
            "p2", FactionName.FREMEN,
            forces_on_board=[ForceGroup(
                territory_name="Shield Wall", sector=4, regular_count=3
            )],
        )
        player = _make_player("p1", FactionName.ATREIDES, hand=[_atomics_card()])
        game = _base_game([player, fremen])
        result = play_family_atomics(game, "p1")
        frm = next(p for p in result.players if p.id == "p2")
        assert frm.forces_in_tanks == 0
        assert any(fg.territory_name == "Shield Wall" for fg in frm.forces_on_board)

    def test_spice_returned_to_bank(self):
        """Spice in the Shield Wall is returned to the bank."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_atomics_card()])
        game = _base_game([player])
        game = game.model_copy(update={
            "territories": {
                **game.territories,
                "Shield Wall": game.territories["Shield Wall"].model_copy(
                    update={"current_spice": 6}
                ),
            },
            "spice_bank": 50,
        })
        result = play_family_atomics(game, "p1")
        assert result.spice_bank == 56
        assert result.territories["Shield Wall"].current_spice == 0

    def test_basic_mode_raises(self):
        """Family Atomics is Advanced-only."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_atomics_card()])
        game = _base_game([player], mode=GameMode.BASIC)
        with pytest.raises(ValueError, match="Advanced-only"):
            play_family_atomics(game, "p1")

    def test_already_destroyed_raises(self):
        """Raises if the Shield Wall has already been destroyed."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_atomics_card()])
        game = _base_game([player])
        game = game.model_copy(update={"shield_wall_destroyed": True})
        with pytest.raises(ValueError, match="already been destroyed"):
            play_family_atomics(game, "p1")

    def test_no_card_raises(self):
        """Raises if player has no Family Atomics card."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_karama_card()])
        game = _base_game([player])
        with pytest.raises(ValueError, match="No Family Atomics"):
            play_family_atomics(game, "p1")

    def test_card_discarded_after_use(self):
        """Family Atomics card is discarded after use."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_atomics_card("fa1")])
        game = _base_game([player])
        result = play_family_atomics(game, "p1")
        atr = next(p for p in result.players if p.id == "p1")
        assert not any(c.id == "fa1" for c in atr.treachery_hand)
        assert any(c.id == "fa1" for c in result.treachery_discard)


# ===========================================================================
# Hajr
# ===========================================================================

class TestHajr:

    def test_sets_hajr_faction(self):
        """Hajr sets hajr_extra_move_faction to the playing faction."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_hajr_card()])
        game = _base_game([player], phase=GamePhase.SHIPMENT_AND_MOVEMENT)
        result = play_hajr(game, "p1")
        assert result.hajr_extra_move_faction == FactionName.ATREIDES

    def test_card_discarded_after_use(self):
        """Hajr card is discarded after use."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_hajr_card("h1")])
        game = _base_game([player], phase=GamePhase.SHIPMENT_AND_MOVEMENT)
        result = play_hajr(game, "p1")
        atr = next(p for p in result.players if p.id == "p1")
        assert not any(c.id == "h1" for c in atr.treachery_hand)
        assert any(c.id == "h1" for c in result.treachery_discard)

    def test_wrong_phase_raises(self):
        """Hajr can only be played during Shipment & Movement."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_hajr_card()])
        game = _base_game([player], phase=GamePhase.BIDDING)
        with pytest.raises(ValueError, match="Shipment & Movement"):
            play_hajr(game, "p1")

    def test_no_card_raises(self):
        """Raises if player has no Hajr card."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_karama_card()])
        game = _base_game([player], phase=GamePhase.SHIPMENT_AND_MOVEMENT)
        with pytest.raises(ValueError, match="No Hajr"):
            play_hajr(game, "p1")


# ===========================================================================
# Weather Control
# ===========================================================================

class TestWeatherControl:

    def test_sets_override(self):
        """Weather Control stores the override value on GameState."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_weather_card()])
        game = _base_game([player])
        result = play_weather_control(game, "p1", 7)
        assert result.weather_control_override == 7

    def test_zero_sectors_valid(self):
        """Weather Control can set override to 0 (storm doesn't move)."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_weather_card()])
        game = _base_game([player])
        result = play_weather_control(game, "p1", 0)
        assert result.weather_control_override == 0

    def test_max_sectors_valid(self):
        """Weather Control can set override to 10."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_weather_card()])
        game = _base_game([player])
        result = play_weather_control(game, "p1", 10)
        assert result.weather_control_override == 10

    def test_out_of_range_raises(self):
        """Weather Control raises for values outside 0-10."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_weather_card()])
        game = _base_game([player])
        with pytest.raises(ValueError, match="0 and 10"):
            play_weather_control(game, "p1", 11)

    def test_negative_raises(self):
        """Weather Control raises for negative values."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_weather_card()])
        game = _base_game([player])
        with pytest.raises(ValueError, match="0 and 10"):
            play_weather_control(game, "p1", -1)

    def test_card_discarded_after_use(self):
        """Weather Control card is discarded after use."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_weather_card("wc1")])
        game = _base_game([player])
        result = play_weather_control(game, "p1", 4)
        atr = next(p for p in result.players if p.id == "p1")
        assert not any(c.id == "wc1" for c in atr.treachery_hand)
        assert any(c.id == "wc1" for c in result.treachery_discard)

    def test_no_card_raises(self):
        """Raises if player has no Weather Control card."""
        player = _make_player("p1", FactionName.ATREIDES, hand=[_karama_card()])
        game = _base_game([player])
        with pytest.raises(ValueError, match="No Weather Control"):
            play_weather_control(game, "p1", 5)

    def test_weather_control_consumed_by_storm(self):
        """Storm phase consumes the override and clears weather_control_override."""
        from ..app.services.game.storm import resolve_storm

        player = _make_player("p1", FactionName.ATREIDES, hand=[_weather_card()])
        game = _base_game([player], phase=GamePhase.STORM)
        game = game.model_copy(update={
            "weather_control_override": 3,
            "storm_sector": 10,
        })
        result = resolve_storm(game)
        assert result.weather_control_override is None
        # Storm moved exactly 3 sectors counterclockwise from sector 10
        assert result.storm_sector == 7
