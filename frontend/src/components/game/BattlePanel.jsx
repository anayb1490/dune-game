import { useState } from 'react'
import Button from '../ui/Button.jsx'

const FACTION_LABELS = {
  atreides: 'Atreides', harkonnen: 'Harkonnen', bene_gesserit: 'Bene Gesserit',
  fremen: 'Fremen', spacing_guild: 'Guild', emperor: 'Emperor',
}

export default function BattlePanel({ activeBattle, myPlayer, onSubmitPlan }) {
  const [forcesDialed, setForcesDialed] = useState(0)
  const [selectedLeader, setSelectedLeader] = useState('')
  const [selectedWeapon, setSelectedWeapon] = useState('')
  const [selectedDefense, setSelectedDefense] = useState('')

  if (!activeBattle || !myPlayer) return null

  const isAttacker = myPlayer.faction === activeBattle.attacker_faction
  const isDefender = myPlayer.faction === activeBattle.defender_faction
  const isParticipant = isAttacker || isDefender

  const myPlanSubmitted = isAttacker
    ? activeBattle.attacker_plan != null
    : isDefender
      ? activeBattle.defender_plan != null
      : false

  // Count my forces in this territory
  const myForcesInTerritory = (myPlayer.forces_on_board || [])
    .filter(fg => fg.territory_name === activeBattle.territory_name)
    .reduce((sum, fg) => sum + (fg.regular_count || 0) + (fg.special_count || 0), 0)

  // Available leaders
  const availableLeaders = (myPlayer.leaders || []).filter(l => l.status === 'available')

  // Available weapon/defense cards
  const weapons = (myPlayer.treachery_hand || []).filter(c => c.card_type === 'weapon')
  const defenses = (myPlayer.treachery_hand || []).filter(c => c.card_type === 'defense')

  function handleSubmit() {
    onSubmitPlan(
      forcesDialed,
      selectedLeader || null,
      selectedWeapon || null,
      selectedDefense || null,
    )
  }

  return (
    <div className="bg-surface border border-[#3a3020] rounded p-2 space-y-2">
      <h2 className="text-sand text-xs font-bold uppercase tracking-wider px-1">Battle</h2>

      {/* Battle info */}
      <div className="border border-[#3a3020] rounded p-2 text-center">
        <p className="text-sand-light text-sm font-bold">{activeBattle.territory_name}</p>
        <div className="flex justify-center gap-2 mt-1 text-[10px]">
          <span className="text-red-400">{FACTION_LABELS[activeBattle.attacker_faction]} (ATK)</span>
          <span className="text-gray-600">vs</span>
          <span className="text-blue-400">{FACTION_LABELS[activeBattle.defender_faction]} (DEF)</span>
        </div>
      </div>

      {isParticipant && !myPlanSubmitted && (
        <div className="space-y-1.5">
          <p className="text-gray-500 text-[10px] uppercase px-1">
            Your Plan ({isAttacker ? 'Attacker' : 'Defender'})
          </p>

          {/* Forces dial */}
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-[10px] w-10">Dial</span>
            <input
              type="number"
              min={0}
              max={myForcesInTerritory}
              value={forcesDialed}
              onChange={(e) => setForcesDialed(Math.max(0, Math.min(myForcesInTerritory, parseInt(e.target.value) || 0)))}
              className="bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs font-mono w-14 focus:border-sand outline-none"
            />
            <span className="text-gray-500 text-[10px]">/ {myForcesInTerritory}</span>
          </div>

          {/* Leader select */}
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-[10px] w-10">Leader</span>
            <select
              value={selectedLeader}
              onChange={(e) => setSelectedLeader(e.target.value)}
              className="bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs flex-1 focus:border-sand outline-none"
            >
              <option value="">None</option>
              {availableLeaders.map(l => (
                <option key={l.id} value={l.id}>{l.name} ({l.strength})</option>
              ))}
            </select>
          </div>

          {/* Weapon card */}
          {weapons.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-gray-400 text-[10px] w-10">Wpn</span>
              <select
                value={selectedWeapon}
                onChange={(e) => setSelectedWeapon(e.target.value)}
                className="bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs flex-1 focus:border-sand outline-none"
              >
                <option value="">None</option>
                {weapons.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          )}

          {/* Defense card */}
          {defenses.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-gray-400 text-[10px] w-10">Def</span>
              <select
                value={selectedDefense}
                onChange={(e) => setSelectedDefense(e.target.value)}
                className="bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs flex-1 focus:border-sand outline-none"
              >
                <option value="">None</option>
                {defenses.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          )}

          <Button onClick={handleSubmit} className="w-full text-xs py-1">
            Submit Battle Plan
          </Button>
        </div>
      )}

      {isParticipant && myPlanSubmitted && (
        <p className="text-gray-500 text-[10px] text-center py-2">
          Plan submitted. Waiting for opponent...
        </p>
      )}

      {!isParticipant && (
        <p className="text-gray-500 text-[10px] text-center py-2">
          Battle in progress...
        </p>
      )}
    </div>
  )
}
