/**
 * GameBoard — arc-based circular SVG board for the Dune game.
 *
 * Each territory is rendered as an annular arc (wedge) matching the
 * physical GF9 board layout: sector position + radial band.
 *
 * Coordinate system:
 *   - Centre: (350, 350)
 *   - Sector 0 at 12 o'clock, increasing clockwise
 *   - Each sector = 20°
 *   - sectorToRad(s) = (s * 20 - 90) * π/180
 */

// ─── Faction colours ──────────────────────────────────────────────────────────
const FACTION_FILL = {
  atreides:      '#4ade80',
  harkonnen:     '#f87171',
  bene_gesserit: '#c084fc',
  fremen:        '#60a5fa',
  spacing_guild: '#facc15',
  emperor:       '#fb923c',
}

const FACTION_LEGEND_LABELS = {
  atreides:      'Atreides',
  harkonnen:     'Harkonnen',
  bene_gesserit: 'Bene Gesserit',
  fremen:        'Fremen',
  spacing_guild: 'Guild',
  emperor:       'Emperor',
}

// ─── Board geometry ───────────────────────────────────────────────────────────
const CX = 350
const CY = 350
const BR = 310          // board radius (px) — storm-track inner edge

const R_POLAR  = Math.round(BR * 0.175)  // 54  — polar sink edge
const R_INNER  = Math.round(BR * 0.46)   // 143 — inner/middle band boundary
const R_MIDDLE = Math.round(BR * 0.68)   // 211 — middle/outer band boundary
const R_OUTER  = Math.round(BR * 0.915)  // 284 — outer/storm boundary

// ─── Territory arc definitions ────────────────────────────────────────────────
//
//  s0 / s1 : sector-angle boundaries (can be fractional; s1 may exceed 18
//             to handle top-wrap — the math handles it naturally).
//  ri / ro : inner / outer radius in px
//
// Territories are grouped into three concentric bands:
//   INNER  — adjacent to Polar Sink (strongholds + inner rock/sand)
//   MIDDLE — outer rock ring + inner sand pockets
//   OUTER  — sand territories (storm-vulnerable, mostly)

const R_INNER_MID = Math.round(R_POLAR + (R_INNER - R_POLAR) * 0.5)

// ─── Polygon shape math helpers ───────────────────────────────────────────────

/** Convert (angle°, normR) → SVG pixel coords.  0° = 12 o'clock, clockwise. */
function polyPt(deg, normR) {
  const rad = (deg - 90) * (Math.PI / 180)
  const r   = normR * BR
  return { x: CX + r * Math.cos(rad), y: CY + r * Math.sin(rad) }
}

/**
 * SVG path string for a polygon territory.
 * arcEdges: [[i,j]…] — vertex-index pairs to draw as circular arcs (CW, short).
 * arcR: pixel radius for those arc segments (default R_POLAR).
 */
function makePolyPath(vertices, arcEdges = [], arcR = R_POLAR) {
  const pts    = vertices.map(([d, r]) => polyPt(d, r))
  const arcSet = new Set(arcEdges.map(([i, j]) => `${i},${j}`))
  let d = `M ${pts[0].x.toFixed(2)} ${pts[0].y.toFixed(2)}`
  for (let i = 0; i < pts.length; i++) {
    const j = (i + 1) % pts.length
    const p = pts[j]
    if (arcSet.has(`${i},${j}`)) {
      // Short clockwise arc along arcR circle
      d += ` A ${arcR} ${arcR} 0 0 1 ${p.x.toFixed(2)} ${p.y.toFixed(2)}`
    } else {
      d += ` L ${p.x.toFixed(2)} ${p.y.toFixed(2)}`
    }
  }
  return d + ' Z'
}

/** Geometric centroid via shoelace formula. */
function polyCentroid(vertices) {
  const pts = vertices.map(([d, r]) => polyPt(d, r))
  const n   = pts.length
  let area = 0, cx = 0, cy = 0
  for (let i = 0; i < n; i++) {
    const j     = (i + 1) % n
    const cross = pts[i].x * pts[j].y - pts[j].x * pts[i].y
    area += cross
    cx   += (pts[i].x + pts[j].x) * cross
    cy   += (pts[i].y + pts[j].y) * cross
  }
  area /= 2
  cx /= (6 * area)
  cy /= (6 * area)
  return { x: cx, y: cy }
}

// ─── Territory polygon definitions ────────────────────────────────────────────
//
// Vertices: [angleDeg, normRadius]  (0° = 12 o'clock, clockwise).
// arcEdges: consecutive vertex-index pairs drawn as circular arcs.
// band:     render-pass bucket  ('inner' | 'middle' | 'outer').
// centroid: optional manual label anchor [deg, normR]; null = auto-compute.
//
// Territories listed here override the arc fallback in TERRITORY_ARCS.

