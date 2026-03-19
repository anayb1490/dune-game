"""
Static leader data for the classic Dune board game (Avalon Hill / GF9 edition).

Each faction has exactly 5 leaders. Leaders are placed in the Tleilaxu Tanks
when killed in battle and may be revived during the Revival Phase.

Fighting strengths verified against the GF9 Dune rulebook faction sheets.

Advanced (Atreides only):
    The Kwisatz Haderach token is NOT included here; it is created dynamically
    by the game-setup service once the Atreides player accumulates 7 force
    losses. See services/game/handlers/atreides.py for details.

Usage:
    from backend.app.data.leaders import LEADERS_BY_FACTION, LEADERS

    # All Atreides leaders for initial player setup
    atreides_leaders = LEADERS_BY_FACTION[FactionName.ATREIDES]

    # Fast ID-based lookup during battle resolution
    leader = LEADERS["fremen_stilgar"]
"""

from ..models.faction import FactionName
from ..models.leader import Leader

LEADERS_BY_FACTION: dict[FactionName, list[Leader]] = {

    # -------------------------------------------------------------------------
    # HOUSE ATREIDES
    # Total fighting strength: 17  (5 + 5 + 4 + 2 + 1)
    # -------------------------------------------------------------------------
    FactionName.ATREIDES: [
        Leader(
            id="atreides_thufir_hawat",
            name="Thufir Hawat",
            faction=FactionName.ATREIDES,
            strength=5,
        ),
        Leader(
            id="atreides_lady_jessica",
            name="Lady Jessica",
            faction=FactionName.ATREIDES,
            strength=5,
        ),
        Leader(
            id="atreides_gurney_halleck",
            name="Gurney Halleck",
            faction=FactionName.ATREIDES,
            strength=4,
        ),
        Leader(
            id="atreides_duncan_idaho",
            name="Duncan Idaho",
            faction=FactionName.ATREIDES,
            strength=2,
        ),
        Leader(
            id="atreides_dr_yueh",
            name="Dr. Wellington Yueh",
            faction=FactionName.ATREIDES,
            strength=1,
        ),
    ],

    # -------------------------------------------------------------------------
    # HOUSE HARKONNEN
    # Total fighting strength: 16  (6 + 4 + 3 + 2 + 1)
    # Advanced: defeated enemy leaders are CAPTURED (see HarkonnenHandler)
    # -------------------------------------------------------------------------
    FactionName.HARKONNEN: [
        Leader(
            id="harkonnen_feyd_rautha",
            name="Feyd-Rautha",
            faction=FactionName.HARKONNEN,
            strength=6,
        ),
        Leader(
            id="harkonnen_beast_rabban",
            name="Beast Rabban",
            faction=FactionName.HARKONNEN,
            strength=4,
        ),
        Leader(
            id="harkonnen_piter_de_vries",
            name="Piter De Vries",
            faction=FactionName.HARKONNEN,
            strength=3,
        ),
        Leader(
            id="harkonnen_capt_nefud",
            name="Captain Iakin Nefud",
            faction=FactionName.HARKONNEN,
            strength=2,
        ),
        Leader(
            id="harkonnen_umman_kudu",
            name="Umman Kudu",
            faction=FactionName.HARKONNEN,
            strength=1,
        ),
    ],

    # -------------------------------------------------------------------------
    # BENE GESSERIT
    # Total fighting strength: 22  (5 + 5 + 5 + 5 + 2)
    # -------------------------------------------------------------------------
    FactionName.BENE_GESSERIT: [
        Leader(
            id="bg_alia",
            name="Alia",
            faction=FactionName.BENE_GESSERIT,
            strength=5,
        ),
        Leader(
            id="bg_margot_fenring",
            name="Margot Lady Fenring",
            faction=FactionName.BENE_GESSERIT,
            strength=5,
        ),
        Leader(
            id="bg_mother_ramallo",
            name="Mother Ramallo",
            faction=FactionName.BENE_GESSERIT,
            strength=5,
        ),
        Leader(
            id="bg_princess_irulan",
            name="Princess Irulan",
            faction=FactionName.BENE_GESSERIT,
            strength=5
        ),
        Leader(
            id="bg_wanna_yueh",
            name="Wanna Yueh",
            faction=FactionName.BENE_GESSERIT,
            strength=5,
        ),
    ],

    # -------------------------------------------------------------------------
    # FREMEN
    # Total fighting strength: 23 (7 + 6 + 5 + 3 + 2)
    # Stilgar is the highest-value leader in the game at strength 7.
    # -------------------------------------------------------------------------
    FactionName.FREMEN: [
        Leader(
            id="fremen_stilgar",
            name="Stilgar",
            faction=FactionName.FREMEN,
            strength=7,
        ),
        Leader(
            id="fremen_chani",
            name="Chani",
            faction=FactionName.FREMEN,
            strength=6,
        ),
        Leader(
            id="fremen_otheym",
            name="Otheym",
            faction=FactionName.FREMEN,
            strength=5,
        ),
        Leader(
            id="fremen_shadout_mapes",
            name="Shadout Mapes",
            faction=FactionName.FREMEN,
            strength=3,
        ),
        Leader(
            id="fremen_jamis",
            name="Jamis",
            faction=FactionName.FREMEN,
            strength=2,
        ),
    ],

    # -------------------------------------------------------------------------
    # SPACING GUILD
    # Total fighting strength: 14  (5 + 3 + 3 + 2 + 1)
    # -------------------------------------------------------------------------
    FactionName.SPACING_GUILD: [
        Leader(
            id="guild_staban_tuek",
            name="Staban Tuek",
            faction=FactionName.SPACING_GUILD,
            strength=5,
        ),
        Leader(
            id="guild_master_bewt",
            name="Master Bewt",
            faction=FactionName.SPACING_GUILD,
            strength=3,
        ),
        Leader(
            id="guild_esmar_tuek",
            name="Esmar Tuek",
            faction=FactionName.SPACING_GUILD,
            strength=3,
        ),
        Leader(
            id="guild_soo_soo_sook",
            name="Soo-Soo Sook",
            faction=FactionName.SPACING_GUILD,
            strength=2,
        ),
        Leader(
            id="guild_rep",
            name="Guild Rep",
            faction=FactionName.SPACING_GUILD,
            strength=1,
        ),
    ],

    # -------------------------------------------------------------------------
    # THE EMPEROR
    # Total fighting strength: 19  (6 + 5 + 3 + 3 + 2)
    # -------------------------------------------------------------------------
    FactionName.EMPEROR: [
        Leader(
            id="emperor_hasimir_fenring",
            name="Hasimir Fenring",
            faction=FactionName.EMPEROR,
            strength=6,
        ),
        Leader(
            id="emperor_capt_aramsham",
            name="Captain Aramsham",
            faction=FactionName.EMPEROR,
            strength=5,
        ),
        Leader(
            id="emperor_caid",
            name="Caid",
            faction=FactionName.EMPEROR,
            strength=3,
        ),
        Leader(
            id="emperor_burseg",
            name="Burseg",
            faction=FactionName.EMPEROR,
            strength=3,
        ),
        Leader(
            id="emperor_bashar",
            name="Bashar",
            faction=FactionName.EMPEROR,
            strength=2,
        ),
    ],
}

# Convenience: flat dict keyed by leader ID for O(1) lookup during battle resolution.
LEADERS: dict[str, Leader] = {
    leader.id: leader
    for leaders in LEADERS_BY_FACTION.values()
    for leader in leaders
}
