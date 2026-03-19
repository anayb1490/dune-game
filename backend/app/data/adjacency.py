"""
Territory adjacency for the Dune board game.

Adjacency is derived algorithmically from the sector and ring data in
territories.py — no hardcoding. Two territories are adjacent when:

  1. Polar Sink  ↔  any Stronghold (ring 0) or Rock (ring 1) territory
  2. All others  ↔  |ring_diff| ≤ 1  AND  their sector spans touch
                    (any pair of sectors ≤ 1 step apart, mod-18)

Ring numbering:
    POLAR_SINK  → -1  (handled specially; spans all sectors)
    STRONGHOLD  →  0
    ROCK        →  1
    SAND        →  2

Exported symbols:
    ADJACENCY: dict[str, frozenset[str]]
        Maps every territory name to the frozenset of territory names it
        borders.  Computed once at import time.

    is_adjacent(t1, t2) -> bool
        Convenience helper.
"""

from __future__ import annotations

from ..models.territory import TerritoryType
from .territories import TERRITORIES


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ring(territory_type: TerritoryType) -> int:
    return {
        TerritoryType.POLAR_SINK:  -1,
        TerritoryType.STRONGHOLD:   0,
        TerritoryType.ROCK:         1,
        TerritoryType.SAND:         2,
    }[territory_type]


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
            r1, r2 = _ring(t1.territory_type), _ring(t2.territory_type)

            # Rule 1: Polar Sink borders all strongholds and rock territories
            if r1 == -1 or r2 == -1:
                other_ring = r2 if r1 == -1 else r1
                if other_ring in (0, 1):
                    adj[n1].add(n2)
                    adj[n2].add(n1)
                continue

            # Rule 2: same or adjacent rings + sectors must touch
            if abs(r1 - r2) <= 1 and _sectors_touch(t1.sectors, t2.sectors):
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