const TERRITORY_POLYGONS = {

  // ── MIDDLE BAND (drawn before inner so inner shapes paint on top) ────────────

  // Large NE crescent — the dominant northeast rock formation.
  // Arrakeen + Carthag (inner band) paint on top of this.
  'Imperial Basin': {
    band: 'middle',
    vertices: [
      [350, 0.54],
      [  0, 0.58],
      [ 60, 0.54],
      [ 80, 0.50],
      [ 80, 0.28],
      [ 40, 0.29],
      [  0, 0.29],
      [350, 0.28],
    ],
    arcEdges: [],
    centroid: [20, 0.43],
  },
  'Rim Wall West': {
    band: 'middle',
    vertices: [[22,0.46],[58,0.46],[56,0.67],[24,0.67]],
    arcEdges: [],
    centroid: null,
  },
  'Shield Wall': {
    band: 'middle',
    // Narrow arc-width but tall radial depth — wall-like appearance
    vertices: [[81,0.46],[96,0.46],[98,0.67],[83,0.68]],
    arcEdges: [],
    centroid: null,
  },
  'False Wall East': {
    band: 'middle',
    vertices: [[120,0.41],[137,0.39],[139,0.67],[122,0.68]],
    arcEdges: [],
    centroid: [129,0.54],
  },
  'False Wall South': {
    band: 'middle',
    vertices: [[160,0.41],[177,0.39],[179,0.67],[162,0.68]],
    arcEdges: [],
    centroid: [169,0.54],
  },
  // Narrow elongated strip mirroring False Wall East on the west side
  'False Wall West': {
    band: 'middle',
    vertices: [[220,0.40],[235,0.38],[237,0.63],[222,0.64]],
    arcEdges: [],
    centroid: [228,0.51],
  },
  'Hagga Basin': {
    band: 'middle',
    vertices: [[240,0.46],[268,0.46],[268,0.62],[252,0.66],[240,0.60]],
    arcEdges: [],
    centroid: null,
  },
  'Sietch Tabr': {
    band: 'middle',
    vertices: [[272,0.47],[288,0.45],[290,0.67],[274,0.69]],
    arcEdges: [],
    centroid: null,
  },
  'Plastic Basin': {
    band: 'middle',
    vertices: [[310,0.44],[338,0.42],[338,0.66],[312,0.67]],
    arcEdges: [],
    centroid: [324,0.55],
  },
  'Tsimpo': {
    band: 'middle',
    vertices: [[340,0.44],[353,0.43],[353,0.68],[341,0.68]],
    arcEdges: [],
    centroid: null,
  },

  // ── INNER BAND ──────────────────────────────────────────────────────────────

  // Compact strongholds — sit inside the Imperial Basin crescent
  'Arrakeen': {
    band: 'inner',
    vertices: [[22,0.30],[48,0.30],[46,0.46],[24,0.46]],
    arcEdges: [],
    centroid: null,
  },
  'Carthag': {
    band: 'inner',
    vertices: [[318,0.30],[342,0.30],[342,0.46],[318,0.46]],
    arcEdges: [],
    centroid: null,
  },
  'Hole in the Rock': {
    band: 'inner',
    vertices: [[60,0.175],[88,0.175],[84,0.30],[62,0.31]],
    arcEdges: [[0,1]], arcR: R_POLAR,
    centroid: null,
  },
  'Harg Pass': {
    band: 'inner',
    vertices: [[90,0.175],[128,0.175],[124,0.30],[93,0.31]],
    arcEdges: [[0,1]], arcR: R_POLAR,
    centroid: null,
  },
  // Isolated stronghold in the SE outer ring
  "Tuek's Sietch": {
    band: 'inner',
    vertices: [[132,0.62],[157,0.60],[158,0.76],[133,0.78]],
    arcEdges: [],
    centroid: null,
  },
  // Full inner-ring depth — from Polar Sink edge to R_INNER
  'Arsunt': {
    band: 'inner',
    vertices: [[240,0.175],[268,0.175],[268,0.46],[240,0.46]],
    arcEdges: [[0,1]], arcR: R_POLAR,
    centroid: null,
  },
  'Wind Pass': {
    band: 'inner',
    vertices: [[300,0.175],[320,0.175],[320,0.30],[300,0.30]],
    arcEdges: [[0,1]], arcR: R_POLAR,
    centroid: null,
  },
  'Wind Pass North': {
    band: 'inner',
    vertices: [[300,0.30],[320,0.30],[320,0.46],[300,0.46]],
    arcEdges: [],
    centroid: null,
  },
  // Isolated stronghold in the W outer ring (~7-8 o'clock)
  'Habbanya Sietch': {
    band: 'inner',
    vertices: [[207,0.63],[225,0.61],[226,0.78],[208,0.80]],
    arcEdges: [],
    centroid: null,
  },
}

