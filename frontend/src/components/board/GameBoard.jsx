/**
 * GameBoard — circular SVG board for the Dune game.
 *
 * Shows territories arranged by sector around the Polar Sink,
 * with storm position, spice, and force tokens.
 */

// Faction dot colors (fill for SVG)
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

// Territory layout: angular position (sector midpoint) and radial ring.
// ring: 0 = stronghold (inner), 1 = rock (middle), 2 = sand (outer)
// For multi-sector territories, we use the midpoint angle.
// sectorMid is the center of the sector span (0-17), used to compute angle.
const TERRITORY_LAYOUT = {
  // Polar Sink — special, rendered separately in the center
  'Polar Sink':           { sectorMid: 0,    ring: -1 },

  // Strongholds (ring 0)
  'Arrakeen':             { sectorMid: 3,    ring: 0 },
  'Carthag':              { sectorMid: 11,   ring: 0 },
  'Sietch Tabr':          { sectorMid: 8,    ring: 0 },
  'Habbanya Sietch':      { sectorMid: 16,   ring: 0 },
  "Tuek's Sietch":        { sectorMid: 6,    ring: 0 },

  // Rock (ring 1)
  'Harga Pass':           { sectorMid: 0,    ring: 1 },
  'Tsimpo':               { sectorMid: 1,    ring: 1 },
  'Wind Pass North':      { sectorMid: 2,    ring: 1 },
  'Shield Wall':          { sectorMid: 4,    ring: 1 },
  'Plastic Basin':        { sectorMid: 5,    ring: 1 },
  'Cielago East':         { sectorMid: 7,    ring: 1 },
  'Cielago West':         { sectorMid: 9,    ring: 1 },
  'Pasty Mesa':           { sectorMid: 12,   ring: 1 },
  'Broken Land':          { sectorMid: 13,   ring: 1 },
  'False Wall East':      { sectorMid: 15,   ring: 1 },
  'False Wall West':      { sectorMid: 17,   ring: 1 },
  'False Wall South':     { sectorMid: 14,   ring: 1 },
  'Wind Pass':            { sectorMid: 16.5, ring: 1 },
  'Hole in the Rock':     { sectorMid: 3.5,  ring: 1 },
  'Sihaya Ridge':         { sectorMid: 6.5,  ring: 1 },

  // Sand (ring 2)
  'Imperial Basin':       { sectorMid: 4.5,  ring: 2 },
  'Gara Kulon':           { sectorMid: 3.5,  ring: 2 },
  'Hagga Basin':          { sectorMid: 1.5,  ring: 2 },
  'Habbanya Ridge Flat':  { sectorMid: 15.5, ring: 2 },
  'The Great Flat':       { sectorMid: 12.5, ring: 2 },
  'The Minor Erg':        { sectorMid: 14.5, ring: 2 },
  'Red Chasm':            { sectorMid: 15.5, ring: 2.5 },
  'Habbanya Erg':         { sectorMid: 16.5, ring: 2 },
  'Cielago Depression':   { sectorMid: 9.5,  ring: 2 },
  'Meridian':             { sectorMid: 10.5, ring: 2 },
  'The Erg':              { sectorMid: 0.5,  ring: 2 },
  'Attendant':            { sectorMid: 7.5,  ring: 2 },
}

const CX = 300
const CY = 300
const BOARD_RADIUS = 275
const RING_RADII = {
  0: 95,    // strongholds
  1: 165,   // rock
  2: 235,   // sand outer
  2.5: 258, // overflow for overlapping sectors
}

function sectorAngle(sectorMid) {
  // Each sector is 20 degrees. Sector 0 starts at top (12 o'clock).
  // We go clockwise, so angle increases clockwise.
  return (sectorMid * 20 - 90) * (Math.PI / 180)
}

function polarToXY(sectorMid, radius) {
  const angle = sectorAngle(sectorMid)
  return {
    x: CX + radius * Math.cos(angle),
    y: CY + radius * Math.sin(angle),
  }
}

