/**
 * GameBoard — Rebuilt circular SVG board for the Dune board game.
 * Faithful recreation of the original GF9 board aesthetic:
 *   - Warm parchment color palette
 *   - Organic territory shapes
 *   - Decorative outer border with storm track
 *   - Stronghold fortress markers
 *   - Authentic sector numbering
 *
 * Coordinate system:
 *   Centre: (350, 350), Sector 0 at 12 o'clock, clockwise, 20° per sector.
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

// ─── Board colour palette (original board aesthetic) ────────────────────────────
const C = {
  // Territory fills
  sand:           '#D4B878',
  sandDark:       '#C8A860',
  rock:           '#BFA060',
  rockDark:       '#A08848',
  stronghold:     '#6B4A28',
  strongholdAlt:  '#7B5A30',

  // Borders
  borderThick:    '#4A3520',
  borderThin:     '#6B5030',
  borderFaint:    '#8B7040',

  // Polar Sink
  polar:          '#E8DCC8',
  polarStroke:    '#A09060',

  // Frame & background
  frameDark:      '#1A1008',
  frameMid:       '#2A1E10',
  frameAccent:    '#8B7040',

  // Text
  textDark:       '#3A2510',
  textMid:        '#5A4020',
  textLight:      '#D4BC88',
  textGold:       '#D4A840',

  // Indicators
  spice:          '#C85000',
  spiceGlow:      '#FF8C00',
  storm:          '#CC3333',
  stormFill:      '#CC333320',
}

// ─── Board geometry ─────────────────────────────────────────────────────────────
const CX = 350
const CY = 350
const BR = 310

const R_POLAR  = Math.round(BR * 0.175)   // 54
const R_INNER  = Math.round(BR * 0.46)    // 143
const R_MIDDLE = Math.round(BR * 0.68)    // 211
const R_OUTER  = Math.round(BR * 0.915)   // 284
const R_FRAME  = 332                       // outer frame edge
const R_TRACK  = BR + 4                   // storm track inner edge

// ─── Math helpers ───────────────────────────────────────────────────────────────

function sectorToRad(s) {
  return (s * 20 - 90) * (Math.PI / 180)
}

function degToRad(deg) {
  return (deg - 90) * (Math.PI / 180)
}

/** Convert (angle°, normR) → SVG pixel coords. 0° = 12 o'clock, clockwise. */
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
 * arcEdges: [[i, j, radius]…] — vertex-index pairs drawn as circular arcs.
 * If radius > 0: CW sweep. If radius < 0: CCW sweep.
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
// TERRITORY_POLYGONS: Territories with custom polygon shapes.
//   vertices: [angleDeg, normRadius]  (0° = 12 o'clock, clockwise).
//   arcEdges: [[i, j, radius]…] — vertex pairs drawn as arcs.
//   band: render-pass bucket ('inner' | 'middle' | 'outer').
//   centroid: optional manual label anchor [deg, normR].
//
// TERRITORY_ARCS: All territories with sector-based arc bounds.
//   Used as fallback when no polygon is defined, and for centroid computation.

