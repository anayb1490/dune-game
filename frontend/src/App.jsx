import { useState, useCallback, useRef } from 'react'
import {
  createLobby,
  joinLobby,
  selectFaction,
  startGame,
  getGameState,
  advancePhase,
  placeBid,
  passBid,
  selectTraitor,
  submitStormDial,
  reviveForces,
  reviveLeader,
  shipForces,
  moveForces,
  submitBattlePlan,
  submitBattlePlanAdvanced,
  declareTraitor,
  proposeAlliance,
  acceptAlliance,
  breakAlliance,
  passNexus,
  submitBgPrediction,
  submitFremenPlacement,
  submitAtreidesPrescienceAck,
  issueVoice,
  acknowledgeVoice,
  askPrescience,
  revealPrescience,
  donePrebattle,
  gameAction,
  fremenSandwormRide,
  fremenSkipSandwormRide,
} from './services/api.js'
import { useWebSocket } from './hooks/useWebSocket.js'
import GameView from './components/game/GameView.jsx'
import HomeScreen from './components/lobby/HomeScreen.jsx'
import LobbyView from './components/lobby/LobbyView.jsx'
import TraitorSelectionView from './components/setup/TraitorSelectionView.jsx'
import StormDialView from './components/setup/StormDialView.jsx'
import BgPredictionView from './components/setup/BgPredictionView.jsx'
import FremenPlacementView from './components/setup/FremenPlacementView.jsx'
import AtreidesPrescienceView from './components/setup/AtreidesPrescienceView.jsx'
import RulesChat from './components/game/RulesChat.jsx'

// Generate a stable player ID for this browser tab
function generatePlayerId() {
  return 'p_' + Math.random().toString(36).slice(2, 10)
}

