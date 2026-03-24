"""
Static territory data for the classic Dune board game (Avalon Hill / GF9 edition).

Sector numbering: 0–17, clockwise from top (12 o'clock = sector 0).
Each sector = 20°. Sectors verified against the GF9 board image.

Board layout (clockwise from top):
  Sec  0  — Tsimpo / top
  Sec  1  — Arrakeen area
  Sec  2  — Rim Wall West / Arrakeen
  Sec  3  — Sihaya Ridge / Gara Kulon
  Sec  4  — Shield Wall / Hole in the Rock
  Sec  5  — False Wall East / Red Chasm
  Sec  6  — Harg Pass / Tuek's Sietch
  Sec  7  — False Wall South / South Mesa
  Sec  8  — Cielago East / Cielago North
  Sec  9  — Cielago West
  Sec 10  — False Wall West / Cielago South
  Sec 11  — Habbanya Sietch / Meridian
  Sec 12  — Arsunt / Habbanya Erg
  Sec 13  — Sietch Tabr / The Greater Flat
  Sec 14  — Wind Pass / The Great Flat
  Sec 15  — Wind Pass North / Plastic Basin
  Sec 16  — Carthag / Funeral Plain
  Sec 17  — Broken Land / Old Gap (wraps back to 0)
"""

from ..models.territory import Territory, TerritoryType

