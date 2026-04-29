/**
 * FactionShipmentPanel — faction-specific Shipment & Movement abilities.
 *
 * Shown during shipment_and_movement on the player's own turn.
 *
 * Bene Gesserit:
 *   • Flip Advisors → Fighters  (Advanced only)
 *   • Flip Fighters → Advisors  (Advanced only)
 *   NOTE: Free Ship is handled out-of-turn via BgFreeShipPanel in GameView.
 *
 * Spacing Guild:
 *   • Cross-Ship      — board-to-board transfer at ½ cost
 *   • Ship to Reserves — pull forces off-board at 1◆/2 forces
 */

import { useState } from 'react'
import Button from '../ui/Button.jsx'

const selectClass =
  'bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs w-full focus:border-sand outline-none'

// ---------------------------------------------------------------------------
// Bene Gesserit
// ---------------------------------------------------------------------------

function BgFlipForm({ myPlayer, territories, direction, onAction, onCancel }) {
  // direction: 'to_fighters' | 'to_advisors'
  const targetIsAdvisor = direction === 'to_fighters'  // we're flipping FROM advisors

  const flippableTerritories = [...new Set(
    (myPlayer?.forces_on_board || [])
      .filter(fg => fg.is_advisor === targetIsAdvisor &&
                    (fg.regular_count + (fg.special_count || 0)) > 0)
      .map(fg => fg.territory_name)
  )].sort()

  const [territory, setTerritory] = useState(flippableTerritories[0] || '')

  const actionType = direction === 'to_fighters'
    ? 'flip_advisors_to_fighters'
    : 'flip_fighters_to_advisors'

  if (flippableTerritories.length === 0) {
    return (
      <div className="mt-2 pt-2 border-t border-[#3a3020]">
        <p className="text-gray-500 text-[10px] px-1">
          No {direction === 'to_fighters' ? 'advisors' : 'fighters'} to flip.
        </p>
        <Button onClick={onCancel} className="text-xs py-1 mt-1 w-full opacity-60">Cancel</Button>
      </div>
    )
  }

  return (
    <div className="space-y-1.5 mt-2 pt-2 border-t border-[#3a3020]">
      <p className="text-gray-400 text-[10px] px-1">
        Flip {direction === 'to_fighters' ? 'Advisors → Fighters' : 'Fighters → Advisors'} in:
      </p>
      <select
        value={territory}
        onChange={e => setTerritory(e.target.value)}
        className={selectClass}
      >
        {flippableTerritories.map(n => <option key={n} value={n}>{n}</option>)}
      </select>
      <div className="flex gap-2">
        <Button
          onClick={() => onAction(actionType, { territory_name: territory })}
          disabled={!territory}
          className="flex-1 text-xs py-1"
        >
          Flip
        </Button>
        <Button onClick={onCancel} className="text-xs py-1 opacity-60">Cancel</Button>
      </div>
    </div>
  )
}