const TERRITORY_POLYGONS = {

  // ── MIDDLE BAND ──────────────────────────────────────────────────────────────

  'Imperial Basin': {
    band: 'middle',
    vertices: [
      [348, 0.53],
      [  4, 0.56],
      [ 30, 0.55],
      [ 58, 0.54],
      [ 78, 0.49],
      [ 78, 0.28],
      [ 40, 0.29],
      [  0, 0.29],
      [348, 0.28],
    ],
    arcEdges: [],
    centroid: [20, 0.42],
  },

  'Rim Wall West': {
    band: 'middle',
    vertices: [
      [24, 0.46], [56, 0.46],
      [58, 0.54], [56, 0.66],
      [24, 0.67], [22, 0.53],
    ],
    arcEdges: [],
    centroid: [40, 0.56],
  },

  'Sihaya Ridge': {
    band: 'middle',
    vertices: [
      [60, 0.46], [78, 0.46],
      [80, 0.49], [80, 0.67],
      [60, 0.67],
    ],
    arcEdges: [],
    centroid: [70, 0.57],
  },

  'Shield Wall': {
    band: 'middle',
    vertices: [
      [82, 0.46], [98, 0.46],
      [100, 0.50], [99, 0.67],
      [83, 0.68], [81, 0.50],
    ],
    arcEdges: [],
    centroid: [90, 0.57],
  },

  'Pasty Mesa': {
    band: 'middle',
    vertices: [
      [100, 0.46], [118, 0.44],
      [120, 0.67], [100, 0.68],
    ],
    arcEdges: [],
    centroid: [110, 0.56],
  },

  'False Wall East': {
    band: 'middle',
    vertices: [
      [120, 0.42], [138, 0.40],
      [140, 0.67], [122, 0.68],
    ],
    arcEdges: [],
    centroid: [130, 0.54],
  },

  'South Mesa': {
    band: 'middle',
    vertices: [
      [140, 0.46], [158, 0.44],
      [160, 0.58], [158, 0.67],
      [140, 0.68],
    ],
    arcEdges: [],
    centroid: [149, 0.56],
  },

  'False Wall South': {
    band: 'middle',
    vertices: [
      [160, 0.42], [178, 0.40],
      [180, 0.67], [162, 0.68], [160, 0.58],
    ],
    arcEdges: [],
    centroid: [170, 0.54],
  },

  'Cielago North': {
    band: 'middle',
    vertices: [
      [180, 0.46], [210, 0.46],
      [210, 0.68], [180, 0.68],
    ],
    arcEdges: [],
    centroid: [195, 0.57],
  },

  'False Wall West': {
    band: 'middle',
    vertices: [
      [218, 0.40], [236, 0.38],
      [238, 0.64], [220, 0.65],
    ],
    arcEdges: [],
    centroid: [228, 0.52],
  },

  'Hagga Basin': {
    band: 'middle',
    vertices: [
      [240, 0.46], [268, 0.46],
      [268, 0.62], [254, 0.66], [240, 0.60],
    ],
    arcEdges: [],
    centroid: [254, 0.54],
  },

  'Bight of the Cliff': {
    band: 'middle',
    vertices: [
      [290, 0.46], [308, 0.46],
      [310, 0.67], [292, 0.68],
    ],
    arcEdges: [],
    centroid: [300, 0.56],
  },

  'Sietch Tabr': {
    band: 'middle',
    vertices: [
      [270, 0.47], [288, 0.46],
      [290, 0.68], [272, 0.69],
    ],
    arcEdges: [],
    centroid: [280, 0.57],
  },

  'Plastic Basin': {
    band: 'middle',
    vertices: [
      [310, 0.44], [338, 0.42],
      [340, 0.66], [312, 0.67],
    ],
    arcEdges: [],
    centroid: [325, 0.55],
  },

  'Tsimpo': {
    band: 'middle',
    vertices: [
      [340, 0.44], [352, 0.44],
      [354, 0.67], [342, 0.67],
    ],
    arcEdges: [],
    centroid: [347, 0.55],
  },

  'Broken Land': {
    band: 'middle',
    vertices: [
      [354, 0.46], [370, 0.46],
      [370, 0.68], [354, 0.68],
    ],
    arcEdges: [],
    centroid: [2, 0.57],
  },

  // ── INNER BAND ────────────────────────────────────────────────────────────────

  'Arrakeen': {
    band: 'inner',
    vertices: [
      [24, 0.30], [48, 0.30],
      [46, 0.46], [24, 0.46],
    ],
    arcEdges: [],
    centroid: [36, 0.38],
  },

  'Carthag': {
    band: 'inner',
    vertices: [
      [316, 0.30], [342, 0.30],
      [342, 0.46], [316, 0.46],
    ],
    arcEdges: [],
    centroid: [329, 0.38],
  },

  'Hole in the Rock': {
    band: 'inner',
    vertices: [
      [60, 0.175], [88, 0.175],
      [84, 0.30], [62, 0.31],
    ],
    arcEdges: [[0, 1, R_POLAR]],
    centroid: [74, 0.24],
  },

  'Harg Pass': {
    band: 'inner',
    vertices: [
      [90, 0.175], [130, 0.175],
      [126, 0.38], [93, 0.38],
    ],
    arcEdges: [[0, 1, R_POLAR]],
    centroid: [110, 0.28],
  },

  "Tuek's Sietch": {
    band: 'inset',
    vertices: [
      [134, 0.64], [155, 0.62],
      [156, 0.78], [135, 0.80],
    ],
    arcEdges: [],
    centroid: [145, 0.71],
  },

  'Cielago East': {
    band: 'inner',
    vertices: [
      [160, 0.175], [192, 0.175],
      [190, 0.44], [162, 0.44],
    ],
    arcEdges: [[0, 1, R_POLAR]],
    centroid: [176, 0.31],
  },

  'Cielago West': {
    band: 'inner',
    vertices: [
      [194, 0.175], [212, 0.175],
      [210, 0.44], [194, 0.44],
    ],
    arcEdges: [[0, 1, R_POLAR]],
    centroid: [203, 0.31],
  },

  'Habbanya Sietch': {
    band: 'inset',
    vertices: [
      [210, 0.64], [228, 0.62],
      [229, 0.80], [211, 0.82],
    ],
    arcEdges: [],
    centroid: [220, 0.72],
  },

  'Arsunt': {
    band: 'inner',
    vertices: [
      [240, 0.175], [268, 0.175],
      [268, 0.46], [240, 0.46],
    ],
    arcEdges: [[0, 1, R_POLAR]],
    centroid: [254, 0.32],
  },

  'Wind Pass': {
    band: 'inner',
    vertices: [
      [300, 0.175], [316, 0.175],
      [316, 0.30], [300, 0.30],
    ],
    arcEdges: [[0, 1, R_POLAR]],
    centroid: [308, 0.24],
  },

  'Wind Pass North': {
    band: 'inner',
    vertices: [
      [300, 0.30], [316, 0.30],
      [316, 0.46], [300, 0.46],
    ],
    arcEdges: [],
    centroid: [308, 0.38],
  },

  // ── OUTER BAND ────────────────────────────────────────────────────────────────

  'Old Gap': {
    band: 'outer',
    vertices: [
      [350, 0.68], [30, 0.68],
      [30, 0.92], [350, 0.92],
    ],
    arcEdges: [],
    centroid: [10, 0.80],
  },

  'Basin': {
    band: 'outer',
    vertices: [
      [30, 0.68], [58, 0.68],
      [60, 0.92], [30, 0.92],
    ],
    arcEdges: [],
    centroid: [45, 0.80],
  },

  'Gara Kulon': {
    band: 'outer',
    vertices: [
      [60, 0.68], [90, 0.68],
      [90, 0.92], [60, 0.92],
    ],
    arcEdges: [],
    centroid: [75, 0.80],
  },

  'Red Chasm': {
    band: 'outer',
    vertices: [
      [90, 0.68], [120, 0.68],
      [120, 0.92], [90, 0.92],
    ],
    arcEdges: [],
    centroid: [105, 0.80],
  },

  'The Minor Erg': {
    band: 'outer',
    vertices: [
      [120, 0.68], [160, 0.68],
      [160, 0.92], [120, 0.92],
    ],
    arcEdges: [],
    centroid: [140, 0.82],
  },

  'Cielago Depression': {
    band: 'outer',
    vertices: [
      [160, 0.68], [192, 0.68],
      [192, 0.92], [160, 0.92],
    ],
    arcEdges: [],
    centroid: [176, 0.82],
  },

  'Cielago South': {
    band: 'outer',
    vertices: [
      [192, 0.68], [222, 0.68],
      [222, 0.92], [192, 0.92],
    ],
    arcEdges: [],
    centroid: [207, 0.82],
  },

  'Meridian': {
    band: 'outer',
    vertices: [
      [222, 0.68], [246, 0.68],
      [246, 0.92], [222, 0.92],
    ],
    arcEdges: [],
    centroid: [234, 0.80],
  },

  'Habbanya Ridge Flat': {
    band: 'outer',
    vertices: [
      [246, 0.68], [270, 0.68],
      [270, 0.92], [246, 0.92],
    ],
    arcEdges: [],
    centroid: [258, 0.80],
  },

  'Habbanya Erg': {
    band: 'outer',
    vertices: [
      [270, 0.68], [290, 0.69],
      [290, 0.92], [270, 0.92],
    ],
    arcEdges: [],
    centroid: [280, 0.80],
  },

  'The Greater Flat': {
    band: 'outer',
    vertices: [
      [290, 0.68], [310, 0.68],
      [310, 0.92], [290, 0.92],
    ],
    arcEdges: [],
    centroid: [300, 0.80],
  },

  'The Great Flat': {
    band: 'outer',
    vertices: [
      [310, 0.68], [330, 0.68],
      [330, 0.92], [310, 0.92],
    ],
    arcEdges: [],
    centroid: [320, 0.80],
  },

  'Funeral Plain': {
    band: 'outer',
    vertices: [
      [330, 0.68], [350, 0.68],
      [350, 0.92], [330, 0.92],
    ],
    arcEdges: [],
    centroid: [340, 0.80],
  },
}

