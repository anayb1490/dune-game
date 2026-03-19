/**
 * TreacheryHandPanel — displays the player's treachery card hand.
 *
 * Shows each card with its name, type badge, and subtype info.
 * Colour-coded by card type: red=weapon, blue=defense, purple=special, gray=worthless.
 * Displays hand limit (e.g. "Hand 2/4") in the header.
 */

const CARD_TYPE_STYLES = {
  weapon:    { label: 'Weapon',    bg: 'bg-red-950/40',    border: 'border-red-800/60',    text: 'text-red-400',    badge: 'text-red-400 bg-red-950/60 border-red-800' },
  defense:   { label: 'Defense',   bg: 'bg-blue-950/40',   border: 'border-blue-800/60',   text: 'text-blue-400',   badge: 'text-blue-400 bg-blue-950/60 border-blue-800' },
  special:   { label: 'Special',   bg: 'bg-purple-950/40', border: 'border-purple-800/60', text: 'text-purple-400', badge: 'text-purple-400 bg-purple-950/60 border-purple-800' },
  worthless: { label: 'Worthless', bg: 'bg-gray-900/40',   border: 'border-gray-700/60',   text: 'text-gray-500',   badge: 'text-gray-500 bg-gray-900/60 border-gray-700' },
}

const WEAPON_LABELS = {
  poison: 'Poison',
  projectile: 'Projectile',
  lasgun: 'Lasgun',
}

const DEFENSE_LABELS = {
  snooper: 'vs Poison',
  shield: 'vs Projectile',
}

const SPECIAL_LABELS = {
  karama: 'Cancel advantage',
  cheap_hero: 'Leader (str 0)',
  cheap_heroine: 'Leader (str 0)',
  truthtrance: 'Force yes/no answer',
  weather_control: 'Control storm',
  family_atomics: 'Destroy Shield Wall',
  hajr: 'Extra movement',
  tleilaxu_ghola: 'Revive leader/forces',
}

function CardSubtype({ card }) {
  if (card.weapon_type) return <span className="text-gray-500">{WEAPON_LABELS[card.weapon_type] ?? card.weapon_type}</span>
  if (card.defense_type) return <span className="text-gray-500">{DEFENSE_LABELS[card.defense_type] ?? card.defense_type}</span>
  if (card.special_type) return <span className="text-gray-500">{SPECIAL_LABELS[card.special_type] ?? card.special_type}</span>
  return null
}

export default function TreacheryHandPanel({ hand = [], maxCards = 4 }) {
  const style = (card) => CARD_TYPE_STYLES[card.card_type] ?? CARD_TYPE_STYLES.worthless

  return (
    <div className="bg-surface border border-[#3a3020] rounded p-2">
      {/* Header with hand count */}
      <div className="flex items-center justify-between px-1 mb-1.5">
        <p className="text-gray-500 text-[10px] uppercase tracking-wider">Treachery Hand</p>
        <span className={`text-[10px] font-mono ${hand.length >= maxCards ? 'text-red-400' : 'text-gray-500'}`}>
          {hand.length}/{maxCards}
        </span>
      </div>

      {hand.length === 0 ? (
        <p className="text-gray-600 text-[10px] text-center py-2 italic">No cards</p>
      ) : (
        <div className="space-y-1">
          {hand.map((card) => {
            const s = style(card)
            return (
              <div key={card.id} className={`${s.bg} border ${s.border} rounded px-2 py-1.5 flex items-center justify-between gap-2`}>
                <div className="min-w-0">
                  <p className={`${s.text} text-xs font-bold truncate`}>{card.name}</p>
                  <div className="text-[10px] leading-tight">
                    <CardSubtype card={card} />
                  </div>
                </div>
                <span className={`shrink-0 text-[9px] px-1 py-0.5 rounded border ${s.badge}`}>
                  {s.label}
                </span>
              </div>
            )
          })}
        </div>
      )}

      {hand.length >= maxCards && (
        <p className="text-red-400/70 text-[10px] text-center mt-1.5">Hand full — cannot bid</p>
      )}
    </div>
  )
}
