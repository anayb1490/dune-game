/**
 * AtreidesPrescienceView — Atreides player sees the top 5 Treachery cards
 * from the deck before the game begins (Advanced mode only).
 *
 * Other players see a waiting message.
 */

const CARD_TYPE_COLORS = {
  weapon:  'text-red-400',
  defense: 'text-blue-400',
  special: 'text-purple-400',
}

const WEAPON_LABELS = {
  projectile: 'Projectile Weapon',
  poison:     'Poison Weapon',
  lasgun:     'Lasgun',
}

const DEFENSE_LABELS = {
  shield:         'Shield',
  snooper:        'Poison Snooper',
  shield_snooper: 'Shield + Snooper',
}

function CardPreview({ card, index }) {
  const subLabel = card.weapon_type
    ? (WEAPON_LABELS[card.weapon_type] ?? card.weapon_type)
    : card.defense_type
      ? (DEFENSE_LABELS[card.defense_type] ?? card.defense_type)
      : (card.special_type ?? card.card_type ?? 'Unknown')

  const typeColor = CARD_TYPE_COLORS[card.card_type] ?? 'text-gray-400'

  return (
    <div className="flex items-start gap-3">
      <span className="text-gray-600 text-xs mt-2 w-4 text-right shrink-0">{index + 1}.</span>
      <div className="flex-1 bg-[#1a1510] border border-[#3a3020] rounded p-2.5">
        <p className="text-gray-100 text-xs font-semibold">{card.name ?? 'Unknown Card'}</p>
        <p className={`text-[10px] mt-0.5 ${typeColor}`}>{subLabel}</p>
      </div>
    </div>
  )
}

export default function AtreidesPrescienceView({
  gameState,
  playerId,
  onAcknowledge,
}) {
  const myPlayer = gameState?.players?.find(p => p.id === playerId)
  const isAtreides = myPlayer?.faction === 'atreides'

  // Cards come from the filtered state field set by state_filter.py
  const cards = gameState?.atreides_prescience_preview ?? []

  if (!isAtreides) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="bg-surface border border-[#3a3020] rounded-lg p-8 max-w-md text-center">
          <h2 className="text-sand text-xl font-bold uppercase tracking-widest mb-3">
            Atreides Prescience
          </h2>
          <p className="text-gray-400 text-sm">
            The Atreides player is using their prescience to study the Treachery deck…
          </p>
          <p className="text-gray-600 text-xs mt-3">
            Waiting for House Atreides to acknowledge.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="bg-surface border border-green-800/60 rounded-lg p-8 max-w-lg w-full">
        <h2 className="text-green-400 text-xl font-bold uppercase tracking-widest mb-1">
          Atreides Prescience
        </h2>
        <p className="text-gray-400 text-sm mb-5">
          Your prescience reveals the top cards of the Treachery deck. These will be bid on
          in order during the Bidding phase — use this knowledge wisely.
        </p>

        {cards.length === 0 ? (
          <p className="text-gray-500 text-sm italic mb-6">
            No cards to preview (deck is empty or state not loaded).
          </p>
        ) : (
          <div className="space-y-2 mb-6">
            {cards.map((card, i) => (
              <CardPreview key={card.id ?? i} card={card} index={i} />
            ))}
          </div>
        )}

        <p className="text-gray-600 text-[11px] mb-5 italic">
          Only you can see this information. During bidding, the card currently up for
          auction will be revealed to you before others bid.
        </p>

        <button
          onClick={onAcknowledge}
          className="w-full bg-green-800 hover:bg-green-700 border border-green-600 text-white rounded px-4 py-2.5 text-sm font-semibold uppercase tracking-wider transition-colors"
        >
          Begin the Game
        </button>
      </div>
    </div>
  )
}