// Arc definitions — used for fallback rendering and centroid when no polygon exists
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

// ─── Label abbreviations ────────────────────────────────────────────────────────

const LABEL_ABBREV = {
  'Habbanya Sietch':     'Habbanya\nSietch',
  'Habbanya Erg':        'Habbanya\nErg',
  'Cielago Depression':  'Cielago\nDepression',
  'Cielago North':       'Cielago\nNorth',
  'Cielago South':       'Cielago\nSouth',
  'Cielago East':        'Cielago\nEast',
  'Cielago West':        'Cielago\nWest',
  'Wind Pass North':     'Wind Pass\nNorth',
  'False Wall East':     'False Wall\nEast',
  'False Wall West':     'False Wall\nWest',
  'False Wall South':    'False Wall\nSouth',
  "Tuek's Sietch":       "Tuek's\nSietch",
  'Plastic Basin':       'Plastic\nBasin',
  'Hole in the Rock':    'Hole in\nthe Rock',
  'Sihaya Ridge':        'Sihaya\nRidge',
  'Broken Land':         'Broken\nLand',
  'Imperial Basin':      'Imperial\nBasin',
  'Bight of the Cliff':  'Bight of\nthe Cliff',
  'Sietch Tabr':         'Sietch\nTabr',
  'Rim Wall West':       'Rim Wall\nWest',
  'The Greater Flat':    'The\nGreater Flat',
  'The Great Flat':      'The\nGreat Flat',
  'The Minor Erg':       'The Minor\nErg',
  'Habbanya Ridge Flat': 'Habbanya\nRidge Flat',
  'Funeral Plain':       'Funeral\nPlain',
  'Wind Pass':           'Wind\nPass',
  'Shield Wall':         'Shield\nWall',
  'Pasty Mesa':          'Pasty\nMesa',
  'South Mesa':          'South\nMesa',
  'Hagga Basin':         'Hagga\nBasin',
  'Red Chasm':           'Red\nChasm',
  'Gara Kulon':          'Gara\nKulon',
  'Polar Sink':          'Polar\nSink',
  'Old Gap':             'Old\nGap',
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

// ─── SVG Definitions (gradients, filters) ───────────────────────────────────────

function BoardDefs() {
  return (
    <defs>
      {/* Parchment radial gradient */}
      <radialGradient id="parchmentGrad" cx="50%" cy="50%" r="55%">
        <stop offset="0%"  stopColor="#E8D8B0" />
        <stop offset="40%" stopColor="#D8C490" />
        <stop offset="75%" stopColor="#C8B478" />
        <stop offset="100%" stopColor="#B8A468" />
      </radialGradient>

      {/* Sand territory gradient */}
      <radialGradient id="sandGrad" cx="50%" cy="50%" r="55%">
        <stop offset="0%"  stopColor="#DCC888" />
        <stop offset="100%" stopColor="#C8B068" />
      </radialGradient>

      {/* Dark vignette for outer edge */}
      <radialGradient id="vignetteGrad" cx="50%" cy="50%" r="50%">
        <stop offset="70%" stopColor="transparent" />
        <stop offset="100%" stopColor="rgba(30,16,8,0.3)" />
      </radialGradient>

      {/* Stronghold pattern */}
      <pattern id="strongholdHatch" patternUnits="userSpaceOnUse" width="4" height="4" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="4" stroke="rgba(100,70,30,0.15)" strokeWidth="1" />
      </pattern>

      {/* Drop shadow for strongholds */}
      <filter id="strongholdShadow" x="-10%" y="-10%" width="120%" height="120%">
        <feDropShadow dx="0" dy="1" stdDeviation="2" floodColor="#1A1008" floodOpacity="0.4" />
      </filter>

      {/* Glow filter for highlights */}
      <filter id="glowGreen">
        <feGaussianBlur stdDeviation="3" result="blur" />
        <feFlood floodColor="#22c55e" floodOpacity="0.6" result="color" />
        <feComposite in="color" in2="blur" operator="in" result="glow" />
        <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>
      <filter id="glowBlue">
        <feGaussianBlur stdDeviation="3" result="blur" />
        <feFlood floodColor="#3b82f6" floodOpacity="0.6" result="color" />
        <feComposite in="color" in2="blur" operator="in" result="glow" />
        <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>
    </defs>
  )
}

// ─── Outer frame & storm track ──────────────────────────────────────────────────

function OuterFrame({ stormSector }) {
  const dots = []
  const sectorNums = []
  const stormArrow = []

  for (let i = 0; i < 18; i++) {
    const a = sectorToRad(i)
    const dotR = R_OUTER + 13

    // Sector boundary dots
    dots.push(
      <circle
        key={`dot-${i}`}
        cx={CX + dotR * Math.cos(a)}
        cy={CY + dotR * Math.sin(a)}
        r={4}
        fill={C.frameDark}
        stroke={C.frameAccent}
        strokeWidth={1.2}
      />
    )

    // Sector numbers (centered in each sector wedge)
    const numA = sectorToRad(i + 0.5)
    const numR = R_OUTER + 13
    const isStorm = i === stormSector
    sectorNums.push(
      <text
        key={`num-${i}`}
        x={CX + numR * Math.cos(numA)}
        y={CY + numR * Math.sin(numA)}
        textAnchor="middle"
        dominantBaseline="central"
        fill={isStorm ? C.storm : C.textMid}
        fontSize={isStorm ? 10 : 8}
        fontWeight={isStorm ? 'bold' : 'normal'}
        fontFamily="serif"
        style={{ userSelect: 'none' }}
      >
        {i}
      </text>
    )
  }

  // Storm position marker (arrow)
  if (stormSector !== undefined) {
    const sA = sectorToRad(stormSector + 0.5)
    const arrowR = R_OUTER + 24
    const ax = CX + arrowR * Math.cos(sA)
    const ay = CY + arrowR * Math.sin(sA)
    stormArrow.push(
      <g key="storm-arrow">
        <circle cx={ax} cy={ay} r={7} fill={C.storm} opacity={0.25} />
        <text
          x={ax} y={ay}
          textAnchor="middle"
          dominantBaseline="central"
          fill={C.storm}
          fontSize={10}
          fontWeight="bold"
          style={{ userSelect: 'none' }}
        >
          ☇
        </text>
      </g>
    )
  }

  return (
    <g>
      {/* Dark outer frame ring */}
      <circle cx={CX} cy={CY} r={R_FRAME} fill="none" stroke={C.frameDark} strokeWidth={20} />
      <circle cx={CX} cy={CY} r={R_FRAME + 10} fill="none" stroke={C.frameDark} strokeWidth={2} />
      <circle cx={CX} cy={CY} r={R_FRAME - 10} fill="none" stroke={C.frameAccent} strokeWidth={0.8} />

      {/* Ornamental inner ring */}
      <circle cx={CX} cy={CY} r={R_OUTER + 2} fill="none" stroke={C.borderThick} strokeWidth={1.5} />
      <circle cx={CX} cy={CY} r={R_OUTER + 24} fill="none" stroke={C.frameAccent} strokeWidth={0.5} />

      {/* Sector boundary dots */}
      {dots}

      {/* Sector numbers */}
      {sectorNums}

      {/* Storm arrow */}
      {stormArrow}
    </g>
  )
}

// ─── Rock band underlays ────────────────────────────────────────────────────────
//
// The middle band (R_INNER → R_MIDDLE) is predominantly rock territories.
// Instead of relying on individual polygon fills to tile seamlessly, we paint
// a continuous rock-colored annular ring first.  Sand territories then paint
// their lighter fill on top, leaving the rock color visible wherever two rock
// polygons meet (eliminating gap artifacts from anti-aliasing / rounding).
//
// We also paint the inner band (R_POLAR → R_INNER) since it has several rock
// territories that border each other (Hole in the Rock, Harg Pass, Arsunt, etc.).

function RockBandUnderlays({ territories }) {
  // Only render if we actually have territory data
  if (!territories) return null
  return (
    <g>
      {/* Inner band rock underlay (Polar Sink → Inner boundary) */}
      {makeArcPath(CX, CY, R_POLAR, R_INNER, 0, 18) && (
        <path
          d={makeArcPath(CX, CY, R_POLAR, R_INNER, 0, 18)}
          fill={C.rock}
          stroke="none"
        />
      )}
      {/* Middle band rock underlay (Inner → Middle boundary) */}
      <path
        d={makeArcPath(CX, CY, R_INNER, R_MIDDLE, 0, 18)}
        fill={C.rock}
        stroke="none"
      />
      {/* Outer band — sand base is already there from parchment gradient,
          but we need a thin rock underlay for territories like South Mesa
          that sit at the middle/outer boundary edge */}
    </g>
  )
}

// ─── Storm sweep wedge ──────────────────────────────────────────────────────────

function StormSweep({ stormSector }) {
  const s0 = stormSector - 0.5
  const s1 = stormSector + 0.5
  const path = makeArcPath(CX, CY, R_POLAR, R_OUTER, s0, s1)
  return (
    <g>
      <path d={path} fill={C.storm} fillOpacity={0.12} stroke={C.storm} strokeWidth={1.2} strokeOpacity={0.5} />
    </g>
  )
}

// ─── Sector division lines ──────────────────────────────────────────────────────

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
            x2={CX + R_OUTER * Math.cos(a)}
            y2={CY + R_OUTER * Math.sin(a)}
            stroke={C.borderThick}
            strokeWidth={0.8}
            opacity={0.5}
          />
        )
      })}
    </g>
  )
}

