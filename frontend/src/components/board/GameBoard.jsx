/**
 * GameBoard — Pure SVG circular board for the Dune board game.
 *
 * Layered rendering with organic border displacement filters for a
 * hand-drawn, professional digital board game aesthetic.
 *
 * Coordinate system:
 *   Centre: (350, 350), Sector 0 at 12 o'clock, clockwise, 20 deg per sector.
 */

// ─── Faction colours ────────────────────────────────────────────────────────────
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

// ─── Colour palette ─────────────────────────────────────────────────────────────
const C = {
  // Territory fills
  sand:       '#D4B878',
  sandDark:   '#C8A860',
  rock:       '#8B7040',
  rockDark:   '#7A6030',
  stronghold: '#5A3818',
  strongholdAlt: '#6B4828',

  // Polar Sink
  polar:      '#E8DCC8',
  polarStroke:'#A09060',

  // Borders
  border:     '#3A2510',
  borderFaint:'#6B5030',
  borderThick:'#2A1808',

  // Frame & background
  frameDark:  '#1A1008',
  frameMid:   '#2A1E10',
  frameAccent:'#8B7040',

  // Text
  textDark:   '#3A2510',
  textMid:    '#5A4020',
  textLight:  '#D4BC88',
  textGold:   '#D4A840',

  // Game indicators
  spice:      '#C85000',
  spiceGlow:  '#FF8C00',
  storm:      '#CC3333',
  stormFill:  '#CC333320',
}

// ─── Board geometry ─────────────────────────────────────────────────────────────
const CX = 350
const CY = 350
const BR = 310

const R_POLAR  = Math.round(BR * 0.175)   // 54
const R_INNER  = Math.round(BR * 0.46)    // 143
const R_MIDDLE = Math.round(BR * 0.68)    // 211
const R_OUTER  = Math.round(BR * 0.915)   // 284
const R_FRAME  = 332

// ─── SVG viewBox ────────────────────────────────────────────────────────────────
const VB_W = 700
const VB_H = 730

// ─── Territory type map (client-side, matching backend data) ────────────────────
const TERRITORY_TYPES = {
  'Polar Sink':          'polar_sink',
  'Arrakeen':            'stronghold',
  'Carthag':             'stronghold',
  'Sietch Tabr':         'stronghold',
  'Habbanya Sietch':     'stronghold',
  "Tuek's Sietch":       'stronghold',
  'Tsimpo':              'rock',
  'Harg Pass':           'rock',
  'Cielago East':        'rock',
  'Cielago West':        'rock',
  'Wind Pass':           'rock',
  'Wind Pass North':     'rock',
  'Broken Land':         'rock',
  'Rim Wall West':       'rock',
  'Sihaya Ridge':        'rock',
  'Hole in the Rock':    'rock',
  'Shield Wall':         'rock',
  'Pasty Mesa':          'rock',
  'False Wall East':     'rock',
  'South Mesa':          'rock',
  'False Wall South':    'rock',
  'Cielago North':       'rock',
  'False Wall West':     'rock',
  'Bight of the Cliff':  'rock',
  'Plastic Basin':       'rock',
  'Imperial Basin':      'sand',
  'Arsunt':              'sand',
  'Hagga Basin':         'sand',
  'Old Gap':             'sand',
  'Basin':               'sand',
  'Gara Kulon':          'sand',
  'Red Chasm':           'sand',
  'The Minor Erg':       'sand',
  'Cielago Depression':  'sand',
  'Cielago South':       'sand',
  'Meridian':            'sand',
  'Habbanya Ridge Flat': 'sand',
  'Habbanya Erg':        'sand',
  'The Greater Flat':    'sand',
  'The Great Flat':      'sand',
  'Funeral Plain':       'sand',
}

// ─── Label abbreviations for multi-line territory names ─────────────────────────
const LABEL_ABBREV = {
  'Imperial Basin':      ['Imperial', 'Basin'],
  'Rim Wall West':       ['Rim Wall', 'West'],
  'Sihaya Ridge':        ['Sihaya', 'Ridge'],
  'Shield Wall':         ['Shield', 'Wall'],
  'Pasty Mesa':          ['Pasty', 'Mesa'],
  'False Wall East':     ['False Wall', 'East'],
  'South Mesa':          ['South', 'Mesa'],
  'False Wall South':    ['False Wall', 'South'],
  'Cielago North':       ['Cielago', 'North'],
  'False Wall West':     ['False Wall', 'West'],
  'Hagga Basin':         ['Hagga', 'Basin'],
  'Bight of the Cliff':  ['Bight of', 'the Cliff'],
  'Sietch Tabr':         ['Sietch', 'Tabr'],
  'Plastic Basin':       ['Plastic', 'Basin'],
  'Broken Land':         ['Broken', 'Land'],
  'Hole in the Rock':    ['Hole in', 'the Rock'],
  'Harg Pass':           ['Harg', 'Pass'],
  "Tuek's Sietch":       ["Tuek's", 'Sietch'],
  'Cielago East':        ['Cielago', 'East'],
  'Cielago West':        ['Cielago', 'West'],
  'Habbanya Sietch':     ['Habbanya', 'Sietch'],
  'Wind Pass':           ['Wind', 'Pass'],
  'Wind Pass North':     ['Wind Pass', 'North'],
  'Old Gap':             ['Old', 'Gap'],
  'Gara Kulon':          ['Gara', 'Kulon'],
  'Red Chasm':           ['Red', 'Chasm'],
  'The Minor Erg':       ['The Minor', 'Erg'],
  'Cielago Depression':  ['Cielago', 'Depress.'],
  'Cielago South':       ['Cielago', 'South'],
  'Habbanya Ridge Flat': ['Habbanya', 'Ridge Flat'],
  'Habbanya Erg':        ['Habbanya', 'Erg'],
  'The Greater Flat':    ['The Greater', 'Flat'],
  'The Great Flat':      ['The Great', 'Flat'],
  'Funeral Plain':       ['Funeral', 'Plain'],
}

// ─── Math helpers ───────────────────────────────────────────────────────────────

