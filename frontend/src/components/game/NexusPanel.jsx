/**
 * NexusPanel — UI for the Nexus (Alliance) phase.
 *
 * During Nexus each player in turn may:
 *   • Propose an alliance to another faction
 *   • Accept a pending proposal from another faction
 *   • Break their current alliance
 *   • Pass (no action)
 *
 * Only the current-turn player can propose/pass; any player may accept or break.
 */
import Button from '../ui/Button.jsx'

const FACTION_LABELS = {
  atreides:      'Atreides',
  harkonnen:     'Harkonnen',
  bene_gesserit: 'Bene Gesserit',
  fremen:        'Fremen',
  spacing_guild: 'Guild',
  emperor:       'Emperor',
}

const FACTION_COLORS = {
  atreides:      'text-green-400',
  harkonnen:     'text-red-400',
  bene_gesserit: 'text-purple-400',
  fremen:        'text-blue-400',
  spacing_guild: 'text-yellow-400',
  emperor:       'text-orange-400',
}

// Alliance bonuses reference (sorted pair key)
const ALLIANCE_BONUSES = {
  'atreides+fremen':
    'Atreides can look at Fremen sandworm cards. Fremen can use Atreides prescience on one card per bidding round.',
  'atreides+bene_gesserit':
    'Atreides: BG Advisors don\'t block prescience. BG: use Atreides prescience on one card per bidding round.',
  'atreides+spacing_guild':
    'Atreides: see Guild shipping costs. Guild: use Atreides prescience on one card per bidding round.',
  'atreides+harkonnen':
    'Atreides: look at one Harkonnen treachery card per turn. Harkonnen: call traitor against Atreides leaders.',
  'atreides+emperor':
    'Atreides: can call traitor against Emperor leaders. Emperor: reduced Sardaukar deployment cost.',
  'bene_gesserit+fremen':
    'BG: Advisors in Fremen territories count for stronghold control. Fremen: Fedaykin fight at +1 strength.',
  'bene_gesserit+spacing_guild':
    'BG: ship forces at Guild rates. Guild: BG prediction protects Guild if prediction succeeds.',
  'bene_gesserit+emperor':
    'BG: Advisors count in Imperial Basin. Emperor: one free Sardaukar revival per turn.',
  'bene_gesserit+harkonnen':
    'BG: look at one Harkonnen card per turn. Harkonnen: one captured leader cannot be traitor-called per turn.',
  'fremen+spacing_guild':
    'Fremen: ship forces free alongside Guild shipments. Guild: Fremen don\'t contest Guild strongholds.',
  'fremen+emperor':
    'Fremen: Fedaykin fight at full strength in storm sectors. Emperor: Sardaukar can station in Sietch Tabr area.',
  'fremen+harkonnen':
    'Fremen: receive one Harkonnen treachery card per turn. Harkonnen: forces in Fremen strongholds immune to worms.',
  'emperor+spacing_guild':
    'Emperor pays half shipping cost. Guild: Emperor can ship Sardaukar off-planet for free once per turn.',
  'harkonnen+spacing_guild':
    'Harkonnen ships at half cost. Guild: Harkonnen draws one extra treachery card per turn.',
  'emperor+harkonnen':
    'Combined forces in the same territory fight as one unit. Both factions collect spice from each other\'s territories.',
}

function getAllianceBonus(a, b) {
  const key = [a, b].sort().join('+')
  return ALLIANCE_BONUSES[key] ?? 'Alliance formed — win together with 4 strongholds (instead of 3 solo).'
}

