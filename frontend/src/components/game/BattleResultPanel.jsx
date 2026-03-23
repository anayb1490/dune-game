/**
 * BattleResultPanel — displays the outcome of the most recent battle.
 * Shown whenever gameState.last_battle_result is set.
 */

const FACTION_LABELS = {
  atreides: 'Atreides', harkonnen: 'Harkonnen', bene_gesserit: 'Bene Gesserit',
  fremen: 'Fremen', spacing_guild: 'Guild', emperor: 'Emperor',
}

function FL(faction) {
  return FACTION_LABELS[faction] ?? faction ?? '—'
}

export default function BattleResultPanel({ result }) {
  if (!result) return null

  const isMutualAnnihilation = result.lasgun_explosion
  const isTraitor = !!result.traitor_called_by
  const isDraw = !result.winner_faction && !isMutualAnnihilation && !isTraitor

  // Header style by outcome type
  let headerClass = 'text-sand-light'
  let headerText = `${FL(result.winner_faction)} Victorious`
  if (isMutualAnnihilation) {
    headerClass = 'text-orange-400'
    headerText = 'LASGUN-SHIELD EXPLOSION'
  } else if (isTraitor) {
    headerClass = 'text-yellow-400'
    headerText = `TRAITOR CALLED`
  }

  const atkWon = result.winner_faction === result.attacker_faction
  const defWon = result.winner_faction === result.defender_faction

  return (
    <div className="bg-surface border border-[#5a3010] rounded p-2 space-y-2">
      <div className="flex items-center gap-2 px-1">
        <h2 className="text-[10px] font-bold uppercase tracking-wider text-gray-500">Battle Result</h2>
        <span className="text-gray-600 text-[10px]">— {result.territory_name}</span>
      </div>

      {/* Outcome headline */}
      <div className={`text-center border border-[#3a3020] rounded p-2 ${
        isMutualAnnihilation ? 'border-orange-800/50 bg-orange-900/10' :
        isTraitor ? 'border-yellow-800/50 bg-yellow-900/10' :
        'border-green-800/30 bg-green-900/5'
      }`}>
        <p className={`text-sm font-bold uppercase tracking-wide ${headerClass}`}>
          {headerText}
        </p>
        {isTraitor && (
          <p className="text-yellow-300 text-[10px] mt-0.5">
            Called by {FL(result.traitor_called_by)}
          </p>
        )}
      </div>

      {/* Battle totals (shown for regular battles) */}
      {result.attacker_total != null && result.defender_total != null && (
        <div className="grid grid-cols-2 gap-1 text-center">
          <div className={`border rounded p-1.5 ${atkWon ? 'border-green-700/60 bg-green-900/10' : 'border-[#3a3020]'}`}>
            <p className={`text-[10px] font-bold ${atkWon ? 'text-green-400' : 'text-gray-400'}`}>
              {FL(result.attacker_faction)} {atkWon ? '👑' : ''}
            </p>
            <p className="text-sand-light text-lg font-mono font-bold">{result.attacker_total}</p>
            <p className="text-[9px] text-gray-500">ATK strength</p>
          </div>
          <div className={`border rounded p-1.5 ${defWon ? 'border-green-700/60 bg-green-900/10' : 'border-[#3a3020]'}`}>
            <p className={`text-[10px] font-bold ${defWon ? 'text-green-400' : 'text-gray-400'}`}>
              {FL(result.defender_faction)} {defWon ? '👑' : ''}
            </p>
            <p className="text-sand-light text-lg font-mono font-bold">{result.defender_total}</p>
            <p className="text-[9px] text-gray-500">DEF strength</p>
          </div>
        </div>
      )}

      {/* Casualties */}
      <div className="space-y-0.5">
        <p className="text-gray-600 text-[9px] uppercase px-1">Casualties</p>
        <div className="grid grid-cols-2 gap-1">
          <div className="border border-[#3a3020] rounded px-2 py-1 text-center">
            <p className="text-[9px] text-gray-500">{FL(result.attacker_faction)}</p>
            <p className={`text-xs font-mono font-bold ${result.attacker_forces_lost > 0 ? 'text-red-400' : 'text-gray-600'}`}>
              -{result.attacker_forces_lost} forces
            </p>
            {result.attacker_leader_killed && (
              <p className="text-[9px] text-red-500">leader killed</p>
            )}
          </div>
          <div className="border border-[#3a3020] rounded px-2 py-1 text-center">
            <p className="text-[9px] text-gray-500">{FL(result.defender_faction)}</p>
            <p className={`text-xs font-mono font-bold ${result.defender_forces_lost > 0 ? 'text-red-400' : 'text-gray-600'}`}>
              -{result.defender_forces_lost} forces
            </p>
            {result.defender_leader_killed && (
              <p className="text-[9px] text-red-500">leader killed</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