// Build force summary: territory_name -> [{ faction, count, special }]
function buildForceMap(players) {
  const map = {}
  for (const player of (players || [])) {
    for (const fg of (player.forces_on_board || [])) {
      const total = (fg.regular_count || 0) + (fg.special_count || 0)
      if (total === 0) continue
      if (!map[fg.territory_name]) map[fg.territory_name] = []
      // Merge if same faction already present in this territory
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

function StormArc({ stormSector }) {
  // Draw an arc segment at the storm's current sector
  const startAngle = (stormSector * 20 - 90 - 10) * (Math.PI / 180)
  const endAngle = (stormSector * 20 - 90 + 10) * (Math.PI / 180)
  const r = BOARD_RADIUS + 4
  const x1 = CX + r * Math.cos(startAngle)
  const y1 = CY + r * Math.sin(startAngle)
  const x2 = CX + r * Math.cos(endAngle)
  const y2 = CY + r * Math.sin(endAngle)

  return (
    <path
      d={`M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}`}
      stroke="#ef4444"
      strokeWidth="6"
      fill="none"
      strokeLinecap="round"
    />
  )
}

function TerritoryNode({ name, territory, layout, forceEntries, isStormSector, highlight }) {
  if (!layout || layout.ring === -1) return null // Polar Sink rendered separately

  const radius = RING_RADII[layout.ring] ?? RING_RADII[2]
  const { x, y } = polarToXY(layout.sectorMid, radius)

  const isStronghold = territory.territory_type === 'stronghold'
  const isSand = territory.territory_type === 'sand'
  const isRock = territory.territory_type === 'rock'
  const hasSpice = territory.current_spice > 0
  const hasForces = forceEntries && forceEntries.length > 0

  // Node size
  const nodeR = isStronghold ? 26 : 20

  // Colors
  let fill = '#1c1a14'
  let stroke = '#3a3020'
  if (isStronghold) { fill = '#2a1f0a'; stroke = '#b8860b' }
  else if (isSand) { fill = '#1f1a0e'; stroke = '#5c4a1e' }
  else if (isRock) { fill = '#1a1a1a'; stroke = '#4a4a3a' }

  if (isStormSector && isSand && !territory.storm_exception) {
    stroke = '#ef4444'
  }

  // Highlight colors: 'from' = green, 'to' = blue, 'adjacent' = dim teal
  const glowColor =
    highlight === 'from'     ? '#22c55e' :
    highlight === 'to'       ? '#3b82f6' :
    highlight === 'adjacent' ? '#0d9488' :
    null

  // Abbreviate long names
  const shortName = name
    .replace('Habbanya Ridge Flat', 'Hab. Ridge')
    .replace('Habbanya Sietch', 'Hab. Sietch')
    .replace('Habbanya Erg', 'Hab. Erg')
    .replace('Cielago Depression', 'Cielago Dep.')
    .replace('Wind Pass North', 'W. Pass N')
    .replace('False Wall East', 'FW East')
    .replace('False Wall West', 'FW West')
    .replace('False Wall South', 'FW South')
    .replace("Tuek's Sietch", "Tuek's")
    .replace('Plastic Basin', 'Plastic B.')
    .replace('Hole in the Rock', 'Hole/Rock')
    .replace('Sihaya Ridge', 'Sihaya R.')
    .replace('Broken Land', 'Broken L.')
    .replace('Imperial Basin', 'Imp. Basin')

  return (
    <g>
      {/* Highlight glow ring — drawn behind the node */}
      {glowColor && (
        <circle
          cx={x} cy={y} r={nodeR + 5}
          fill="none"
          stroke={glowColor}
          strokeWidth={highlight === 'adjacent' ? 1.5 : 2.5}
          opacity={highlight === 'adjacent' ? 0.5 : 0.9}
        />
      )}

      {/* Node circle */}
      <circle
        cx={x} cy={y} r={nodeR}
        fill={fill}
        stroke={glowColor ?? stroke}
        strokeWidth={isStronghold ? 2 : 1.5}
      />

      {/* Stronghold inner marker */}
      {isStronghold && (
        <circle cx={x} cy={y} r={nodeR - 4} fill="none" stroke={stroke} strokeWidth={0.5} strokeDasharray="2,2" />
      )}

      {/* Territory name */}
      <text
        x={x} y={y - (hasForces || hasSpice ? 4 : 0)}
        textAnchor="middle"
        dominantBaseline="central"
        fill={isStronghold ? '#d4a84b' : '#999'}
        fontSize={isStronghold ? 7.5 : 6.5}
        fontWeight={isStronghold ? 'bold' : 'normal'}
      >
        {shortName}
      </text>

      {/* Spice indicator */}
      {hasSpice && (
        <text
          x={x} y={y + 8}
          textAnchor="middle"
          fill="#d97706"
          fontSize={8}
          fontWeight="bold"
        >
          {'◆'}{territory.current_spice}
        </text>
      )}

      {/* Force dots */}
      {hasForces && (
        <g>
          {forceEntries.map((entry, i) => {
            const dotX = x - ((forceEntries.length - 1) * 6) / 2 + i * 6
            const dotY = y + (hasSpice ? 16 : 10)
            return (
              <g key={entry.faction}>
                <circle
                  cx={dotX} cy={dotY} r={5}
                  fill={FACTION_FILL[entry.faction] || '#888'}
                  opacity={0.9}
                />
                <text
                  x={dotX} y={dotY}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fill="#000"
                  fontSize={6}
                  fontWeight="bold"
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

export default function GameBoard({ territories, players, stormSector, highlightFrom = '', highlightTo = '', adjacentTo = [] }) {
  if (!territories) return null

  const forceMap = buildForceMap(players)

  // Determine which sectors the storm currently occupies
  const stormSectorNum = stormSector ?? 0

  // Build highlight lookup: territory name → 'from' | 'to' | 'adjacent' | null
  const adjacentSet = new Set(adjacentTo)
  function getHighlight(name) {
    if (name === highlightFrom) return 'from'
    if (name === highlightTo) return 'to'
    if (highlightFrom && adjacentSet.has(name)) return 'adjacent'
    return null
  }

  return (
    <div className="bg-surface border border-[#3a3020] rounded p-2 h-full flex flex-col">
      <svg
        viewBox="0 0 600 600"
        className="flex-1 w-full min-h-0"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Background */}
        <circle cx={CX} cy={CY} r={BOARD_RADIUS} fill="#0e0d09" stroke="#3a3020" strokeWidth="1.5" />

        {/* Sector division lines */}
        {Array.from({ length: 18 }, (_, i) => {
          const angle = (i * 20 - 90) * (Math.PI / 180)
          const x2 = CX + BOARD_RADIUS * Math.cos(angle)
          const y2 = CY + BOARD_RADIUS * Math.sin(angle)
          // Lines only extend from outer edge to the rock ring
          const innerR = 55
          const x1 = CX + innerR * Math.cos(angle)
          const y1 = CY + innerR * Math.sin(angle)
          return (
            <line
              key={i}
              x1={x1} y1={y1} x2={x2} y2={y2}
              stroke="#2a2418"
              strokeWidth="0.5"
            />
          )
        })}

        {/* Sector numbers around the edge */}
        {Array.from({ length: 18 }, (_, i) => {
          const angle = sectorAngle(i + 0.5) // center of sector
          const r = BOARD_RADIUS - 10
          const x = CX + r * Math.cos(angle)
          const y = CY + r * Math.sin(angle)
          const isStorm = i === stormSectorNum
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
            >
              {i}
            </text>
          )
        })}

        {/* Ring guides (subtle) */}
        <circle cx={CX} cy={CY} r={RING_RADII[0]} fill="none" stroke="#1e1b12" strokeWidth="0.5" />
        <circle cx={CX} cy={CY} r={RING_RADII[1]} fill="none" stroke="#1e1b12" strokeWidth="0.5" />
        <circle cx={CX} cy={CY} r={RING_RADII[2]} fill="none" stroke="#1e1b12" strokeWidth="0.5" />

        {/* Polar Sink (center) */}
        <circle cx={CX} cy={CY} r={45} fill="#0f1520" stroke="#2a3a5a" strokeWidth="1.5" />
        <text
          x={CX} y={CY - 5}
          textAnchor="middle"
          fill="#6b8ab0"
          fontSize={8}
          fontWeight="bold"
        >
          Polar Sink
        </text>
        {/* Polar Sink forces */}
        {forceMap['Polar Sink'] && (
          <g>
            {forceMap['Polar Sink'].map((entry, i) => {
              const dotX = CX - ((forceMap['Polar Sink'].length - 1) * 6) / 2 + i * 6
              return (
                <g key={entry.faction}>
                  <circle cx={dotX} cy={CY + 10} r={5} fill={FACTION_FILL[entry.faction] || '#888'} opacity={0.9} />
                  <text x={dotX} y={CY + 10} textAnchor="middle" dominantBaseline="central" fill="#000" fontSize={6} fontWeight="bold">
                    {entry.count}
                  </text>
                </g>
              )
            })}
          </g>
        )}

        {/* Storm arc */}
        <StormArc stormSector={stormSectorNum} />

        {/* Territory nodes */}
        {Object.entries(territories).map(([name, territory]) => {
          const layout = TERRITORY_LAYOUT[name]
          if (!layout) return null
          const forces = forceMap[name] || []
          // Check if this territory is in the storm sector
          const isStormSector = (territory.sectors || []).includes(stormSectorNum)
          return (
            <TerritoryNode
              key={name}
              name={name}
              territory={territory}
              layout={layout}
              forceEntries={forces}
              isStormSector={isStormSector}
              highlight={getHighlight(name)}
            />
          )
        })}
      </svg>

      {/* Map Legend */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-2 py-1 border-t border-[#3a3020] text-[10px] text-gray-500 shrink-0">
        {/* Territory types */}
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-full border-2" style={{ borderColor: '#b8860b', background: '#2a1f0a' }} />
          Stronghold
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-full border" style={{ borderColor: '#4a4a3a', background: '#1a1a1a' }} />
          Rock
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-full border" style={{ borderColor: '#5c4a1e', background: '#1f1a0e' }} />
          Sand
        </span>

        {/* Symbols */}
        <span className="flex items-center gap-1">
          <span className="text-spice font-bold text-xs">◆</span>
          Spice
        </span>
        <span className="flex items-center gap-1">
          <span className="text-red-500 font-bold">━</span>
          Storm
        </span>

        {/* Divider */}
        <span className="text-[#3a3020]">|</span>

        {/* Faction colors */}
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
