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

const TERRITORY_ARCS = {

  // ── INNER BAND  (ri = R_POLAR, ro = R_INNER) ─────────────────────────────
  // Non-overlapping sector allocation going clockwise from top (0→18):
  //   Tsimpo       17.5 → 1.5
  //   Arrakeen      1.5 → 3.0
  //   Hole/Rock     3.0 → 4.0
  //   Imp Basin     4.0 → 6.0
  //   Harg Pass     5.8 → 7.0
  //   Tuek's        6.8 → 8.2
  //   Cielago E     8.0 → 9.5
  //   Cielago W     9.5 → 11.0
  //   Hab Sietch   10.8 → 12.2
  //   Arsunt       12.0 → 13.5
  //   Sietch Tabr  13.3 → 15.0
  //   Wind Pass    14.8 → 16.0
  //   Wind Pass N  15.8 → 17.2
  //   Carthag      17.0 → 18.5
  'Tsimpo':            { s0: 17.5, s1: 1.5,  ri: R_POLAR, ro: R_INNER },
  'Arrakeen':          { s0:  1.5, s1: 3.0,  ri: R_POLAR, ro: R_INNER },
  'Hole in the Rock':  { s0:  3.0, s1: 4.0,  ri: R_POLAR, ro: Math.round(R_POLAR + (R_INNER - R_POLAR) * 0.55) },
  'Imperial Basin':    { s0:  4.0, s1: 6.0,  ri: Math.round(R_POLAR + (R_INNER - R_POLAR) * 0.45), ro: R_INNER },
  'Harg Pass':         { s0:  5.8, s1: 7.0,  ri: R_POLAR, ro: Math.round(R_POLAR + (R_INNER - R_POLAR) * 0.55) },
  "Tuek's Sietch":     { s0:  6.8, s1: 8.2,  ri: R_POLAR, ro: R_INNER },
  'Cielago East':      { s0:  8.0, s1: 9.5,  ri: R_POLAR, ro: R_INNER },
  'Cielago West':      { s0:  9.5, s1: 11.0, ri: R_POLAR, ro: R_INNER },
  'Habbanya Sietch':   { s0: 10.8, s1: 12.2, ri: R_POLAR, ro: R_INNER },
  'Arsunt':            { s0: 12.0, s1: 13.5, ri: R_POLAR, ro: R_INNER },
  'Sietch Tabr':       { s0: 13.3, s1: 15.0, ri: R_POLAR, ro: R_INNER },
  'Wind Pass':         { s0: 14.8, s1: 16.0, ri: R_POLAR, ro: R_INNER },
  'Wind Pass North':   { s0: 15.8, s1: 17.2, ri: R_POLAR, ro: R_INNER },
  'Carthag':           { s0: 17.0, s1: 18.5, ri: R_POLAR, ro: R_INNER },

  // ── MIDDLE BAND  (ri = R_INNER, ro = R_MIDDLE) ───────────────────────────
  'Broken Land':       { s0: 17.2, s1: 19.3, ri: R_INNER, ro: R_MIDDLE },
  'Rim Wall West':     { s0:  1.5, s1:  3.0, ri: R_INNER, ro: R_MIDDLE },
  'Sihaya Ridge':      { s0:  2.5, s1:  4.2, ri: R_INNER, ro: R_MIDDLE },
  'Shield Wall':       { s0:  3.8, s1:  5.5, ri: R_INNER, ro: R_MIDDLE },
  'Pasty Mesa':        { s0:  4.5, s1:  6.2, ri: R_INNER, ro: R_MIDDLE },
  'False Wall East':   { s0:  5.2, s1:  7.0, ri: R_INNER, ro: R_MIDDLE },
  'South Mesa':        { s0:  6.5, s1:  8.0, ri: R_INNER, ro: R_MIDDLE },
  'False Wall South':  { s0:  7.2, s1:  9.0, ri: R_INNER, ro: R_MIDDLE },
  'Cielago North':     { s0:  8.8, s1: 10.5, ri: R_INNER, ro: R_MIDDLE },
  'False Wall West':   { s0: 10.2, s1: 12.0, ri: R_INNER, ro: R_MIDDLE },
  'Hagga Basin':       { s0: 12.0, s1: 14.5, ri: R_INNER, ro: R_MIDDLE },
  'Bight of the Cliff':{ s0: 13.5, s1: 15.2, ri: R_INNER, ro: R_MIDDLE },
  'Plastic Basin':     { s0: 15.0, s1: 17.5, ri: R_INNER, ro: R_MIDDLE },

  // ── OUTER BAND  (ri = R_MIDDLE, ro = R_OUTER) ────────────────────────────
  'Old Gap':           { s0: 17.0, s1: 19.5, ri: R_MIDDLE, ro: R_OUTER },
  'Basin':             { s0:  1.2, s1:  3.0, ri: R_MIDDLE, ro: R_OUTER },
  'Gara Kulon':        { s0:  3.0, s1:  5.0, ri: R_MIDDLE, ro: R_OUTER },
  'Red Chasm':         { s0:  4.5, s1:  6.5, ri: R_MIDDLE, ro: R_OUTER },
  'The Minor Erg':     { s0:  6.0, s1:  8.2, ri: R_MIDDLE, ro: R_OUTER },
  'Cielago Depression':{ s0:  8.2, s1:  9.8, ri: R_MIDDLE, ro: R_OUTER },
  'Cielago South':     { s0:  9.5, s1: 11.2, ri: R_MIDDLE, ro: R_OUTER },
  'Meridian':          { s0: 11.0, s1: 12.5, ri: R_MIDDLE, ro: R_OUTER },
  'Habbanya Ridge Flat':{ s0:12.3, s1: 13.5, ri: R_MIDDLE, ro: R_OUTER },
  'Habbanya Erg':      { s0: 13.2, s1: 14.8, ri: R_MIDDLE, ro: R_OUTER },
  'The Greater Flat':  { s0: 14.5, s1: 15.8, ri: R_MIDDLE, ro: R_OUTER },
  'The Great Flat':    { s0: 15.5, s1: 16.8, ri: R_MIDDLE, ro: R_OUTER },
  'Funeral Plain':     { s0: 16.5, s1: 17.8, ri: R_MIDDLE, ro: R_OUTER },
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
            stroke="#1a1510"
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
      <circle cx={CX} cy={CY} r={R_POLAR}  stroke="#2a3a5a" />
      <circle cx={CX} cy={CY} r={R_INNER}  stroke="#1e1b12" />
      <circle cx={CX} cy={CY} r={R_MIDDLE} stroke="#1e1b12" />
      <circle cx={CX} cy={CY} r={R_OUTER}  stroke="#1e1b12" />
      <circle cx={CX} cy={CY} r={BR}        stroke="#3a3020" strokeWidth={1.5} />
    </g>
  )
}