// ─── Ring boundary circles ──────────────────────────────────────────────────────

function RingCircles() {
  return (
    <g fill="none">
      <circle cx={CX} cy={CY} r={R_POLAR}  stroke={C.borderFaint} strokeWidth={1.2} />
      <circle cx={CX} cy={CY} r={R_INNER}  stroke={C.borderThick} strokeWidth={0.8} opacity={0.6} />
      <circle cx={CX} cy={CY} r={R_MIDDLE} stroke={C.borderThick} strokeWidth={0.8} opacity={0.6} />
      <circle cx={CX} cy={CY} r={R_OUTER}  stroke={C.borderThick} strokeWidth={1.2} />
    </g>
  )
}

// ─── Polar Sink ─────────────────────────────────────────────────────────────────

function PolarSink({ forces }) {
  return (
    <g>
      {/* Main polar sink circle */}
      <circle cx={CX} cy={CY} r={R_POLAR} fill={C.polar} stroke={C.polarStroke} strokeWidth={1.5} />

      {/* Inner detail ring */}
      <circle cx={CX} cy={CY} r={R_POLAR - 8}
        fill="none" stroke={C.polarStroke} strokeWidth={0.6} strokeDasharray="4,3" opacity={0.6} />

      {/* "False Wall East" vertical text */}
      <text
        x={CX + 2} y={CY - 16}
        textAnchor="middle"
        fill={C.textMid}
        fontSize={5.5}
        fontFamily="serif"
        fontStyle="italic"
        letterSpacing="1"
        opacity={0.5}
        transform={`rotate(90, ${CX + 2}, ${CY - 16})`}
        style={{ userSelect: 'none' }}
      >
        FALSE WALL EAST
      </text>

      {/* Polar Sink label */}
      <text
        x={CX} y={CY - 5}
        textAnchor="middle" dominantBaseline="central"
        fill={C.textDark} fontSize={9} fontWeight="bold" fontFamily="serif"
        style={{ userSelect: 'none' }}
      >
        Polar
      </text>
      <text
        x={CX} y={CY + 7}
        textAnchor="middle" dominantBaseline="central"
        fill={C.textDark} fontSize={9} fontWeight="bold" fontFamily="serif"
        style={{ userSelect: 'none' }}
      >
        Sink
      </text>

      {/* Force tokens */}
      {forces && forces.length > 0 && forces.map((entry, i) => {
        const dotX = CX - ((forces.length - 1) * 7) / 2 + i * 7
        return (
          <g key={entry.faction}>
            <circle cx={dotX} cy={CY + 20} r={5}
              fill={FACTION_FILL[entry.faction] || '#888'} stroke="#00000040" strokeWidth={0.5} opacity={0.92} />
            <text x={dotX} y={CY + 20}
              textAnchor="middle" dominantBaseline="central"
              fill="#000" fontSize={5.5} fontWeight="bold"
              style={{ userSelect: 'none' }}>
              {entry.count}
            </text>
          </g>
        )
      })}
    </g>
  )
}

