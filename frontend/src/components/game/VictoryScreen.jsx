/**
 * VictoryScreen — full-screen overlay shown when is_game_over === true.
 *
 * Displays the winning faction (and ally, if any), the win condition description,
 * and faction-appropriate accent colours. A "View Final Board" button dismisses
 * the overlay so players can inspect the end state.
 */

import { useState } from 'react'

// Faction display names
const FACTION_LABELS = {
  atreides:      'House Atreides',
  harkonnen:     'House Harkonnen',
  bene_gesserit: 'Bene Gesserit',
  fremen:        'The Fremen',
  spacing_guild: 'Spacing Guild',
  emperor:       'The Emperor',
}

// Faction accent colours (Tailwind arbitrary values / CSS strings)
const FACTION_COLOURS = {
  atreides:      { primary: '#4ea8de', glow: 'rgba(78,168,222,0.35)',  label: 'text-blue-300'   },
  harkonnen:     { primary: '#c94040', glow: 'rgba(201,64,64,0.35)',   label: 'text-red-400'    },
  bene_gesserit: { primary: '#9b59b6', glow: 'rgba(155,89,182,0.35)', label: 'text-purple-400' },
  fremen:        { primary: '#e8a44a', glow: 'rgba(232,164,74,0.35)', label: 'text-amber-400'  },
  spacing_guild: { primary: '#f39c12', glow: 'rgba(243,156,18,0.35)', label: 'text-yellow-400' },
  emperor:       { primary: '#e74c3c', glow: 'rgba(231,76,60,0.35)',  label: 'text-rose-400'   },
}

// Faction flavour quotes
const FACTION_QUOTES = {
  atreides:      '"The gift of words is the gift of deception." — Lady Jessica',
  harkonnen:     '"Power over men — not for them." — Baron Harkonnen',
  bene_gesserit: '"We predicted this moment long ago." — Bene Gesserit Sisterhood',
  fremen:        '"The desert takes all. We are the desert." — Stilgar',
  spacing_guild: '"He who controls the spice controls the universe." — Guild Navigator',
  emperor:       '"The Imperium bows to none." — Emperor Shaddam IV',
}

const DEFAULT_COLOURS = { primary: '#c8a84b', glow: 'rgba(200,168,75,0.35)', label: 'text-sand' }

export default function VictoryScreen({ gameState, onDismiss }) {
  const [dismissed, setDismissed] = useState(false)

  if (dismissed) return null

  const { winner, ally_winner, win_condition, players } = gameState

  const winnerColour  = FACTION_COLOURS[winner]  ?? DEFAULT_COLOURS
  const allyColour    = FACTION_COLOURS[ally_winner] ?? DEFAULT_COLOURS

  const winnerLabel = FACTION_LABELS[winner]   ?? winner   ?? 'Unknown'
  const allyLabel   = FACTION_LABELS[ally_winner] ?? ally_winner

  const quote = FACTION_QUOTES[winner] ?? '"The spice must flow."'

  const isAlliance = Boolean(ally_winner)

  function handleDismiss() {
    setDismissed(true)
    onDismiss?.()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(5,4,2,0.92)', backdropFilter: 'blur(6px)' }}
    >
      {/* Glow backdrop */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `radial-gradient(ellipse 60% 50% at 50% 40%, ${winnerColour.glow} 0%, transparent 70%)`,
        }}
      />

      {/* Card */}
      <div
        className="relative z-10 max-w-lg w-full mx-4 rounded-xl border p-8 text-center"
        style={{
          background: 'rgba(15,12,6,0.97)',
          borderColor: winnerColour.primary,
          boxShadow: `0 0 60px ${winnerColour.glow}, 0 0 120px ${winnerColour.glow}`,
        }}
      >
        {/* Crown / victory icon */}
        <div className="text-5xl mb-3 select-none">👑</div>

        {/* Title */}
        <p className="text-gray-500 text-xs uppercase tracking-[0.3em] mb-2">
          Victory Achieved
        </p>

        {/* Winner name */}
        {isAlliance ? (
          <div className="mb-1">
            <span
              className="text-3xl font-bold tracking-wide"
              style={{ color: winnerColour.primary }}
            >
              {winnerLabel}
            </span>
            <span className="text-gray-400 text-xl mx-3">&amp;</span>
            <span
              className="text-3xl font-bold tracking-wide"
              style={{ color: allyColour.primary }}
            >
              {allyLabel}
            </span>
          </div>
        ) : (
          <h1
            className="text-4xl font-bold tracking-wide mb-1"
            style={{ color: winnerColour.primary }}
          >
            {winnerLabel}
          </h1>
        )}

        {/* Alliance label */}
        {isAlliance && (
          <p className="text-gray-400 text-sm mb-3">Allied Victory</p>
        )}

        {/* Divider */}
        <div
          className="h-px my-4 mx-8"
          style={{ background: `linear-gradient(to right, transparent, ${winnerColour.primary}, transparent)` }}
        />

        {/* Win condition */}
        {win_condition && (
          <div className="mb-4">
            <p className="text-gray-500 text-[10px] uppercase tracking-widest mb-1">
              How victory was achieved
            </p>
            <p className="text-gray-200 text-sm font-medium">{win_condition}</p>
          </div>
        )}

        {/* No victor stalemate */}
        {!winner && (
          <p className="text-gray-400 text-lg mb-4">
            No faction achieved victory.<br />
            <span className="text-gray-500 text-sm">The desert claimed all ambitions.</span>
          </p>
        )}

        {/* Flavour quote */}
        <p className="text-gray-600 text-xs italic mt-2 mb-6 px-4">{quote}</p>

        {/* Player roster */}
        {players && (
          <div className="grid grid-cols-2 gap-1 text-xs mb-6">
            {players.map(p => {
              const isWinner  = p.faction === winner
              const isAlly    = p.faction === ally_winner
              const col       = FACTION_COLOURS[p.faction] ?? DEFAULT_COLOURS
              return (
                <div
                  key={p.id}
                  className="flex items-center gap-2 rounded px-2 py-1"
                  style={{
                    background: (isWinner || isAlly) ? `${col.glow}` : 'rgba(255,255,255,0.03)',
                    border: `1px solid ${(isWinner || isAlly) ? col.primary : 'transparent'}`,
                  }}
                >
                  {(isWinner || isAlly) && <span className="text-sm">👑</span>}
                  <div className="text-left min-w-0">
                    <p
                      className="font-semibold truncate"
                      style={{ color: (isWinner || isAlly) ? col.primary : '#9ca3af' }}
                    >
                      {p.name}
                    </p>
                    <p className="text-gray-600 text-[10px] truncate">
                      {FACTION_LABELS[p.faction] ?? p.faction}
                    </p>
                  </div>
                  <p className="ml-auto text-spice font-mono">◆{p.spice}</p>
                </div>
              )
            })}
          </div>
        )}

        {/* Dismiss button */}
        <button
          onClick={handleDismiss}
          className="px-6 py-2 rounded text-sm font-semibold transition-all"
          style={{
            background: `linear-gradient(135deg, ${winnerColour.primary}22, ${winnerColour.primary}44)`,
            border: `1px solid ${winnerColour.primary}`,
            color: winnerColour.primary,
          }}
          onMouseEnter={e => e.currentTarget.style.background = `${winnerColour.primary}55`}
          onMouseLeave={e => e.currentTarget.style.background = `linear-gradient(135deg, ${winnerColour.primary}22, ${winnerColour.primary}44)`}
        >
          View Final Board
        </button>
      </div>
    </div>
  )
}
