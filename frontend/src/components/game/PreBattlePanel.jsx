/**
 * PreBattlePanel — handles pre-battle faction abilities before plans are submitted.
 *
 * Two abilities must resolve before battle plans are submitted:
 *   1. BG Voice     — command opponent to play/not play a card type
 *   2. Atreides Prescience — ask opponent to reveal one plan element
 *
 * Each battle participant (attacker + defender) must either use their ability
 * or explicitly pass. Once both sides are done, plan submission unlocks.
 *
 * Shown whenever:  active_battle != null && !active_battle.prebattle_complete
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
  { value: 'snooper',           label: 'Snooper' },
  { value: 'shield',            label: 'Shield' },
  { value: 'worthless',         label: 'Worthless Card' },
  { value: 'cheap_hero',        label: 'Cheap Hero/Heroine' },
]

const PRESCIENCE_ELEMENTS = [
  { value: 'leader',  label: 'Leader' },
  { value: 'weapon',  label: 'Weapon card' },
  { value: 'defense', label: 'Defense card' },
  { value: 'number',  label: 'Number of forces' },
]

export default function PreBattlePanel({
  activeBattle,
  myPlayer,
  players,
  gameState,
  onIssueVoice,
  onAcknowledgeVoice,
  onAskPrescience,
  onRevealPrescience,
  onDonePrebattle,
  actionBusy = false,
}) {
  const [voiceCommand, setVoiceCommand] = useState('not_play')
  const [voiceCardType, setVoiceCardType] = useState('poison_weapon')
  const [prescienceElement, setPrescienceElement] = useState('leader')
  const [revealValue, setRevealValue] = useState('')

  if (!activeBattle || activeBattle.prebattle_complete) return null

  const myFaction = myPlayer?.faction
  const isAdvanced = gameState?.mode === 'advanced'
  const isAttacker = myFaction === activeBattle.attacker_faction
  const isDefender = myFaction === activeBattle.defender_faction
  const isParticipant = isAttacker || isDefender

  if (!isParticipant) return null

  const myDone = isAttacker
    ? activeBattle.attacker_prebattle_done
    : activeBattle.defender_prebattle_done

  // Determine the opponent faction in this battle
  const opponentFaction = isAttacker ? activeBattle.defender_faction : activeBattle.attacker_faction

  // BG (or BG ally in Advanced) can issue Voice
  const bgPlayer = players?.find(p => p.faction === 'bene_gesserit')
  const isBG = myFaction === 'bene_gesserit'
  const isBGAllyInAdvanced = isAdvanced && bgPlayer?.ally === myFaction
  const canIssueVoice = (isBG || isBGAllyInAdvanced)

  // Atreides (or Atreides ally in Advanced) can use prescience
  const atreidesPlayer = players?.find(p => p.faction === 'atreides')
  const isAtreides = myFaction === 'atreides'
  const isAtreidesAlly = isAdvanced && atreidesPlayer?.ally === myFaction
  const canUsePrescience = (isAtreides || isAtreidesAlly)
    && (myFaction === activeBattle.attacker_faction || myFaction === activeBattle.defender_faction)

  // Voice state
  const voiceIssued = activeBattle.voice_command != null
  const voiceAcknowledged = activeBattle.voice_acknowledged === true
  const isVoiceTarget = myFaction === activeBattle.voice_target_faction

  // Prescience state
  const prescienceAsked = activeBattle.prescience_element_asked != null
  const prescienceRevealed = activeBattle.prescience_revealed_value != null
  const atreidesFaction = activeBattle.atreides_faction
  const isPrescienceTarget = atreidesFaction != null
    && myFaction !== atreidesFaction
    && (myFaction === activeBattle.attacker_faction || myFaction === activeBattle.defender_faction)

  // If already done, show waiting state
  if (myDone) {
    return (
      <div className="bg-surface border border-yellow-900/50 rounded p-2">
        <p className="text-yellow-400 text-[10px] uppercase tracking-wider px-1 mb-1">Pre-Battle</p>
        <p className="text-gray-500 text-[10px] text-center py-1">
          Pre-battle actions submitted. Waiting for opponent...
        </p>
        {/* Show Voice/Prescience info to this player */}
        {voiceIssued && isVoiceTarget && voiceAcknowledged && (
          <div className="mt-1 border border-yellow-800/40 rounded p-1.5 text-[10px]">
            <p className="text-yellow-400 font-bold">Voice Command Received:</p>
            <p className="text-gray-300 mt-0.5">
              {activeBattle.voice_command?.command === 'play' ? 'You MUST play' : 'You must NOT play'} a{' '}
              <span className="text-yellow-200 font-bold">
                {VOICE_CARD_TYPES.find(t => t.value === activeBattle.voice_command?.card_type)?.label ?? activeBattle.voice_command?.card_type}
              </span>
              {' '}(if able)
            </p>
          </div>
        )}
        {prescienceRevealed && (canUsePrescience || isAtreides) && (
          <div className="mt-1 border border-blue-800/40 rounded p-1.5 text-[10px]">
            <p className="text-blue-400 font-bold">Prescience Revealed:</p>
            <p className="text-gray-300 mt-0.5">
              <span className="text-blue-200 capitalize">{activeBattle.prescience_element_asked}</span>:{' '}
              <span className="text-sand font-bold">{activeBattle.prescience_revealed_value}</span>
            </p>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="bg-surface border border-yellow-900/50 rounded p-2 space-y-2">
      <div className="flex items-center justify-between px-1">
        <p className="text-yellow-400 text-[10px] uppercase tracking-wider">Pre-Battle Phase</p>
        <p className="text-gray-600 text-[9px]">Before plans are submitted</p>
      </div>

      {/* ── VOICE TARGET: acknowledge command ── */}
      {isVoiceTarget && voiceIssued && !voiceAcknowledged && (
        <div className="border border-yellow-700/60 bg-yellow-900/10 rounded p-2 space-y-1">
          <p className="text-yellow-400 text-xs font-bold">⚡ Voice Command!</p>
          <p className="text-gray-300 text-[10px]">
            {FACTION_LABELS[bgPlayer?.faction ?? 'bene_gesserit']} commands you to{' '}
            <span className="text-yellow-200 font-bold">
              {activeBattle.voice_command?.command === 'play' ? 'PLAY' : 'NOT PLAY'}
            </span>{' '}
            a{' '}
            <span className="text-yellow-200 font-bold">
              {VOICE_CARD_TYPES.find(t => t.value === activeBattle.voice_command?.card_type)?.label ?? activeBattle.voice_command?.card_type}
            </span>
            {' '}(if able).
          </p>
          <Button onClick={onAcknowledgeVoice} disabled={actionBusy} className="w-full text-xs py-1">
            Acknowledge
          </Button>
        </div>
      )}

      {/* ── PRESCIENCE TARGET: reveal element ── */}
      {isPrescienceTarget && prescienceAsked && !prescienceRevealed && (
        <div className="border border-blue-700/60 bg-blue-900/10 rounded p-2 space-y-2">
          <p className="text-blue-400 text-xs font-bold">🔮 Atreides Prescience</p>
          <p className="text-gray-300 text-[10px]">
            {FACTION_LABELS[atreidesFaction]} asks you to reveal your{' '}
            <span className="text-blue-200 font-bold capitalize">{activeBattle.prescience_element_asked}</span>.
          </p>
          <input
            value={revealValue}
            onChange={e => setRevealValue(e.target.value)}
            placeholder={
              activeBattle.prescience_element_asked === 'leader' ? 'Leader name or "none"' :
              activeBattle.prescience_element_asked === 'number' ? 'Number of forces' :
              'Card name or "none"'
            }
            className="w-full bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs focus:border-sand outline-none"
          />
          <Button
            onClick={() => onRevealPrescience(revealValue)}
            disabled={actionBusy || !revealValue.trim()}
            className="w-full text-xs py-1"
          >
            Reveal
          </Button>
        </div>
      )}

      {/* ── BG: issue Voice ── */}
      {canIssueVoice && !voiceIssued && !myDone && (
        <div className="border border-purple-800/50 rounded p-2 space-y-2">
          <p className="text-purple-400 text-xs font-bold">Issue Voice</p>
          <div className="flex gap-2">
            <div className="flex-1">
              <p className="text-gray-500 text-[9px] mb-1">Command</p>
              <select
                value={voiceCommand}
                onChange={e => setVoiceCommand(e.target.value)}
                className="w-full bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-[10px] focus:border-sand outline-none"
              >
                <option value="play">Must PLAY</option>
                <option value="not_play">Must NOT PLAY</option>
              </select>
            </div>
            <div className="flex-1">
              <p className="text-gray-500 text-[9px] mb-1">Card type</p>
              <select
                value={voiceCardType}
                onChange={e => setVoiceCardType(e.target.value)}
                className="w-full bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-[10px] focus:border-sand outline-none"
              >
                {VOICE_CARD_TYPES.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => onIssueVoice(opponentFaction, voiceCommand, voiceCardType)}
              disabled={actionBusy}
              className="flex-1 text-xs py-1"
            >
              Issue Voice
            </Button>
            <Button onClick={onDonePrebattle} disabled={actionBusy} className="text-xs py-1 opacity-60">
              Pass
            </Button>
          </div>
        </div>
      )}

      {/* Show voice acknowledged status */}
      {canIssueVoice && voiceIssued && (
        <div className="text-[10px] text-gray-500 text-center">
          Voice issued to {FACTION_LABELS[activeBattle.voice_target_faction] ?? activeBattle.voice_target_faction}.{' '}
          {voiceAcknowledged ? '✓ Acknowledged' : 'Awaiting acknowledgement...'}
        </div>
      )}

      {/* ── ATREIDES: ask prescience ── */}
      {canUsePrescience && !prescienceAsked && !myDone && !(canIssueVoice && !voiceIssued) && (
        <div className="border border-blue-800/50 rounded p-2 space-y-2">
          <p className="text-blue-400 text-xs font-bold">Battle Prescience</p>
          <p className="text-gray-500 text-[9px]">Ask opponent to reveal one element of their battle plan</p>
          <select
            value={prescienceElement}
            onChange={e => setPrescienceElement(e.target.value)}
            className="w-full bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs focus:border-sand outline-none"
          >
            {PRESCIENCE_ELEMENTS.map(el => (
              <option key={el.value} value={el.value}>{el.label}</option>
            ))}
          </select>
          <div className="flex gap-2">
            <Button
              onClick={() => onAskPrescience(prescienceElement)}
              disabled={actionBusy}
              className="flex-1 text-xs py-1"
            >
              Ask
            </Button>
            <Button onClick={onDonePrebattle} disabled={actionBusy} className="text-xs py-1 opacity-60">
              Pass
            </Button>
          </div>
        </div>
      )}

      {/* Show prescience result when available */}
      {canUsePrescience && prescienceRevealed && (
        <div className="border border-blue-800/40 bg-blue-900/10 rounded p-2 text-[10px]">
          <p className="text-blue-400 font-bold">Prescience Revealed:</p>
          <p className="text-gray-300 mt-0.5">
            <span className="text-blue-200 capitalize">{activeBattle.prescience_element_asked}</span>:{' '}
            <span className="text-sand font-bold">{activeBattle.prescience_revealed_value}</span>
          </p>
        </div>
      )}

      {/* ── DEFAULT: pass button (non-BG, non-Atreides, or after abilities used) ── */}
      {!myDone && !isVoiceTarget && !isPrescienceTarget && !canIssueVoice && !canUsePrescience && (
        <div className="text-center">
          <p className="text-gray-600 text-[10px] mb-1">No pre-battle abilities</p>
          <Button onClick={onDonePrebattle} disabled={actionBusy} className="w-full text-xs py-1">
            Ready for Battle
          </Button>
        </div>
      )}

      {/* Pass button when BG/Atreides has already done their thing and needs to pass the other slot */}
      {!myDone && (canIssueVoice || canUsePrescience) && voiceIssued && prescienceAsked && (
        <Button onClick={onDonePrebattle} disabled={actionBusy} className="w-full text-xs py-1 opacity-70">
          Done with Pre-Battle
        </Button>
      )}
    </div>
  )
}
