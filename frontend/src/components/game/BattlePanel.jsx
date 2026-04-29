import { useState } from 'react'
import Button from '../ui/Button.jsx'

const FACTION_LABELS = {
  atreides: 'Atreides', harkonnen: 'Harkonnen', bene_gesserit: 'Bene Gesserit',
  fremen: 'Fremen', spacing_guild: 'Guild', emperor: 'Emperor',
}

const CARD_TYPE_BADGE = {
  weapon: { label: 'WPN', color: 'text-red-400' },
  defense: { label: 'DEF', color: 'text-blue-400' },
  special: { label: 'SPL', color: 'text-purple-400' },
  worthless: { label: 'WTH', color: 'text-gray-500' },
}

function CardBadge({ type }) {
  const badge = CARD_TYPE_BADGE[type] ?? { label: type?.toUpperCase(), color: 'text-gray-400' }
  return <span className={`text-[9px] font-bold ${badge.color}`}>[{badge.label}]</span>
}

function findLeaderName(players, leaderId) {
  if (!leaderId) return null
  if (leaderId === 'kwisatz_haderach') return 'Kwisatz Haderach'
  for (const p of (players || [])) {
    const leader = (p.leaders || []).find(l => l.id === leaderId)
    if (leader) return leader.name
  }
  return leaderId // fallback to ID
}

