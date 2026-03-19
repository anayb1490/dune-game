const STATUS_COLORS = {
  available: 'text-gray-200',
  in_tanks: 'text-red-400',
  face_down_in_tanks: 'text-red-600',
  captured: 'text-purple-400',
}

const FACTION_COLORS = {
  atreides: 'text-green-400',
  harkonnen: 'text-gray-300',
  bene_gesserit: 'text-blue-400',
  fremen: 'text-yellow-600',
  spacing_guild: 'text-orange-400',
  emperor: 'text-red-400',
}

function factionLabel(faction) {
  return (faction || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export default function LeadersPanel({ leaders, traitorCards, myFaction }) {
  const traitors = traitorCards || []
  const sortedLeaders = [...(leaders || [])].sort((a, b) => b.strength - a.strength)
  const hasOwnTraitor = traitors.some(t => t.faction === myFaction)

  return (
    <div className="bg-surface border border-[#3a3020] rounded p-2">
      <h2 className="text-sand text-[10px] font-bold uppercase tracking-widest mb-1 px-1">Leaders</h2>

      <div className="space-y-0.5">
        {sortedLeaders.map(leader => {
          const statusColor = STATUS_COLORS[leader.status] || 'text-gray-200'
          const isAvailable = leader.status === 'available'
          return (
            <div
              key={leader.id}
              className={`flex items-center justify-between text-xs px-1 ${isAvailable ? '' : 'opacity-40'}`}
            >
              <span className={statusColor}>{leader.name}</span>
              <span className="text-sand font-mono font-bold">{leader.strength}</span>
            </div>
          )
        })}
      </div>

      {traitors.length > 0 && (
        <div className="border-t border-[#3a3020] mt-1.5 pt-1.5">
          <h3 className="text-gray-500 text-[10px] uppercase tracking-widest mb-1 px-1">
            {hasOwnTraitor ? 'Protected' : 'Traitor'}
          </h3>
          {traitors.map(card => {
            const isOwn = card.faction === myFaction
            const factionColor = FACTION_COLORS[card.faction] || 'text-gray-400'
            return (
              <div
                key={card.id}
                className={`rounded border px-2 py-1.5 ${
                  isOwn ? 'border-blue-800/40 bg-blue-900/20' : 'border-red-800/40 bg-red-900/20'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-gray-200 text-xs font-medium">{card.leader_name}</span>
                  <span className="text-sand font-mono font-bold text-xs">{card.leader_strength}</span>
                </div>
                <div className="flex items-center justify-between mt-0.5">
                  <span className={`text-[10px] ${factionColor}`}>{factionLabel(card.faction)}</span>
                  <span className={`text-[9px] uppercase ${isOwn ? 'text-blue-400' : 'text-red-400'}`}>
                    {isOwn ? 'protected' : 'traitor'}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
