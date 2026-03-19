/**
 * PlayerPanel — compact player stats.
 */

const FACTION_STYLES = {
  atreides:      { color: 'text-green-400',  border: 'border-green-800',  bg: 'bg-green-950/40',  label: 'Atreides' },
  harkonnen:     { color: 'text-red-400',    border: 'border-red-800',    bg: 'bg-red-950/40',    label: 'Harkonnen' },
  bene_gesserit: { color: 'text-purple-400', border: 'border-purple-800', bg: 'bg-purple-950/40', label: 'Bene Gesserit' },
  fremen:        { color: 'text-blue-400',   border: 'border-blue-800',   bg: 'bg-blue-950/40',   label: 'Fremen' },
  spacing_guild: { color: 'text-yellow-400', border: 'border-yellow-800', bg: 'bg-yellow-950/40', label: 'Guild' },
  emperor:       { color: 'text-orange-400', border: 'border-orange-800', bg: 'bg-orange-950/40', label: 'Emperor' },
}

const FACTION_SHORT = {
  atreides: 'ATR', harkonnen: 'HAR', bene_gesserit: 'BG',
  fremen: 'FRE', spacing_guild: 'GLD', emperor: 'EMP',
}

function PlayerCard({ player, isCurrentTurn }) {
  const style = FACTION_STYLES[player.faction] ?? {
    color: 'text-gray-400', border: 'border-gray-700', bg: 'bg-gray-900/40', label: player.faction
  }

  const totalBoard = (player.forces_on_board || []).reduce(
    (sum, fg) => sum + (fg.regular_count || 0) + (fg.special_count || 0), 0
  )

  const activeBorder = isCurrentTurn ? 'border-sand ring-1 ring-sand/30' : style.border

  return (
    <div className={`border ${activeBorder} ${style.bg} rounded p-2`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-gray-200 text-xs font-semibold truncate">
          {isCurrentTurn && <span className="text-sand mr-1">▶</span>}
          {player.name}
        </span>
        <span className={`${style.color} text-[10px] uppercase`}>{style.label}</span>
      </div>
      <div className="flex gap-2 text-[10px] text-gray-400">
        <span title="Spice">◆<span className="text-gray-200 font-mono ml-0.5">{player.spice}</span></span>
        <span title="Reserve">Rsv<span className="text-gray-200 font-mono ml-0.5">{player.forces_in_reserve}</span></span>
        <span title="On board">Brd<span className="text-gray-200 font-mono ml-0.5">{totalBoard}</span></span>
        <span title="Cards">Crd<span className="text-gray-200 font-mono ml-0.5">{player.treachery_hand?.length ?? player.treachery_hand_count ?? 0}</span></span>
      </div>
      {/* Alliance badge */}
      {player.ally && (
        <div className="mt-1 flex items-center gap-1">
          <span className="text-yellow-500 text-[9px]">⚭</span>
          <span className={`text-[9px] font-semibold ${FACTION_STYLES[player.ally]?.color ?? 'text-gray-400'}`}>
            {FACTION_SHORT[player.ally] ?? player.ally}
          </span>
        </div>
      )}
      {player.is_eliminated && (
        <div className="text-red-400 text-[10px] font-bold uppercase mt-1">Eliminated</div>
      )}
    </div>
  )
}

export default function PlayerPanel({ players, currentPlayerIndex }) {
  return (
    <div className="bg-surface border border-[#3a3020] rounded p-2">
      <h2 className="text-sand text-[10px] font-bold uppercase tracking-widest mb-1 px-1">Players</h2>
      <div className="space-y-1.5">
        {players.map((player, i) => (
          <PlayerCard key={player.id} player={player} isCurrentTurn={i === currentPlayerIndex} />
        ))}
      </div>
    </div>
  )
}