const TERRITORY_ARCS = {

  // ── INNER BAND  (ri = R_POLAR, ro = R_INNER) ─────────────────────────────
  // Clockwise from top. Gaps at 0–1.5 (top) and 13.5–15.0 (left) are intentional —
  // those sectors are covered by middle-band territories (Broken Land, Sietch Tabr).
  'Arrakeen':          { s0:  1.5, s1:  3.0, ri: R_POLAR,     ro: R_INNER },
  'Hole in the Rock':  { s0:  3.0, s1:  4.5, ri: R_POLAR,     ro: R_INNER_MID },
  'Imperial Basin':    { s0:  3.0, s1:  6.0, ri: R_INNER_MID, ro: R_INNER },
  'Harg Pass':         { s0:  4.5, s1:  6.5, ri: R_POLAR,     ro: R_INNER_MID },
  "Tuek's Sietch":     { s0:  6.5, s1:  8.0, ri: R_POLAR,     ro: R_INNER },
  'Cielago East':      { s0:  8.0, s1:  9.5, ri: R_POLAR,     ro: R_INNER },
  'Cielago West':      { s0:  9.5, s1: 10.5, ri: R_POLAR,     ro: R_INNER },
  'Habbanya Sietch':   { s0: 10.5, s1: 12.0, ri: R_POLAR,     ro: R_INNER },
  'Arsunt':            { s0: 12.0, s1: 13.5, ri: R_POLAR,     ro: R_INNER },
  // gap 13.5–15.0: Sietch Tabr sits in middle band here
  'Wind Pass':         { s0: 15.0, s1: 16.0, ri: R_POLAR,     ro: R_INNER },
  'Wind Pass North':   { s0: 16.0, s1: 17.0, ri: R_POLAR,     ro: R_INNER },
  'Carthag':           { s0: 17.0, s1: 18.0, ri: R_POLAR,     ro: R_INNER },

  // ── MIDDLE BAND  (ri = R_INNER, ro = R_MIDDLE) ───────────────────────────
  // Fully tiles 17.5 → 17.5 with no gaps or overlaps.
  'Broken Land':       { s0: 17.5, s1: 19.5, ri: R_INNER,     ro: R_MIDDLE },
  'Tsimpo':            { s0: 17.0, s1: 17.5, ri: R_INNER,     ro: R_MIDDLE },
  'Plastic Basin':     { s0: 15.5, s1: 17.0, ri: R_INNER,     ro: R_MIDDLE },
  'Bight of the Cliff':{ s0: 14.5, s1: 15.5, ri: R_INNER,     ro: R_MIDDLE },
  'Sietch Tabr':       { s0: 13.5, s1: 14.5, ri: R_INNER,     ro: R_MIDDLE },
  'Hagga Basin':       { s0: 12.0, s1: 13.5, ri: R_INNER,     ro: R_MIDDLE },
  'False Wall West':   { s0: 10.5, s1: 12.0, ri: R_INNER,     ro: R_MIDDLE },
  'Cielago North':     { s0:  9.0, s1: 10.5, ri: R_INNER,     ro: R_MIDDLE },
  'False Wall South':  { s0:  8.0, s1:  9.0, ri: R_INNER,     ro: R_MIDDLE },
  'South Mesa':        { s0:  7.0, s1:  8.0, ri: R_INNER,     ro: R_MIDDLE },
  'False Wall East':   { s0:  6.0, s1:  7.0, ri: R_INNER,     ro: R_MIDDLE },
  'Pasty Mesa':        { s0:  5.0, s1:  6.0, ri: R_INNER,     ro: R_MIDDLE },
  'Shield Wall':       { s0:  4.0, s1:  5.0, ri: R_INNER,     ro: R_MIDDLE },
  'Sihaya Ridge':      { s0:  3.0, s1:  4.0, ri: R_INNER,     ro: R_MIDDLE },
  'Rim Wall West':     { s0:  1.5, s1:  3.0, ri: R_INNER,     ro: R_MIDDLE },
  // gap 19.5(=1.5): Rim Wall West picks up exactly where Broken Land ends

  // ── OUTER BAND  (ri = R_MIDDLE, ro = R_OUTER) ────────────────────────────
  // Fully tiles 17.5 → 17.5.
  'Old Gap':           { s0: 17.5, s1: 19.5, ri: R_MIDDLE,    ro: R_OUTER },
  'Basin':             { s0:  1.5, s1:  3.0, ri: R_MIDDLE,    ro: R_OUTER },
  'Gara Kulon':        { s0:  3.0, s1:  4.5, ri: R_MIDDLE,    ro: R_OUTER },
  'Red Chasm':         { s0:  4.5, s1:  6.0, ri: R_MIDDLE,    ro: R_OUTER },
  'The Minor Erg':     { s0:  6.0, s1:  8.0, ri: R_MIDDLE,    ro: R_OUTER },
  'Cielago Depression':{ s0:  8.0, s1:  9.5, ri: R_MIDDLE,    ro: R_OUTER },
  'Cielago South':     { s0:  9.5, s1: 11.0, ri: R_MIDDLE,    ro: R_OUTER },
  'Meridian':          { s0: 11.0, s1: 12.3, ri: R_MIDDLE,    ro: R_OUTER },
  'Habbanya Ridge Flat':{ s0:12.3, s1: 13.5, ri: R_MIDDLE,    ro: R_OUTER },
  'Habbanya Erg':      { s0: 13.5, s1: 14.5, ri: R_MIDDLE,    ro: R_OUTER },
  'The Greater Flat':  { s0: 14.5, s1: 15.5, ri: R_MIDDLE,    ro: R_OUTER },
  'The Great Flat':    { s0: 15.5, s1: 16.5, ri: R_MIDDLE,    ro: R_OUTER },
  'Funeral Plain':     { s0: 16.5, s1: 17.5, ri: R_MIDDLE,    ro: R_OUTER },
}