// ─── Stronghold fortress icon ───────────────────────────────────────────────────

function StrongholdIcon({ cx, cy, scale = 1 }) {
  const s = scale * 0.8
  // Simple fortress silhouette
  return (
    <g transform={`translate(${cx}, ${cy}) scale(${s})`} opacity={0.6}>
      {/* Base */}
      <rect x={-8} y={-2} width={16} height={6} fill={C.textDark} rx={0.5} />
      {/* Left tower */}
      <rect x={-7} y={-8} width={4} height={6} fill={C.textDark} rx={0.3} />
      <rect x={-8} y={-10} width={6} height={3} fill={C.textDark} rx={0.3} />
      {/* Right tower */}
      <rect x={3} y={-8} width={4} height={6} fill={C.textDark} rx={0.3} />
      <rect x={2} y={-10} width={6} height={3} fill={C.textDark} rx={0.3} />
      {/* Center spire */}
      <rect x={-2} y={-6} width={4} height={4} fill={C.textDark} rx={0.3} />
      <polygon points="0,-11 -3,-6 3,-6" fill={C.textDark} />
      {/* Gate */}
      <rect x={-1.5} y={0} width={3} height={4} fill={C.polar} rx={1} />
    </g>
  )
}

// ─── Spice blow indicator ───────────────────────────────────────────────────────

