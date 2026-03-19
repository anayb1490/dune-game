export default function PlayerList({ players, hostPlayerId, factions }) {
  function getFactionDisplay(factionId) {
    if (!factionId) return null
    const f = factions.find(f => f.id === factionId)
    return f ? { name: f.name, color: f.color } : { name: factionId, color: 'text-gray-400' }
  }

  return (
    <div className="space-y-2">
      {players.map(p => {
        const faction = getFactionDisplay(p.faction)
        const isHost = p.id === hostPlayerId

        return (
          <div
            key={p.id}
            className="flex items-center justify-between px-3 py-2 bg-[#1c1a14] border border-[#3a3020] rounded"
          >
            <div className="flex items-center gap-2">
              {isHost && <span className="text-xs text-sand" title="Host">★</span>}
              <span className="text-gray-200 text-sm">{p.name}</span>
            </div>
            {faction ? (
              <span className={`text-xs ${faction.color}`}>{faction.name}</span>
            ) : (
              <span className="text-xs text-gray-600 italic">choosing...</span>
            )}
          </div>
        )
      })}

      {players.length === 0 && (
        <p className="text-gray-600 text-sm italic">No players yet</p>
      )}
    </div>
  )
}
