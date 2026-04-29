import { useState } from 'react'
import Button from '../ui/Button.jsx'

const FACTION_LABELS = {
  atreides: 'House Atreides',
  harkonnen: 'House Harkonnen',
  fremen: 'Fremen',
  spacing_guild: 'Spacing Guild',
  emperor: 'Emperor',
  bene_gesserit: 'Bene Gesserit',
}

const FACTION_COLORS = {
  atreides: 'text-green-400',
  harkonnen: 'text-gray-300',
  fremen: 'text-yellow-600',
  spacing_guild: 'text-orange-400',
  emperor: 'text-red-400',
  bene_gesserit: 'text-blue-400',
}

export default function BgPredictionView({ gameState, playerId, onSubmitPrediction }) {
  const [predictedFaction, setPredictedFaction] = useState('')
  const [predictedTurn, setPredictedTurn] = useState(5)
  const [submitted, setSubmitted] = useState(false)

  if (!gameState?.setup_state) return null

  const myPlayer = gameState.players?.find(p => p.id === playerId)
  const isBgPlayer = myPlayer?.faction === 'bene_gesserit'

  // Factions available to predict (all except BG)
  const otherFactions = (gameState.players || [])
    .map(p => p.faction)
    .filter(f => f !== 'bene_gesserit')

  async function handleSubmit() {
    if (!predictedFaction) return
    try {
      await onSubmitPrediction(predictedFaction, predictedTurn)
      setSubmitted(true)
    } catch {
      // error handled in parent
    }
  }

  // Non-BG players see a waiting screen
  if (!isBgPlayer) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-60px)]">
        <div className="text-center">
          <h2 className="text-sand text-2xl font-bold mb-4">Bene Gesserit Prediction</h2>
          <p className="text-gray-400 mb-2">The Bene Gesserit is making their secret prediction...</p>
          <p className="text-gray-500 text-sm">Waiting for the Bene Gesserit player to submit.</p>
        </div>
      </div>
    )
  }

  // Already submitted
  if (submitted) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-60px)]">
        <div className="text-center">
          <h2 className="text-sand text-2xl font-bold mb-4">Prediction Recorded</h2>
          <p className="text-gray-400 text-sm">Your secret prediction has been sealed. No one else can see it.</p>
        </div>
      </div>
    )
  }

  // BG player's prediction form
  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-60px)]">
      <div className="w-full max-w-md">
        <div className="text-center mb-6">
          <h2 className="text-sand text-2xl font-bold mb-2">Bene Gesserit Prediction</h2>
          <p className="text-gray-400 text-sm">
            Secretly choose which faction will win, and on which turn. If your prediction
            comes true, you win — even if another faction controls the strongholds.
          </p>
          <p className="text-blue-400 text-xs mt-2 italic">
            This prediction is secret. Other players will not see your choice.
          </p>
        </div>

        <div className="space-y-5 bg-[#1a160e] border border-[#3a3020] rounded-lg p-6">
          {/* Faction selector */}
          <div>
            <label className="block text-sand text-sm font-semibold mb-2 uppercase tracking-wide">
              Predicted Winner
            </label>
            <div className="grid grid-cols-1 gap-2">
              {otherFactions.map(faction => (
                <button
                  key={faction}
                  onClick={() => setPredictedFaction(faction)}
                  className={`p-3 rounded border text-left transition-all ${
                    predictedFaction === faction
                      ? 'border-sand bg-sand/10 ring-1 ring-sand/30'
                      : 'border-[#3a3020] hover:border-sand/40'
                  }`}
                >
                  <span className={`font-medium ${FACTION_COLORS[faction] || 'text-gray-300'}`}>
                    {FACTION_LABELS[faction] || faction}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Turn selector */}
          <div>
            <label className="block text-sand text-sm font-semibold mb-2 uppercase tracking-wide">
              Predicted Turn: <span className="text-sand font-mono text-xl ml-1">{predictedTurn}</span>
            </label>
            <input
              type="range"
              min={1}
              max={10}
              value={predictedTurn}
              onChange={e => setPredictedTurn(parseInt(e.target.value))}
              className="w-full accent-[#c9a84c]"
            />
            <div className="flex justify-between text-xs text-gray-600 mt-1">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => (
                <span key={n}>{n}</span>
              ))}
            </div>
          </div>

          <div className="pt-2 text-center">
            <Button
              variant="primary"
              disabled={!predictedFaction}
              onClick={handleSubmit}
              className="px-8"
            >
              Seal Prediction
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