function SpiceBlowMarker({ cx, cy, amount }) {
  if (!amount) return null
  return (
    <g>
      <circle cx={cx} cy={cy} r={8} fill="rgba(200,80,0,0.15)" stroke={C.spice} strokeWidth={0.6} />
      <text x={cx} y={cy + 0.5}
        textAnchor="middle" dominantBaseline="central"
        fill={C.spice} fontSize={7} fontWeight="bold" fontFamily="serif"
        style={{ userSelect: 'none' }}>
        {amount}
      </text>
    </g>
  )
}

// ─── Territory renderer ─────────────────────────────────────────────────────────

function getTerritoryStyling(territory) {
  const type = territory.territory_type
  if (type === 'stronghold') {
    return { fill: C.stronghold, stroke: C.borderThick, strokeW: 2 }
  } else if (type === 'rock') {
    return { fill: C.rock, stroke: C.borderThick, strokeW: 1 }
  } else if (type === 'sand') {
    return { fill: C.sand, stroke: C.borderThin, strokeW: 1 }
  }
  return { fill: C.sand, stroke: C.borderThin, strokeW: 1 }
}

function TerritoryShape({ name, territory, forceEntries, isStorm, highlight, mode }) {
  const poly = TERRITORY_POLYGONS[name]
  const arc = TERRITORY_ARCS[name]
  if (!poly && !arc) return null

  // Compute path and centroid
  let path, cx, cy

  if (poly) {
    path = makePolyPath(poly.vertices, poly.arcEdges)
    if (poly.centroid) {
      const pt = polyPt(poly.centroid[0], poly.centroid[1])
      cx = pt.x; cy = pt.y
    } else {
      const c = polyCentroid(poly.vertices)
      cx = c.x; cy = c.y
    }
  } else {
    const { s0, s1, ri, ro } = arc
    path = makeArcPath(CX, CY, ri, ro, s0, s1)
    const c = arcCentroid(CX, CY, ri, ro, s0, s1)
    cx = c.x; cy = c.y
  }

  const { fill, stroke, strokeW } = getTerritoryStyling(territory)
  const isStronghold = territory.territory_type === 'stronghold'
  const isSand = territory.territory_type === 'sand'
  const hasSpice = territory.current_spice > 0
  const hasForces = forceEntries && forceEntries.length > 0

  // Storm highlight
  let stormStroke = stroke
  let stormStrokeW = strokeW
  if (isStorm && isSand && !territory.storm_exception) {
    stormStroke = C.storm
    stormStrokeW = 2
  }

  // Movement highlight
  const glowColor =
    highlight === 'from'     ? '#22c55e' :
    highlight === 'to'       ? '#3b82f6' :
    highlight === 'adjacent' ? '#0d9488' :
    null
  const glowFilter =
    highlight === 'from' ? 'url(#glowGreen)' :
    highlight === 'to'   ? 'url(#glowBlue)' :
    null

  const isRock = territory.territory_type === 'rock'

  // ── FILL PASS ──
  if (mode === 'fill') {
    // Rock territories: the continuous RockBandUnderlays provides the fill.
    // We only draw a thin internal dividing line so the rock band looks like
    // one seamless shape with subtle territory boundaries.
    if (isRock) {
      return (
        <g>
          {glowColor && (
            <path
              d={path}
              fill="none"
              stroke={glowColor}
              strokeWidth={highlight === 'adjacent' ? 3 : 5}
              opacity={highlight === 'adjacent' ? 0.4 : 0.8}
              filter={glowFilter}
            />
          )}
          <path
            d={path}
            fill="none"
            stroke={glowColor ?? C.borderFaint}
            strokeWidth={0.5}
            strokeLinejoin="round"
            opacity={0.5}
          />
        </g>
      )
    }

    return (
      <g>
        {/* Glow outline for highlights */}
        {glowColor && (
          <path
            d={path}
            fill="none"
            stroke={glowColor}
            strokeWidth={highlight === 'adjacent' ? 3 : 5}
            opacity={highlight === 'adjacent' ? 0.4 : 0.8}
            filter={glowFilter}
          />
        )}

        {/* Territory fill */}
        <path
          d={path}
          fill={fill}
          stroke={glowColor ?? stormStroke}
          strokeWidth={stormStrokeW}
          strokeLinejoin="round"
        />

        {/* Stronghold inner border decoration */}
        {isStronghold && poly && (
          <path
            d={path}
            fill="url(#strongholdHatch)"
            stroke={C.textDark}
            strokeWidth={0.5}
            strokeDasharray="3,3"
            opacity={0.4}
          />
        )}
      </g>
    )
  }

  // ── LABEL PASS ──
  const labelText = LABEL_ABBREV[name] ?? name
  const lines = labelText.split('\n')

  // Calculate font size based on available space
  let availW
  if (poly) {
    const pts = poly.vertices.map(([d, r]) => polyPt(d, r))
    const bboxW = Math.max(...pts.map(p => p.x)) - Math.min(...pts.map(p => p.x))
    const bboxH = Math.max(...pts.map(p => p.y)) - Math.min(...pts.map(p => p.y))
    availW = Math.min(bboxW, bboxH) * 0.75
  } else {
    const { s0, s1, ri, ro } = arc
    const arcSpanDeg = (s1 - s0) * 20
    const arcMidR = (ri + ro) / 2
    const arcWidthPx = arcMidR * (arcSpanDeg * Math.PI / 180)
    availW = Math.min(arcWidthPx * 0.88, (ro - ri) * 0.88)
  }

  const longestLine = Math.max(...lines.map(l => l.length))
  const fontSize = isStronghold
    ? Math.max(5.5, Math.min(8.5, availW / longestLine * 1.6))
    : Math.max(5, Math.min(7.5, availW / longestLine * 1.6))

  const lineH = fontSize + 1.5
  const totalLabelH = lines.length * lineH
  const spiceH = hasSpice ? 10 : 0
  const forceH = hasForces ? 10 : 0
  const iconH = isStronghold ? 14 : 0
  const totalH = iconH + totalLabelH + spiceH + forceH
  const topY = cy - totalH / 2

  // Spice blow amount (static indicator from game data)
  return (
    <g>
      {/* Stronghold fortress icon */}
      {isStronghold && (
        <StrongholdIcon cx={cx} cy={topY + 6} scale={0.7} />
      )}

      {/* Territory name */}
      {lines.map((line, i) => (
        <text
          key={i}
          x={cx}
          y={topY + iconH + (i + 0.6) * lineH}
          textAnchor="middle"
          dominantBaseline="central"
          fill={isStronghold ? C.textGold : isSand ? C.textDark : C.textDark}
          fontSize={fontSize}
          fontWeight={isStronghold ? 'bold' : 'normal'}
          fontFamily="serif"
          style={{ pointerEvents: 'none', userSelect: 'none' }}
        >
          {line}
        </text>
      ))}

      {/* Current spice on territory */}
      {hasSpice && (
        <g>
          <circle
            cx={cx} cy={topY + iconH + totalLabelH + spiceH * 0.5}
            r={6} fill="rgba(200,80,0,0.2)" stroke={C.spice} strokeWidth={0.6}
          />
          <text
            x={cx}
            y={topY + iconH + totalLabelH + spiceH * 0.55}
            textAnchor="middle" dominantBaseline="central"
            fill={C.spice} fontSize={7.5} fontWeight="bold" fontFamily="serif"
            style={{ pointerEvents: 'none', userSelect: 'none' }}
          >
            {territory.current_spice}
          </text>
        </g>
      )}

      {/* Force tokens */}
      {hasForces && (
        <g>
          {forceEntries.map((entry, i) => {
            const totalDots = forceEntries.length
            const dotX = cx - ((totalDots - 1) * 8) / 2 + i * 8
            const dotY = topY + iconH + totalLabelH + spiceH + forceH * 0.5
            return (
              <g key={entry.faction}>
                <circle cx={dotX} cy={dotY} r={5}
                  fill={FACTION_FILL[entry.faction] || '#888'}
                  stroke="#00000030" strokeWidth={0.5}
                  opacity={0.92} />
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

      {/* Spice blow amount indicator */}
      {territory.has_spice_blow && territory.spice_blow_amount > 0 && !hasSpice && (
        <SpiceBlowMarker
          cx={cx + (availW > 40 ? 18 : 12)}
          cy={topY + iconH + lineH * 0.5}
          amount={territory.spice_blow_amount}
        />
      )}
    </g>
  )
}

// ─── Corner decorations ─────────────────────────────────────────────────────────

function DuneTitle() {
  return (
    <g>
      <text
        x={CX + BR - 30} y={CY - BR + 38}
        textAnchor="end"
        fill={C.frameAccent}
        fontSize={22}
        fontWeight="bold"
        fontFamily="serif"
        letterSpacing="4"
        opacity={0.7}
        style={{ userSelect: 'none' }}
      >
        DUNE
      </text>
    </g>
  )
}

function BottomLabels() {
  return (
    <g>
      <text
        x={CX - BR + 50} y={CY + BR + 24}
        textAnchor="start"
        fill={C.frameAccent}
        fontSize={8}
        fontFamily="serif"
        letterSpacing="2"
        opacity={0.6}
        style={{ userSelect: 'none' }}
      >
        BENE TLEILAXU TANKS
      </text>
      <text
        x={CX + BR - 50} y={CY + BR + 24}
        textAnchor="end"
        fill={C.frameAccent}
        fontSize={8}
        fontFamily="serif"
        letterSpacing="2"
        opacity={0.6}
        style={{ userSelect: 'none' }}
      >
        SPICE BANK
      </text>
    </g>
  )
}

// ─── Storm start indicator ──────────────────────────────────────────────────────

function StormStart() {
  const a = sectorToRad(9)  // bottom of board
  const r = R_OUTER + 14
  return (
    <g>
      <text
        x={CX + r * Math.cos(a) + 20} y={CY + r * Math.sin(a) + 2}
        textAnchor="middle"
        fill={C.textMid}
        fontSize={5}
        fontFamily="serif"
        letterSpacing="1"
        opacity={0.6}
        style={{ userSelect: 'none' }}
      >
        STORM START ▸▸▸
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

  function getBand(name) {
    const poly = TERRITORY_POLYGONS[name]
    if (poly) return poly.band
    const arc = TERRITORY_ARCS[name]
    if (!arc) return null
    if (arc.ri >= R_MIDDLE) return 'outer'
    if (arc.ri >= R_INNER) return 'middle'
    return 'inner'
  }

  return (
    <div className="bg-[#0f0e0b] border border-[#3a3020] rounded p-2 h-full flex flex-col">
      <svg
        viewBox="0 0 700 700"
        className="flex-1 w-full min-h-0"
        preserveAspectRatio="xMidYMid meet"
      >
        <BoardDefs />

        {/* Background */}
        <rect width="700" height="700" fill={C.frameDark} rx="8" />

        {/* Board background disc — dark frame ring */}
        <circle cx={CX} cy={CY} r={R_FRAME} fill={C.frameDark} />

        {/* Parchment base layer — warm sand gradient */}
        <circle cx={CX} cy={CY} r={R_OUTER} fill="url(#parchmentGrad)" />

        {/* Subtle vignette overlay */}
        <circle cx={CX} cy={CY} r={R_OUTER} fill="url(#vignetteGrad)" />

        {/* Storm sector fill */}
        <StormSweep stormSector={stormSectorNum} />

        {/* Rock band underlays — continuous rings so no gaps show between
            adjacent rock territory polygons. Individual territory fills paint
            on top; sand territories cover sections of these rings with sand color. */}
        <RockBandUnderlays territories={territories} />

        {/* PASS 1: Territory fills — outer → middle → inner → inset strongholds */}
        {['outer', 'middle', 'inner', 'inset'].map(band =>
          Object.entries(territories).map(([name, territory]) => {
            if (getBand(name) !== band) return null
            const forces = forceMap[name] || []
            const isStorm = (territory.sectors || []).includes(stormSectorNum)
            const highlight = getHighlight(name)
            return (
              <TerritoryShape
                key={`fill-${name}`}
                name={name}
                territory={territory}
                forceEntries={forces}
                isStorm={isStorm}
                highlight={highlight}
                mode="fill"
              />
            )
          })
        )}

        {/* Ring boundary circles */}
        <RingCircles />

        {/* Sector dividing lines */}
        <SectorLines />

        {/* Polar Sink */}
        <PolarSink forces={forceMap['Polar Sink']} />

        {/* PASS 2: Territory labels — on top of all fills */}
        {['outer', 'middle', 'inner', 'inset'].map(band =>
          Object.entries(territories).map(([name, territory]) => {
            if (name === 'Polar Sink') return null
            if (getBand(name) !== band) return null
            const forces = forceMap[name] || []
            const isStorm = (territory.sectors || []).includes(stormSectorNum)
            const highlight = getHighlight(name)
            return (
              <TerritoryShape
                key={`label-${name}`}
                name={name}
                territory={territory}
                forceEntries={forces}
                isStorm={isStorm}
                highlight={highlight}
                mode="label"
              />
            )
          })
        )}

        {/* Outer frame & storm track */}
        <OuterFrame stormSector={stormSectorNum} />

        {/* Corner decorations */}
        <DuneTitle />
        <BottomLabels />
        <StormStart />
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-2 py-1 border-t border-[#3a3020] text-[10px] text-[#8B7040] shrink-0">
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm border-2" style={{ borderColor: C.borderThick, background: C.stronghold }} />
          Stronghold
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm border" style={{ borderColor: C.borderThick, background: C.rock }} />
          Rock
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm border" style={{ borderColor: C.borderThin, background: C.sand }} />
          Sand
        </span>
        <span className="flex items-center gap-1">
          <span className="font-bold text-xs" style={{ color: C.spice }}>⬥</span>
          Spice
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: C.stormFill, border: `1px solid ${C.storm}` }} />
          Storm
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