export default function NexusPanel({
  gameState,
  myPlayer,
  actionBusy,
  onProposeAlliance,
  onAcceptAlliance,
  onBreakAlliance,
  onPassNexus,
}) {
  if (!myPlayer) return null

  const { players, nexus_state, current_player_index } = gameState
  if (!nexus_state) return null

  const currentTurnPlayer = players?.[current_player_index ?? 0]
  const isMyTurn = currentTurnPlayer?.id === myPlayer.id

  // All active (non-eliminated) factions except my own
  const otherFactions = (players || [])
    .filter(p => !p.is_eliminated && p.faction !== myPlayer.faction)
    .map(p => p.faction)

  // Pending proposal TO me from another faction
  const pendingProposalFrom = Object.entries(nexus_state.proposals || {})
    .filter(([_proposer, target]) => target === myPlayer.faction)
    .map(([proposer]) => proposer)

  // My outgoing proposal
  const myOutgoingProposal = nexus_state.proposals?.[myPlayer.faction]

  const alreadyDone = (nexus_state.factions_done || []).includes(myPlayer.faction)
  const hasAlly = !!myPlayer.ally

  // Build public alliance board: pairs already formed
  const alliancePairs = []
  const seenAllies = new Set()
  for (const p of (players || [])) {
    if (p.ally && !seenAllies.has(p.faction) && !seenAllies.has(p.ally)) {
      alliancePairs.push([p.faction, p.ally])
      seenAllies.add(p.faction)
      seenAllies.add(p.ally)
    }
  }

  // All pending proposals (public)
  const allProposals = Object.entries(nexus_state.proposals || {})

  return (
    <div className="bg-surface border border-yellow-800/60 rounded p-3 space-y-3">
      <h3 className="text-yellow-400 text-[11px] font-bold uppercase tracking-widest">
        ☽ Nexus — Alliances
      </h3>

      {/* Public: Active alliances */}
      {alliancePairs.length > 0 && (
        <div className="space-y-1">
          <p className="text-[10px] text-gray-400 uppercase tracking-wider">Active alliances</p>
          {alliancePairs.map(([a, b]) => (
            <div key={`${a}-${b}`} className="flex items-center gap-1.5 bg-yellow-900/20 border border-yellow-700/30 rounded px-2 py-1">
              <span className={`text-[10px] font-bold ${FACTION_COLORS[a] ?? 'text-gray-300'}`}>
                {FACTION_LABELS[a] ?? a}
              </span>
              <span className="text-gray-600 text-[9px]">+</span>
              <span className={`text-[10px] font-bold ${FACTION_COLORS[b] ?? 'text-gray-300'}`}>
                {FACTION_LABELS[b] ?? b}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Public: Pending proposals */}
      {allProposals.length > 0 && (
        <div className="space-y-1">
          <p className="text-[10px] text-gray-400 uppercase tracking-wider">Pending proposals</p>
          {allProposals.map(([proposer, target]) => (
            <p key={proposer} className="text-[10px] text-gray-400">
              <span className={FACTION_COLORS[proposer] ?? 'text-gray-300'}>{FACTION_LABELS[proposer] ?? proposer}</span>
              {' → '}
              <span className={FACTION_COLORS[target] ?? 'text-gray-300'}>{FACTION_LABELS[target] ?? target}</span>
            </p>
          ))}
        </div>
      )}

      {/* Incoming proposals — Accept only on your own turn */}
      {pendingProposalFrom.length > 0 && (
        <div className="space-y-1">
          <p className="text-[10px] text-gray-400 uppercase tracking-wider">Proposals to you</p>
          {pendingProposalFrom.map(proposer => (
            <div key={proposer} className="flex items-center justify-between gap-2">
              <span className={`text-xs font-semibold ${FACTION_COLORS[proposer] ?? 'text-gray-300'}`}>
                {FACTION_LABELS[proposer] ?? proposer}
              </span>
              {isMyTurn && !hasAlly && (
                <Button
                  onClick={() => onAcceptAlliance(proposer)}
                  disabled={actionBusy}
                  className="text-[10px] px-2 py-0.5 bg-yellow-700 hover:bg-yellow-600"
                >
                  Accept
                </Button>
              )}
              {!isMyTurn && (
                <span className="text-[9px] text-gray-600 italic">accept on your turn</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Break alliance — available anytime during nexus if allied */}
      {hasAlly && (
        <Button
          onClick={onBreakAlliance}
          disabled={actionBusy}
          className="w-full text-[10px] bg-red-900 hover:bg-red-800 border-red-700"
        >
          Break Alliance with {FACTION_LABELS[myPlayer.ally] ?? myPlayer.ally}
        </Button>
      )}

      {/* Turn-holder controls: propose or pass */}
      {isMyTurn && !alreadyDone && (
        <div className="space-y-2 border-t border-[#3a3020] pt-2">
          <p className="text-[10px] text-gray-400 uppercase tracking-wider">Your turn</p>

          {/* Show outgoing proposal if already sent */}
          {myOutgoingProposal ? (
            <p className="text-[10px] text-gray-400 italic">
              Proposal sent to{' '}
              <span className={FACTION_COLORS[myOutgoingProposal] ?? 'text-gray-300'}>
                {FACTION_LABELS[myOutgoingProposal] ?? myOutgoingProposal}
              </span>
              . Waiting for acceptance…
            </p>
          ) : !hasAlly ? (
            /* Propose buttons — one per eligible faction */
            <div className="space-y-1">
              <p className="text-[10px] text-gray-500">Propose alliance to:</p>
              {otherFactions.map(faction => (
                <Button
                  key={faction}
                  onClick={() => onProposeAlliance(faction)}
                  disabled={actionBusy}
                  className="w-full text-[10px] py-0.5"
                >
                  <span className={FACTION_COLORS[faction] ?? 'text-gray-300'}>
                    {FACTION_LABELS[faction] ?? faction}
                  </span>
                </Button>
              ))}
            </div>
          ) : null}

          <Button
            onClick={onPassNexus}
            disabled={actionBusy}
            className="w-full text-[10px] bg-gray-800 hover:bg-gray-700 border-gray-600"
          >
            Pass
          </Button>
        </div>
      )}

      {/* Waiting indicator */}
      {!isMyTurn && currentTurnPlayer && (
        <p className="text-[10px] text-gray-500 text-center">
          Waiting for {currentTurnPlayer.name} ({FACTION_LABELS[currentTurnPlayer.faction] ?? currentTurnPlayer.faction})…
        </p>
      )}

      {alreadyDone && isMyTurn && (
        <p className="text-[10px] text-gray-500 text-center italic">
          You have finished your nexus turn.
        </p>
      )}

      {/* Alliance bonuses reference — collapsible */}
      <details className="border-t border-[#3a3020] pt-2">
        <summary className="text-[10px] text-gray-500 cursor-pointer hover:text-gray-300 uppercase tracking-wider select-none">
          Alliance Bonuses ▾
        </summary>
        <div className="mt-2 space-y-1.5">
          {hasAlly ? (
            /* Show current alliance bonus */
            <div className="bg-yellow-900/20 border border-yellow-700/30 rounded p-2">
              <p className="text-[10px] font-semibold text-yellow-400 mb-1">
                Your alliance with {FACTION_LABELS[myPlayer.ally] ?? myPlayer.ally}:
              </p>
              <p className="text-[10px] text-gray-300 leading-relaxed">
                {getAllianceBonus(myPlayer.faction, myPlayer.ally)}
              </p>
            </div>
          ) : (
            /* Show potential bonuses for each other faction */
            otherFactions.map(f => (
              <div key={f} className="rounded bg-[#1a1510] border border-[#2a2010] p-1.5">
                <p className={`text-[10px] font-semibold mb-0.5 ${FACTION_COLORS[f] ?? 'text-gray-300'}`}>
                  + {FACTION_LABELS[f] ?? f}
                </p>
                <p className="text-[9px] text-gray-500 leading-relaxed">
                  {getAllianceBonus(myPlayer.faction, f)}
                </p>
              </div>
            ))
          )}
        </div>
      </details>
    </div>
  )
}