function BgPanel({ myPlayer, territories, gameState, onAction, actionBusy }) {
  const isAdvanced = gameState?.mode === 'advanced'
  const [activeForm, setActiveForm] = useState(null)

  const hasAdvisors = (myPlayer?.forces_on_board || []).some(
    fg => fg.is_advisor && (fg.regular_count + (fg.special_count || 0)) > 0
  )
  const hasFighters = (myPlayer?.forces_on_board || []).some(
    fg => !fg.is_advisor && (fg.regular_count + (fg.special_count || 0)) > 0
  )

  // Only show this panel in Advanced mode when there are forces to flip
  if (!isAdvanced || (!hasAdvisors && !hasFighters)) return null

  function cancel() { setActiveForm(null) }
  function submit(type, payload) { onAction(type, payload); setActiveForm(null) }

  return (
    <div className="bg-surface border border-purple-900/50 rounded p-2">
      <p className="text-purple-400 text-[10px] font-bold uppercase tracking-wider px-1 mb-1.5">
        BG Abilities
      </p>

      {!activeForm && (
        <div className="space-y-1">
          {/* Flip advisors → fighters (Advanced) */}
          {hasAdvisors && (
            <button
              onClick={() => setActiveForm('to_fighters')}
              disabled={actionBusy}
              className="w-full text-left px-2 py-1.5 rounded border border-purple-800/40 bg-purple-950/30 hover:bg-purple-900/40 disabled:opacity-40 text-xs"
            >
              <span className="text-purple-300 font-medium">Flip → Fighters</span>
              <span className="text-gray-500 text-[9px] ml-2">advisors become combatants</span>
            </button>
          )}

          {/* Flip fighters → advisors (Advanced) */}
          {hasFighters && (
            <button
              onClick={() => setActiveForm('to_advisors')}
              disabled={actionBusy}
              className="w-full text-left px-2 py-1.5 rounded border border-purple-800/40 bg-purple-950/30 hover:bg-purple-900/40 disabled:opacity-40 text-xs"
            >
              <span className="text-purple-300 font-medium">Flip → Advisors</span>
              <span className="text-gray-500 text-[9px] ml-2">retreat to coexistence</span>
            </button>
          )}
        </div>
      )}

      {(activeForm === 'to_fighters' || activeForm === 'to_advisors') && (
        <BgFlipForm
          myPlayer={myPlayer}
          territories={territories}
          direction={activeForm}
          onAction={submit}
          onCancel={cancel}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Spacing Guild
// ---------------------------------------------------------------------------

function GuildCrossShipForm({ myPlayer, territories, gameState, onAction, onCancel }) {
  const stormSector = gameState?.storm_sector ?? -1
  const myForces = (myPlayer?.forces_on_board || []).filter(
    fg => (fg.regular_count + (fg.special_count || 0)) > 0
  )
  const territoryNames = Object.keys(territories || {}).sort()

  const [fromKey, setFromKey] = useState('')       // "territory|sector"
  const [toTerritory, setToTerritory] = useState('')
  const [toSector, setToSector] = useState(0)
  const [regularCount, setRegularCount] = useState(1)
  const [specialCount, setSpecialCount] = useState(0)

  const [fromTerritory, fromSectorStr] = fromKey.split('|')
  const fromSector = parseInt(fromSectorStr || '0')

  const sourceForce = myForces.find(
    fg => fg.territory_name === fromTerritory && fg.sector === fromSector
  )
  const maxRegular = sourceForce?.regular_count || 0
  const maxSpecial = sourceForce?.special_count || 0
  const total = regularCount + specialCount

  const toSectors = territories?.[toTerritory]?.sectors || []
  const cost = Math.ceil(total / 2)  // half normal rate

  return (
    <div className="space-y-1.5 mt-2 pt-2 border-t border-[#3a3020]">
      <p className="text-gray-400 text-[10px] px-1">Cross-ship: board → board at ½ cost</p>

      {/* From */}
      <select
        value={fromKey}
        onChange={e => {
          setFromKey(e.target.value)
          setRegularCount(1); setSpecialCount(0)
        }}
        className={selectClass}
      >
        <option value="">From…</option>
        {myForces.map(fg => {
          const tot = (fg.regular_count || 0) + (fg.special_count || 0)
          return (
            <option key={`${fg.territory_name}|${fg.sector}`} value={`${fg.territory_name}|${fg.sector}`}>
              {fg.territory_name} s{fg.sector} ({tot})
            </option>
          )
        })}
      </select>

      {/* To */}
      <select
        value={toTerritory}
        onChange={e => {
          setToTerritory(e.target.value)
          const secs = territories?.[e.target.value]?.sectors || []
          setToSector(secs[0] ?? 0)
        }}
        className={selectClass}
        disabled={!fromKey}
      >
        <option value="">To…</option>
        {territoryNames.map(n => <option key={n} value={n}>{n}</option>)}
      </select>

      {toSectors.length > 1 && (
        <select
          value={toSector}
          onChange={e => setToSector(parseInt(e.target.value))}
          className={selectClass}
        >
          {toSectors.map(s => (
            <option key={s} value={s}>
              Sector {s}{s === stormSector ? ' ⚡' : ''}
            </option>
          ))}
        </select>
      )}

      {/* Counts */}
      {fromKey && (
        <div className="flex gap-2">
          <div className="flex items-center gap-1">
            <span className="text-gray-400 text-[9px]">Reg</span>
            <input
              type="number" min={0} max={maxRegular} value={regularCount}
              onChange={e => setRegularCount(Math.max(0, Math.min(maxRegular, parseInt(e.target.value) || 0)))}
              className="w-12 bg-[#0f0e0b] border border-[#3a3020] rounded px-1 py-0.5 text-sand-light text-xs font-mono focus:border-sand outline-none"
            />
            <span className="text-gray-600 text-[9px]">/{maxRegular}</span>
          </div>
          {maxSpecial > 0 && (
            <div className="flex items-center gap-1">
              <span className="text-gray-400 text-[9px]">Spc</span>
              <input
                type="number" min={0} max={maxSpecial} value={specialCount}
                onChange={e => setSpecialCount(Math.max(0, Math.min(maxSpecial, parseInt(e.target.value) || 0)))}
                className="w-12 bg-[#0f0e0b] border border-[#3a3020] rounded px-1 py-0.5 text-sand-light text-xs font-mono focus:border-sand outline-none"
              />
              <span className="text-gray-600 text-[9px]">/{maxSpecial}</span>
            </div>
          )}
          <span className="text-spice text-[10px] ml-auto">◆{cost}</span>
        </div>
      )}

      <div className="flex gap-2">
        <Button
          onClick={() => onAction('guild_cross_ship', {
            from_territory: fromTerritory,
            from_sector: fromSector,
            to_territory: toTerritory,
            to_sector: toSector,
            regular_count: regularCount,
            special_count: specialCount,
          })}
          disabled={!fromKey || !toTerritory || total === 0 || cost > (myPlayer?.spice || 0)}
          className="flex-1 text-xs py-1"
        >
          Cross-Ship {total > 0 ? `${total} (◆${cost})` : ''}
        </Button>
        <Button onClick={onCancel} className="text-xs py-1 opacity-60">Cancel</Button>
      </div>
    </div>
  )
}

function GuildReservesForm({ myPlayer, territories, onAction, onCancel }) {
  const myForces = (myPlayer?.forces_on_board || []).filter(
    fg => (fg.regular_count + (fg.special_count || 0)) > 0
  )

  const [fromKey, setFromKey] = useState('')
  const [regularCount, setRegularCount] = useState(1)
  const [specialCount, setSpecialCount] = useState(0)

  const [fromTerritory, fromSectorStr] = fromKey.split('|')
  const fromSector = parseInt(fromSectorStr || '0')

  const sourceForce = myForces.find(
    fg => fg.territory_name === fromTerritory && fg.sector === fromSector
  )
  const maxRegular = sourceForce?.regular_count || 0
  const maxSpecial = sourceForce?.special_count || 0
  const total = regularCount + specialCount
  const cost = Math.ceil(total / 2)

  return (
    <div className="space-y-1.5 mt-2 pt-2 border-t border-[#3a3020]">
      <p className="text-gray-400 text-[10px] px-1">Ship to reserves: ◆1 per 2 forces (rounded up)</p>

      <select
        value={fromKey}
        onChange={e => {
          setFromKey(e.target.value)
          setRegularCount(1); setSpecialCount(0)
        }}
        className={selectClass}
      >
        <option value="">From…</option>
        {myForces.map(fg => {
          const tot = (fg.regular_count || 0) + (fg.special_count || 0)
          return (
            <option key={`${fg.territory_name}|${fg.sector}`} value={`${fg.territory_name}|${fg.sector}`}>
              {fg.territory_name} s{fg.sector} ({tot})
            </option>
          )
        })}
      </select>

      {fromKey && (
        <div className="flex gap-2 items-center">
          <div className="flex items-center gap-1">
            <span className="text-gray-400 text-[9px]">Reg</span>
            <input
              type="number" min={0} max={maxRegular} value={regularCount}
              onChange={e => setRegularCount(Math.max(0, Math.min(maxRegular, parseInt(e.target.value) || 0)))}
              className="w-12 bg-[#0f0e0b] border border-[#3a3020] rounded px-1 py-0.5 text-sand-light text-xs font-mono focus:border-sand outline-none"
            />
          </div>
          {maxSpecial > 0 && (
            <div className="flex items-center gap-1">
              <span className="text-gray-400 text-[9px]">Spc</span>
              <input
                type="number" min={0} max={maxSpecial} value={specialCount}
                onChange={e => setSpecialCount(Math.max(0, Math.min(maxSpecial, parseInt(e.target.value) || 0)))}
                className="w-12 bg-[#0f0e0b] border border-[#3a3020] rounded px-1 py-0.5 text-sand-light text-xs font-mono focus:border-sand outline-none"
              />
            </div>
          )}
          <span className="text-spice text-[10px] ml-auto">◆{cost}</span>
        </div>
      )}

      <div className="flex gap-2">
        <Button
          onClick={() => onAction('guild_ship_to_reserves', {
            from_territory: fromTerritory,
            from_sector: fromSector,
            regular_count: regularCount,
            special_count: specialCount,
          })}
          disabled={!fromKey || total === 0 || cost > (myPlayer?.spice || 0)}
          className="flex-1 text-xs py-1"
        >
          Withdraw {total > 0 ? `${total} (◆${cost})` : ''}
        </Button>
        <Button onClick={onCancel} className="text-xs py-1 opacity-60">Cancel</Button>
      </div>
    </div>
  )
}

function GuildPanel({ myPlayer, territories, gameState, onAction, actionBusy }) {
  const [activeForm, setActiveForm] = useState(null)

  const hasForces = (myPlayer?.forces_on_board || []).some(
    fg => (fg.regular_count + (fg.special_count || 0)) > 0
  )

  function cancel() { setActiveForm(null) }
  function submit(type, payload) { onAction(type, payload); setActiveForm(null) }

  return (
    <div className="bg-surface border border-yellow-900/50 rounded p-2">
      <p className="text-yellow-400 text-[10px] font-bold uppercase tracking-wider px-1 mb-1.5">
        Guild Abilities
      </p>

      {!activeForm && (
        <div className="space-y-1">
          <button
            onClick={() => setActiveForm('cross_ship')}
            disabled={actionBusy || !hasForces}
            className="w-full text-left px-2 py-1.5 rounded border border-yellow-800/40 bg-yellow-950/30 hover:bg-yellow-900/40 disabled:opacity-40 text-xs"
          >
            <span className="text-yellow-300 font-medium">Cross-Ship</span>
            <span className="text-gray-500 text-[9px] ml-2">board → board, ½ cost</span>
          </button>
          <button
            onClick={() => setActiveForm('reserves')}
            disabled={actionBusy || !hasForces}
            className="w-full text-left px-2 py-1.5 rounded border border-yellow-800/40 bg-yellow-950/30 hover:bg-yellow-900/40 disabled:opacity-40 text-xs"
          >
            <span className="text-yellow-300 font-medium">Ship to Reserves</span>
            <span className="text-gray-500 text-[9px] ml-2">◆1 per 2 forces</span>
          </button>
        </div>
      )}

      {activeForm === 'cross_ship' && (
        <GuildCrossShipForm
          myPlayer={myPlayer}
          territories={territories}
          gameState={gameState}
          onAction={submit}
          onCancel={cancel}
        />
      )}
      {activeForm === 'reserves' && (
        <GuildReservesForm
          myPlayer={myPlayer}
          territories={territories}
          onAction={submit}
          onCancel={cancel}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------

export default function FactionShipmentPanel({
  myPlayer,
  territories,
  gameState,
  onAction,
  actionBusy = false,
}) {
  if (!myPlayer) return null
  const faction = myPlayer.faction

  if (faction === 'bene_gesserit') {
    return (
      <BgPanel
        myPlayer={myPlayer}
        territories={territories}
        gameState={gameState}
        onAction={onAction}
        actionBusy={actionBusy}
      />
    )
  }

  if (faction === 'spacing_guild') {
    return (
      <GuildPanel
        myPlayer={myPlayer}
        territories={territories}
        gameState={gameState}
        onAction={onAction}
        actionBusy={actionBusy}
      />
    )
  }

  return null
}
