import { useState } from 'react'
import Button from '../ui/Button.jsx'

const FACTION_COLORS = {
  atreides: 'text-green-400',
  harkonnen: 'text-gray-300',
  bene_gesserit: 'text-blue-400',
  fremen: 'text-yellow-600',
  spacing_guild: 'text-orange-400',
  emperor: 'text-red-400',
}

const FACTION_BG = {
  atreides: 'bg-green-900/20',
  harkonnen: 'bg-gray-700/20',
  bene_gesserit: 'bg-blue-900/20',
  fremen: 'bg-yellow-900/20',
  spacing_guild: 'bg-orange-900/20',
  emperor: 'bg-red-900/20',
}

function factionLabel(faction) {
  return (faction || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export default function TraitorSelectionView({ gameState, playerId, onSelectTraitor }) {
  const [selectedCard, setSelectedCard] = useState(null)
  const setup = gameState?.setup_state
  if (!setup) return null

  const myHand = setup.traitor_hands_dealt?.[playerId] || []
  const alreadySelected = setup.traitor_selections_done?.includes(playerId)
  const totalPlayers = gameState.players?.length || 0
  const doneCount = setup.traitor_selections_done?.length || 0

  // Find this player's faction to determine own vs opponent leaders
  const myPlayer = gameState.players?.find(p => p.id === playerId)
  const myFaction = myPlayer?.faction

  const hasOpponentLeader = myHand.some(c => c.faction !== myFaction)

  function handleConfirm() {
    if (selectedCard) {
      onSelectTraitor(selectedCard)
    }
  }

  if (alreadySelected) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-60px)]">
        <div className="text-center">
          <h2 className="text-sand text-2xl font-bold mb-4">Traitor Selected</h2>
          <p className="text-gray-400 mb-2">Waiting for other players...</p>
          <p className="text-gray-500 text-sm">{doneCount} / {totalPlayers} players ready</p>
          <div className="flex justify-center gap-2 mt-4">
            {gameState.players.map(p => (
              <div
                key={p.id}
                className={`w-3 h-3 rounded-full ${
                  setup.traitor_selections_done?.includes(p.id)
                    ? 'bg-green-500'
                    : 'bg-gray-700'
                }`}
                title={p.name}
              />
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-60px)]">
      <div className="w-full max-w-xl">
        <div className="text-center mb-6">
          <h2 className="text-sand text-2xl font-bold mb-2">Choose Your Traitor</h2>
          <p className="text-gray-400 text-sm">
            {hasOpponentLeader
              ? "Select an opponent's leader to become your secret traitor. In battle, you can reveal them to instantly win."
              : "You drew no opponent leaders. Select one of your own leaders to protect from being called as a traitor."
            }
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-6">
          {myHand.map(card => {
            const isOwn = card.faction === myFaction
            const color = FACTION_COLORS[card.faction] || 'text-gray-400'
            const bg = FACTION_BG[card.faction] || ''

            return (
              <button
                key={card.id}
                onClick={() => setSelectedCard(card.id)}
                className={`p-4 rounded border text-left transition-all ${
                  selectedCard === card.id
                    ? 'border-sand bg-sand/10 ring-1 ring-sand/30'
                    : `border-[#3a3020] hover:border-sand/50 ${bg}`
                }`}
              >
                {/* Leader name */}
                <div className="text-gray-200 font-medium">{card.leader_name}</div>

                {/* Faction + strength row */}
                <div className="flex items-center justify-between mt-2">
                  <span className={`text-xs ${color}`}>
                    {factionLabel(card.faction)}
                  </span>
                  <span className="text-sand font-mono font-bold text-lg" title="Fighting strength">
                    {card.leader_strength}
                  </span>
                </div>

                {/* Own vs opponent badge */}
                <div className="mt-2">
                  {isOwn ? (
                    <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-blue-900/30 text-blue-400 border border-blue-800/40">
                      your leader — protect
                    </span>
                  ) : (
                    <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-red-900/30 text-red-400 border border-red-800/40">
                      opponent — traitor
                    </span>
                  )}
                </div>
              </button>
            )
          })}
        </div>

        <div className="text-center">
          <Button
            variant="primary"
            disabled={!selectedCard}
            onClick={handleConfirm}
            className="px-8"
          >
            Confirm Selection
          </Button>
        </div>
      </div>
    </div>
  )
}
