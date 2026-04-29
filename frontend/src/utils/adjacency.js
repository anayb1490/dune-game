/**
 * Territory adjacency helpers — mirrors the backend algorithm in adjacency.py.
 *
 * Two territories are adjacent when:
 *   1. Polar Sink  ↔  any territory in the INNER band (band 0)
 *   2. Arrakeen    ↔  Imperial Basin (inset stronghold)
 *   3. All others  ↔  same or adjacent band  AND  sector spans touch
 *                     (any sector pair within 1 step, mod-18)
 *
 * Band assignments represent radial position on the board, NOT territory type.
 */

const TERRITORY_BAND = {
  // POLAR SINK (central)
  'Polar Sink':          -1,

  // INNER BAND (band 0) — territories touching the polar sink
  'Imperial Basin':       0,
  'Arrakeen':             0,
  'Carthag':              0,
  'Hole in the Rock':     0,
  'Harg Pass':            0,
  "Tuek's Sietch":        0,
  'Cielago North':        0,
  'Habbanya Sietch':      0,
  'Arsunt':               0,
  'Wind Pass':            0,
  'Wind Pass North':      0,

  // MIDDLE BAND (band 1)
  'Broken Land':          1,
  'Tsimpo':               1,
  'Rim Wall West':        1,
  'Sihaya Ridge':         1,
  'Shield Wall':          1,
  'Pasty Mesa':           1,
  'False Wall East':      1,
  'South Mesa':           1,
  'False Wall South':     1,
  'Cielago East':         1,
  'Cielago Depression':   1,
  'Cielago West':         1,
  'False Wall West':      1,
  'Hagga Basin':          1,
  'Sietch Tabr':          1,
  'Bight of the Cliff':   1,
  'Plastic Basin':        1,

  // OUTER BAND (band 2)
  'Old Gap':              2,
  'Basin':                2,
  'Gara Kulon':           2,
  'Red Chasm':            2,
  'The Minor Erg':        2,
  'Cielago South':        2,
  'Meridian':             2,
  'Habbanya Ridge Flat':  2,
  'Habbanya Erg':         2,
  'The Greater Flat':     2,
  'The Great Flat':       2,
  'Funeral Plain':        2,
}

function sectorsTouch(s1, s2) {
  for (const a of s1) {
    for (const b of s2) {
      if (Math.min(Math.abs(a - b), 18 - Math.abs(a - b)) <= 1) return true
    }
  }
  return false
}

/**
 * Build a full adjacency map from the territories dict received from the server.
 * Returns object mapping name → Set<name>.
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
    const b1 = TERRITORY_BAND[n1] ?? 1

    for (let j = i + 1; j < names.length; j++) {
      const n2 = names[j]
      const t2 = territories[n2]
      const b2 = TERRITORY_BAND[n2] ?? 1

      let adjacent = false

      // Rule 1: Polar Sink borders all inner-band territories
      if (b1 === -1 || b2 === -1) {
        const otherBand = b1 === -1 ? b2 : b1
        adjacent = otherBand === 0
      }
      // Rule 2: Arrakeen ↔ Imperial Basin (inset stronghold)
      else if (
        (n1 === 'Arrakeen' && n2 === 'Imperial Basin') ||
        (n1 === 'Imperial Basin' && n2 === 'Arrakeen')
      ) {
        adjacent = true
      }
      // Rule 3: Same band or adjacent bands + touching sectors
      else {
        adjacent =
          Math.abs(b1 - b2) <= 1 &&
          sectorsTouch(t1.sectors || [], t2.sectors || [])
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