function sectorToRad(s) {
  return (s * 20 - 90) * (Math.PI / 180)
}

function degToRad(deg) {
  return (deg - 90) * (Math.PI / 180)
}

/** Convert (angle deg, normR) to SVG pixel coords. 0 deg = 12 o'clock, clockwise. */
function polyPt(deg, normR) {
  const rad = degToRad(deg)
  const r = normR * BR
  return { x: CX + r * Math.cos(rad), y: CY + r * Math.sin(rad) }
}

/** SVG path for an annular arc (wedge shape). */
function makeArcPath(cx, cy, ri, ro, s0, s1) {
  const a0 = sectorToRad(s0)
  const a1 = sectorToRad(s1)
  const spanDeg = (s1 - s0) * 20
  const large = spanDeg > 180 ? 1 : 0

  const x0o = cx + ro * Math.cos(a0), y0o = cy + ro * Math.sin(a0)
  const x1o = cx + ro * Math.cos(a1), y1o = cy + ro * Math.sin(a1)
  const x1i = cx + ri * Math.cos(a1), y1i = cy + ri * Math.sin(a1)
  const x0i = cx + ri * Math.cos(a0), y0i = cy + ri * Math.sin(a0)

  return [
    `M ${x0o.toFixed(2)} ${y0o.toFixed(2)}`,
    `A ${ro} ${ro} 0 ${large} 1 ${x1o.toFixed(2)} ${y1o.toFixed(2)}`,
    `L ${x1i.toFixed(2)} ${y1i.toFixed(2)}`,
    `A ${ri} ${ri} 0 ${large} 0 ${x0i.toFixed(2)} ${y0i.toFixed(2)}`,
    'Z',
  ].join(' ')
}

/** Centroid of an annular arc. */
function arcCentroid(cx, cy, ri, ro, s0, s1) {
  const midA = sectorToRad((s0 + s1) / 2)
  const midR = (ri + ro) / 2
  return { x: cx + midR * Math.cos(midA), y: cy + midR * Math.sin(midA) }
}

/**
 * SVG path for a polygon territory.
 * arcEdges: [[i, j, radius]] vertex-index pairs drawn as circular arcs.
 */
function makePolyPath(vertices, arcEdges = []) {
  const pts = vertices.map(([d, r]) => polyPt(d, r))
  const arcMap = {}
  for (const edge of arcEdges) {
    const [i, j, r] = edge.length === 3 ? edge : [...edge, R_POLAR]
    arcMap[`${i},${j}`] = r
  }
  let d = `M ${pts[0].x.toFixed(2)} ${pts[0].y.toFixed(2)}`
  for (let i = 0; i < pts.length; i++) {
    const j = (i + 1) % pts.length
    const p = pts[j]
    const key = `${i},${j}`
    if (arcMap[key] !== undefined) {
      const r = arcMap[key]
      const absR = Math.abs(r)
      const sweep = r > 0 ? 1 : 0
      d += ` A ${absR} ${absR} 0 0 ${sweep} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`
    } else {
      d += ` L ${p.x.toFixed(2)} ${p.y.toFixed(2)}`
    }
  }
  return d + ' Z'
}

/** Geometric centroid via shoelace formula. */
function polyCentroid(vertices) {
  const pts = vertices.map(([d, r]) => polyPt(d, r))
  const n = pts.length
  let area = 0, cx = 0, cy = 0
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n
    const cross = pts[i].x * pts[j].y - pts[j].x * pts[i].y
    area += cross
    cx += (pts[i].x + pts[j].x) * cross
    cy += (pts[i].y + pts[j].y) * cross
  }
  area /= 2
  cx /= (6 * area)
  cy /= (6 * area)
  return { x: cx, y: cy }
}

// ─── Territory definitions ──────────────────────────────────────────────────────
//
// All territories use exact sector-aligned boundaries to guarantee zero gaps.
//   • Sector boundaries at multiples of 20° (sector N = N×20°)
//   • Ring boundaries at exact normalised radii: 0.175, 0.46, 0.68, 0.915
//   • Adjacent territories share identical boundary vertices
//   • Midpoint vertices on each arc edge approximate circular curves
//   • The organicBorders displacement filter adds visual waviness
//
// INNER  band: polar sink (0.175) → inner ring (0.46)
// MIDDLE band: inner ring  (0.46) → middle ring (0.68)
// OUTER  band: middle ring (0.68) → outer ring  (0.915)

