/**
 * SpecialCardPanel — lets the player play out-of-battle special treachery cards.
 *
 * Shows actionable special cards in the player's hand with inline forms:
 *   • Karama (basic)        — block a faction's special ability
 *   • Karama (Advanced)     — use your faction's unique Karama power
 *   • Tleilaxu Ghola        — free revival (leader or up to 5 forces)
 *   • Family Atomics        — destroy the Shield Wall (Advanced)
 *   • Hajr                  — extra movement action (Shipment phase only)
 *   • Weather Control       — set next storm movement 0–10
 *
 * Each card renders a "Play" button that expands into an inline form.
 * Calling onAction(actionType, payload) sends the action to the server.
 */

import { useState } from 'react'
import Button from '../ui/Button.jsx'

const FACTION_LABELS = {
  atreides: 'Atreides', harkonnen: 'Harkonnen', bene_gesserit: 'Bene Gesserit',
  fremen: 'Fremen', spacing_guild: 'Guild', emperor: 'Emperor',
}

const VOICE_CARD_TYPES = [
  { value: 'poison_weapon',     label: 'Poison Weapon' },
  { value: 'projectile_weapon', label: 'Projectile Weapon' },
  { value: 'lasgun',            label: 'Lasgun' },
  { value: 'snooper',           label: 'Snooper (vs Poison)' },
  { value: 'shield',            label: 'Shield (vs Projectile)' },
  { value: 'worthless',         label: 'Worthless Card' },
  { value: 'cheap_hero',        label: 'Cheap Hero/Heroine' },
]

// ---------------------------------------------------------------------------
// Individual card action forms
// ---------------------------------------------------------------------------

function KaramaBlockForm({ players, myPlayer, onSubmit, onCancel }) {
  const others = (players || []).filter(p => p.faction !== myPlayer?.faction && !p.is_eliminated)
  const [target, setTarget] = useState(others[0]?.faction || '')

  return (
    <div className="space-y-2 mt-2 pt-2 border-t border-[#3a3020]">
      <p className="text-gray-400 text-[10px]">Block which faction's ability?</p>
      <select
        value={target}
        onChange={e => setTarget(e.target.value)}
        className="w-full bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs focus:border-sand outline-none"
      >
        {others.map(p => (
          <option key={p.faction} value={p.faction}>{FACTION_LABELS[p.faction] ?? p.faction}</option>
        ))}
      </select>
      <div className="flex gap-2">
        <Button onClick={() => onSubmit({ target_faction: target })} className="flex-1 text-xs py-1">Block</Button>
        <Button onClick={onCancel} className="text-xs py-1 opacity-60">Cancel</Button>
      </div>
    </div>
  )
}

