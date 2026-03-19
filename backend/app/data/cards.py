"""
Static card definitions for the classic Dune board game (Avalon Hill / GF9 edition).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TREACHERY DECK  (33 cards)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Card names and types verified against original Avalon Hill / GF9 rulebook.

    Projectile weapons  ×4  (Crysknife, Maula Pistol, Stunner, Hunter-Seeker)
    Poison weapons      ×4  (Chaumas, Chaumurky, Ellaca Drug, Gom Jabbar)
    Lasgun              ×1
    Snooper defenses    ×4
    Shield defenses     ×4
    Karama              ×2
    Cheap Hero          ×2
    Cheap Heroine       ×1
    Worthless cards     ×5  (Baliset, Jubba Cloak, Kulon, La La La, Trip to Gamont)
    Special (advanced)  ×6  (Truthtrance ×2, Weather Control, Family Atomics,
                             Hajr, Tleilaxu Ghola)
    ─────────────────────
    Total               33

Basic game: exclude the 6 Advanced-only cards (is_advanced=True), leaving 27.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SPICE DECK  (26 cards)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    10 territory cards × 2 copies each = 20
    Shai-Hulud                           ×6
    ─────────────────────────────────────
    Total                                26

Territory spice amounts verified from rulebook card image (p.8) and board map.

Usage:
    from backend.app.data.cards import TREACHERY_DECK, SPICE_DECK
"""

from ..models.card import (
    DefenseType,
    SpiceCard,
    SpiceCardType,
    SpecialCardType,
    TreacheryCard,
    TreacheryCardType,
    WeaponType,
)


# =============================================================================
# TREACHERY DECK  (33 cards)
# =============================================================================