export default function BattlePanel({ activeBattle, myPlayer, players, gameState, onSubmitPlan, onDeclareTraitor }) {
  const [forcesDialed, setForcesDialed] = useState(0)
  const [specialForcesDialed, setSpecialForcesDialed] = useState(0)
  const [spiceToExpend, setSpiceToExpend] = useState(0)
  const [selectedLeader, setSelectedLeader] = useState('')
  const [selectedWeapon, setSelectedWeapon] = useState('')
  const [selectedDefense, setSelectedDefense] = useState('')

  const isAdvanced = gameState?.mode === 'advanced'

  if (!activeBattle || !myPlayer) return null

  const isAttacker = myPlayer.faction === activeBattle.attacker_faction
  const isDefender = myPlayer.faction === activeBattle.defender_faction
  const isParticipant = isAttacker || isDefender

  const myPlanSubmitted = isAttacker
    ? activeBattle.attacker_plan != null
    : isDefender
      ? activeBattle.defender_plan != null
      : false

  const myTraitorDeclared = isAttacker
    ? activeBattle.attacker_traitor_called != null
    : isDefender
      ? activeBattle.defender_traitor_called != null
      : false

  const awaitingTraitor = activeBattle.awaiting_traitor_declarations === true

  // Count my forces in this territory (regular and special separately)
  const myForceGroups = (myPlayer.forces_on_board || [])
    .filter(fg => fg.territory_name === activeBattle.territory_name)
  const myRegularInTerritory = myForceGroups.reduce((s, fg) => s + (fg.regular_count || 0), 0)
  const mySpecialInTerritory = myForceGroups.reduce((s, fg) => s + (fg.special_count || 0), 0)
  const myForcesInTerritory = myRegularInTerritory + mySpecialInTerritory

  // Available leaders
  const availableLeaders = (myPlayer.leaders || []).filter(l => l.status === 'available')

  // All treachery cards — any card may be played in weapon or defense slot (bluffing is valid)
  const allCards = myPlayer.treachery_hand || []

  // Determine which traitor cards match the opponent's leader
  const opponentLeaderId = isAttacker
    ? activeBattle.defender_plan?.leader_id
    : activeBattle.attacker_plan?.leader_id

  const opponentLeaderName = findLeaderName(players, opponentLeaderId)

  const matchingTraitorCards = (myPlayer.traitor_cards || []).filter(
    tc => tc.leader_id === opponentLeaderId && opponentLeaderId
  )
  const hasMatchingTraitor = matchingTraitorCards.length > 0

  function handleSubmit() {
    onSubmitPlan(
      forcesDialed,
      selectedLeader || null,
      selectedWeapon || null,
      selectedDefense || null,
      specialForcesDialed,
      spiceToExpend,
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
        {/* Submission status indicators */}
        <div className="flex justify-center gap-3 mt-1.5 text-[9px]">
          <span className={activeBattle.attacker_plan ? 'text-green-500' : 'text-gray-600'}>
            {activeBattle.attacker_plan ? '✓' : '○'} ATK plan
          </span>
          <span className={activeBattle.defender_plan ? 'text-green-500' : 'text-gray-600'}>
            {activeBattle.defender_plan ? '✓' : '○'} DEF plan
          </span>
        </div>
      </div>

      {/* ── PRE-BATTLE INCOMPLETE WARNING ── */}
      {isParticipant && !myPlanSubmitted && !awaitingTraitor && activeBattle.prebattle_complete === false && (
        <div className="border border-yellow-800/50 bg-yellow-900/10 rounded p-2 text-center">
          <p className="text-yellow-500 text-[10px] font-bold">⏳ Pre-Battle Phase Active</p>
          <p className="text-gray-500 text-[9px] mt-0.5">
            Resolve Voice &amp; Prescience above before submitting your plan.
          </p>
        </div>
      )}

      {/* ── BATTLE PLAN SUBMISSION ── */}
      {isParticipant && !myPlanSubmitted && !awaitingTraitor && (activeBattle.prebattle_complete !== false) && (
        <div className="space-y-1.5">
          <p className="text-gray-500 text-[10px] uppercase px-1">
            Your Plan ({isAttacker ? 'Attacker' : 'Defender'})
          </p>

          {/* Regular forces dial */}
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-[10px] w-14">Regular</span>
            <input
              type="number"
              min={0}
              max={myRegularInTerritory}
              value={forcesDialed - specialForcesDialed}
              onChange={(e) => {
                const reg = Math.max(0, Math.min(myRegularInTerritory, parseInt(e.target.value) || 0))
                setForcesDialed(reg + specialForcesDialed)
              }}
              className="bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs font-mono w-14 focus:border-sand outline-none"
            />
            <span className="text-gray-500 text-[10px]">/ {myRegularInTerritory}</span>
          </div>

          {/* Special forces dial (only if player has special forces here) */}
          {mySpecialInTerritory > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-gray-400 text-[10px] w-14">Special</span>
              <input
                type="number"
                min={0}
                max={mySpecialInTerritory}
                value={specialForcesDialed}
                onChange={(e) => {
                  const sp = Math.max(0, Math.min(mySpecialInTerritory, parseInt(e.target.value) || 0))
                  setSpecialForcesDialed(sp)
                  setForcesDialed((forcesDialed - specialForcesDialed) + sp)
                }}
                className="bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs font-mono w-14 focus:border-sand outline-none"
              />
              <span className="text-gray-500 text-[10px]">/ {mySpecialInTerritory}</span>
            </div>
          )}

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

          {/* Weapon slot — any card allowed */}
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-[10px] w-10">Wpn</span>
            <select
              value={selectedWeapon}
              onChange={(e) => {
                setSelectedWeapon(e.target.value)
                if (e.target.value && e.target.value === selectedDefense) setSelectedDefense('')
              }}
              className="bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs flex-1 focus:border-sand outline-none"
            >
              <option value="">None</option>
              {allCards
                .filter(c => c.id !== selectedDefense)
                .map(c => (
                  <option key={c.id} value={c.id}>
                    {c.name} [{c.card_type?.toUpperCase()?.slice(0,3)}]
                  </option>
                ))}
            </select>
          </div>

          {/* Defense slot — any card allowed */}
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-[10px] w-10">Def</span>
            <select
              value={selectedDefense}
              onChange={(e) => {
                setSelectedDefense(e.target.value)
                if (e.target.value && e.target.value === selectedWeapon) setSelectedWeapon('')
              }}
              className="bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs flex-1 focus:border-sand outline-none"
            >
              <option value="">None</option>
              {allCards
                .filter(c => c.id !== selectedWeapon)
                .map(c => (
                  <option key={c.id} value={c.id}>
                    {c.name} [{c.card_type?.toUpperCase()?.slice(0,3)}]
                  </option>
                ))}
            </select>
          </div>

          {/* Spice expenditure — Advanced mode only (supports forces to prevent half-strength) */}
          {isAdvanced && (
            <div className="flex items-center gap-2 mt-1 pt-1 border-t border-[#3a3020]">
              <span className="text-gray-400 text-[10px] w-14">Spice</span>
              <input
                type="number"
                min={0}
                max={Math.min(myPlayer.spice || 0, forcesDialed)}
                value={spiceToExpend}
                onChange={(e) => setSpiceToExpend(Math.max(0, Math.min(myPlayer.spice || 0, forcesDialed, parseInt(e.target.value) || 0)))}
                className="bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-spice text-xs font-mono w-14 focus:border-sand outline-none"
              />
              <span className="text-gray-500 text-[9px]">supports {spiceToExpend}/{forcesDialed} forces</span>
            </div>
          )}
          {isAdvanced && forcesDialed > 0 && (
            <p className="text-gray-600 text-[9px] px-1">
              Unsupported forces fight at ½ strength in Advanced mode
            </p>
          )}

          <Button onClick={handleSubmit} className="w-full text-xs py-1 mt-1">
            Submit Battle Plan
          </Button>
        </div>
      )}

      {/* ── TRAITOR DECLARATION ── */}
      {isParticipant && awaitingTraitor && !myTraitorDeclared && (
        <div className="space-y-2">
          <div className="border border-yellow-800/60 bg-yellow-900/10 rounded p-2">
            <p className="text-yellow-400 text-xs font-bold text-center uppercase tracking-wide">
              Plans Revealed — Call Traitor?
            </p>
            {opponentLeaderId ? (
              <p className="text-gray-400 text-[10px] text-center mt-1">
                Opponent plays: <span className="text-sand-light">{opponentLeaderName}</span>
              </p>
            ) : (
              <p className="text-gray-400 text-[10px] text-center mt-1">
                Opponent plays: <span className="text-gray-500">no leader</span>
              </p>
            )}
            {hasMatchingTraitor && (
              <div className="mt-1.5 space-y-0.5">
                {matchingTraitorCards.map(tc => (
                  <p key={tc.id} className="text-yellow-300 text-[10px] text-center">
                    You hold traitor card: <strong>{tc.leader_name}</strong>
                  </p>
                ))}
              </div>
            )}
          </div>

          <div className="flex gap-2">
            {hasMatchingTraitor && (
              <Button
                onClick={() => onDeclareTraitor(true)}
                className="flex-1 text-xs py-1 bg-yellow-800 hover:bg-yellow-700 border-yellow-600"
              >
                Call Traitor!
              </Button>
            )}
            <Button
              onClick={() => onDeclareTraitor(false)}
              className={`text-xs py-1 ${hasMatchingTraitor ? 'flex-1' : 'w-full'} opacity-80`}
            >
              Pass
            </Button>
          </div>
        </div>
      )}

      {isParticipant && awaitingTraitor && myTraitorDeclared && (
        <p className="text-gray-500 text-[10px] text-center py-2">
          Declaration submitted. Waiting for opponent...
        </p>
      )}

      {isParticipant && myPlanSubmitted && !awaitingTraitor && (
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