export default function App() {
  const [playerId] = useState(generatePlayerId)
  const [playerName, setPlayerName] = useState('')
  const [gameId, setGameId] = useState(null)
  const [gameState, setGameState] = useState(null)
  const [error, setError] = useState(null)

  // Prevent double-clicks: tracks whether an action is currently in flight.
  // Uses a ref so it doesn't trigger re-renders, and a state for UI disabling.
  const actionInFlightRef = useRef(false)
  const [actionBusy, setActionBusy] = useState(false)

  // WebSocket updates
  useWebSocket(gameId, playerId, setGameState)

  // Determine which screen to show based on game phase
  function getScreen() {
    if (!gameId || !gameState) return 'home'

    const phase = gameState.current_phase
    if (phase === 'lobby') return 'lobby'
    if (phase === 'setup') {
      const sub = gameState.setup_state?.sub_phase
      if (sub === 'traitor_selection') return 'traitor_selection'
      if (sub === 'storm_dial') return 'storm_dial'
      if (sub === 'bg_prediction') return 'bg_prediction'
      if (sub === 'fremen_placement') return 'fremen_placement'
      if (sub === 'atreides_prescience') return 'atreides_prescience'
      return 'setup'
    }
    return 'game'
  }

  // ----- Home screen handlers -----

  async function handleCreateGame(name, mode) {
    try {
      setError(null)
      setPlayerName(name)
      const { game_id, join_code } = await createLobby(playerId, name, mode)
      setGameId(game_id)
      const state = await getGameState(game_id, playerId)
      setGameState(state)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleJoinGame(name, joinCode) {
    try {
      setError(null)
      setPlayerName(name)
      const { game_id } = await joinLobby(playerId, name, joinCode)
      setGameId(game_id)
      const state = await getGameState(game_id, playerId)
      setGameState(state)
    } catch (err) {
      setError(err.message)
    }
  }

  // ----- Lobby handlers -----

  async function handleSelectFaction(faction) {
    try {
      setError(null)
      await selectFaction(gameId, playerId, faction)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleStartGame() {
    try {
      setError(null)
      await startGame(gameId, playerId)
    } catch (err) {
      setError(err.message)
    }
  }

  // ----- Setup handlers -----

  async function handleSelectTraitor(traitorCardId) {
    try {
      setError(null)
      await selectTraitor(gameId, playerId, traitorCardId)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleSubmitStormDial(number) {
    try {
      setError(null)
      await submitStormDial(gameId, playerId, number)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleBgPrediction(predictedFaction, predictedTurn) {
    try {
      setError(null)
      await submitBgPrediction(gameId, playerId, predictedFaction, predictedTurn)
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  async function handleFremenPlacement(placements) {
    try {
      setError(null)
      await submitFremenPlacement(gameId, playerId, placements)
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  async function handleAtreidesPrescienceAck() {
    try {
      setError(null)
      await submitAtreidesPrescienceAck(gameId, playerId)
    } catch (err) {
      setError(err.message)
    }
  }

  // ----- Action guard (prevents double-clicks) -----

  /**
   * Wraps an async action so that only ONE action can be in flight at a time.
   * If a second click arrives while the first is pending, it is silently ignored.
   * The button is disabled in the UI via the `actionBusy` state.
   */
  async function guardedAction(fn) {
    if (actionInFlightRef.current) return  // Already processing an action
    actionInFlightRef.current = true
    setActionBusy(true)
    try {
      await fn()
    } catch (err) {
      setError(err.message)
    } finally {
      actionInFlightRef.current = false
      setActionBusy(false)
    }
  }

  // ----- Game handlers -----

  async function handleAdvancePhase() {
    if (!gameId || !gameState) return
    await guardedAction(() => advancePhase(gameId, playerId))
  }

  async function handlePlaceBid(amount) {
    if (!gameId) return
    await guardedAction(() => placeBid(gameId, playerId, amount))
  }

  async function handlePassBid() {
    if (!gameId) return
    await guardedAction(() => passBid(gameId, playerId))
  }

  // ----- Revival handlers -----

  async function handleReviveForces(count) {
    if (!gameId) return
    await guardedAction(() => reviveForces(gameId, playerId, count))
  }

  async function handleReviveLeader(leaderId) {
    if (!gameId) return
    await guardedAction(() => reviveLeader(gameId, playerId, leaderId))
  }

  // ----- Shipment & Movement handlers -----

  async function handleShipForces(territoryName, sector, count, specialCount = 0) {
    if (!gameId) return
    await guardedAction(() => shipForces(gameId, playerId, territoryName, sector, count, specialCount))
  }

  async function handleMoveForces(fromTerritory, fromSector, toTerritory, toSector, regularCount, specialCount = 0) {
    if (!gameId) return
    await guardedAction(() => moveForces(gameId, playerId, fromTerritory, fromSector, toTerritory, toSector, regularCount, specialCount))
  }

  // ----- Battle handlers -----

  async function handleSubmitBattlePlan(forcesDialed, leaderId, weaponCardId, defenseCardId, specialForcesDialed = 0, spiceToExpend = 0) {
    if (!gameId) return
    await guardedAction(() => submitBattlePlanAdvanced(gameId, playerId, forcesDialed, leaderId, weaponCardId, defenseCardId, specialForcesDialed, spiceToExpend))
  }

  async function handleDeclareTraitor(callTraitor) {
    if (!gameId) return
    await guardedAction(() => declareTraitor(gameId, playerId, callTraitor))
  }

  // ----- Pre-battle handlers -----

  async function handleIssueVoice(targetFaction, command, cardType) {
    if (!gameId) return
    await guardedAction(() => issueVoice(gameId, playerId, targetFaction, command, cardType))
  }

  async function handleAcknowledgeVoice() {
    if (!gameId) return
    await guardedAction(() => acknowledgeVoice(gameId, playerId))
  }

  async function handleAskPrescience(element) {
    if (!gameId) return
    await guardedAction(() => askPrescience(gameId, playerId, element))
  }

  async function handleRevealPrescience(revealedValue) {
    if (!gameId) return
    await guardedAction(() => revealPrescience(gameId, playerId, revealedValue))
  }

  async function handleDonePrebattle() {
    if (!gameId) return
    await guardedAction(() => donePrebattle(gameId, playerId))
  }

  // ----- Generic action handler (special cards, etc.) -----

  async function handleAction(actionType, payload) {
    if (!gameId) return
    await guardedAction(() => gameAction(gameId, playerId, actionType, payload))
  }

  // ----- Fremen sandworm ride -----

  async function handleFremenRide(toTerritory, toSector, regularCount, specialCount) {
    if (!gameId) return
    await guardedAction(() => fremenSandwormRide(gameId, playerId, toTerritory, toSector, regularCount, specialCount))
  }

  async function handleFremenSkipRide() {
    if (!gameId) return
    await guardedAction(() => fremenSkipSandwormRide(gameId, playerId))
  }

  // ----- Nexus (Alliance) handlers -----

  async function handleProposeAlliance(targetFaction) {
    if (!gameId) return
    await guardedAction(() => proposeAlliance(gameId, playerId, targetFaction))
  }

  async function handleAcceptAlliance(proposerFaction) {
    if (!gameId) return
    await guardedAction(() => acceptAlliance(gameId, playerId, proposerFaction))
  }

  async function handleBreakAlliance() {
    if (!gameId) return
    await guardedAction(() => breakAlliance(gameId, playerId))
  }

  async function handlePassNexus() {
    if (!gameId) return
    await guardedAction(() => passNexus(gameId, playerId))
  }

  // ----- Render -----

  const screen = getScreen()

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-[#3a3020] px-6 py-3 flex items-center justify-between">
        <h1 className="text-sand text-xl font-bold tracking-widest uppercase">
          Dune — The Board Game
        </h1>
        <div className="flex items-center gap-4 text-sm text-gray-400">
          {gameState && (
            <>
              {gameState.current_turn > 0 && gameState.current_phase !== 'lobby' && gameState.current_phase !== 'setup' && (
                <span>Turn <strong className="text-sand-light">{gameState.current_turn}</strong> / 10</span>
              )}
              {gameState.lobby_state?.join_code && (
                <span>Code: <strong className="text-sand font-mono">{gameState.lobby_state.join_code}</strong></span>
              )}
            </>
          )}
          {gameId && (
            <span>Game <code className="text-xs text-gray-500">{gameId?.slice(0, 8)}</code></span>
          )}
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="bg-red-900/40 border-b border-red-700 px-6 py-2 text-red-300 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200 ml-4">dismiss</button>
        </div>
      )}

      {/* Screen router */}
      {screen === 'home' && (
        <HomeScreen
          onCreateGame={handleCreateGame}
          onJoinGame={handleJoinGame}
        />
      )}

      {screen === 'lobby' && (
        <LobbyView
          gameState={gameState}
          playerId={playerId}
          onSelectFaction={handleSelectFaction}
          onStartGame={handleStartGame}
        />
      )}

      {screen === 'traitor_selection' && (
        <TraitorSelectionView
          gameState={gameState}
          playerId={playerId}
          onSelectTraitor={handleSelectTraitor}
        />
      )}

      {screen === 'storm_dial' && (
        <StormDialView
          gameState={gameState}
          playerId={playerId}
          onSubmitDial={handleSubmitStormDial}
        />
      )}

      {screen === 'bg_prediction' && (
        <BgPredictionView
          gameState={gameState}
          playerId={playerId}
          onSubmitPrediction={handleBgPrediction}
        />
      )}

      {screen === 'fremen_placement' && (
        <FremenPlacementView
          gameState={gameState}
          playerId={playerId}
          onSubmitPlacement={handleFremenPlacement}
        />
      )}

      {screen === 'atreides_prescience' && (
        <AtreidesPrescienceView
          gameState={gameState}
          playerId={playerId}
          onAcknowledge={handleAtreidesPrescienceAck}
        />
      )}

      {screen === 'game' && (
        <GameView
          gameState={gameState}
          playerId={playerId}
          actionBusy={actionBusy}
          onAdvancePhase={handleAdvancePhase}
          onPlaceBid={handlePlaceBid}
          onPassBid={handlePassBid}
          onReviveForces={handleReviveForces}
          onReviveLeader={handleReviveLeader}
          onShipForces={handleShipForces}
          onMoveForces={handleMoveForces}
          onSubmitBattlePlan={handleSubmitBattlePlan}
          onDeclareTraitor={handleDeclareTraitor}
          onProposeAlliance={handleProposeAlliance}
          onAcceptAlliance={handleAcceptAlliance}
          onBreakAlliance={handleBreakAlliance}
          onPassNexus={handlePassNexus}
          onIssueVoice={handleIssueVoice}
          onAcknowledgeVoice={handleAcknowledgeVoice}
          onAskPrescience={handleAskPrescience}
          onRevealPrescience={handleRevealPrescience}
          onDonePrebattle={handleDonePrebattle}
          onAction={handleAction}
          onFremenRide={handleFremenRide}
          onFremenSkipRide={handleFremenSkipRide}
        />
      )}
      {/* Rules explainer — always available once a game exists */}
      {gameState && screen !== 'home' && <RulesChat />}
    </div>
  )
}