function KaramaPowerForm({ myPlayer, players, territories, activeBattle, onSubmit, onCancel }) {
  const faction = myPlayer?.faction
  const others = (players || []).filter(p => p.faction !== faction && !p.is_eliminated)

  // Atreides: pick target from battle participants
  const [atrTarget, setAtrTarget] = useState(
    activeBattle
      ? (activeBattle.attacker_faction === faction
          ? activeBattle.defender_faction
          : activeBattle.attacker_faction)
      : others[0]?.faction || ''
  )

  // Emperor: forces or leader
  const [empMode, setEmpMode] = useState('forces')
  const [empCount, setEmpCount] = useState(1)
  const [empLeader, setEmpLeader] = useState(
    myPlayer?.leaders?.find(l => l.status === 'in_tanks')?.id || ''
  )

  // Fremen: sand territory
  const sandTerritories = Object.entries(territories || {})
    .filter(([, t]) => t.territory_type === 'sand')
    .map(([name]) => name)
    .sort()
  const [fremenTerritory, setFremenTerritory] = useState(sandTerritories[0] || '')

  // Guild: target faction
  const [guildTarget, setGuildTarget] = useState(others[0]?.faction || '')

  // Harkonnen: select target, then pick cards
  const [harkTarget, setHarkTarget] = useState(others[0]?.faction || '')
  const [takeIds, setTakeIds] = useState('')
  const [giveIds, setGiveIds] = useState('')

  const leadersInTanks = myPlayer?.leaders?.filter(l => l.status === 'in_tanks') || []

  if (faction === 'atreides') {
    if (!activeBattle) return (
      <div className="mt-2 pt-2 border-t border-[#3a3020]">
        <p className="text-yellow-500 text-[10px]">Atreides power requires an active battle.</p>
        <Button onClick={onCancel} className="text-xs py-1 mt-1 w-full opacity-60">Cancel</Button>
      </div>
    )
    return (
      <div className="space-y-2 mt-2 pt-2 border-t border-[#3a3020]">
        <p className="text-gray-400 text-[10px]">Reveal whose full Battle Plan?</p>
        <select
          value={atrTarget}
          onChange={e => setAtrTarget(e.target.value)}
          className="w-full bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs focus:border-sand outline-none"
        >
          {[activeBattle.attacker_faction, activeBattle.defender_faction]
            .filter(f => f !== faction)
            .map(f => <option key={f} value={f}>{FACTION_LABELS[f] ?? f}</option>)}
        </select>
        <div className="flex gap-2">
          <Button onClick={() => onSubmit({ target_faction: atrTarget })} className="flex-1 text-xs py-1">Reveal Plan</Button>
          <Button onClick={onCancel} className="text-xs py-1 opacity-60">Cancel</Button>
        </div>
      </div>
    )
  }

  if (faction === 'emperor') {
    return (
      <div className="space-y-2 mt-2 pt-2 border-t border-[#3a3020]">
        <p className="text-gray-400 text-[10px]">Revive for free:</p>
        <div className="flex gap-3 text-xs">
          <label className="flex items-center gap-1 cursor-pointer">
            <input type="radio" checked={empMode === 'forces'} onChange={() => setEmpMode('forces')} />
            <span className="text-gray-300">Forces (up to 3)</span>
          </label>
          <label className="flex items-center gap-1 cursor-pointer">
            <input type="radio" checked={empMode === 'leader'} onChange={() => setEmpMode('leader')} />
            <span className="text-gray-300">Leader</span>
          </label>
        </div>
        {empMode === 'forces' && (
          <input
            type="number" min={1} max={3} value={empCount}
            onChange={e => setEmpCount(Math.min(3, Math.max(1, parseInt(e.target.value) || 1)))}
            className="w-full bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs font-mono focus:border-sand outline-none"
          />
        )}
        {empMode === 'leader' && (
          <select
            value={empLeader}
            onChange={e => setEmpLeader(e.target.value)}
            className="w-full bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs focus:border-sand outline-none"
          >
            <option value="">— select leader —</option>
            {leadersInTanks.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
        )}
        <div className="flex gap-2">
          <Button
            onClick={() => onSubmit(empMode === 'forces'
              ? { force_count: empCount }
              : { leader_id: empLeader })}
            className="flex-1 text-xs py-1"
          >
            Revive
          </Button>
          <Button onClick={onCancel} className="text-xs py-1 opacity-60">Cancel</Button>
        </div>
      </div>
    )
  }

  if (faction === 'fremen') {
    return (
      <div className="space-y-2 mt-2 pt-2 border-t border-[#3a3020]">
        <p className="text-gray-400 text-[10px]">Place worm in which sand territory?</p>
        <select
          value={fremenTerritory}
          onChange={e => setFremenTerritory(e.target.value)}
          className="w-full bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs focus:border-sand outline-none"
        >
          {sandTerritories.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <div className="flex gap-2">
          <Button onClick={() => onSubmit({ territory_name: fremenTerritory })} className="flex-1 text-xs py-1">Place Worm</Button>
          <Button onClick={onCancel} className="text-xs py-1 opacity-60">Cancel</Button>
        </div>
      </div>
    )
  }

  if (faction === 'spacing_guild') {
    return (
      <div className="space-y-2 mt-2 pt-2 border-t border-[#3a3020]">
        <p className="text-gray-400 text-[10px]">Block whose next shipment?</p>
        <select
          value={guildTarget}
          onChange={e => setGuildTarget(e.target.value)}
          className="w-full bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs focus:border-sand outline-none"
        >
          {others.map(p => <option key={p.faction} value={p.faction}>{FACTION_LABELS[p.faction] ?? p.faction}</option>)}
        </select>
        <div className="flex gap-2">
          <Button onClick={() => onSubmit({ target_faction: guildTarget })} className="flex-1 text-xs py-1">Block Ship</Button>
          <Button onClick={onCancel} className="text-xs py-1 opacity-60">Cancel</Button>
        </div>
      </div>
    )
  }

  if (faction === 'harkonnen') {
    const targetPlayer = players?.find(p => p.faction === harkTarget)
    const targetCardCount = targetPlayer?.treachery_hand_count ?? targetPlayer?.treachery_hand?.length ?? '?'
    return (
      <div className="space-y-2 mt-2 pt-2 border-t border-[#3a3020]">
        <p className="text-gray-400 text-[10px]">1-for-1 card exchange:</p>
        <select
          value={harkTarget}
          onChange={e => setHarkTarget(e.target.value)}
          className="w-full bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs focus:border-sand outline-none"
        >
          {others.map(p => <option key={p.faction} value={p.faction}>{FACTION_LABELS[p.faction] ?? p.faction} ({p.treachery_hand_count ?? p.treachery_hand?.length ?? '?'} cards)</option>)}
        </select>
        <input
          placeholder="Card ID(s) to TAKE (comma-separated)"
          value={takeIds}
          onChange={e => setTakeIds(e.target.value)}
          className="w-full bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs focus:border-sand outline-none"
        />
        <input
          placeholder="Card ID(s) to GIVE (comma-separated)"
          value={giveIds}
          onChange={e => setGiveIds(e.target.value)}
          className="w-full bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs focus:border-sand outline-none"
        />
        <p className="text-gray-600 text-[9px]">Card IDs visible in opponent's hand display (hover over cards)</p>
        <div className="flex gap-2">
          <Button
            onClick={() => onSubmit({
              target_faction: harkTarget,
              take_card_ids: takeIds.split(',').map(s => s.trim()).filter(Boolean),
              give_card_ids: giveIds.split(',').map(s => s.trim()).filter(Boolean),
            })}
            className="flex-1 text-xs py-1"
          >
            Exchange
          </Button>
          <Button onClick={onCancel} className="text-xs py-1 opacity-60">Cancel</Button>
        </div>
      </div>
    )
  }

  if (faction === 'bene_gesserit') {
    return (
      <div className="space-y-2 mt-2 pt-2 border-t border-[#3a3020]">
        <p className="text-gray-400 text-[10px]">BG has no unique Karama power — the card is simply discarded.</p>
        <div className="flex gap-2">
          <Button onClick={() => onSubmit({})} className="flex-1 text-xs py-1">Discard Karama</Button>
          <Button onClick={onCancel} className="text-xs py-1 opacity-60">Cancel</Button>
        </div>
      </div>
    )
  }

  return null
}

function GholaForm({ myPlayer, onSubmit, onCancel }) {
  const [mode, setMode] = useState('forces')
  const [count, setCount] = useState(1)
  const [leaderId, setLeaderId] = useState(
    myPlayer?.leaders?.find(l => l.status === 'in_tanks')?.id || ''
  )
  const leadersInTanks = myPlayer?.leaders?.filter(l => l.status === 'in_tanks') || []
  const tanksCount = myPlayer?.forces_in_tanks || 0

  return (
    <div className="space-y-2 mt-2 pt-2 border-t border-[#3a3020]">
      <p className="text-gray-400 text-[10px]">Tleilaxu Ghola — free revival:</p>
      <div className="flex gap-3 text-xs">
        <label className="flex items-center gap-1 cursor-pointer">
          <input type="radio" checked={mode === 'forces'} onChange={() => setMode('forces')} />
          <span className="text-gray-300">Forces (up to 5)</span>
        </label>
        <label className="flex items-center gap-1 cursor-pointer">
          <input type="radio" checked={mode === 'leader'} onChange={() => setMode('leader')} />
          <span className="text-gray-300">Leader</span>
        </label>
      </div>
      {mode === 'forces' && (
        <div className="flex items-center gap-2">
          <input
            type="number" min={1} max={Math.min(5, tanksCount)} value={count}
            onChange={e => setCount(Math.min(5, tanksCount, Math.max(1, parseInt(e.target.value) || 1)))}
            className="w-16 bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs font-mono focus:border-sand outline-none"
          />
          <span className="text-gray-500 text-[10px]">/ {Math.min(5, tanksCount)} available</span>
        </div>
      )}
      {mode === 'leader' && (
        <select
          value={leaderId}
          onChange={e => setLeaderId(e.target.value)}
          className="w-full bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs focus:border-sand outline-none"
        >
          <option value="">— select leader —</option>
          {leadersInTanks.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
        </select>
      )}
      <div className="flex gap-2">
        <Button
          onClick={() => onSubmit(mode === 'forces' ? { force_count: count } : { leader_id: leaderId })}
          className="flex-1 text-xs py-1"
        >
          Revive
        </Button>
        <Button onClick={onCancel} className="text-xs py-1 opacity-60">Cancel</Button>
      </div>
    </div>
  )
}

function TruthtranceForm({ players, myPlayer, onSubmit, onCancel }) {
  const others = (players || []).filter(p => p.faction !== myPlayer?.faction && !p.is_eliminated)
  const [target, setTarget] = useState(others[0]?.faction || '')
  const [question, setQuestion] = useState('')

  return (
    <div className="space-y-2 mt-2 pt-2 border-t border-[#3a3020]">
      <p className="text-gray-400 text-[10px]">
        Ask a yes/no question — the target must answer truthfully (honour system).
      </p>
      <select
        value={target}
        onChange={e => setTarget(e.target.value)}
        className="w-full bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs focus:border-sand outline-none"
      >
        {others.map(p => (
          <option key={p.faction} value={p.faction}>{FACTION_LABELS[p.faction] ?? p.faction}</option>
        ))}
      </select>
      <textarea
        placeholder="Your yes/no question (max 200 chars)…"
        value={question}
        onChange={e => setQuestion(e.target.value.slice(0, 200))}
        rows={2}
        className="w-full bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs focus:border-sand outline-none resize-none"
      />
      <p className="text-gray-600 text-[9px]">{question.length}/200</p>
      <div className="flex gap-2">
        <Button
          onClick={() => onSubmit({ target_faction: target, question })}
          disabled={!question.trim() || !target}
          className="flex-1 text-xs py-1"
        >
          Ask Question
        </Button>
        <Button onClick={onCancel} className="text-xs py-1 opacity-60">Cancel</Button>
      </div>
    </div>
  )
}

function WeatherControlForm({ onSubmit, onCancel }) {
  const [sectors, setSectors] = useState(3)
  return (
    <div className="space-y-2 mt-2 pt-2 border-t border-[#3a3020]">
      <p className="text-gray-400 text-[10px]">Set next storm movement (0–10 sectors):</p>
      <div className="flex items-center gap-2">
        <input
          type="range" min={0} max={10} value={sectors}
          onChange={e => setSectors(parseInt(e.target.value))}
          className="flex-1"
        />
        <span className="text-sand font-mono font-bold text-sm w-6 text-right">{sectors}</span>
      </div>
      <p className="text-gray-600 text-[9px]">0 = storm doesn't move; 10 = maximum storm movement</p>
      <div className="flex gap-2">
        <Button onClick={() => onSubmit({ sectors })} className="flex-1 text-xs py-1">Set Storm</Button>
        <Button onClick={onCancel} className="text-xs py-1 opacity-60">Cancel</Button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

// Cards that have out-of-battle special actions (not weapon/defense)
const ACTIONABLE_SPECIAL_TYPES = new Set([
  'karama', 'tleilaxu_ghola', 'family_atomics', 'hajr', 'weather_control', 'truthtrance',
])

export default function SpecialCardPanel({
  myPlayer,
  players,
  territories,
  gameState,
  onAction,
  actionBusy = false,
}) {
  const [activeCard, setActiveCard] = useState(null)   // card ID being configured
  const [activeMode, setActiveMode] = useState(null)   // 'basic_block' | 'faction_power'

  if (!myPlayer) return null

  const currentPhase = gameState?.current_phase
  const isAdvanced = gameState?.mode === 'advanced'
  const activeBattle = gameState?.active_battle
  const shieldWallDestroyed = gameState?.shield_wall_destroyed || false

  // Filter hand to only actionable special cards
  const actionableCards = (myPlayer.treachery_hand || []).filter(card => {
    if (card.card_type !== 'special') return false
    if (!ACTIONABLE_SPECIAL_TYPES.has(card.special_type)) return false
    // Hajr only usable during shipment
    if (card.special_type === 'hajr' && currentPhase !== 'shipment_and_movement') return false
    // Family Atomics: Advanced only; not if already destroyed
    if (card.special_type === 'family_atomics' && (!isAdvanced || shieldWallDestroyed)) return false
    // Truthtrance: Advanced only
    if (card.special_type === 'truthtrance' && !isAdvanced) return false
    return true
  })

  if (actionableCards.length === 0) return null

  function handleSubmitAction(actionType, payload) {
    onAction(actionType, payload)
    setActiveCard(null)
    setActiveMode(null)
  }

  function handleCancel() {
    setActiveCard(null)
    setActiveMode(null)
  }

  return (
    <div className="bg-surface border border-purple-900/60 rounded p-2">
      <p className="text-purple-400 text-[10px] uppercase tracking-wider px-1 mb-1.5">
        Special Cards
      </p>

      <div className="space-y-2">
        {actionableCards.map(card => {
          const isExpanded = activeCard === card.id

          return (
            <div
              key={card.id}
              className="bg-purple-950/30 border border-purple-800/50 rounded px-2 py-1.5"
            >
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-purple-300 text-xs font-bold">{card.name}</p>
                  <p className="text-gray-500 text-[9px]">
                    {card.special_type === 'karama' && (isAdvanced ? 'Block ability · Faction power' : 'Block faction ability')}
                    {card.special_type === 'tleilaxu_ghola' && 'Revive leader or forces'}
                    {card.special_type === 'family_atomics' && 'Destroy Shield Wall'}
                    {card.special_type === 'hajr' && 'Extra move this turn'}
                    {card.special_type === 'weather_control' && 'Control next storm'}
                    {card.special_type === 'truthtrance' && 'Force opponent to answer truthfully'}
                  </p>
                </div>
                {!isExpanded && (
                  <div className="flex gap-1 shrink-0">
                    {card.special_type === 'karama' && (
                      <>
                        <button
                          onClick={() => { setActiveCard(card.id); setActiveMode('basic_block') }}
                          disabled={actionBusy}
                          className="text-[9px] px-1.5 py-0.5 bg-purple-900/50 hover:bg-purple-800/60 border border-purple-700 rounded text-purple-300 disabled:opacity-40"
                        >
                          Block
                        </button>
                        {isAdvanced && (
                          <button
                            onClick={() => { setActiveCard(card.id); setActiveMode('faction_power') }}
                            disabled={actionBusy}
                            className="text-[9px] px-1.5 py-0.5 bg-purple-900/50 hover:bg-purple-800/60 border border-purple-700 rounded text-purple-300 disabled:opacity-40"
                          >
                            Power
                          </button>
                        )}
                      </>
                    )}
                    {card.special_type === 'hajr' && (
                      <button
                        onClick={() => handleSubmitAction('play_hajr', {})}
                        disabled={actionBusy}
                        className="text-[9px] px-1.5 py-0.5 bg-purple-900/50 hover:bg-purple-800/60 border border-purple-700 rounded text-purple-300 disabled:opacity-40"
                      >
                        Play
                      </button>
                    )}
                    {card.special_type === 'family_atomics' && (
                      <button
                        onClick={() => { setActiveCard(card.id); setActiveMode('confirm') }}
                        disabled={actionBusy}
                        className="text-[9px] px-1.5 py-0.5 bg-red-900/50 hover:bg-red-800/60 border border-red-700 rounded text-red-300 disabled:opacity-40"
                      >
                        Detonate
                      </button>
                    )}
                    {(card.special_type === 'tleilaxu_ghola' || card.special_type === 'weather_control' || card.special_type === 'truthtrance') && (
                      <button
                        onClick={() => { setActiveCard(card.id); setActiveMode('form') }}
                        disabled={actionBusy}
                        className="text-[9px] px-1.5 py-0.5 bg-purple-900/50 hover:bg-purple-800/60 border border-purple-700 rounded text-purple-300 disabled:opacity-40"
                      >
                        Play
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Expanded form */}
              {isExpanded && (
                <>
                  {card.special_type === 'karama' && activeMode === 'basic_block' && (
                    <KaramaBlockForm
                      players={players}
                      myPlayer={myPlayer}
                      onSubmit={payload => handleSubmitAction('play_karama_block', payload)}
                      onCancel={handleCancel}
                    />
                  )}
                  {card.special_type === 'karama' && activeMode === 'faction_power' && (
                    <KaramaPowerForm
                      myPlayer={myPlayer}
                      players={players}
                      territories={territories}
                      activeBattle={activeBattle}
                      onSubmit={payload => handleSubmitAction('play_karama_power', payload)}
                      onCancel={handleCancel}
                    />
                  )}
                  {card.special_type === 'tleilaxu_ghola' && (
                    <GholaForm
                      myPlayer={myPlayer}
                      onSubmit={payload => handleSubmitAction('play_tleilaxu_ghola', payload)}
                      onCancel={handleCancel}
                    />
                  )}
                  {card.special_type === 'family_atomics' && (
                    <div className="space-y-2 mt-2 pt-2 border-t border-red-900/50">
                      <p className="text-red-400 text-[10px]">
                        ⚠ This permanently destroys the Shield Wall. All non-Fremen forces there go to the tanks. This cannot be undone.
                      </p>
                      <div className="flex gap-2">
                        <Button
                          onClick={() => handleSubmitAction('play_family_atomics', {})}
                          className="flex-1 text-xs py-1 border-red-700 text-red-300"
                        >
                          Confirm Detonation
                        </Button>
                        <Button onClick={handleCancel} className="text-xs py-1 opacity-60">Cancel</Button>
                      </div>
                    </div>
                  )}
                  {card.special_type === 'weather_control' && (
                    <WeatherControlForm
                      onSubmit={payload => handleSubmitAction('play_weather_control', payload)}
                      onCancel={handleCancel}
                    />
                  )}
                  {card.special_type === 'truthtrance' && (
                    <TruthtranceForm
                      players={players}
                      myPlayer={myPlayer}
                      onSubmit={payload => handleSubmitAction('play_truthtrance', payload)}
                      onCancel={handleCancel}
                    />
                  )}
                </>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