const TERRITORY_POLYGONS = {

  // ── INNER BAND (polar sink 0.175 → inner ring 0.46) ──────────────────────────
  // Arc edges along the polar sink ensure the inner boundary follows the circle.
  // Gap at 270°→300° is intentional (rock underlay, no distinct territory).

  'Imperial Basin': {
    band: 'inner',
    vertices: [
      [0, 0.175], [20, 0.175], [40, 0.175], [60, 0.175],
      [60, 0.46], [40, 0.46], [20, 0.46], [0, 0.46],
    ],
    arcEdges: [[0,1,R_POLAR],[1,2,R_POLAR],[2,3,R_POLAR]],
    centroid: [30, 0.32],
  },

  'Hole in the Rock': {
    band: 'inner',
    vertices: [
      [60, 0.175], [75, 0.175], [90, 0.175],
      [90, 0.46], [75, 0.46], [60, 0.46],
    ],
    arcEdges: [[0,1,R_POLAR],[1,2,R_POLAR]],
    centroid: [75, 0.32],
  },

  'Harg Pass': {
    band: 'inner',
    vertices: [
      [90, 0.175], [110, 0.175], [130, 0.175],
      [130, 0.46], [110, 0.46], [90, 0.46],
    ],
    arcEdges: [[0,1,R_POLAR],[1,2,R_POLAR]],
    centroid: [110, 0.32],
  },

  "Tuek's Sietch": {
    band: 'inner',
    vertices: [
      [130, 0.175], [145, 0.175], [160, 0.175],
      [160, 0.46], [145, 0.46], [130, 0.46],
    ],
    arcEdges: [[0,1,R_POLAR],[1,2,R_POLAR]],
    centroid: [145, 0.32],
  },

  'Cielago East': {
    band: 'inner',
    vertices: [
      [160, 0.175], [175, 0.175], [190, 0.175],
      [190, 0.46], [175, 0.46], [160, 0.46],
    ],
    arcEdges: [[0,1,R_POLAR],[1,2,R_POLAR]],
    centroid: [175, 0.32],
  },

  'Cielago West': {
    band: 'inner',
    vertices: [
      [190, 0.175], [200, 0.175], [210, 0.175],
      [210, 0.46], [200, 0.46], [190, 0.46],
    ],
    arcEdges: [[0,1,R_POLAR],[1,2,R_POLAR]],
    centroid: [200, 0.32],
  },

  'Habbanya Sietch': {
    band: 'inner',
    vertices: [
      [210, 0.175], [225, 0.175], [240, 0.175],
      [240, 0.46], [225, 0.46], [210, 0.46],
    ],
    arcEdges: [[0,1,R_POLAR],[1,2,R_POLAR]],
    centroid: [225, 0.32],
  },

  'Arsunt': {
    band: 'inner',
    vertices: [
      [240, 0.175], [255, 0.175], [270, 0.175],
      [270, 0.46], [255, 0.46], [240, 0.46],
    ],
    arcEdges: [[0,1,R_POLAR],[1,2,R_POLAR]],
    centroid: [255, 0.32],
  },

  'Wind Pass': {
    band: 'inner',
    vertices: [
      [300, 0.175], [310, 0.175], [320, 0.175],
      [320, 0.46], [310, 0.46], [300, 0.46],
    ],
    arcEdges: [[0,1,R_POLAR],[1,2,R_POLAR]],
    centroid: [310, 0.32],
  },

  'Wind Pass North': {
    band: 'inner',
    vertices: [
      [320, 0.175], [330, 0.175], [340, 0.175],
      [340, 0.46], [330, 0.46], [320, 0.46],
    ],
    arcEdges: [[0,1,R_POLAR],[1,2,R_POLAR]],
    centroid: [330, 0.32],
  },

  'Carthag': {
    band: 'inner',
    vertices: [
      [340, 0.175], [350, 0.175], [360, 0.175],
      [360, 0.46], [350, 0.46], [340, 0.46],
    ],
    arcEdges: [[0,1,R_POLAR],[1,2,R_POLAR]],
    centroid: [350, 0.32],
  },

  // ── INSET STRONGHOLD (drawn on top of inner band) ─────────────────────────────

  'Arrakeen': {
    band: 'inset',
    vertices: [
      [25, 0.24], [45, 0.24], [47, 0.34], [45, 0.44],
      [25, 0.44], [23, 0.34],
    ],
    arcEdges: [],
    centroid: [35, 0.35],
  },

  // ── MIDDLE BAND (inner ring 0.46 → middle ring 0.68) ──────────────────────────
  // Full 360° tiling — no gaps.  Adjacent territories share boundary angles.

  'Broken Land': {
    band: 'middle',
    vertices: [
      [350, 0.46], [10, 0.46], [30, 0.46],
      [30, 0.68], [10, 0.68], [350, 0.68],
    ],
    arcEdges: [],
    centroid: [10, 0.57],
  },

  'Rim Wall West': {
    band: 'middle',
    vertices: [
      [30, 0.46], [45, 0.46], [60, 0.46],
      [60, 0.68], [45, 0.68], [30, 0.68],
    ],
    arcEdges: [],
    centroid: [45, 0.57],
  },

  'Sihaya Ridge': {
    band: 'middle',
    vertices: [
      [60, 0.46], [70, 0.46], [80, 0.46],
      [80, 0.68], [70, 0.68], [60, 0.68],
    ],
    arcEdges: [],
    centroid: [70, 0.57],
  },

  'Shield Wall': {
    band: 'middle',
    vertices: [
      [80, 0.46], [90, 0.46], [100, 0.46],
      [100, 0.68], [90, 0.68], [80, 0.68],
    ],
    arcEdges: [],
    centroid: [90, 0.57],
  },

  'Pasty Mesa': {
    band: 'middle',
    vertices: [
      [100, 0.46], [110, 0.46], [120, 0.46],
      [120, 0.68], [110, 0.68], [100, 0.68],
    ],
    arcEdges: [],
    centroid: [110, 0.57],
  },

  'False Wall East': {
    band: 'middle',
    vertices: [
      [120, 0.46], [130, 0.46], [140, 0.46],
      [140, 0.68], [130, 0.68], [120, 0.68],
    ],
    arcEdges: [],
    centroid: [130, 0.57],
  },

  'South Mesa': {
    band: 'middle',
    vertices: [
      [140, 0.46], [150, 0.46], [160, 0.46],
      [160, 0.68], [150, 0.68], [140, 0.68],
    ],
    arcEdges: [],
    centroid: [150, 0.57],
  },

  'False Wall South': {
    band: 'middle',
    vertices: [
      [160, 0.46], [170, 0.46], [180, 0.46],
      [180, 0.68], [170, 0.68], [160, 0.68],
    ],
    arcEdges: [],
    centroid: [170, 0.57],
  },

  'Cielago North': {
    band: 'middle',
    vertices: [
      [180, 0.46], [195, 0.46], [210, 0.46],
      [210, 0.68], [195, 0.68], [180, 0.68],
    ],
    arcEdges: [],
    centroid: [195, 0.57],
  },

  'False Wall West': {
    band: 'middle',
    vertices: [
      [210, 0.46], [225, 0.46], [240, 0.46],
      [240, 0.68], [225, 0.68], [210, 0.68],
    ],
    arcEdges: [],
    centroid: [225, 0.57],
  },

  'Hagga Basin': {
    band: 'middle',
    vertices: [
      [240, 0.46], [255, 0.46], [270, 0.46],
      [270, 0.68], [255, 0.68], [240, 0.68],
    ],
    arcEdges: [],
    centroid: [255, 0.57],
  },

  'Sietch Tabr': {
    band: 'middle',
    vertices: [
      [270, 0.46], [280, 0.46], [290, 0.46],
      [290, 0.68], [280, 0.68], [270, 0.68],
    ],
    arcEdges: [],
    centroid: [280, 0.57],
  },

  'Bight of the Cliff': {
    band: 'middle',
    vertices: [
      [290, 0.46], [300, 0.46], [310, 0.46],
      [310, 0.68], [300, 0.68], [290, 0.68],
    ],
    arcEdges: [],
    centroid: [300, 0.57],
  },

  'Plastic Basin': {
    band: 'middle',
    vertices: [
      [310, 0.46], [325, 0.46], [340, 0.46],
      [340, 0.68], [325, 0.68], [310, 0.68],
    ],
    arcEdges: [],
    centroid: [325, 0.57],
  },

  'Tsimpo': {
    band: 'middle',
    vertices: [
      [340, 0.46], [345, 0.46], [350, 0.46],
      [350, 0.68], [345, 0.68], [340, 0.68],
    ],
    arcEdges: [],
    centroid: [345, 0.57],
  },

  // ── OUTER BAND (middle ring 0.68 → outer ring 0.915) ─────────────────────────
  // Full 360° tiling.  Boundary angles differ from middle band in places
  // (e.g. Meridian / Habbanya Ridge Flat split at 246°).

  'Old Gap': {
    band: 'outer',
    vertices: [
      [350, 0.68], [10, 0.68], [30, 0.68],
      [30, 0.915], [10, 0.915], [350, 0.915],
    ],
    arcEdges: [],
    centroid: [10, 0.80],
  },

  'Basin': {
    band: 'outer',
    vertices: [
      [30, 0.68], [45, 0.68], [60, 0.68],
      [60, 0.915], [45, 0.915], [30, 0.915],
    ],
    arcEdges: [],
    centroid: [45, 0.80],
  },

  'Gara Kulon': {
    band: 'outer',
    vertices: [
      [60, 0.68], [75, 0.68], [90, 0.68],
      [90, 0.915], [75, 0.915], [60, 0.915],
    ],
    arcEdges: [],
    centroid: [75, 0.80],
  },

  'Red Chasm': {
    band: 'outer',
    vertices: [
      [90, 0.68], [105, 0.68], [120, 0.68],
      [120, 0.915], [105, 0.915], [90, 0.915],
    ],
    arcEdges: [],
    centroid: [105, 0.80],
  },

  'The Minor Erg': {
    band: 'outer',
    vertices: [
      [120, 0.68], [140, 0.68], [160, 0.68],
      [160, 0.915], [140, 0.915], [120, 0.915],
    ],
    arcEdges: [],
    centroid: [140, 0.80],
  },

  'Cielago Depression': {
    band: 'outer',
    vertices: [
      [160, 0.68], [175, 0.68], [190, 0.68],
      [190, 0.915], [175, 0.915], [160, 0.915],
    ],
    arcEdges: [],
    centroid: [175, 0.80],
  },

  'Cielago South': {
    band: 'outer',
    vertices: [
      [190, 0.68], [205, 0.68], [220, 0.68],
      [220, 0.915], [205, 0.915], [190, 0.915],
    ],
    arcEdges: [],
    centroid: [205, 0.80],
  },

  'Meridian': {
    band: 'outer',
    vertices: [
      [220, 0.68], [233, 0.68], [246, 0.68],
      [246, 0.915], [233, 0.915], [220, 0.915],
    ],
    arcEdges: [],
    centroid: [233, 0.80],
  },

  'Habbanya Ridge Flat': {
    band: 'outer',
    vertices: [
      [246, 0.68], [258, 0.68], [270, 0.68],
      [270, 0.915], [258, 0.915], [246, 0.915],
    ],
    arcEdges: [],
    centroid: [258, 0.80],
  },

  'Habbanya Erg': {
    band: 'outer',
    vertices: [
      [270, 0.68], [280, 0.68], [290, 0.68],
      [290, 0.915], [280, 0.915], [270, 0.915],
    ],
    arcEdges: [],
    centroid: [280, 0.80],
  },

  'The Greater Flat': {
    band: 'outer',
    vertices: [
      [290, 0.68], [300, 0.68], [310, 0.68],
      [310, 0.915], [300, 0.915], [290, 0.915],
    ],
    arcEdges: [],
    centroid: [300, 0.80],
  },

  'The Great Flat': {
    band: 'outer',
    vertices: [
      [310, 0.68], [320, 0.68], [330, 0.68],
      [330, 0.915], [320, 0.915], [310, 0.915],
    ],
    arcEdges: [],
    centroid: [320, 0.80],
  },

  'Funeral Plain': {
    band: 'outer',
    vertices: [
      [330, 0.68], [340, 0.68], [350, 0.68],
      [350, 0.915], [340, 0.915], [330, 0.915],
    ],
    arcEdges: [],
    centroid: [340, 0.80],
  },
}