// ─── Arc math helpers ─────────────────────────────────────────────────────────

function sectorToRad(s) {
  return (s * 20 - 90) * (Math.PI / 180)
}

/** SVG path for an annular arc (wedge shape). */
function makeArcPath(cx, cy, ri, ro, s0, s1) {
  const a0 = sectorToRad(s0)
  const a1 = sectorToRad(s1)
  const spanDeg = (s1 - s0) * 20
  const large = spanDeg > 180 ? 1 : 0

  const x0o = cx + ro * Math.cos(a0)
  const y0o = cy + ro * Math.sin(a0)
  const x1o = cx + ro * Math.cos(a1)
  const y1o = cy + ro * Math.sin(a1)
  const x1i = cx + ri * Math.cos(a1)
  const y1i = cy + ri * Math.sin(a1)
  const x0i = cx + ri * Math.cos(a0)
  const y0i = cy + ri * Math.sin(a0)

  return [
    `M ${x0o.toFixed(2)} ${y0o.toFixed(2)}`,
    `A ${ro} ${ro} 0 ${large} 1 ${x1o.toFixed(2)} ${y1o.toFixed(2)}`,
    `L ${x1i.toFixed(2)} ${y1i.toFixed(2)}`,
    `A ${ri} ${ri} 0 ${large} 0 ${x0i.toFixed(2)} ${y0i.toFixed(2)}`,
    'Z',
  ].join(' ')
}

/** Centroid of an annular arc — used for label/token placement. */
function arcCentroid(cx, cy, ri, ro, s0, s1) {
  const midA = sectorToRad((s0 + s1) / 2)
  const midR = (ri + ro) / 2
  return {
    x: cx + midR * Math.cos(midA),
    y: cy + midR * Math.sin(midA),
  }
}

// ─── Force map builder ────────────────────────────────────────────────────────

function buildForceMap(players) {
  const map = {}
  for (const player of (players || [])) {
    for (const fg of (player.forces_on_board || [])) {
      const total = (fg.regular_count || 0) + (fg.special_count || 0)
      if (total === 0) continue
      if (!map[fg.territory_name]) map[fg.territory_name] = []
      const existing = map[fg.territory_name].find(e => e.faction === player.faction)
      if (existing) {
        existing.count += total
        existing.special += fg.special_count || 0
      } else {
        map[fg.territory_name].push({
          faction: player.faction,
          count: total,
          special: fg.special_count || 0,
        })
      }
    }
  }
  return map
}

// ─── Storm sector sweep ───────────────────────────────────────────────────────

function StormSweep({ stormSector }) {
  // Filled wedge from inner polar edge to outer board edge, one sector wide
  const s0 = stormSector - 0.5
  const s1 = stormSector + 0.5
  const path = makeArcPath(CX, CY, R_POLAR, BR, s0, s1)
  return (
    <path d={path} fill="#ef4444" fillOpacity={0.18} stroke="#ef4444" strokeWidth={1} strokeOpacity={0.6} />
  )
}

// ─── Sector division lines ────────────────────────────────────────────────────

function SectorLines() {
  return (
    <g>
      {Array.from({ length: 18 }, (_, i) => {
        const a = sectorToRad(i)
        return (
          <line
            key={i}
            x1={CX + R_POLAR * Math.cos(a)}
            y1={CY + R_POLAR * Math.sin(a)}
            x2={CX + BR * Math.cos(a)}
            y2={CY + BR * Math.sin(a)}
            stroke="rgba(60,35,5,0.7)"
            strokeWidth={0.8}
          />
        )
      })}
    </g>
  )
}

