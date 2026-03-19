/**
 * GameView — board-centric layout.
 *
 * Layout:
 *   [Left 180px: PhaseTracker + Players]
 *   [Center: Board (fills viewport)]
 *   [Right 200px: Stats + Leaders + Phase panels]
 */
import { useState, useEffect } from 'react'
import PhaseTracker from './PhaseTracker.jsx'
import PlayerPanel from './PlayerPanel.jsx'
import BiddingPanel from './BiddingPanel.jsx'
import LeadersPanel from './LeadersPanel.jsx'
import NexusPanel from './NexusPanel.jsx'
import RevivalPanel from './RevivalPanel.jsx'
import ShipmentPanel from './ShipmentPanel.jsx'
import BattlePanel from './BattlePanel.jsx'
import GameLog from './GameLog.jsx'
import TreacheryHandPanel from './TreacheryHandPanel.jsx'
import GameBoard from '../board/GameBoard.jsx'
import Button from '../ui/Button.jsx'
import { getAdjacentTerritories } from '../../utils/adjacency.js'

const PHASE_LABELS = {
  storm:                  'Storm Phase',
  spice_blow:             'Spice Blow',
  nexus:                  'Nexus',
  choam_charity:          'CHOAM Charity',
  bidding:                'Bidding Phase',
  revival:                'Revival Phase',
  shipment_and_movement:  'Shipment & Movement',
  battle:                 'Battle Phase',
  spice_collection:       'Spice Collection',
  mentat_pause:           'Mentat Pause',
}

const FACTION_LABELS = {
  atreides: 'Atreides', harkonnen: 'Harkonnen', bene_gesserit: 'Bene Gesserit',
  fremen: 'Fremen', spacing_guild: 'Guild', emperor: 'Emperor',
}

// Phases resolved server-side — host advances
const AUTOMATED_PHASES = new Set([
  'storm', 'spice_blow', 'choam_charity', 'spice_collection', 'mentat_pause',
])

// Phases where players take turns one at a time
const TURN_BASED_PHASES = new Set(['revival', 'shipment_and_movement', 'nexus'])