// Arc definitions — fallback for territories without polygon data
const TERRITORY_ARCS = {
  // INNER BAND
  'Arrakeen':          { s0:  1.5, s1:  3.0, ri: R_POLAR,  ro: R_INNER },
  'Hole in the Rock':  { s0:  3.0, s1:  4.5, ri: R_POLAR,  ro: R_INNER },
  'Imperial Basin':    { s0:  1.5, s1:  6.0, ri: R_POLAR,  ro: R_INNER },
  'Harg Pass':         { s0:  4.5, s1:  6.5, ri: R_POLAR,  ro: R_INNER },
  "Tuek's Sietch":     { s0:  6.5, s1:  8.0, ri: R_POLAR,  ro: R_INNER },
  'Cielago East':      { s0:  8.0, s1:  9.5, ri: R_POLAR,  ro: R_INNER },
  'Cielago West':      { s0:  9.5, s1: 10.5, ri: R_POLAR,  ro: R_INNER },
  'Habbanya Sietch':   { s0: 10.5, s1: 12.0, ri: R_POLAR,  ro: R_INNER },
  'Arsunt':            { s0: 12.0, s1: 13.5, ri: R_POLAR,  ro: R_INNER },
  'Wind Pass':         { s0: 15.0, s1: 16.0, ri: R_POLAR,  ro: R_INNER },
  'Wind Pass North':   { s0: 16.0, s1: 17.0, ri: R_POLAR,  ro: R_INNER },
  'Carthag':           { s0: 17.0, s1: 18.0, ri: R_POLAR,  ro: R_INNER },
  // MIDDLE BAND
  'Broken Land':       { s0: 17.5, s1: 19.5, ri: R_INNER,  ro: R_MIDDLE },
  'Tsimpo':            { s0: 17.0, s1: 17.5, ri: R_INNER,  ro: R_MIDDLE },
  'Plastic Basin':     { s0: 15.5, s1: 17.0, ri: R_INNER,  ro: R_MIDDLE },
  'Bight of the Cliff':{ s0: 14.5, s1: 15.5, ri: R_INNER,  ro: R_MIDDLE },
  'Sietch Tabr':       { s0: 13.5, s1: 14.5, ri: R_INNER,  ro: R_MIDDLE },
  'Hagga Basin':       { s0: 12.0, s1: 13.5, ri: R_INNER,  ro: R_MIDDLE },
  'False Wall West':   { s0: 10.5, s1: 12.0, ri: R_INNER,  ro: R_MIDDLE },
  'Cielago North':     { s0:  9.0, s1: 10.5, ri: R_INNER,  ro: R_MIDDLE },
  'False Wall South':  { s0:  8.0, s1:  9.0, ri: R_INNER,  ro: R_MIDDLE },
  'South Mesa':        { s0:  7.0, s1:  8.0, ri: R_INNER,  ro: R_MIDDLE },
  'False Wall East':   { s0:  6.0, s1:  7.0, ri: R_INNER,  ro: R_MIDDLE },
  'Pasty Mesa':        { s0:  5.0, s1:  6.0, ri: R_INNER,  ro: R_MIDDLE },
  'Shield Wall':       { s0:  4.0, s1:  5.0, ri: R_INNER,  ro: R_MIDDLE },
  'Sihaya Ridge':      { s0:  3.0, s1:  4.0, ri: R_INNER,  ro: R_MIDDLE },
  'Rim Wall West':     { s0:  1.5, s1:  3.0, ri: R_INNER,  ro: R_MIDDLE },
  // OUTER BAND
  'Old Gap':           { s0: 17.5, s1: 19.5, ri: R_MIDDLE, ro: R_OUTER },
  'Basin':             { s0:  1.5, s1:  3.0, ri: R_MIDDLE, ro: R_OUTER },
  'Gara Kulon':        { s0:  3.0, s1:  4.5, ri: R_MIDDLE, ro: R_OUTER },
  'Red Chasm':         { s0:  4.5, s1:  6.0, ri: R_MIDDLE, ro: R_OUTER },
  'The Minor Erg':     { s0:  6.0, s1:  8.0, ri: R_MIDDLE, ro: R_OUTER },
  'Cielago Depression':{ s0:  8.0, s1:  9.5, ri: R_MIDDLE, ro: R_OUTER },
  'Cielago South':     { s0:  9.5, s1: 11.0, ri: R_MIDDLE, ro: R_OUTER },
  'Meridian':          { s0: 11.0, s1: 12.3, ri: R_MIDDLE, ro: R_OUTER },
  'Habbanya Ridge Flat':{ s0:12.3, s1: 13.5, ri: R_MIDDLE, ro: R_OUTER },
  'Habbanya Erg':      { s0: 13.5, s1: 14.5, ri: R_MIDDLE, ro: R_OUTER },
  'The Greater Flat':  { s0: 14.5, s1: 15.5, ri: R_MIDDLE, ro: R_OUTER },
  'The Great Flat':    { s0: 15.5, s1: 16.5, ri: R_MIDDLE, ro: R_OUTER },
  'Funeral Plain':     { s0: 16.5, s1: 17.5, ri: R_MIDDLE, ro: R_OUTER },
}