// ─── Territory arc ────────────────────────────────────────────────────────────

const LABEL_ABBREV = {
  'Habbanya Ridge Flat': 'Hab. Ridge Flat',
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
  'Rim Wall West':       'Rim Wall W.',
  'The Greater Flat':    'Gr. Flat+',
  'The Great Flat':      'Gr. Flat',
  'The Minor Erg':       'Minor Erg',
  'Habbanya Ridge Flat': 'Hab. Ridge',
}

function TerritoryArc({ name, territory, forceEntries, isStorm, highlight }) {
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
  let fill   = '#17140e'
  let stroke = '#2a2418'
  let strokeW = 0.8

  if (isStronghold) {
    fill   = '#2a1d08'
    stroke = '#b8860b'
    strokeW = 1.5
  } else if (isRock) {
    fill   = '#191714'
    stroke = '#3a352a'
  } else if (isSand) {
    fill   = '#1e1a0d'
    stroke = '#4a3c18'
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

  const label = LABEL_ABBREV[name] ?? name

  // Rough arc width for font sizing
  const arcSpanDeg = (s1 - s0) * 20
  const arcMidR    = (ri + ro) / 2
  const arcWidthPx = arcMidR * (arcSpanDeg * Math.PI / 180)
  const arcHeightPx = ro - ri
  const availW = Math.min(arcWidthPx * 0.85, arcHeightPx * 0.85)
  const fontSize = isStronghold
    ? Math.max(6, Math.min(8.5, availW / label.length * 1.6))
    : Math.max(5, Math.min(7.5, availW / label.length * 1.6))

  // Vertical layout inside arc
  const lineH   = fontSize + 1
  const spiceH  = hasSpice  ? 8 : 0
  const forceH  = hasForces ? 8 : 0
  const totalH  = lineH + spiceH + forceH
  const topY    = cy - totalH / 2

  return (
    <g>
      {/* Glow ring for highlighted territory */}
      {glowColor && (
        <path
          d={makeArcPath(CX, CY, Math.max(0, ri - 3), ro + 3, s0, s1)}
          fill="none"
          stroke={glowColor}
          strokeWidth={highlight === 'adjacent' ? 1.5 : 2.5}
          opacity={highlight === 'adjacent' ? 0.5 : 0.9}
        />
      )}

      {/* Territory fill */}
      <path
        d={path}
        fill={fill}
        stroke={glowColor ?? stroke}
        strokeWidth={strokeW}
      />

      {/* Stronghold inner dashed ring */}
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

      {/* Territory name */}
      <text
        x={cx}
        y={topY + lineH * 0.75}
        textAnchor="middle"
        dominantBaseline="central"
        fill={isStronghold ? '#d4a84b' : '#9a8a6a'}
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

// ─── Polar Sink ───────────────────────────────────────────────────────────────

function PolarSink({ forces }) {
  return (
    <g>
      <circle cx={CX} cy={CY} r={R_POLAR} fill="#0c1220" stroke="#2a3a5a" strokeWidth={1.5} />
      {/* Subtle octagon feel */}
      <circle cx={CX} cy={CY} r={R_POLAR - 6} fill="none" stroke="#1a2a40" strokeWidth={0.8} strokeDasharray="3,3" />
      <text
        x={CX} y={CY - 6}
        textAnchor="middle"
        dominantBaseline="central"
        fill="#5a7a9a"
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
        fill="#5a7a9a"
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
        <circle cx={CX} cy={CY} r={BR} fill="#0e0c08" />

        {/* Storm sector fill */}
        <StormSweep stormSector={stormSectorNum} />

        {/* Territory arcs — drawn bottom-up so inner territories appear on top */}
        {/* Outer band first */}
        {Object.entries(territories).map(([name, territory]) => {
          const arc = TERRITORY_ARCS[name]
          if (!arc || arc.ri >= R_MIDDLE) return null
          return null // placeholder — handled below in correct order
        })}

        {/* Render in band order: outer → middle → inner (so inner overlaps outer at boundaries) */}
        {['outer', 'middle', 'inner'].map(band => (
          Object.entries(territories).map(([name, territory]) => {
            const arc = TERRITORY_ARCS[name]
            if (!arc) return null
            const inBand =
              band === 'outer'  ? arc.ri >= R_MIDDLE :
              band === 'middle' ? arc.ri >= R_INNER && arc.ri < R_MIDDLE :
              /* inner */         arc.ri < R_INNER
            if (!inBand) return null

            const forces      = forceMap[name] || []
            const isStorm     = (territory.sectors || []).includes(stormSectorNum)
            const highlight   = getHighlight(name)
            return (
              <TerritoryArc
                key={name}
                name={name}
                territory={territory}
                forceEntries={forces}
                isStorm={isStorm}
                highlight={highlight}
              />
            )
          })
        ))}

        {/* Ring guide circles */}
        <RingCircles />

        {/* Sector dividing lines */}
        <SectorLines />

        {/* Polar Sink (drawn last so it sits on top of inner arcs) */}
        <PolarSink forces={forceMap['Polar Sink']} />

        {/* Sector number labels (outermost ring) */}
        <SectorLabels stormSector={stormSectorNum} />
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-2 py-1 border-t border-[#3a3020] text-[10px] text-gray-500 shrink-0">
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm border-2" style={{ borderColor: '#b8860b', background: '#2a1d08' }} />
          Stronghold
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm border" style={{ borderColor: '#3a352a', background: '#191714' }} />
          Rock
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm border" style={{ borderColor: '#4a3c18', background: '#1e1a0d' }} />
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
