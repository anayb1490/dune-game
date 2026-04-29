/**
 * FremenRidePanel — shown after a Shai-Hulud attack triggers a sandworm ride.
 *
 * In Advanced mode, when a worm attacks a territory containing Fremen forces,
 * the Fremen player may ride the worm to any adjacent (non-storm) territory.
 *
 * Shown when:  myPlayer.faction === 'fremen'  &&  gameState.fremen_sandworm_ride_territory != null
 */

import { useState, useEffect } from 'react'
import Button from '../ui/Button.jsx'

export default function FremenRidePanel({
  myPlayer,
  gameState,
  onRide,
  onSkip,
  actionBusy = false,
}) {
  const [destination, setDestination] = useState('')
  const [destSector, setDestSector] = useState(0)
  const [regularCount, setRegularCount] = useState(0)
  const [specialCount, setSpecialCount] = useState(0)

  const rideTerritory = gameState?.fremen_sandworm_ride_territory
  const territories = gameState?.territories || {}
  const stormSector = gameState?.storm_sector ?? -1

  // Only show for Fremen player with an active ride opportunity
  if (!myPlayer || myPlayer.faction !== 'fremen' || !rideTerritory) return null

  // Count Fremen forces in the attacked territory
  const forcesAtSource = (myPlayer.forces_on_board || [])
    .filter(fg => fg.territory_name === rideTerritory)
  const regularAtSource = forcesAtSource.reduce((s, fg) => s + (fg.regular_count || 0), 0)
  const specialAtSource = forcesAtSource.reduce((s, fg) => s + (fg.special_count || 0), 0)

  // Get all territory names for destination (exclude source, exclude polar sink in storm)
  const territoryNames = Object.keys(territories).filter(n => n !== rideTerritory).sort()

  const destTerritory = territories[destination]
  const destSectors = destTerritory?.sectors || []

  // Auto-set sector when territory changes
  useEffect(() => {
    if (destSectors.length > 0) {
      setDestSector(destSectors[0])
    }
  }, [destination])

  function handleRide() {
    onRide(destination, destSector, regularCount, specialCount)
  }

  return (
    <div className="bg-surface border border-amber-700/70 rounded p-2 space-y-2">
      {/* Header */}
      <div className="flex items-center gap-2 px-1">
        <span className="text-2xl">🐛</span>
        <div>
          <p className="text-amber-400 text-xs font-bold uppercase tracking-wider">Sandworm Ride!</p>
          <p className="text-gray-400 text-[10px]">
            Worm surfaced in <span className="text-sand-light">{rideTerritory}</span>
          </p>
        </div>
      </div>

      <p className="text-gray-400 text-[10px] px-1">
        Ride to any non-storm territory, or skip. Forces left behind are unaffected.
      </p>

      {/* Available forces */}
      <div className="flex gap-3 text-[10px] px-1">
        <span className="text-gray-400">Available: <span className="text-gray-200">{regularAtSource}</span> regular</span>
        {specialAtSource > 0 && (
          <span className="text-gray-400">, <span className="text-amber-300">{specialAtSource}</span> Fedaykin</span>
        )}
      </div>

      {/* Destination select */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-gray-400 text-[10px] w-12">Ride to</span>
          <select
            value={destination}
            onChange={e => setDestination(e.target.value)}
            className="flex-1 bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs focus:border-sand outline-none"
          >
            <option value="">— select territory —</option>
            {territoryNames.map(name => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </div>

        {/* Sector select */}
        {destination && destSectors.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-[10px] w-12">Sector</span>
            <select
              value={destSector}
              onChange={e => setDestSector(parseInt(e.target.value))}
              className="flex-1 bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs focus:border-sand outline-none"
            >
              {destSectors.map(s => (
                <option key={s} value={s}>
                  Sector {s}{s === stormSector ? ' ⚡ (storm)' : ''}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Force counts */}
      {destination && (
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-[10px] w-12">Regular</span>
            <input
              type="number"
              min={0}
              max={regularAtSource}
              value={regularCount}
              onChange={e => setRegularCount(Math.max(0, Math.min(regularAtSource, parseInt(e.target.value) || 0)))}
              className="w-14 bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs font-mono focus:border-sand outline-none"
            />
            <span className="text-gray-600 text-[9px]">/ {regularAtSource}</span>
          </div>
          {specialAtSource > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-gray-400 text-[10px] w-12">Fedaykin</span>
              <input
                type="number"
                min={0}
                max={specialAtSource}
                value={specialCount}
                onChange={e => setSpecialCount(Math.max(0, Math.min(specialAtSource, parseInt(e.target.value) || 0)))}
                className="w-14 bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-amber-300 text-xs font-mono focus:border-sand outline-none"
              />
              <span className="text-gray-600 text-[9px]">/ {specialAtSource}</span>
            </div>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        <Button
          onClick={handleRide}
          disabled={actionBusy || !destination || (regularCount + specialCount === 0)}
          className="flex-1 text-xs py-1"
        >
          Ride the Worm!
        </Button>
        <Button
          onClick={onSkip}
          disabled={actionBusy}
          className="text-xs py-1 opacity-70"
        >
          Skip Ride
        </Button>
      </div>
    </div>
  )
}