// ─── Force map builder ──────────────────────────────────────────────────────────

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

// ─── Centroid calculator ────────────────────────────────────────────────────────

function getTerritoryCentroid(name) {
  const poly = TERRITORY_POLYGONS[name]
  if (poly) {
    if (poly.centroid) {
      return polyPt(poly.centroid[0], poly.centroid[1])
    }
    return polyCentroid(poly.vertices)
  }
  const arc = TERRITORY_ARCS[name]
  if (arc) {
    return arcCentroid(CX, CY, arc.ri, arc.ro, arc.s0, arc.s1)
  }
  return { x: CX, y: CY }
}

// ─── Path calculator ────────────────────────────────────────────────────────────

function getTerritoryPath(name) {
  const poly = TERRITORY_POLYGONS[name]
  if (poly) {
    return makePolyPath(poly.vertices, poly.arcEdges)
  }
  const arc = TERRITORY_ARCS[name]
  if (arc) {
    return makeArcPath(CX, CY, arc.ri, arc.ro, arc.s0, arc.s1)
  }
  return null
}

// ─── Get fill colour for a territory based on its type ──────────────────────────

function getTerritoryFill(name) {
  const type = TERRITORY_TYPES[name]
  if (type === 'stronghold') return C.stronghold
  if (type === 'sand') return C.sand
  if (type === 'rock') return C.rock
  return C.rock // fallback
}

// ─── SVG Definitions ────────────────────────────────────────────────────────────

