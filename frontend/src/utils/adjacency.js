/**
 * Territory adjacency helpers — mirrors the backend algorithm in adjacency.py.
 *
 * Two territories are adjacent when:
 *   1. Polar Sink  ↔  any Stronghold (ring 0) or Rock (ring 1)
 *   2. All others  ↔  |ring_diff| ≤ 1  AND  their sector spans touch
 *                     (any sector pair within 1 step, mod-18)
 */

const RING = {
  polar_sink:  -1,
  stronghold:   0,
  rock:         1,
  sand:         2,
}

function sectorsTough(s1, s2) {
  for (const a of s1) {
    for (const b of s2) {
      if (Math.min(Math.abs(a - b), 18 - Math.abs(a - b)) <= 1) return true
    }
  }
  return false
}

/**
 * Build a full adjacency map from the territories dict received from the server.
 * Returns Map<name, Set<name>>.
 *
 * Memoised per territories reference so it's only computed once per game state.
 */
let _cache = null
let _cacheRef = null

function buildAdjacency(territories) {
  if (territories === _cacheRef && _cache) return _cache

  const names = Object.keys(territories)
  const adj = {}
  for (const n of names) adj[n] = new Set()

  for (let i = 0; i < names.length; i++) {
    const n1 = names[i]
    const t1 = territories[n1]
    const r1 = RING[t1.territory_type] ?? 1

    for (let j = i + 1; j < names.length; j++) {
      const n2 = names[j]
      const t2 = territories[n2]
      const r2 = RING[t2.territory_type] ?? 1

      let adjacent = false

      // Rule 1: Polar Sink borders all stronghold and rock territories
      if (r1 === -1 || r2 === -1) {
        const otherRing = r1 === -1 ? r2 : r1
        adjacent = otherRing === 0 || otherRing === 1
      } else {
        // Rule 2: adjacent rings + touching sectors
        adjacent =
          Math.abs(r1 - r2) <= 1 &&
          sectorsTough(t1.sectors || [], t2.sectors || [])
      }

      if (adjacent) {
        adj[n1].add(n2)
        adj[n2].add(n1)
      }
    }
  }

  _cacheRef = territories
  _cache = adj
  return adj
}

/**
 * Returns an array of territory names adjacent to `fromName`.
 * Excludes `fromName` itself and territories not in the map.
 */
export function getAdjacentTerritories(fromName, territories) {
  if (!fromName || !territories) return Object.keys(territories || {})
  const adj = buildAdjacency(territories)
  return Array.from(adj[fromName] || []).sort()
}

/**
 * Returns true if the two territories are adjacent.
 */
export function isAdjacent(name1, name2, territories) {
  if (!territories) return false
  const adj = buildAdjacency(territories)
  return (adj[name1] || new Set()).has(name2)
}
