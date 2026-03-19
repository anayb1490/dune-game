"""
Static territory data for the classic Dune board game (Avalon Hill / GF9 edition).

This module is the single source of truth for board geography. Runtime state
(current_spice, force occupancy) lives on GameState and Player respectively —
not here. This data layer is purely declarative.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠  NOTE ON SECTOR ASSIGNMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sectors are numbered 0–17 clockwise around the board (sector 0 at top-center,
increasing clockwise). The values below are APPROXIMATE and must be verified
against the physical GF9 board before the storm movement and force-placement
logic is finalised. Incorrect sectors would produce wrong storm sweep results.

If you have the physical board, map each territory to its true sector span and
update accordingly. The territory NAMES, TYPES, and SPICE BLOW amounts are
taken from the GF9 rulebook and are reliable; only the sector indices need
verification.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠  NOTE ON SPICE BLOW AMOUNTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Spice blow amounts are taken from GF9 rulebook Spice Deck references. Values
marked with # VERIFY should be cross-checked against the physical Spice Deck.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Board layout quick-reference (approximate, clockwise from top):
    Sector  0  — Harga Pass / north
    Sector  1  — Tsimpo / north-northwest
    Sector  2  — Wind Pass North / northwest
    Sector  3  — Arrakeen / northwest
    Sector  4  — Shield Wall / west-northwest
    Sector  5  — Imperial Basin / west
    Sector  6  — Tuek's Sietch / west-southwest
    Sector  7  — Cielago East / southwest
    Sector  8  — Sietch Tabr / south
    Sector  9  — Cielago West / south-southeast
    Sector 10  — Cielago Depression / southeast
    Sector 11  — Carthag / east-southeast
    Sector 12  — Pasty Mesa / east
    Sector 13  — The Great Flat / east-northeast
    Sector 14  — Red Chasm / northeast
    Sector 15  — False Wall East / north-northeast
    Sector 16  — Habbanya Sietch / north
    Sector 17  — False Wall West / north (wraps to 0)

Usage:
    from backend.app.data.territories import TERRITORIES
    arrakeen = TERRITORIES["Arrakeen"]
    is_stronghold = arrakeen.is_stronghold  # True
"""

from ..models.territory import Territory, TerritoryType