// ─── Ring boundary circles ────────────────────────────────────────────────────

function RingCircles() {
  return (
    <g fill="none" strokeWidth={0.6}>
      <circle cx={CX} cy={CY} r={R_POLAR}  stroke="#a09050" />
      <circle cx={CX} cy={CY} r={R_INNER}  stroke="#1e1b12" />
      <circle cx={CX} cy={CY} r={R_MIDDLE} stroke="#1e1b12" />
      <circle cx={CX} cy={CY} r={R_OUTER}  stroke="#1e1b12" />
      <circle cx={CX} cy={CY} r={BR}        stroke="#3a3020" strokeWidth={1.5} />
    </g>
  )
}

// ─── Territory arc ────────────────────────────────────────────────────────────

const LABEL_ABBREV = {
  'Habbanya Sietch':     'Hab. Sietch',
  'Habbanya Erg':        'Hab. Erg',
  'Cielago Depression':  'Cielago Dep.',
  'Cielago North':       'Cielago N.',
  'Cielago South':       'Cielago S.',
  'Wind Pass North':     'W. Pass N.',
  'False Wall East':     'FW East',
  'False Wall West':     'FW West',
  'False Wall South':    'FW South',
  "Tuek's Sietch":       "Tuek's",
  'Plastic Basin':       'Plastic B.',
  'Hole in the Rock':    'Hole/Rock',
  'Sihaya Ridge':        'Sihaya R.',
  'Broken Land':         'Broken L.',
  'Imperial Basin':      'Imp. Basin',
  'Bight of the Cliff':  'Bight',
  'Sietch Tabr':         'S. Tabr',
  'Rim Wall West':       'Rim Wall W.',
  'The Greater Flat':    'Greater Flat',
  'The Great Flat':      'Great Flat',
  'The Minor Erg':       'Minor Erg',
  'Habbanya Ridge Flat': 'Hab. Ridge',
}

function TerritoryArc({ name, territory, forceEntries, isStorm, highlight, mode }) {
  const arc = TERRITORY_ARCS[name]
  if (!arc) return null

  const { s0, s1, ri, ro } = arc
  const path = makeArcPath(CX, CY, ri, ro, s0, s1)
  const { x: cx, y: cy } = arcCentroid(CX, CY, ri, ro, s0, s1)

  const isStronghold = territory.territory_type === 'stronghold'
  const isSand       = territory.territory_type === 'sand'
  const isRock       = territory.territory_type === 'rock'
  const hasSpice     = territory.current_spice > 0
  const hasForces    = forceEntries && forceEntries.length > 0

  // Territory fill & stroke
  let fill   = '#2a1e0a'
  let stroke = '#1a1208'
  let strokeW = 0.8

  if (isStronghold) {
    fill   = '#4A2C0A'
    stroke = '#C8960A'
    strokeW = 1.8
  } else if (isRock) {
    fill   = '#8B6420'
    stroke = '#6B4C18'
  } else if (isSand) {
    fill   = '#C8A96E'
    stroke = '#8a6830'
  }

  // Storm highlight on vulnerable sand
  if (isStorm && isSand && !territory.storm_exception) {
    stroke  = '#ef4444'
    strokeW = 1.5
  }

  // Movement highlight
  const glowColor =
    highlight === 'from'     ? '#22c55e' :
    highlight === 'to'       ? '#3b82f6' :
    highlight === 'adjacent' ? '#0d9488' :
    null

  // ── FILL PASS: draw territory shape ──
  if (mode === 'fill') {
    return (
      <g>
        {glowColor && (
          <path
            d={makeArcPath(CX, CY, Math.max(0, ri - 3), ro + 3, s0, s1)}
            fill="none"
            stroke={glowColor}
            strokeWidth={highlight === 'adjacent' ? 1.5 : 2.5}
            opacity={highlight === 'adjacent' ? 0.5 : 0.9}
          />
        )}
        <path
          d={path}
          fill={fill}
          stroke={glowColor ?? stroke}
          strokeWidth={strokeW}
        />
        {isStronghold && (
          <path
            d={makeArcPath(CX, CY, ri + 4, ro - 4, s0 + 0.1, s1 - 0.1)}
            fill="none"
            stroke={stroke}
            strokeWidth={0.5}
            strokeDasharray="2,2"
            opacity={0.6}
          />
        )}
      </g>
    )
  }

  // ── LABEL PASS: draw text & tokens on top of all fills ──
  const label = LABEL_ABBREV[name] ?? name

  const arcSpanDeg = (s1 - s0) * 20
  const arcMidR    = (ri + ro) / 2
  const arcWidthPx = arcMidR * (arcSpanDeg * Math.PI / 180)
  const arcHeightPx = ro - ri
  const availW = Math.min(arcWidthPx * 0.88, arcHeightPx * 0.88)
  const fontSize = isStronghold
    ? Math.max(6, Math.min(9, availW / label.length * 1.7))
    : Math.max(5, Math.min(7.5, availW / label.length * 1.7))

  const lineH   = fontSize + 1
  const spiceH  = hasSpice  ? 8 : 0
  const forceH  = hasForces ? 8 : 0
  const totalH  = lineH + spiceH + forceH
  const topY    = cy - totalH / 2

  return (
    <g>
      {/* Territory name */}
      <text
        x={cx}
        y={topY + lineH * 0.75}
        textAnchor="middle"
        dominantBaseline="central"
        fill={isStronghold ? '#f0d060' : isSand ? '#3a1a05' : '#F0E0B0'}
        fontSize={fontSize}
        fontWeight={isStronghold ? 'bold' : 'normal'}
        fontFamily="serif"
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        {label}
      </text>

      {/* Spice indicator */}
      {hasSpice && (
        <text
          x={cx}
          y={topY + lineH + spiceH * 0.65}
          textAnchor="middle"
          dominantBaseline="central"
          fill="#d97706"
          fontSize={7.5}
          fontWeight="bold"
          style={{ pointerEvents: 'none', userSelect: 'none' }}
        >
          {'◆'}{territory.current_spice}
        </text>
      )}

      {/* Force tokens */}
      {hasForces && (
        <g>
          {forceEntries.map((entry, i) => {
            const totalDots = forceEntries.length
            const dotX = cx - ((totalDots - 1) * 7) / 2 + i * 7
            const dotY = topY + lineH + spiceH + forceH * 0.5
            return (
              <g key={entry.faction}>
                <circle
                  cx={dotX} cy={dotY} r={4.5}
                  fill={FACTION_FILL[entry.faction] || '#888'}
                  opacity={0.92}
                />
                <text
                  x={dotX} y={dotY}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fill="#000"
                  fontSize={5.5}
                  fontWeight="bold"
                  style={{ pointerEvents: 'none', userSelect: 'none' }}
                >
                  {entry.count}
                </text>
              </g>
            )
          })}
        </g>
      )}
    </g>
  )
}