TERRITORIES: dict[str, Territory] = {

    # =========================================================================
    # POLAR SINK — central region, immune to storm, free Fremen haven
    # =========================================================================
    "Polar Sink": Territory(
        name="Polar Sink",
        territory_type=TerritoryType.POLAR_SINK,
        sectors=list(range(18)),
        has_spice_blow=False,
    ),

    # =========================================================================
    # STRONGHOLDS (5)
    # =========================================================================

    "Arrakeen": Territory(
        name="Arrakeen",
        territory_type=TerritoryType.STRONGHOLD,
        sectors=[1, 2],
        has_spice_blow=False,
    ),

    "Carthag": Territory(
        name="Carthag",
        territory_type=TerritoryType.STRONGHOLD,
        sectors=[16, 17],
        has_spice_blow=False,
    ),

    "Sietch Tabr": Territory(
        name="Sietch Tabr",
        territory_type=TerritoryType.STRONGHOLD,
        sectors=[13, 14],
        has_spice_blow=False,
    ),

    "Habbanya Sietch": Territory(
        name="Habbanya Sietch",
        territory_type=TerritoryType.STRONGHOLD,
        sectors=[10, 11],
        has_spice_blow=False,
    ),

    "Tuek's Sietch": Territory(
        name="Tuek's Sietch",
        territory_type=TerritoryType.STRONGHOLD,
        sectors=[6, 7],
        has_spice_blow=False,
    ),

    # =========================================================================
    # ROCK TERRITORIES — inner band (adjacent to Polar Sink)
    # =========================================================================

    "Tsimpo": Territory(
        name="Tsimpo",
        territory_type=TerritoryType.ROCK,
        sectors=[0, 1],
        has_spice_blow=False,
    ),

    "Harg Pass": Territory(
        name="Harg Pass",
        territory_type=TerritoryType.ROCK,
        sectors=[5, 6],
        has_spice_blow=False,
    ),

    "Cielago East": Territory(
        name="Cielago East",
        territory_type=TerritoryType.ROCK,
        sectors=[7, 8],
        has_spice_blow=False,
    ),

    "Cielago West": Territory(
        name="Cielago West",
        territory_type=TerritoryType.ROCK,
        sectors=[9, 10],
        has_spice_blow=False,
    ),

    "Wind Pass": Territory(
        name="Wind Pass",
        territory_type=TerritoryType.ROCK,
        sectors=[14, 15],
        has_spice_blow=False,
    ),

    "Wind Pass North": Territory(
        name="Wind Pass North",
        territory_type=TerritoryType.ROCK,
        sectors=[15, 16],
        has_spice_blow=False,
    ),

    # =========================================================================
    # ROCK TERRITORIES — middle band
    # =========================================================================

    "Broken Land": Territory(
        name="Broken Land",
        territory_type=TerritoryType.ROCK,
        sectors=[17, 0],
        has_spice_blow=False,
    ),

    "Rim Wall West": Territory(
        name="Rim Wall West",
        territory_type=TerritoryType.ROCK,
        sectors=[1, 2],
        has_spice_blow=False,
    ),

    "Sihaya Ridge": Territory(
        name="Sihaya Ridge",
        territory_type=TerritoryType.ROCK,
        sectors=[2, 3],
        has_spice_blow=False,
    ),

    "Hole in the Rock": Territory(
        name="Hole in the Rock",
        territory_type=TerritoryType.ROCK,
        sectors=[3, 4],
        has_spice_blow=False,
    ),

    "Shield Wall": Territory(
        name="Shield Wall",
        territory_type=TerritoryType.ROCK,
        sectors=[4, 5],
        has_spice_blow=False,
    ),

    "Pasty Mesa": Territory(
        name="Pasty Mesa",
        territory_type=TerritoryType.ROCK,
        sectors=[4, 5],
        has_spice_blow=False,
    ),

    "False Wall East": Territory(
        name="False Wall East",
        territory_type=TerritoryType.ROCK,
        sectors=[5, 6],
        has_spice_blow=False,
    ),

    "South Mesa": Territory(
        name="South Mesa",
        territory_type=TerritoryType.ROCK,
        sectors=[6, 7],
        has_spice_blow=False,
    ),

    "False Wall South": Territory(
        name="False Wall South",
        territory_type=TerritoryType.ROCK,
        sectors=[7, 8],
        has_spice_blow=False,
        # Fremen starting position (3 regular forces).
    ),

    "Cielago North": Territory(
        name="Cielago North",
        territory_type=TerritoryType.ROCK,
        sectors=[8, 9],
        has_spice_blow=False,
    ),

    "False Wall West": Territory(
        name="False Wall West",
        territory_type=TerritoryType.ROCK,
        sectors=[10, 11],
        has_spice_blow=False,
        # Fremen starting position (2 regular forces).
    ),

    "Bight of the Cliff": Territory(
        name="Bight of the Cliff",
        territory_type=TerritoryType.ROCK,
        sectors=[13, 14],
        has_spice_blow=False,
    ),

    "Plastic Basin": Territory(
        name="Plastic Basin",
        territory_type=TerritoryType.ROCK,
        sectors=[15, 16, 17],
        has_spice_blow=False,
    ),

    # =========================================================================
    # SAND TERRITORIES — inner band (adjacent to Polar Sink)
    # =========================================================================

    "Imperial Basin": Territory(
        name="Imperial Basin",
        territory_type=TerritoryType.SAND,
        sectors=[3, 4, 5],
        storm_exception=True,
        has_spice_blow=True,
        spice_blow_amount=4,
    ),

    "Arsunt": Territory(
        name="Arsunt",
        territory_type=TerritoryType.SAND,
        sectors=[11, 12],
        has_spice_blow=False,
    ),

    "Hagga Basin": Territory(
        name="Hagga Basin",
        territory_type=TerritoryType.SAND,
        sectors=[12, 13],
        has_spice_blow=True,
        spice_blow_amount=6,
    ),

    # =========================================================================
    # SAND TERRITORIES — outer band
    # =========================================================================

    "Old Gap": Territory(
        name="Old Gap",
        territory_type=TerritoryType.SAND,
        sectors=[17, 0, 1],
        has_spice_blow=False,
    ),

    "Basin": Territory(
        name="Basin",
        territory_type=TerritoryType.SAND,
        sectors=[1, 2],
        has_spice_blow=False,
    ),

    "Gara Kulon": Territory(
        name="Gara Kulon",
        territory_type=TerritoryType.SAND,
        sectors=[3, 4],
        has_spice_blow=True,
        spice_blow_amount=6,
    ),

    "Red Chasm": Territory(
        name="Red Chasm",
        territory_type=TerritoryType.SAND,
        sectors=[4, 5],
        has_spice_blow=True,
        spice_blow_amount=8,
    ),

    "The Minor Erg": Territory(
        name="The Minor Erg",
        territory_type=TerritoryType.SAND,
        sectors=[5, 6, 7],
        has_spice_blow=True,
        spice_blow_amount=8,
    ),

    "Cielago Depression": Territory(
        name="Cielago Depression",
        territory_type=TerritoryType.SAND,
        sectors=[8, 9],
        has_spice_blow=True,
        spice_blow_amount=6,
    ),

    "Cielago South": Territory(
        name="Cielago South",
        territory_type=TerritoryType.SAND,
        sectors=[9, 10],
        has_spice_blow=True,
        spice_blow_amount=12,
    ),

    "Meridian": Territory(
        name="Meridian",
        territory_type=TerritoryType.SAND,
        sectors=[10, 11],
        has_spice_blow=True,
        spice_blow_amount=6,
    ),

    "Habbanya Ridge Flat": Territory(
        name="Habbanya Ridge Flat",
        territory_type=TerritoryType.SAND,
        sectors=[11, 12],
        has_spice_blow=True,
        spice_blow_amount=10,
    ),

    "Habbanya Erg": Territory(
        name="Habbanya Erg",
        territory_type=TerritoryType.SAND,
        sectors=[12, 13],
        has_spice_blow=True,
        spice_blow_amount=8,
    ),

    "The Greater Flat": Territory(
        name="The Greater Flat",
        territory_type=TerritoryType.SAND,
        sectors=[13, 14],
        has_spice_blow=False,
    ),

    "The Great Flat": Territory(
        name="The Great Flat",
        territory_type=TerritoryType.SAND,
        sectors=[14, 15],
        has_spice_blow=True,
        spice_blow_amount=10,
    ),

    "Funeral Plain": Territory(
        name="Funeral Plain",
        territory_type=TerritoryType.SAND,
        sectors=[15, 16],
        has_spice_blow=True,
        spice_blow_amount=6,
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
