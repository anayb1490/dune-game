export default function FactionSelect({ factions, takenFactions, selectedFaction, onSelect }) {
  return (
    <div className="space-y-2">
      {factions.map(f => {
        const isTaken = takenFactions.includes(f.id) && f.id !== selectedFaction
        const isSelected = f.id === selectedFaction

        return (
          <button
            key={f.id}
            onClick={() => !isTaken && onSelect(f.id)}
            disabled={isTaken}
            className={`w-full text-left px-3 py-2 rounded border transition-colors ${
              isSelected
                ? 'border-sand bg-sand/10 text-sand'
                : isTaken
                  ? 'border-[#2a2418] text-gray-600 cursor-not-allowed opacity-50'
                  : 'border-[#3a3020] text-gray-300 hover:border-sand/50 hover:text-sand-light'
            }`}
          >
            <span className={`text-sm font-medium ${isSelected ? f.color : ''}`}>
              {f.name}
            </span>
            {isTaken && <span className="text-xs text-gray-600 ml-2">(taken)</span>}
            {isSelected && <span className="text-xs text-sand ml-2">(you)</span>}
          </button>
        )
      })}
    </div>
  )
}