export default function GameView({
  gameState, playerId, actionBusy = false,
  onAdvancePhase, onPlaceBid, onPassBid,
  onReviveForces, onReviveLeader,
  onShipForces, onMoveForces,
  onSubmitBattlePlan,
  onProposeAlliance, onAcceptAlliance, onBreakAlliance, onPassNexus,
}) {
  const {
    current_phase,
    current_turn,
    current_player_index,
    storm_sector,
    spice_bank,
    players,
    territories,
    bidding_state,
    active_battle,
    winner,
    is_game_over,
    phase_messages,
  } = gameState

  const [boardHighlight, setBoardHighlight] = useState({ from: '', to: '' })

  // Clear board highlight when leaving shipment phase
  useEffect(() => {
    if (current_phase !== 'shipment_and_movement') {
      setBoardHighlight({ from: '', to: '' })
    }
  }, [current_phase])

  const myPlayer = players?.find(p => p.id === playerId)
  const currentTurnPlayer = players?.[current_player_index ?? 0]
  const isMyTurn = currentTurnPlayer?.id === playerId
  // Host is lobby creator, or first player as fallback for legacy games
  const hostPlayerId = gameState.lobby_state?.host_player_id ?? players?.[0]?.id
  const isHost = hostPlayerId === playerId

  const isBidding = current_phase === 'bidding' && bidding_state != null
  const isNexus = current_phase === 'nexus'
  const isRevival = current_phase === 'revival'
  const isShipment = current_phase === 'shipment_and_movement'
  const isBattle = current_phase === 'battle' && active_battle != null
  const isAutomated = AUTOMATED_PHASES.has(current_phase)
  const isTurnBased = TURN_BASED_PHASES.has(current_phase)
  const isLastPlayer = (current_player_index ?? 0) >= (players?.length ?? 1) - 1
  const hasMessages = phase_messages && phase_messages.length > 0

  // Show advance button when there's no active sub-panel that handles its own flow
  // Nexus manages its own flow — hide the generic advance button
  const showAdvanceButton = !isBidding && !isBattle && !isNexus

  // Button label logic:
  // - Automated phases: "Resolve Phase" (first click) or "Advance Phase" (after resolved)
  // - Turn-based: "End Turn" (more players) or "End Phase" (last player)
  const buttonLabel = is_game_over
    ? 'Game Over'
    : isAutomated
      ? hasMessages ? 'Advance Phase' : 'Resolve Phase'
      : isTurnBased
        ? isLastPlayer ? 'End Phase' : 'End Turn'
        : 'Advance Phase'

  // Automated phases: only host can advance
  // Interactive phases: only the current player can advance
  const canClickAdvance = isAutomated ? isHost : isMyTurn

  return (
    <main className="grid grid-cols-[180px_1fr_200px] gap-2 p-2 h-[calc(100vh-53px)] overflow-hidden">

      {/* -- Left column ------------------------------------------------- */}
      <aside className="space-y-2 overflow-y-auto min-h-0">
        <PhaseTracker currentPhase={current_phase} />
        <PlayerPanel players={players} currentPlayerIndex={current_player_index} />
      </aside>

      {/* -- Center: Board ----------------------------------------------- */}
      <section className="flex flex-col min-h-0">
        {/* Game over banner */}
        {is_game_over && (
          <div className="bg-sand/20 border border-sand rounded px-3 py-2 text-center mb-2 shrink-0">
            <p className="text-sand font-bold uppercase tracking-widest">
              {winner ? `${winner.replace('_', ' ')} wins!` : 'Game Over'}
            </p>
          </div>
        )}

        {/* Board fills remaining space */}
        <div className="flex-1 min-h-0">
          <GameBoard
            territories={territories}
            players={players}
            stormSector={storm_sector}
            highlightFrom={boardHighlight.from}
            highlightTo={boardHighlight.to}
            adjacentTo={boardHighlight.from ? getAdjacentTerritories(boardHighlight.from, territories) : []}
          />
        </div>
      </section>

      {/* -- Right column ------------------------------------------------ */}
      <aside className="space-y-2 overflow-y-auto min-h-0">

        {/* Compact stats row */}
        <div className="bg-surface border border-[#3a3020] rounded p-3">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-gray-500 text-[10px] uppercase">Turn</p>
              <p className="text-gray-200 font-mono font-bold">{current_turn}<span className="text-gray-600 text-xs">/10</span></p>
            </div>
            <div>
              <p className="text-gray-500 text-[10px] uppercase">Storm</p>
              <p className="text-sand-light font-mono font-bold">{storm_sector}</p>
            </div>
            <div>
              <p className="text-gray-500 text-[10px] uppercase">Bank</p>
              <p className="text-spice font-mono font-bold">◆{spice_bank}</p>
            </div>
          </div>
        </div>

        {/* Phase + turn indicator + action button */}
        <div className="bg-surface border border-[#3a3020] rounded p-3">
          <p className="text-gray-500 text-[10px] uppercase tracking-wider">Phase</p>
          <p className="text-sand-light text-sm font-bold">{PHASE_LABELS[current_phase] ?? current_phase}</p>

          {/* Turn indicator for turn-based phases */}
          {isTurnBased && currentTurnPlayer && (
            <p className={`text-[10px] mt-1 mb-2 ${isMyTurn ? 'text-green-400' : 'text-gray-500'}`}>
              {isMyTurn
                ? "Your turn"
                : `${currentTurnPlayer.name}'s turn (${FACTION_LABELS[currentTurnPlayer.faction] ?? currentTurnPlayer.faction})`
              }
            </p>
          )}

          {/* Host indicator for automated phases */}
          {isAutomated && (
            <p className={`text-[10px] mt-1 mb-2 ${isHost ? 'text-green-400' : 'text-gray-500'}`}>
              {isHost ? 'You advance this phase' : 'Waiting for host to advance...'}
            </p>
          )}

          {!isTurnBased && !isAutomated && <div className="mb-2" />}

          {showAdvanceButton && (
            canClickAdvance ? (
              <Button
                onClick={onAdvancePhase}
                disabled={is_game_over || actionBusy}
                className="w-full text-xs"
              >
                {actionBusy ? 'Processing...' : buttonLabel}
              </Button>
            ) : (
              <p className="text-gray-500 text-[10px] text-center">
                {isAutomated
                  ? 'Waiting for host...'
                  : `Waiting for ${currentTurnPlayer?.name}...`
                }
              </p>
            )
          )}
        </div>

        {/* Persistent event log — accumulates all phase events */}
        <GameLog entries={gameState.game_log || []} />

        {/* Bidding panel */}
        {isBidding && (
          <BiddingPanel
            biddingState={bidding_state}
            players={players}
            playerId={playerId}
            onPlaceBid={onPlaceBid}
            onPassBid={onPassBid}
          />
        )}

        {/* Revival panel — only show when it's your turn */}
        {isRevival && isMyTurn && (
          <RevivalPanel
            myPlayer={myPlayer}
            onReviveForces={onReviveForces}
            onReviveLeader={onReviveLeader}
          />
        )}

        {/* Shipment & Movement panel — only show when it's your turn */}
        {isShipment && isMyTurn && (
          <ShipmentPanel
            myPlayer={myPlayer}
            territories={territories}
            gameState={gameState}
            onShipForces={onShipForces}
            onMoveForces={onMoveForces}
            onHighlight={(from, to) => setBoardHighlight({ from: from || '', to: to || '' })}
          />
        )}

        {/* Battle panel */}
        {isBattle && (
          <BattlePanel
            activeBattle={active_battle}
            myPlayer={myPlayer}
            onSubmitPlan={onSubmitBattlePlan}
          />
        )}

        {/* Nexus panel — shown during Nexus phase */}
        {isNexus && (
          <NexusPanel
            gameState={gameState}
            myPlayer={myPlayer}
            actionBusy={actionBusy}
            onProposeAlliance={onProposeAlliance}
            onAcceptAlliance={onAcceptAlliance}
            onBreakAlliance={onBreakAlliance}
            onPassNexus={onPassNexus}
          />
        )}

        {/* Treachery hand — always visible to the player */}
        {myPlayer && (
          <TreacheryHandPanel
            hand={myPlayer.treachery_hand || []}
            maxCards={myPlayer.faction === 'harkonnen' ? 8 : 4}
          />
        )}

        {/* Leaders & Traitor */}
        {myPlayer && (
          <LeadersPanel
            leaders={myPlayer.leaders}
            traitorCards={myPlayer.traitor_cards}
            myFaction={myPlayer.faction}
          />
        )}
      </aside>
    </main>
  )
}
