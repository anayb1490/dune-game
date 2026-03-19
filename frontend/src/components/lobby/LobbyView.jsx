import Button from '../ui/Button.jsx'
import FactionSelect from './FactionSelect.jsx'
import PlayerList from './PlayerList.jsx'

const FACTIONS = [
  { id: 'atreides', name: 'House Atreides', color: 'text-green-400' },
  { id: 'harkonnen', name: 'House Harkonnen', color: 'text-gray-300' },
  { id: 'bene_gesserit', name: 'Bene Gesserit', color: 'text-blue-400' },
  { id: 'fremen', name: 'Fremen', color: 'text-yellow-600' },
  { id: 'spacing_guild', name: 'Spacing Guild', color: 'text-orange-400' },
  { id: 'emperor', name: 'The Emperor', color: 'text-red-400' },
]

export default function LobbyView({ gameState, playerId, onSelectFaction, onStartGame }) {
  const lobby = gameState?.lobby_state
  if (!lobby) return null

  const isHost = lobby.host_player_id === playerId
  const players = lobby.players || []
  const takenFactions = players.filter(p => p.faction).map(p => p.faction)
  const myPlayer = players.find(p => p.id === playerId)
  const myFaction = myPlayer?.faction
  const allReady = players.length >= 2 && players.every(p => p.faction)

  return (
    <div className="flex items-start justify-center min-h-[calc(100vh-60px)] py-8">
      <div className="w-full max-w-2xl">
        {/* Join code */}
        <div className="text-center mb-8">
          <p className="text-gray-400 text-sm mb-1">Share this code with other players</p>
          <div className="inline-block bg-[#1c1a14] border border-[#3a3020] rounded-lg px-8 py-3">
            <span className="text-sand text-3xl font-mono font-bold tracking-[0.3em]">
              {lobby.join_code}
            </span>
          </div>
          <p className="text-gray-500 text-xs mt-2">
            {players.length} / 6 players
          </p>
        </div>

        {/* Two columns: players + faction picker */}
        <div className="grid grid-cols-2 gap-6">
          {/* Left: player list */}
          <div>
            <h3 className="text-gray-400 text-xs uppercase tracking-wide mb-3">Players</h3>
            <PlayerList
              players={players}
              hostPlayerId={lobby.host_player_id}
              factions={FACTIONS}
            />
          </div>

          {/* Right: faction picker */}
          <div>
            <h3 className="text-gray-400 text-xs uppercase tracking-wide mb-3">Choose Your Faction</h3>
            <FactionSelect
              factions={FACTIONS}
              takenFactions={takenFactions}
              selectedFaction={myFaction}
              onSelect={onSelectFaction}
            />
          </div>
        </div>

        {/* Start button (host only) */}
        {isHost && (
          <div className="mt-8 text-center">
            <Button
              variant="primary"
              disabled={!allReady}
              onClick={onStartGame}
              className="px-8"
            >
              {allReady ? 'Start Game' : 'Waiting for players to pick factions...'}
            </Button>
          </div>
        )}

        {!isHost && (
          <div className="mt-8 text-center text-gray-500 text-sm">
            Waiting for the host to start the game...
          </div>
        )}
      </div>
    </div>
  )
}
