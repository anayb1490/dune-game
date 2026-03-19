import { useState } from 'react'
import Button from '../ui/Button.jsx'

export default function RevivalPanel({ myPlayer, onReviveForces, onReviveLeader }) {
  const [reviveCount, setReviveCount] = useState(1)
  if (!myPlayer) return null

  const inTanks = (myPlayer.forces_in_tanks || 0) + (myPlayer.special_forces_in_tanks || 0)
  const maxAffordable = Math.floor(myPlayer.spice / 2)
  const maxRevive = Math.min(inTanks, maxAffordable)

  const deadLeaders = (myPlayer.leaders || []).filter(l => l.status === 'in_tanks')

  return (
    <div className="bg-surface border border-[#3a3020] rounded p-2 space-y-2">
      <h2 className="text-sand text-xs font-bold uppercase tracking-wider px-1">Revival</h2>

      <div className="text-[10px] text-gray-400 px-1">
        Forces in tanks: <span className="text-gray-200 font-mono">{inTanks}</span>
        <span className="text-gray-600 ml-2">(2◆ each)</span>
      </div>

      {inTanks > 0 && maxAffordable > 0 && (
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={1}
            max={maxRevive}
            value={reviveCount}
            onChange={(e) => setReviveCount(Math.max(1, Math.min(maxRevive, parseInt(e.target.value) || 1)))}
            className="bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs font-mono w-14 focus:border-sand outline-none"
          />
          <Button
            onClick={() => onReviveForces(reviveCount)}
            className="text-xs flex-1 py-1"
            disabled={reviveCount < 1 || reviveCount > maxRevive}
          >
            Revive {reviveCount} (◆{reviveCount * 2})
          </Button>
        </div>
      )}

      {deadLeaders.length > 0 && (
        <div className="space-y-1 border-t border-[#3a3020] pt-1.5">
          <p className="text-gray-500 text-[10px] uppercase px-1">Dead Leaders</p>
          {deadLeaders.map(leader => (
            <div key={leader.id} className="flex items-center justify-between px-1">
              <span className="text-gray-300 text-xs">{leader.name} ({leader.strength})</span>
              <Button
                onClick={() => onReviveLeader(leader.id)}
                className="text-[10px] px-2 py-0.5"
                disabled={myPlayer.spice < leader.strength}
              >
                ◆{leader.strength}
              </Button>
            </div>
          ))}
        </div>
      )}

      {inTanks === 0 && deadLeaders.length === 0 && (
        <p className="text-gray-600 text-[10px] px-1">Nothing to revive</p>
      )}
    </div>
  )
}