TREACHERY_DECK: list[TreacheryCard] = [

    # -------------------------------------------------------------------------
    # Projectile Weapons (×4)
    # Countered only by a Shield defense.
    # -------------------------------------------------------------------------
    TreacheryCard(
        id="tw_crysknife",
        name="Crysknife",
        card_type=TreacheryCardType.WEAPON,
        weapon_type=WeaponType.PROJECTILE,
    ),
    TreacheryCard(
        id="tw_maula_pistol",
        name="Maula Pistol",
        card_type=TreacheryCardType.WEAPON,
        weapon_type=WeaponType.PROJECTILE,
    ),
    TreacheryCard(
        id="tw_stunner",
        name="Stunner",
        card_type=TreacheryCardType.WEAPON,
        weapon_type=WeaponType.PROJECTILE,
    ),
    TreacheryCard(
        id="tw_hunter_seeker",
        name="Hunter-Seeker",
        card_type=TreacheryCardType.WEAPON,
        weapon_type=WeaponType.PROJECTILE,
    ),

    # -------------------------------------------------------------------------
    # Poison Weapons (×4)
    # Countered only by a Snooper defense.
    # -------------------------------------------------------------------------
    TreacheryCard(
        id="tw_chaumas",
        name="Chaumas",
        card_type=TreacheryCardType.WEAPON,
        weapon_type=WeaponType.POISON,
    ),
    TreacheryCard(
        id="tw_chaumurky",
        name="Chaumurky",
        card_type=TreacheryCardType.WEAPON,
        weapon_type=WeaponType.POISON,
    ),
    TreacheryCard(
        id="tw_ellaca_drug",
        name="Ellaca Drug",
        card_type=TreacheryCardType.WEAPON,
        weapon_type=WeaponType.POISON,
    ),
    TreacheryCard(
        id="tw_gom_jabbar",
        name="Gom Jabbar",
        card_type=TreacheryCardType.WEAPON,
        weapon_type=WeaponType.POISON,
    ),

    # -------------------------------------------------------------------------
    # Lasgun (×1)
    # No defense. Kills opponent's leader outright. If a Shield is also played
    # in the same battle, a nuclear explosion destroys ALL forces in the territory.
    # -------------------------------------------------------------------------
    TreacheryCard(
        id="tw_lasgun",
        name="Lasgun",
        card_type=TreacheryCardType.WEAPON,
        weapon_type=WeaponType.LASGUN,
    ),

    # -------------------------------------------------------------------------
    # Snooper Defenses (×4)
    # Blocks poison weapons.
    # -------------------------------------------------------------------------
    TreacheryCard(
        id="td_snooper_1",
        name="Snooper",
        card_type=TreacheryCardType.DEFENSE,
        defense_type=DefenseType.SNOOPER,
    ),
    TreacheryCard(
        id="td_snooper_2",
        name="Snooper",
        card_type=TreacheryCardType.DEFENSE,
        defense_type=DefenseType.SNOOPER,
    ),
    TreacheryCard(
        id="td_snooper_3",
        name="Snooper",
        card_type=TreacheryCardType.DEFENSE,
        defense_type=DefenseType.SNOOPER,
    ),
    TreacheryCard(
        id="td_snooper_4",
        name="Snooper",
        card_type=TreacheryCardType.DEFENSE,
        defense_type=DefenseType.SNOOPER,
    ),

    # -------------------------------------------------------------------------
    # Shield Defenses (×4)
    # Blocks projectile weapons. Triggers lasgun explosion if a Lasgun is played.
    # -------------------------------------------------------------------------
    TreacheryCard(
        id="td_shield_1",
        name="Shield",
        card_type=TreacheryCardType.DEFENSE,
        defense_type=DefenseType.SHIELD,
    ),
    TreacheryCard(
        id="td_shield_2",
        name="Shield",
        card_type=TreacheryCardType.DEFENSE,
        defense_type=DefenseType.SHIELD,
    ),
    TreacheryCard(
        id="td_shield_3",
        name="Shield",
        card_type=TreacheryCardType.DEFENSE,
        defense_type=DefenseType.SHIELD,
    ),
    TreacheryCard(
        id="td_shield_4",
        name="Shield",
        card_type=TreacheryCardType.DEFENSE,
        defense_type=DefenseType.SHIELD,
    ),

    # -------------------------------------------------------------------------
    # Karama (×2)
    # Cancel any one faction's special advantage for a single use, OR
    # activate your own faction's special Karama power.
    # -------------------------------------------------------------------------
    TreacheryCard(
        id="ts_karama_1",
        name="Karama",
        card_type=TreacheryCardType.SPECIAL,
        special_type=SpecialCardType.KARAMA,
    ),
    TreacheryCard(
        id="ts_karama_2",
        name="Karama",
        card_type=TreacheryCardType.SPECIAL,
        special_type=SpecialCardType.KARAMA,
    ),

    # -------------------------------------------------------------------------
    # Cheap Hero (×2) and Cheap Heroine (×1)
    # Stand-in leader with strength 0. Can be used instead of a real leader
    # in battle. Player may still play weapon + defense alongside it.
    # -------------------------------------------------------------------------
    TreacheryCard(
        id="ts_cheap_hero_1",
        name="Cheap Hero",
        card_type=TreacheryCardType.SPECIAL,
        special_type=SpecialCardType.CHEAP_HERO,
    ),
    TreacheryCard(
        id="ts_cheap_hero_2",
        name="Cheap Hero",
        card_type=TreacheryCardType.SPECIAL,
        special_type=SpecialCardType.CHEAP_HERO,
    ),
    TreacheryCard(
        id="ts_cheap_heroine",
        name="Cheap Heroine",
        card_type=TreacheryCardType.SPECIAL,
        special_type=SpecialCardType.CHEAP_HEROINE,
    ),

    # -------------------------------------------------------------------------
    # Worthless Cards (×5)
    # No combat value. Can only be discarded by playing them in a Battle Plan
    # as a weapon or defense — they provide no actual effect.
    # BG special: may use any Worthless card as a Karama in advanced play.
    # -------------------------------------------------------------------------
    TreacheryCard(
        id="tw_baliset",
        name="Baliset",
        card_type=TreacheryCardType.WORTHLESS,
    ),
    TreacheryCard(
        id="tw_jubba_cloak",
        name="Jubba Cloak",
        card_type=TreacheryCardType.WORTHLESS,
    ),
    TreacheryCard(
        id="tw_kulon",
        name="Kulon",
        card_type=TreacheryCardType.WORTHLESS,
    ),
    TreacheryCard(
        id="tw_la_la_la",
        name="La La La",
        card_type=TreacheryCardType.WORTHLESS,
    ),
    TreacheryCard(
        id="tw_trip_to_gamont",
        name="Trip to Gamont",
        card_type=TreacheryCardType.WORTHLESS,
    ),

    # -------------------------------------------------------------------------
    # Advanced-Only Special Cards (×6)
    # Excluded from the deck in Basic game (is_advanced=True).
    # -------------------------------------------------------------------------
    TreacheryCard(
        id="ts_truthtrance_1",
        name="Truthtrance",
        card_type=TreacheryCardType.SPECIAL,
        special_type=SpecialCardType.TRUTHTRANCE,
        is_advanced=True,
    ),
    TreacheryCard(
        id="ts_truthtrance_2",
        name="Truthtrance",
        card_type=TreacheryCardType.SPECIAL,
        special_type=SpecialCardType.TRUTHTRANCE,
        is_advanced=True,
    ),
    TreacheryCard(
        id="ts_weather_control",
        name="Weather Control",
        card_type=TreacheryCardType.SPECIAL,
        special_type=SpecialCardType.WEATHER_CONTROL,
        is_advanced=True,
    ),
    TreacheryCard(
        id="ts_family_atomics",
        name="Family Atomics",
        card_type=TreacheryCardType.SPECIAL,
        special_type=SpecialCardType.FAMILY_ATOMICS,
        is_advanced=True,
    ),
    TreacheryCard(
        id="ts_hajr",
        name="Hajr",
        card_type=TreacheryCardType.SPECIAL,
        special_type=SpecialCardType.HAJR,
        is_advanced=True,
    ),
    TreacheryCard(
        id="ts_tleilaxu_ghola",
        name="Tleilaxu Ghola",
        card_type=TreacheryCardType.SPECIAL,
        special_type=SpecialCardType.TLEILAXU_GHOLA,
        is_advanced=True,
    ),
]