// ─── Territory polygon ────────────────────────────────────────────────────────

function TerritoryPoly({ name, territory, forceEntries, isStorm, highlight, mode }) {
  const poly = TERRITORY_POLYGONS[name]
  if (!poly) return null

  const { vertices, arcEdges = [], arcR = R_POLAR } = poly
  const path = makePolyPath(vertices, arcEdges, arcR)

  const { x: cx, y: cy } = poly.centroid
    ? polyPt(poly.centroid[0], poly.centroid[1])
    : polyCentroid(vertices)

  const isStronghold = territory.territory_type === 'stronghold'
  const isSand       = territory.territory_type === 'sand'
  const hasSpice     = territory.current_spice > 0
  const hasForces    = forceEntries && forceEntries.length > 0

  let fill    = '#2a1e0a'
  let stroke  = '#1a1208'
  let strokeW = 0.8

  if (isStronghold) {
    fill    = '#4A2C0A'
    stroke  = '#C8960A'
    strokeW = 1.8
  } else if (isSand) {
    fill    = '#C8A96E'
    stroke  = '#8a6830'
  } else {
    fill    = '#8B6420'
    stroke  = '#6B4C18'
  }

  if (isStorm && isSand && !territory.storm_exception) {
    stroke  = '#ef4444'
    strokeW = 1.5
  }

  const glowColor =
    highlight === 'from'     ? '#22c55e' :
    highlight === 'to'       ? '#3b82f6' :
    highlight === 'adjacent' ? '#0d9488' :
    null

  // ── FILL PASS ──
  if (mode === 'fill') {
    // Inset polygon for stronghold dashed inner ring
    const rVals   = vertices.map(v => v[1])
    const rMid    = (Math.max(...rVals) + Math.min(...rVals)) / 2
    const insetV  = vertices.map(([d, r]) => [d, r < rMid ? r + 0.014 : r - 0.014])
    const insetPath = makePolyPath(insetV, arcEdges, arcR)

    return (
      <g>
        {glowColor && (
          <path
            d={path}
            fill="none"
            stroke={glowColor}
            strokeWidth={highlight === 'adjacent' ? 4 : 6}
            opacity={highlight === 'adjacent' ? 0.45 : 0.85}
          />
        )}
        <path d={path} fill={fill} stroke={glowColor ?? stroke} strokeWidth={strokeW} />
        {isStronghold && (
          <path
            d={insetPath}
            fill="none"
            stroke={stroke}
            strokeWidth={0.5}
            strokeDasharray="2,2"
            opacity={0.6}
          />
        )}
      </g>
    )
  }

  // ── LABEL PASS ──
  const label = LABEL_ABBREV[name] ?? name

  const pts    = vertices.map(([d, r]) => polyPt(d, r))
  const bbox_w = Math.max(...pts.map(p => p.x)) - Math.min(...pts.map(p => p.x))
  const bbox_h = Math.max(...pts.map(p => p.y)) - Math.min(...pts.map(p => p.y))
  const availW = Math.min(bbox_w, bbox_h) * 0.75
  const fontSize = isStronghold
    ? Math.max(6, Math.min(9,   availW / label.length * 1.7))
    : Math.max(5, Math.min(7.5, availW / label.length * 1.7))

  const lineH  = fontSize + 1
  const spiceH = hasSpice  ? 8 : 0
  const forceH = hasForces ? 8 : 0
  const totalH = lineH + spiceH + forceH
  const topY   = cy - totalH / 2

  return (
    <g>
      <text
        x={cx} y={topY + lineH * 0.75}
        textAnchor="middle" dominantBaseline="central"
        fill={isStronghold ? '#f0d060' : isSand ? '#3a1a05' : '#F0E0B0'}
        fontSize={fontSize}
        fontWeight={isStronghold ? 'bold' : 'normal'}
        fontFamily="serif"
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        {label}
      </text>

      {hasSpice && (
        <text
          x={cx} y={topY + lineH + spiceH * 0.65}
          textAnchor="middle" dominantBaseline="central"
          fill="#d97706" fontSize={7.5} fontWeight="bold"
          style={{ pointerEvents: 'none', userSelect: 'none' }}
        >
          {'◆'}{territory.current_spice}
        </text>
      )}

      {hasForces && (
        <g>
          {forceEntries.map((entry, i) => {
            const totalDots = forceEntries.length
            const dotX = cx - ((totalDots - 1) * 7) / 2 + i * 7
            const dotY = topY + lineH + spiceH + forceH * 0.5
            return (
              <g key={entry.faction}>
                <circle cx={dotX} cy={dotY} r={4.5}
                  fill={FACTION_FILL[entry.faction] || '#888'} opacity={0.92} />
                <text
                  x={dotX} y={dotY}
                  textAnchor="middle" dominantBaseline="central"
                  fill="#000" fontSize={5.5} fontWeight="bold"
                  style={{ pointerEvents: 'none', userSelect: 'none' }}
                >
                  {entry.count}
                </text>
              </g>
            )
          })}
        </g>
      )}
    </g>
  )
}

