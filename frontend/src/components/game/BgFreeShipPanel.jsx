/**
 * BgFreeShipPanel — out-of-turn BG free-ship prompt.
 *
 * Shown during Shipment & Movement when `gameState.bg_free_ship_pending === true`
 * AND the local player is Bene Gesserit — regardless of whose turn it currently is.
 *
 * Rules (Rulebook p.13):
 *   Basic   — must ship to Polar Sink.
 *   Advanced — may ship to the territory the triggering faction just shipped to,
 *              OR to the Polar Sink.
 *
 * BG may also pass, forfeiting the opportunity.
 */

import { useState } from 'react'
import Button from '../ui/Button.jsx'

const POLAR_SINK = 'Polar Sink'

const selectClass =
  'bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs w-full focus:border-sand outline-none'

export default function BgFreeShipPanel({
  myPlayer,
  gameState,
  territories,
  onAction,
  actionBusy = false,
}) {
  const isAdvanced = gameState?.mode === 'advanced'
  const lastTerritory = gameState?.bg_free_ship_last_territory || POLAR_SINK
  const stormSector = gameState?.storm_sector ?? -1
  const reserveCount = myPlayer?.forces_in_reserve || 0

  // Allowed destinations: Basic → only Polar Sink; Advanced → last territory + Polar Sink
  const destinationOptions = isAdvanced
    ? [...new Set([lastTerritory, POLAR_SINK])]
    : [POLAR_SINK]

  const [destination, setDestination] = useState(destinationOptions[0] || POLAR_SINK)
  const [sector, setSector] = useState(() => {
    const secs = territories?.[destinationOptions[0]]?.sectors || []
    return secs[0] ?? 0
  })
  const [asAdvisor, setAsAdvisor] = useState(false)

  const destTerritory = territories?.[destination]
  const destSectors = destTerritory?.sectors || []

  function handleDestChange(newDest) {
    setDestination(newDest)
    const secs = territories?.[newDest]?.sectors || []
    setSector(secs[0] ?? 0)
    setAsAdvisor(false)
  }

  // Advisor option: only when others are present in destination (Advanced + non-Polar Sink)
  const othersPresent =
    isAdvanced &&
    destination !== POLAR_SINK &&
    (gameState?.players || []).some(
      p =>
        p.faction !== 'bene_gesserit' &&
        !p.is_eliminated &&
        (p.forces_on_board || []).some(
          fg =>
            fg.territory_name === destination &&
            !fg.is_advisor &&
            (fg.regular_count + fg.special_count) > 0
        )
    )

  function handleShip() {
    onAction('bg_free_ship', {
      territory_name: destination,
      sector,
      as_advisor: asAdvisor && othersPresent,
    })
  }

  function handlePass() {
    onAction('pass_bg_free_ship', {})
  }

  return (
    <div className="bg-surface border border-purple-500/60 rounded p-2 ring-1 ring-purple-700/30">
      <p className="text-purple-400 text-[10px] font-bold uppercase tracking-wider mb-1">
        ✦ BG Free Shipment Triggered
      </p>
      <p className="text-gray-400 text-[10px] mb-2 leading-relaxed">
        {isAdvanced
          ? `Another faction shipped to ${lastTerritory}. Ship 1 force there or to Polar Sink for free.`
          : 'Another faction shipped. Ship 1 force to the Polar Sink for free.'}
        {reserveCount === 0 && (
          <span className="text-red-400 ml-1">(no forces in reserve)</span>
        )}
      </p>

      {/* Destination selector — only shown when there's a real choice */}
      {destinationOptions.length > 1 && (
        <select
          value={destination}
          onChange={e => handleDestChange(e.target.value)}
          className={selectClass}
        >
          {destinationOptions.map(n => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
      )}

      {/* Sector selector — only when destination has multiple sectors */}
      {destSectors.length > 1 && (
        <select
          value={sector}
          onChange={e => setSector(parseInt(e.target.value))}
          className={`${selectClass} mt-1`}
        >
          {destSectors.map(s => (
            <option key={s} value={s}>
              Sector {s}{s === stormSector ? ' ⚡ (storm)' : ''}
            </option>
          ))}
        </select>
      )}

      {/* Advisor checkbox — Advanced + non-Polar Sink + others present */}
      {othersPresent && (
        <label className="flex items-center gap-2 px-1 mt-1 cursor-pointer">
          <input
            type="checkbox"
            checked={asAdvisor}
            onChange={e => setAsAdvisor(e.target.checked)}
            className="accent-purple-500"
          />
          <span className="text-purple-300 text-[10px]">Ship as Advisor (coexist)</span>
        </label>
      )}

      <div className="flex gap-2 mt-2">
        <Button
          onClick={handleShip}
          disabled={actionBusy || reserveCount === 0}
          className="flex-1 text-xs py-1"
        >
          Free Ship
        </Button>
        <Button
          onClick={handlePass}
          disabled={actionBusy}
          className="text-xs py-1 opacity-60"
        >
          Pass
        </Button>
      </div>
    </div>
  )
}