function BoardDefs() {
  return (
    <defs>
      {/* Parchment gradient */}
      <radialGradient id="parchmentGrad" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stopColor="#E8D8B0" />
        <stop offset="70%" stopColor="#D8C898" />
        <stop offset="100%" stopColor="#C8B878" />
      </radialGradient>

      {/* Parchment noise texture — very subtle grain */}
      <filter id="parchmentTexture" filterUnits="objectBoundingBox">
        <feTurbulence type="fractalNoise" baseFrequency="0.4" numOctaves="3" seed="2" result="noise" />
        <feColorMatrix type="saturate" values="0" in="noise" result="graynoise" />
        <feComponentTransfer in="graynoise" result="faintNoise">
          <feFuncA type="linear" slope="0.12" intercept="0" />
        </feComponentTransfer>
        <feBlend in="SourceGraphic" in2="faintNoise" mode="multiply" />
      </filter>

      {/* Organic border displacement */}
      <filter id="organicBorders" filterUnits="userSpaceOnUse" x="0" y="0" width="700" height="730">
        <feTurbulence type="turbulence" baseFrequency="0.018" numOctaves="4" seed="42" result="noise" />
        <feDisplacementMap in="SourceGraphic" in2="noise" scale="5" xChannelSelector="R" yChannelSelector="G" />
      </filter>

      {/* Stronghold hatching pattern */}
      <pattern id="strongholdHatch" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="6" stroke="#3A200880" strokeWidth="1" />
      </pattern>

      {/* Highlight glow filters */}
      <filter id="glowGreen" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="4" result="blur" />
        <feFlood floodColor="#22c55e" floodOpacity="0.7" result="color" />
        <feComposite in="color" in2="blur" operator="in" result="glow" />
        <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>
      <filter id="glowBlue" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="4" result="blur" />
        <feFlood floodColor="#3b82f6" floodOpacity="0.7" result="color" />
        <feComposite in="color" in2="blur" operator="in" result="glow" />
        <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>
      <filter id="glowTeal" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="3" result="blur" />
        <feFlood floodColor="#0d9488" floodOpacity="0.5" result="color" />
        <feComposite in="color" in2="blur" operator="in" result="glow" />
        <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>

      {/* Spice glow filter */}
      <filter id="spiceGlow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="2" result="blur" />
        <feFlood floodColor={C.spiceGlow} floodOpacity="0.6" result="color" />
        <feComposite in="color" in2="blur" operator="in" result="glow" />
        <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>
    </defs>
  )
}

// ─── Layer 2: Rock Band Underlays ───────────────────────────────────────────────

function RockBandUnderlays() {
  return (
    <g>
      {/* Inner band: R_POLAR to R_INNER */}
      <circle cx={CX} cy={CY} r={R_INNER} fill={C.rock} />
      {/* Middle band: R_INNER to R_MIDDLE */}
      <circle cx={CX} cy={CY} r={R_MIDDLE} fill={C.rock} />
      {/* Cut out the polar sink area — painted over by polar sink layer */}
    </g>
  )
}

// ─── Layer 3: Territory Fill (no stroke) ────────────────────────────────────────

function TerritoryFill({ name }) {
  const path = getTerritoryPath(name)
  if (!path) return null
  const type = TERRITORY_TYPES[name]
  const fill = getTerritoryFill(name)
  const isStronghold = type === 'stronghold'

  return (
    <g>
      <path
        d={path}
        fill={fill}
        stroke={C.border}
        strokeWidth={isStronghold ? 1.6 : 1.0}
        strokeLinejoin="round"
        strokeOpacity={0.6}
      />
      {/* Stronghold hatching overlay */}
      {isStronghold && (
        <path d={path} fill="url(#strongholdHatch)" stroke="none" opacity={0.5} />
      )}
    </g>
  )
}

// ─── Layer 4: Storm Sweep ───────────────────────────────────────────────────────

function StormSweep({ stormSector }) {
  const s0 = stormSector - 0.5
  const s1 = stormSector + 0.5
  const path = makeArcPath(CX, CY, R_POLAR, R_OUTER, s0, s1)
  return (
    <path d={path} fill={C.storm} fillOpacity={0.15} stroke={C.storm} strokeWidth={1.5} strokeOpacity={0.6} />
  )
}

// ─── Layer 5: Territory Borders (organic displaced strokes) ─────────────────────
//
// Only territory polygon outlines — NO separate sector lines or ring circles.
// The territory shapes themselves define all visible boundaries on the map.

function TerritoryBorders() {
  const borderPaths = []
  const allNames = Object.keys(TERRITORY_POLYGONS)
  for (const name of allNames) {
    const path = getTerritoryPath(name)
    if (path) {
      const type = TERRITORY_TYPES[name]
      const isStronghold = type === 'stronghold'
      borderPaths.push(
        <path
          key={`border-${name}`}
          d={path}
          fill="none"
          stroke={C.border}
          strokeWidth={isStronghold ? 1.8 : 1.2}
          strokeLinejoin="round"
          opacity={0.8}
        />
      )
    }
  }

  // Outer board edge circle
  borderPaths.push(
    <circle
      key="outer-edge"
      cx={CX} cy={CY} r={R_OUTER}
      fill="none" stroke={C.borderThick} strokeWidth={2.0}
    />
  )

  return (
    <g filter="url(#organicBorders)">
      {borderPaths}
    </g>
  )
}

// ─── Layer 6: Polar Sink ────────────────────────────────────────────────────────