// ─── Polar Sink ───────────────────────────────────────────────────────────────

function PolarSink({ forces }) {
  return (
    <g>
      <circle cx={CX} cy={CY} r={R_POLAR} fill="#D4C9A0" stroke="#a09050" strokeWidth={1.5} />
      {/* Subtle inner ring */}
      <circle cx={CX} cy={CY} r={R_POLAR - 6} fill="none" stroke="#a09050" strokeWidth={0.8} strokeDasharray="3,3" />
      <text
        x={CX} y={CY - 6}
        textAnchor="middle"
        dominantBaseline="central"
        fill="#5a3a10"
        fontSize={8}
        fontWeight="bold"
        fontFamily="serif"
        style={{ userSelect: 'none' }}
      >
        Polar
      </text>
      <text
        x={CX} y={CY + 6}
        textAnchor="middle"
        dominantBaseline="central"
        fill="#5a3a10"
        fontSize={8}
        fontWeight="bold"
        fontFamily="serif"
        style={{ userSelect: 'none' }}
      >
        Sink
      </text>
      {forces && forces.length > 0 && forces.map((entry, i) => {
        const dotX = CX - ((forces.length - 1) * 7) / 2 + i * 7
        return (
          <g key={entry.faction}>
            <circle cx={dotX} cy={CY + 18} r={4.5} fill={FACTION_FILL[entry.faction] || '#888'} opacity={0.9} />
            <text x={dotX} y={CY + 18} textAnchor="middle" dominantBaseline="central" fill="#000" fontSize={5.5} fontWeight="bold" style={{ userSelect: 'none' }}>
              {entry.count}
            </text>
          </g>
        )
      })}
    </g>
  )
}

// ─── Sector number labels ─────────────────────────────────────────────────────

function SectorLabels({ stormSector }) {
  return (
    <g>
      {Array.from({ length: 18 }, (_, i) => {
        const a = sectorToRad(i + 0.5)
        const r = BR - 12
        const x = CX + r * Math.cos(a)
        const y = CY + r * Math.sin(a)
        const isStorm = i === stormSector
        return (
          <text
            key={i}
            x={x} y={y}
            textAnchor="middle"
            dominantBaseline="central"
            fill={isStorm ? '#ef4444' : '#3a3020'}
            fontSize={isStorm ? 9 : 7}
            fontWeight={isStorm ? 'bold' : 'normal'}
            fontFamily="monospace"
            style={{ userSelect: 'none' }}
          >
            {i}
          </text>
        )
      })}
    </g>
  )
}

