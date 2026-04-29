/**
 * FremenSietchTracker — Advanced mode only.
 *
 * Shows which of the three sietches (Sietch Tabr, Habbanya Sietch, Tuek's Sietch)
 * the Fremen currently control. When all 3 are held (and Fremen has no ally),
 * the Fremen win — so this indicator gives every player a clear view of how
 * close the Fremen are to their special victory condition.
 *
 * Force occupancy lives on Player.forces_on_board (ForceGroup[]),
 * NOT on territory objects.
 */

const SIETCHES = ["Sietch Tabr", "Habbanya Sietch", "Tuek's Sietch"]

const FACTION_COLORS = {
  fremen:        'text-blue-400',
  atreides:      'text-green-400',
  harkonnen:     'text-red-400',
  bene_gesserit: 'text-purple-400',
  spacing_guild: 'text-yellow-400',
  emperor:       'text-orange-400',
}

const FACTION_SHORT = {
  fremen: 'FRE', atreides: 'ATR', harkonnen: 'HAR',
  bene_gesserit: 'BG', spacing_guild: 'GLD', emperor: 'EMP',
}

/**
 * Returns a map of { faction -> totalForces } for all factions with forces
 * in the given territory (any sector).
 */
function getOccupants(players, territoryName) {
  const result = {}
  for (const player of (players || [])) {
    const groups = (player.forces_on_board || []).filter(fg => fg.territory_name === territoryName)
    const total = groups.reduce((s, fg) => s + (fg.regular_count || 0) + (fg.special_count || 0), 0)
    if (total > 0) result[player.faction] = total
  }
  return result
}

export default function FremenSietchTracker({ players, isAdvanced }) {
  if (!isAdvanced) return null

  const fremenPlayer = (players || []).find(p => p.faction === 'fremen')
  if (!fremenPlayer) return null

  const sietchStates = SIETCHES.map(name => {
    const occupants = getOccupants(players, name)
    const fremenHere = (occupants.fremen || 0) > 0
    return { name, occupants, fremenHere }
  })

  const fremenCount = sietchStates.filter(s => s.fremenHere).length
  const hasAlly = !!fremenPlayer.ally

  return (
    <div className="bg-surface border border-blue-900/50 rounded p-2">
      <div className="flex items-center justify-between mb-1.5 px-1">
        <p className="text-blue-400 text-[10px] font-bold uppercase tracking-wider">
          Fremen Sietches
        </p>
        <span className={`text-[10px] font-mono font-bold ${fremenCount === 3 ? 'text-green-400' : 'text-gray-400'}`}>
          {fremenCount}/3
        </span>
      </div>

      <div className="space-y-1">
        {sietchStates.map(({ name, occupants, fremenHere }) => {
          // Short display names
          const shortName = name === "Tuek's Sietch" ? "Tuek's"
            : name === "Habbanya Sietch" ? "Habbanya"
            : "Sietch Tabr"

          const otherFactions = Object.entries(occupants).filter(([f]) => f !== 'fremen')

          return (
            <div
              key={name}
              className={`flex items-center justify-between rounded px-1.5 py-0.5 text-[10px] ${
                fremenHere
                  ? 'bg-blue-900/30 border border-blue-700/40'
                  : 'border border-transparent'
              }`}
            >
              <span className={fremenHere ? 'text-blue-300 font-medium' : 'text-gray-500'}>
                {fremenHere ? '✓' : '○'} {shortName}
              </span>

              <span className="flex gap-1 items-center">
                {fremenHere && (
                  <span className="text-blue-400 font-mono">
                    FRE:{occupants.fremen}
                  </span>
                )}
                {otherFactions.map(([faction, count]) => (
                  <span key={faction} className={`${FACTION_COLORS[faction] ?? 'text-gray-400'} font-mono`}>
                    {FACTION_SHORT[faction] ?? faction.slice(0,3).toUpperCase()}:{count}
                  </span>
                ))}
                {Object.keys(occupants).length === 0 && (
                  <span className="text-gray-600">empty</span>
                )}
              </span>
            </div>
          )
        })}
      </div>

      {fremenCount === 3 && (
        <p className={`text-[10px] text-center mt-1.5 font-bold ${hasAlly ? 'text-yellow-500' : 'text-green-400'}`}>
          {hasAlly ? '⚠ Allied — victory blocked!' : '🏆 Desert control achieved!'}
        </p>
      )}
    </div>
  )
}