TERRITORIES: dict[str, Territory] = {

    # =========================================================================
    # POLAR SINK — central region, immune to storm, free Fremen haven
    # Spans ALL sectors (the storm never reaches the centre).
    # =========================================================================
    "Polar Sink": Territory(
        name="Polar Sink",
        territory_type=TerritoryType.POLAR_SINK,
        sectors=list(range(18)),  # Storm cannot reach the polar centre
        has_spice_blow=False,
    ),

    # =========================================================================
    # STRONGHOLDS (5)
    # Rock territories that count toward the 3-stronghold victory condition.
    # Storm does not destroy forces here.
    # =========================================================================

    "Arrakeen": Territory(
        name="Arrakeen",
        territory_type=TerritoryType.STRONGHOLD,
        sectors=[3],              # VERIFY against physical board
        has_spice_blow=False,
        # Note: Atreides start here with 10 regular forces; provides +1 force
        # in battle (ornithopter bonus — implemented in engine, not here).
    ),

    "Carthag": Territory(
        name="Carthag",
        territory_type=TerritoryType.STRONGHOLD,
        sectors=[11],             # VERIFY
        has_spice_blow=False,
        # Note: Harkonnen start here with 10 regular forces; also provides
        # ornithopter bonus when occupied (same as Arrakeen).
    ),

    "Sietch Tabr": Territory(
        name="Sietch Tabr",
        territory_type=TerritoryType.STRONGHOLD,
        sectors=[8],              # VERIFY
        has_spice_blow=False,
        # Fremen starting position (5 regular forces).
    ),

    "Habbanya Sietch": Territory(
        name="Habbanya Sietch",
        territory_type=TerritoryType.STRONGHOLD,
        sectors=[16],             # VERIFY
        has_spice_blow=False,
    ),

    "Tuek's Sietch": Territory(
        name="Tuek's Sietch",
        territory_type=TerritoryType.STRONGHOLD,
        sectors=[6],              # VERIFY
        has_spice_blow=False,
        # Spacing Guild start here with 5 regular forces.
    ),

    # =========================================================================
    # ROCK TERRITORIES
    # Protected from storm. No forces are lost when storm passes through.
    # Not strongholds — do not count toward victory condition.
    # =========================================================================

    "Harga Pass": Territory(
        name="Harga Pass",
        territory_type=TerritoryType.ROCK,
        sectors=[0],              # VERIFY — northernmost rock passage
        has_spice_blow=False,
    ),

    "Tsimpo": Territory(
        name="Tsimpo",
        territory_type=TerritoryType.ROCK,
        sectors=[1],              # VERIFY
        has_spice_blow=False,
    ),

    "Wind Pass North": Territory(
        name="Wind Pass North",
        territory_type=TerritoryType.ROCK,
        sectors=[2],              # VERIFY
        has_spice_blow=False,
    ),

    "Shield Wall": Territory(
        name="Shield Wall",
        territory_type=TerritoryType.ROCK,
        sectors=[4],              # VERIFY — rocky ridge east of Arrakeen
        has_spice_blow=False,
    ),

    "Plastic Basin": Territory(
        name="Plastic Basin",
        territory_type=TerritoryType.ROCK,
        sectors=[5],              # VERIFY
        has_spice_blow=False,
    ),

    "Cielago East": Territory(
        name="Cielago East",
        territory_type=TerritoryType.ROCK,
        sectors=[7],              # VERIFY
        has_spice_blow=False,
    ),

    "Cielago West": Territory(
        name="Cielago West",
        territory_type=TerritoryType.ROCK,
        sectors=[9],              # VERIFY
        has_spice_blow=False,
    ),

    "Pasty Mesa": Territory(
        name="Pasty Mesa",
        territory_type=TerritoryType.ROCK,
        sectors=[12],             # VERIFY
        has_spice_blow=False,
    ),

    "Broken Land": Territory(
        name="Broken Land",
        territory_type=TerritoryType.ROCK,
        sectors=[13],             # VERIFY
        has_spice_blow=False,
    ),

    "False Wall East": Territory(
        name="False Wall East",
        territory_type=TerritoryType.ROCK,
        sectors=[15],             # VERIFY
        has_spice_blow=False,
    ),

    "False Wall West": Territory(
        name="False Wall West",
        territory_type=TerritoryType.ROCK,
        sectors=[17],             # VERIFY
        # Fremen starting position (2 regular forces).
        has_spice_blow=False,
    ),

    "False Wall South": Territory(
        name="False Wall South",
        territory_type=TerritoryType.ROCK,
        sectors=[14],             # VERIFY
        # Fremen starting position (3 regular forces).
        has_spice_blow=False,
    ),

    "Wind Pass": Territory(
        name="Wind Pass",
        territory_type=TerritoryType.ROCK,
        sectors=[16, 17],         # VERIFY — spans two sectors in some board prints
        has_spice_blow=False,
    ),

    "Hole in the Rock": Territory(
        name="Hole in the Rock",
        territory_type=TerritoryType.ROCK,
        sectors=[3, 4],           # VERIFY — rocky outcrop near Arrakeen
        has_spice_blow=False,
    ),

    "Sihaya Ridge": Territory(
        name="Sihaya Ridge",
        territory_type=TerritoryType.ROCK,
        sectors=[6, 7],           # VERIFY
        has_spice_blow=False,
    ),

    # =========================================================================
    # SAND TERRITORIES
    # Subject to sandworm and storm. Forces here are destroyed when the storm
    # sweeps through (except Fremen, who are always immune).
    # Spice blow territories receive new spice when their Spice Deck card
    # is revealed during the Spice Blow phase.
    # =========================================================================

    # --- Sand territories with spice blow ------------------------------------

    "Imperial Basin": Territory(
        name="Imperial Basin",
        territory_type=TerritoryType.SAND,
        sectors=[4, 5],           # VERIFY — the central basin around Arrakeen
        storm_exception=True,     # Rulebook p.7: forces here are NEVER destroyed
                                  # by the storm, despite being sand.
        has_spice_blow=True,
        spice_blow_amount=4,      # VERIFY amount against physical Spice Deck card
    ),

    "Gara Kulon": Territory(
        name="Gara Kulon",
        territory_type=TerritoryType.SAND,
        sectors=[3, 4],           # VERIFY — confirmed on board map, near Arrakeen area
        has_spice_blow=True,
        spice_blow_amount=6,
    ),

    "Hagga Basin": Territory(
        name="Hagga Basin",
        territory_type=TerritoryType.SAND,
        sectors=[1, 2],           # VERIFY
        has_spice_blow=True,
        spice_blow_amount=6,      # VERIFY
    ),

    "Habbanya Ridge Flat": Territory(
        name="Habbanya Ridge Flat",
        territory_type=TerritoryType.SAND,
        sectors=[15, 16],         # VERIFY — near Habbanya Sietch
        has_spice_blow=True,
        spice_blow_amount=10,     # Confirmed from Spice Deck card image (rulebook p.8)
    ),

    "The Great Flat": Territory(
        name="The Great Flat",
        territory_type=TerritoryType.SAND,
        sectors=[12, 13],         # VERIFY — the largest open sand territory
        has_spice_blow=True,
        spice_blow_amount=10,     # Largest single spice blow on the board
    ),

    "The Minor Erg": Territory(
        name="The Minor Erg",
        territory_type=TerritoryType.SAND,
        sectors=[14, 15],         # VERIFY
        has_spice_blow=True,
        spice_blow_amount=8,
    ),

    "Red Chasm": Territory(
        name="Red Chasm",
        territory_type=TerritoryType.SAND,
        sectors=[15, 16],         # VERIFY
        has_spice_blow=True,
        spice_blow_amount=8,
    ),

    "Habbanya Erg": Territory(
        name="Habbanya Erg",
        territory_type=TerritoryType.SAND,
        sectors=[16, 17],         # VERIFY — adjacent to Habbanya Sietch
        has_spice_blow=True,
        spice_blow_amount=8,
    ),

    "Cielago Depression": Territory(
        name="Cielago Depression",
        territory_type=TerritoryType.SAND,
        sectors=[9, 10],          # VERIFY — open sand south of the Cielagos
        has_spice_blow=True,
        spice_blow_amount=6,
    ),

    "Meridian": Territory(
        name="Meridian",
        territory_type=TerritoryType.SAND,
        sectors=[10, 11],         # VERIFY
        has_spice_blow=True,
        spice_blow_amount=6,
    ),

    # --- Sand territories without spice blow ---------------------------------

    "The Erg": Territory(
        name="The Erg",
        territory_type=TerritoryType.SAND,
        sectors=[0, 1],           # VERIFY
        has_spice_blow=False,
    ),

    "Attendant": Territory(
        name="Attendant",
        territory_type=TerritoryType.SAND,
        sectors=[7, 8],           # VERIFY
        has_spice_blow=False,
    ),
}


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

STRONGHOLD_NAMES: list[str] = [
    name
    for name, t in TERRITORIES.items()
    if t.is_stronghold
]

SPICE_BLOW_TERRITORY_NAMES: list[str] = [
    name
    for name, t in TERRITORIES.items()
    if t.has_spice_blow
]