// ─── Main board component ─────────────────────────────────────────────────────

export default function GameBoard({
  territories,
  players,
  stormSector,
  highlightFrom = '',
  highlightTo = '',
  adjacentTo = [],
}) {
  if (!territories) return null

  const forceMap = buildForceMap(players)
  const stormSectorNum = stormSector ?? 0
  const adjacentSet = new Set(adjacentTo)

  function getHighlight(name) {
    if (name === highlightFrom) return 'from'
    if (name === highlightTo)   return 'to'
    if (highlightFrom && adjacentSet.has(name)) return 'adjacent'
    return null
  }

  // Draw order: background → storm → territory arcs → polar sink → lines → labels
  return (
    <div className="bg-surface border border-[#3a3020] rounded p-2 h-full flex flex-col">
      <svg
        viewBox="0 0 700 700"
        className="flex-1 w-full min-h-0"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Board background disc */}
        <circle cx={CX} cy={CY} r={BR} fill="#1a1008" />

        {/* Sand base layer — fills board interior with sand colour so no black
            gaps appear where polygon vertices don't perfectly tile */}
        <circle cx={CX} cy={CY} r={R_OUTER} fill="#C8A96E" />

        {/* Storm sector fill */}
        <StormSweep stormSector={stormSectorNum} />

        {/* PASS 1: Territory fills — outer → middle → inner (so inner overlaps outer) */}
        {['outer', 'middle', 'inner'].map(band => (
          Object.entries(territories).map(([name, territory]) => {
            const poly = TERRITORY_POLYGONS[name]
            const arc  = TERRITORY_ARCS[name]
            if (!poly && !arc) return null
            const inBand = poly
              ? poly.band === band
              : (band === 'outer'  ? arc.ri >= R_MIDDLE :
                 band === 'middle' ? arc.ri >= R_INNER && arc.ri < R_MIDDLE :
                 /* inner */         arc.ri < R_INNER)
            if (!inBand) return null

            const forces    = forceMap[name] || []
            const isStorm   = (territory.sectors || []).includes(stormSectorNum)
            const highlight = getHighlight(name)
            const sharedProps = {
              key: `fill-${name}`, name, territory,
              forceEntries: forces, isStorm, highlight, mode: 'fill',
            }
            return poly
              ? <TerritoryPoly {...sharedProps} />
              : <TerritoryArc  {...sharedProps} />
          })
        ))}

        {/* Ring guide circles */}
        <RingCircles />

        {/* Sector dividing lines */}
        <SectorLines />

        {/* Polar Sink (drawn on top of inner arcs) */}
        <PolarSink forces={forceMap['Polar Sink']} />

        {/* PASS 2: Territory labels — rendered on top of ALL fills */}
        {['outer', 'middle', 'inner'].map(band => (
          Object.entries(territories).map(([name, territory]) => {
            const poly = TERRITORY_POLYGONS[name]
            const arc  = TERRITORY_ARCS[name]
            if (!poly && !arc) return null
            const inBand = poly
              ? poly.band === band
              : (band === 'outer'  ? arc.ri >= R_MIDDLE :
                 band === 'middle' ? arc.ri >= R_INNER && arc.ri < R_MIDDLE :
                 /* inner */         arc.ri < R_INNER)
            if (!inBand) return null

            const forces    = forceMap[name] || []
            const isStorm   = (territory.sectors || []).includes(stormSectorNum)
            const highlight = getHighlight(name)
            const sharedProps = {
              key: `label-${name}`, name, territory,
              forceEntries: forces, isStorm, highlight, mode: 'label',
            }
            return poly
              ? <TerritoryPoly {...sharedProps} />
              : <TerritoryArc  {...sharedProps} />
          })
        ))}

        {/* Sector number labels (outermost ring) */}
        <SectorLabels stormSector={stormSectorNum} />
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-2 py-1 border-t border-[#3a3020] text-[10px] text-gray-500 shrink-0">
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm border-2" style={{ borderColor: '#C8960A', background: '#4A2C0A' }} />
          Stronghold
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm border" style={{ borderColor: '#6B4C18', background: '#8B6420' }} />
          Rock
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm border" style={{ borderColor: '#8a6830', background: '#C8A96E' }} />
          Sand
        </span>
        <span className="flex items-center gap-1">
          <span className="text-spice font-bold text-xs">◆</span>
          Spice
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: '#ef444430' }} />
          Storm
        </span>
        <span className="text-[#3a3020]">|</span>
        {Object.entries(FACTION_FILL).map(([faction, color]) => (
          <span key={faction} className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: color }} />
            {FACTION_LEGEND_LABELS[faction]}
          </span>
        ))}
      </div>
    </div>
  )
}
