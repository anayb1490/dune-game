"""
Territory adjacency for the Dune board game.

Adjacency is derived from the explicit radial band placement and sector
spans of each territory.  Two territories are adjacent when:

  1. Polar Sink  ↔  any territory in the INNER band (band 0)
  2. Arrakeen    ↔  Imperial Basin (Arrakeen is inset within Imperial Basin)
  3. All others  ↔  adjacent or same band  AND  sector spans touch
                    (any pair of sectors ≤ 1 step apart, mod-18)

Band numbering (radial position on the board):
    POLAR_SINK  → -1  (central; borders all inner-band territories)
    INNER       →  0  (touching polar sink: strongholds, inner rocks, sands)
    MIDDLE      →  1  (middle ring: rocks, strongholds)
    OUTER       →  2  (outermost ring: sands)

Exported symbols:
    ADJACENCY: dict[str, frozenset[str]]
    is_adjacent(t1, t2) -> bool
    get_adjacent(territory) -> frozenset[str]
"""

from __future__ import annotations

from .territories import TERRITORIES


# ---------------------------------------------------------------------------
# Explicit band assignments — radial position on the board, NOT territory type
# ---------------------------------------------------------------------------

TERRITORY_BAND: dict[str, int] = {
    # POLAR SINK (central)
    "Polar Sink":          -1,

    # INNER BAND (band 0) — territories touching the polar sink
    "Imperial Basin":       0,
    "Arrakeen":             0,   # inset within Imperial Basin
    "Carthag":              0,
    "Hole in the Rock":     0,
    "Harg Pass":            0,
    "Tuek's Sietch":        0,
    "Cielago North":        0,
    "Habbanya Sietch":      0,
    "Arsunt":               0,
    "Wind Pass":            0,
    "Wind Pass North":      0,

    # MIDDLE BAND (band 1)
    "Broken Land":          1,
    "Tsimpo":               1,
    "Rim Wall West":        1,
    "Sihaya Ridge":         1,
    "Shield Wall":          1,
    "Pasty Mesa":           1,
    "False Wall East":      1,
    "South Mesa":           1,
    "False Wall South":     1,
    "Cielago East":         1,
    "Cielago Depression":   1,
    "Cielago West":         1,
    "False Wall West":      1,
    "Hagga Basin":          1,
    "Sietch Tabr":          1,
    "Bight of the Cliff":   1,
    "Plastic Basin":        1,

    # OUTER BAND (band 2)
    "Old Gap":              2,
    "Basin":                2,
    "Gara Kulon":           2,
    "Red Chasm":            2,
    "The Minor Erg":        2,
    "Cielago South":        2,
    "Meridian":             2,
    "Habbanya Ridge Flat":  2,
    "Habbanya Erg":         2,
    "The Greater Flat":     2,
    "The Great Flat":       2,
    "Funeral Plain":        2,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sectors_touch(s1: list[int], s2: list[int]) -> bool:
    """Return True if any sector in s1 is within 1 step of any sector in s2 (mod 18)."""
    for a in s1:
        for b in s2:
            if min(abs(a - b), 18 - abs(a - b)) <= 1:
                return True
    return False


# ---------------------------------------------------------------------------
# Adjacency computation
# ---------------------------------------------------------------------------

def _compute_adjacency() -> dict[str, frozenset[str]]:
    adj: dict[str, set[str]] = {name: set() for name in TERRITORIES}
    names = list(TERRITORIES.keys())

    for i, n1 in enumerate(names):
        for n2 in names[i + 1:]:
            t1, t2 = TERRITORIES[n1], TERRITORIES[n2]
            b1 = TERRITORY_BAND[n1]
            b2 = TERRITORY_BAND[n2]

            # Rule 1: Polar Sink borders all inner-band territories
            if b1 == -1 or b2 == -1:
                other_band = b2 if b1 == -1 else b1
                if other_band == 0:
                    adj[n1].add(n2)
                    adj[n2].add(n1)
                continue

            # Rule 2: Arrakeen ↔ Imperial Basin (inset stronghold)
            if {n1, n2} == {"Arrakeen", "Imperial Basin"}:
                adj[n1].add(n2)
                adj[n2].add(n1)
                continue

            # Rule 3: Same band or adjacent bands + sectors touch
            if abs(b1 - b2) <= 1 and _sectors_touch(t1.sectors, t2.sectors):
                adj[n1].add(n2)
                adj[n2].add(n1)

    return {k: frozenset(v) for k, v in adj.items()}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

ADJACENCY: dict[str, frozenset[str]] = _compute_adjacency()


def is_adjacent(territory1: str, territory2: str) -> bool:
    """Return True if territory1 and territory2 share a border."""
    return territory2 in ADJACENCY.get(territory1, frozenset())


def get_adjacent(territory: str) -> frozenset[str]:
    """Return the set of territory names adjacent to the given territory."""
    return ADJACENCY.get(territory, frozenset())


def get_reachable_within(
    from_territory: str,
    max_hops: int,
    blocked_territories: frozenset[str] | None = None,
) -> frozenset[str]:
    """
    Return all territories reachable from `from_territory` in at most
    `max_hops` adjacency steps, optionally skipping blocked territories.

    Used for extended movement (ornithopter range 3, Fremen range 2).
    Blocked territories cannot be entered or used as transit waypoints.

    Returns a frozenset of reachable territory names (excluding the start).
    """
    if max_hops <= 0:
        return frozenset()

    blocked = blocked_territories or frozenset()
    visited: set[str] = {from_territory}
    frontier: set[str] = {from_territory}

    for _ in range(max_hops):
        next_frontier: set[str] = set()
        for territory in frontier:
            for neighbor in ADJACENCY.get(territory, frozenset()):
                if neighbor not in visited and neighbor not in blocked:
                    visited.add(neighbor)
                    next_frontier.add(neighbor)
        frontier = next_frontier
        if not frontier:
            break

    visited.discard(from_territory)
    return frozenset(visited)
