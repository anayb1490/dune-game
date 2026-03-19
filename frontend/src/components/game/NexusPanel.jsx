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

  return (
    <div className="bg-surface border border-yellow-800/60 rounded p-3 space-y-3">
      <h3 className="text-yellow-400 text-[11px] font-bold uppercase tracking-widest">
        ☽ Nexus — Alliances
      </h3>

      {/* Current alliance status */}
      {hasAlly && (
        <div className="bg-yellow-900/20 border border-yellow-700/40 rounded px-2 py-1.5">
          <p className="text-[10px] text-gray-400">Allied with</p>
          <p className={`text-sm font-bold ${FACTION_COLORS[myPlayer.ally] ?? 'text-gray-200'}`}>
            {FACTION_LABELS[myPlayer.ally] ?? myPlayer.ally}
          </p>
        </div>
      )}

      {/* Pending incoming proposals — any player can accept */}
      {pendingProposalFrom.length > 0 && (
        <div className="space-y-1">
          <p className="text-[10px] text-gray-400 uppercase tracking-wider">Proposals received</p>
          {pendingProposalFrom.map(proposer => (
            <div key={proposer} className="flex items-center justify-between gap-2">
              <span className={`text-xs font-semibold ${FACTION_COLORS[proposer] ?? 'text-gray-300'}`}>
                {FACTION_LABELS[proposer] ?? proposer}
              </span>
              {!hasAlly && (
                <Button
                  onClick={() => onAcceptAlliance(proposer)}
                  disabled={actionBusy}
                  className="text-[10px] px-2 py-0.5 bg-yellow-700 hover:bg-yellow-600"
                >
                  Accept
                </Button>
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
    </div>
  )
}