assert len(TREACHERY_DECK) == 33, (
    f"Treachery Deck must have exactly 33 cards, found {len(TREACHERY_DECK)}"
)


# =============================================================================
# SPICE DECK  (26 cards)
# 10 territory cards × 2 copies + 6 Shai-Hulud = 26
# Territory spice amounts verified from rulebook (p.8 card image, board map).
# =============================================================================

# Territory spice blow definitions: (territory_name, spice_amount)
_SPICE_BLOW_TERRITORIES: list[tuple[str, int]] = [
    ("Gara Kulon",           6),
    ("Imperial Basin",       4),
    ("Hagga Basin",          6),
    ("The Great Flat",      10),
    ("The Minor Erg",        8),
    ("Red Chasm",            8),
    ("Habbanya Erg",         8),
    ("Cielago Depression",   6),
    ("Meridian",             6),
    ("Habbanya Ridge Flat", 10),
]

SPICE_DECK: list[SpiceCard] = []

# Each territory appears twice in the deck
for _territory_name, _spice_amount in _SPICE_BLOW_TERRITORIES:
    for _copy in range(1, 3):  # copies 1 and 2
        _card_id = (
            f"sc_{_territory_name.lower().replace(' ', '_').replace(chr(39), '')}"
            f"_{_copy}"
        )
        SPICE_DECK.append(SpiceCard(
            id=_card_id,
            name=_territory_name,
            card_type=SpiceCardType.TERRITORY,
            territory_name=_territory_name,
            spice_amount=_spice_amount,
        ))

# Shai-Hulud (×6) — triggers sandworm attack / Nexus
# The original Avalon Hill / GF9 edition includes 6 worm cards in the
# 26-card spice deck (20 territory + 6 Shai-Hulud).
for _worm_copy in range(1, 7):  # 6 copies
    SPICE_DECK.append(SpiceCard(
        id=f"sc_shai_hulud_{_worm_copy}",
        name="Shai-Hulud",
        card_type=SpiceCardType.SHAI_HULUD,
    ))

assert len(SPICE_DECK) == 26, (
    f"Spice Deck must have exactly 26 cards, found {len(SPICE_DECK)}"
)