function PolarSink({ forces }) {
  return (
    <g>
      <circle cx={CX} cy={CY} r={R_POLAR} fill={C.polar} />
      <circle cx={CX} cy={CY} r={R_POLAR - 6} fill="none" stroke={C.polarStroke} strokeWidth={1} strokeDasharray="4 3" opacity={0.6} />
      <text
        x={CX} y={CY - 6}
        textAnchor="middle" dominantBaseline="central"
        fill={C.textDark} fontSize={9} fontWeight="bold" fontFamily="serif"
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        POLAR
      </text>
      <text
        x={CX} y={CY + 6}
        textAnchor="middle" dominantBaseline="central"
        fill={C.textDark} fontSize={9} fontWeight="bold" fontFamily="serif"
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        SINK
      </text>
      {/* Force tokens in the Polar Sink */}
      {forces && forces.length > 0 && (
        <g>
          {forces.map((entry, i) => {
            const dotX = CX - ((forces.length - 1) * 9) / 2 + i * 9
            const dotY = CY + 24
            return (
              <g key={entry.faction}>
                <circle cx={dotX} cy={dotY} r={6}
                  fill={FACTION_FILL[entry.faction] || '#888'}
                  stroke="#00000050" strokeWidth={0.8}
                  opacity={0.95} />
                <text
                  x={dotX} y={dotY + 0.5}
                  textAnchor="middle" dominantBaseline="central"
                  fill="#000" fontSize={6.5} fontWeight="bold"
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

// ─── Layer 7: Territory Labels ──────────────────────────────────────────────────

function TerritoryLabel({ name }) {
  if (name === 'Polar Sink') return null
  const { x: cx, y: cy } = getTerritoryCentroid(name)
  const type = TERRITORY_TYPES[name]
  const isStronghold = type === 'stronghold'
  const lines = LABEL_ABBREV[name] || [name]
  const fontSize = isStronghold ? 7 : 5.5
  const fill = isStronghold ? C.textGold : C.textDark
  const fontWeight = isStronghold ? 'bold' : 'normal'

  const startY = cy - ((lines.length - 1) * (fontSize + 1)) / 2

  return (
    <g style={{ pointerEvents: 'none', userSelect: 'none' }}>
      {/* Stronghold fortress icon */}
      {isStronghold && (
        <g transform={`translate(${cx}, ${startY - fontSize - 4})`}>
          <polygon
            points="-5,2 -5,-2 -3,-2 -3,-4 -1,-4 -1,-2 1,-2 1,-4 3,-4 3,-2 5,-2 5,2"
            fill={C.textGold}
            opacity={0.8}
          />
        </g>
      )}
      {lines.map((line, i) => (
        <text
          key={i}
          x={cx} y={startY + i * (fontSize + 1)}
          textAnchor="middle" dominantBaseline="central"
          fill={fill} fontSize={fontSize} fontWeight={fontWeight}
          fontFamily="serif"
          opacity={0.85}
        >
          {line}
        </text>
      ))}
    </g>
  )
}

// ─── Layer 8: Spice Indicator ───────────────────────────────────────────────────

function SpiceIndicator({ name, territory }) {
  if (!territory.current_spice || territory.current_spice <= 0) return null
  const { x: cx, y: cy } = getTerritoryCentroid(name)

  return (
    <g>
      <circle cx={cx + 16} cy={cy - 6} r={7}
        fill="rgba(200,80,0,0.25)" stroke={C.spice} strokeWidth={0.8} />
      <text
        x={cx + 16} y={cy - 5.5}
        textAnchor="middle" dominantBaseline="central"
        fill={C.spice} fontSize={7} fontWeight="bold" fontFamily="serif"
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        {territory.current_spice}
      </text>
    </g>
  )
}

// ─── Layer 8: Force Tokens ──────────────────────────────────────────────────────

function ForceTokens({ name, forceEntries }) {
  if (!forceEntries || forceEntries.length === 0) return null
  const { x: cx, y: cy } = getTerritoryCentroid(name)

  return (
    <g>
      {forceEntries.map((entry, i) => {
        const totalDots = forceEntries.length
        const dotX = cx - ((totalDots - 1) * 9) / 2 + i * 9
        const dotY = cy + 8
        return (
          <g key={entry.faction}>
            <circle cx={dotX} cy={dotY} r={6}
              fill={FACTION_FILL[entry.faction] || '#888'}
              stroke="#00000050" strokeWidth={0.8}
              opacity={0.95} />
            <text
              x={dotX} y={dotY + 0.5}
              textAnchor="middle" dominantBaseline="central"
              fill="#000" fontSize={6.5} fontWeight="bold"
              style={{ pointerEvents: 'none', userSelect: 'none' }}
            >
              {entry.count}
            </text>
          </g>
        )
      })}
    </g>
  )
}

// ─── Layer 8: Territory Highlight ───────────────────────────────────────────────

function TerritoryHighlight({ name, highlight }) {
  if (!highlight) return null
  const path = getTerritoryPath(name)
  if (!path) return null

  const glowColor =
    highlight === 'from'     ? '#22c55e' :
    highlight === 'to'       ? '#3b82f6' :
    highlight === 'adjacent' ? '#0d9488' :
    null
  const glowFilter =
    highlight === 'from'     ? 'url(#glowGreen)' :
    highlight === 'to'       ? 'url(#glowBlue)' :
    highlight === 'adjacent' ? 'url(#glowTeal)' :
    null
  const fillOpacity =
    highlight === 'from'     ? 0.25 :
    highlight === 'to'       ? 0.25 :
    highlight === 'adjacent' ? 0.15 :
    0

  if (!glowColor) return null

  return (
    <path
      d={path}
      fill={glowColor}
      fillOpacity={fillOpacity}
      stroke={glowColor}
      strokeWidth={highlight === 'adjacent' ? 2 : 3}
      strokeOpacity={highlight === 'adjacent' ? 0.5 : 0.8}
      filter={glowFilter}
    />
  )
}

// ─── Layer 9: Outer Frame ───────────────────────────────────────────────────────

function OuterFrame({ stormSector }) {
  const sectorDots = []
  const sectorNumbers = []
  for (let s = 0; s < 18; s++) {
    const a = sectorToRad(s)
    // Dots at the outer frame boundary
    const dx = CX + R_FRAME * Math.cos(a)
    const dy = CY + R_FRAME * Math.sin(a)
    sectorDots.push(
      <circle key={`dot-${s}`} cx={dx.toFixed(2)} cy={dy.toFixed(2)} r={2.5}
        fill={C.frameAccent} />
    )
    // Sector numbers outside the frame
    const numR = R_FRAME + 14
    const nx = CX + numR * Math.cos(a)
    const ny = CY + numR * Math.sin(a)
    sectorNumbers.push(
      <text key={`num-${s}`}
        x={nx.toFixed(2)} y={ny.toFixed(2)}
        textAnchor="middle" dominantBaseline="central"
        fill={C.textLight} fontSize={8} fontFamily="serif"
        opacity={0.7}
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        {s}
      </text>
    )
  }

  // Storm position marker
  const stormA = sectorToRad(stormSector)
  const stormX = CX + (R_FRAME + 14) * Math.cos(stormA)
  const stormY = CY + (R_FRAME + 14) * Math.sin(stormA)

  return (
    <g>
      {/* Dark frame ring */}
      <circle cx={CX} cy={CY} r={R_FRAME} fill="none"
        stroke={C.frameMid} strokeWidth={4} />
      <circle cx={CX} cy={CY} r={R_FRAME + 2} fill="none"
        stroke={C.border} strokeWidth={1} opacity={0.5} />

      {sectorDots}
      {sectorNumbers}

      {/* Storm marker */}
      <g>
        <circle cx={stormX.toFixed(2)} cy={stormY.toFixed(2)} r={10}
          fill={C.storm} fillOpacity={0.3}
          stroke={C.storm} strokeWidth={1.5} />
        <text
          x={stormX.toFixed(2)} y={(stormY + 0.5).toFixed(2)}
          textAnchor="middle" dominantBaseline="central"
          fill={C.storm} fontSize={7} fontWeight="bold" fontFamily="serif"
          style={{ pointerEvents: 'none', userSelect: 'none' }}
        >
          S
        </text>
      </g>
    </g>
  )
}

// ─── Title and info labels ──────────────────────────────────────────────────────

function BoardLabels() {
  return (
    <g style={{ pointerEvents: 'none', userSelect: 'none' }}>
      {/* DUNE title at top */}
      <text
        x={CX} y={24}
        textAnchor="middle" dominantBaseline="central"
        fill={C.textGold} fontSize={22} fontWeight="bold" fontFamily="serif"
        letterSpacing="6"
        opacity={0.9}
      >
        DUNE
      </text>

      {/* BENE TLEILAXU TANKS label — bottom left */}
      <text
        x={90} y={VB_H - 18}
        textAnchor="middle" dominantBaseline="central"
        fill={C.textMid} fontSize={7} fontFamily="serif"
        opacity={0.7}
      >
        BENE TLEILAXU TANKS
      </text>

      {/* SPICE BANK label — bottom right */}
      <text
        x={VB_W - 90} y={VB_H - 18}
        textAnchor="middle" dominantBaseline="central"
        fill={C.textMid} fontSize={7} fontFamily="serif"
        opacity={0.7}
      >
        SPICE BANK
      </text>
    </g>
  )
}

// ─── Main board component ───────────────────────────────────────────────────────

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
    if (name === highlightTo) return 'to'
    if (highlightFrom && adjacentSet.has(name)) return 'adjacent'
    return null
  }

  // Collect territory names by band order for correct layering
  const outerNames = []
  const middleNames = []
  const innerNames = []
  const insetNames = []

  for (const [name, poly] of Object.entries(TERRITORY_POLYGONS)) {
    if (poly.band === 'outer') outerNames.push(name)
    else if (poly.band === 'middle') middleNames.push(name)
    else if (poly.band === 'inner') innerNames.push(name)
    else if (poly.band === 'inset') insetNames.push(name)
  }

  const allTerritoryNames = [...outerNames, ...middleNames, ...innerNames, ...insetNames]

  return (
    <div className="bg-[#0f0e0b] border border-[#3a3020] rounded p-2 h-full flex flex-col">
      <svg
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        className="flex-1 w-full min-h-0"
        preserveAspectRatio="xMidYMid meet"
      >
        <BoardDefs />

        {/* LAYER 1: Base */}
        <rect width={VB_W} height={VB_H} fill={C.frameDark} />
        {/* Dark frame circle */}
        <circle cx={CX} cy={CY} r={R_FRAME} fill={C.frameMid} />
        {/* Parchment gradient circle with noise texture */}
        <circle cx={CX} cy={CY} r={R_OUTER} fill="url(#parchmentGrad)" filter="url(#parchmentTexture)" />

        {/* LAYER 2: Rock Band Underlays */}
        <RockBandUnderlays />

        {/* LAYER 3: Territory Fills — outer first, then middle, inner, inset */}
        {/* Sand territories paint ON TOP of rock underlays */}
        {allTerritoryNames.map(name => (
          <TerritoryFill key={`fill-${name}`} name={name} />
        ))}

        {/* LAYER 4: Storm Sweep */}
        <StormSweep stormSector={stormSectorNum} />

        {/* LAYER 5: Organic Borders */}
        <TerritoryBorders />

        {/* LAYER 6: Polar Sink */}
        <PolarSink forces={forceMap['Polar Sink']} />

        {/* LAYER 7: Territory Labels */}
        {allTerritoryNames.map(name => (
          <TerritoryLabel key={`label-${name}`} name={name} />
        ))}

        {/* LAYER 8: Dynamic Game Overlays */}
        {/* Spice indicators */}
        {Object.entries(territories).map(([name, territory]) => (
          <SpiceIndicator key={`spice-${name}`} name={name} territory={territory} />
        ))}

        {/* Force tokens */}
        {Object.entries(territories).map(([name]) => (
          <ForceTokens
            key={`forces-${name}`}
            name={name}
            forceEntries={forceMap[name]}
          />
        ))}

        {/* Movement highlights */}
        {Object.entries(territories).map(([name]) => {
          if (name === 'Polar Sink') return null
          const highlight = getHighlight(name)
          if (!highlight) return null
          return (
            <TerritoryHighlight
              key={`highlight-${name}`}
              name={name}
              highlight={highlight}
            />
          )
        })}

        {/* LAYER 9: Outer Frame */}
        <OuterFrame stormSector={stormSectorNum} />

        {/* Board labels */}
        <BoardLabels />
      </svg>

      {/* Legend bar */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-2 py-1 border-t border-[#3a3020] text-[10px] text-[#8B7040] shrink-0">
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: C.stormFill, border: `1px solid ${C.storm}` }} />
          Storm
        </span>
        <span className="flex items-center gap-1">
          <span className="font-bold text-xs" style={{ color: C.spice }}>&#x2B25;</span>
          Spice
        </span>
        <span style={{ color: '#3a3020' }}>|</span>
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
