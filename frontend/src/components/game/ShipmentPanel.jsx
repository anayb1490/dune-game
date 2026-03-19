import { useState, useEffect } from 'react'
import Button from '../ui/Button.jsx'
import { getAdjacentTerritories } from '../../utils/adjacency.js'

export default function ShipmentPanel({
  myPlayer,
  territories,
  gameState,
  onShipForces,
  onMoveForces,
  onHighlight,   // (fromName, toName) → highlights on the board
}) {
  const [shipTerritory, setShipTerritory] = useState('')
  const [shipSector, setShipSector] = useState(0)
  const [shipCount, setShipCount] = useState(1)

  const [moveFrom, setMoveFrom] = useState('')
  const [moveFromSector, setMoveFromSector] = useState(0)
  const [moveTo, setMoveTo] = useState('')
  const [moveToSector, setMoveToSector] = useState(0)
  const [moveCount, setMoveCount] = useState(1)

  if (!myPlayer) return null

  const territoryNames = Object.keys(territories || {}).sort()
  const reserveForces = myPlayer.forces_in_reserve || 0
  const movesThisTurn = myPlayer.moves_this_turn || 0
  // Fremen in Advanced get 2 moves; everyone else gets 1
  const isFremen = myPlayer.faction === 'fremen'
  const isAdvanced = gameState?.mode === 'advanced'
  const maxMoves = (isFremen && isAdvanced) ? 2 : 1
  const hasMoved = movesThisTurn >= maxMoves

  // Get sectors for selected territory
  const shipSectors = territories?.[shipTerritory]?.sectors || []
  const moveToSectors = territories?.[moveTo]?.sectors || []

  // Force groups for movement source
  const myForces = (myPlayer.forces_on_board || []).filter(
    fg => (fg.regular_count || 0) + (fg.special_count || 0) > 0
  )

  const selectedSourceForce = myForces.find(
    fg => fg.territory_name === moveFrom && fg.sector === moveFromSector
  )
  const sourceTotal = selectedSourceForce
    ? (selectedSourceForce.regular_count || 0) + (selectedSourceForce.special_count || 0)
    : 0

  // Adjacent territories for the "To" dropdown — filter when a source is selected
  const validMoveTargets = moveFrom
    ? getAdjacentTerritories(moveFrom, territories)
    : territoryNames

  // Notify parent of highlight changes
  useEffect(() => {
    onHighlight?.(moveFrom, moveTo)
  }, [moveFrom, moveTo])

  // Reset moveTo if it's no longer a valid adjacent target
  useEffect(() => {
    if (moveTo && moveFrom && !validMoveTargets.includes(moveTo)) {
      setMoveTo('')
      setMoveToSector(0)
    }
  }, [moveFrom])

  function handleShip() {
    if (shipTerritory && shipCount > 0) {
      onShipForces(shipTerritory, shipSector, shipCount)
    }
  }

  function handleMove() {
    if (moveFrom && moveTo && moveCount > 0 && selectedSourceForce) {
      const regToMove = Math.min(moveCount, selectedSourceForce.regular_count || 0)
      const specToMove = moveCount - regToMove
      onMoveForces(moveFrom, moveFromSector, moveTo, moveToSector, regToMove, specToMove)
      // Clear after move
      setMoveFrom('')
      setMoveFromSector(0)
      setMoveTo('')
      setMoveToSector(0)
      setMoveCount(1)
    }
  }

  const selectClass = 'bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs w-full focus:border-sand outline-none'

  return (
    <div className="bg-surface border border-[#3a3020] rounded p-2 space-y-2">
      <h2 className="text-sand text-xs font-bold uppercase tracking-wider px-1">Ship & Move</h2>

      {/* ── Ship forces ─────────────────────────────────────── */}
      <div className="space-y-1">
        <p className="text-gray-500 text-[10px] uppercase px-1">
          Ship from Reserve ({reserveForces}) — 1◆/force
        </p>
        <select
          value={shipTerritory}
          onChange={(e) => {
            setShipTerritory(e.target.value)
            const sectors = territories?.[e.target.value]?.sectors || []
            if (sectors.length > 0) setShipSector(sectors[0])
          }}
          className={selectClass}
        >
          <option value="">Select territory...</option>
          {territoryNames.map(name => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>

        {shipSectors.length > 1 && (
          <select
            value={shipSector}
            onChange={(e) => setShipSector(parseInt(e.target.value))}
            className={selectClass}
          >
            {shipSectors.map(s => (
              <option key={s} value={s}>Sector {s}</option>
            ))}
          </select>
        )}

        <div className="flex items-center gap-2">
          <input
            type="number" min={1} max={reserveForces} value={shipCount}
            onChange={(e) => setShipCount(Math.max(1, parseInt(e.target.value) || 1))}
            className="bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs font-mono w-14 focus:border-sand outline-none"
          />
          <Button
            onClick={handleShip}
            className="text-xs flex-1 py-1"
            disabled={!shipTerritory || shipCount < 1 || shipCount > reserveForces || shipCount > myPlayer.spice}
          >
            Ship {shipCount} (◆{shipCount})
          </Button>
        </div>
      </div>

      {/* ── Move forces ─────────────────────────────────────── */}
      {myForces.length > 0 && (
        <div className="space-y-1 border-t border-[#3a3020] pt-1.5">
          <p className="text-gray-500 text-[10px] uppercase px-1">
            Move Forces
            {hasMoved && <span className="text-red-400 ml-1">(already moved this turn)</span>}
          </p>

          {/* From */}
          <select
            value={moveFrom ? `${moveFrom}|${moveFromSector}` : ''}
            onChange={(e) => {
              const [terr, sec] = e.target.value.split('|')
              setMoveFrom(terr || '')
              setMoveFromSector(parseInt(sec) || 0)
              setMoveTo('')
              setMoveToSector(0)
            }}
            className={selectClass}
            disabled={hasMoved}
          >
            <option value="">From...</option>
            {myForces.map(fg => {
              const total = (fg.regular_count || 0) + (fg.special_count || 0)
              return (
                <option key={`${fg.territory_name}|${fg.sector}`} value={`${fg.territory_name}|${fg.sector}`}>
                  {fg.territory_name} s{fg.sector} ({total})
                </option>
              )
            })}
          </select>

          {/* To — filtered to adjacent only */}
          <select
            value={moveTo}
            onChange={(e) => {
              setMoveTo(e.target.value)
              const sectors = territories?.[e.target.value]?.sectors || []
              if (sectors.length > 0) setMoveToSector(sectors[0])
            }}
            className={selectClass}
            disabled={hasMoved || !moveFrom}
          >
            <option value="">
              {moveFrom ? `To (${validMoveTargets.length} adjacent)...` : 'To...'}
            </option>
            {validMoveTargets.map(name => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>

          {moveToSectors.length > 1 && (
            <select
              value={moveToSector}
              onChange={(e) => setMoveToSector(parseInt(e.target.value))}
              className={selectClass}
              disabled={hasMoved}
            >
              {moveToSectors.map(s => (
                <option key={s} value={s}>Sector {s}</option>
              ))}
            </select>
          )}

          <div className="flex items-center gap-2">
            <input
              type="number" min={1} max={sourceTotal} value={moveCount}
              onChange={(e) => setMoveCount(Math.max(1, Math.min(sourceTotal, parseInt(e.target.value) || 1)))}
              className="bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs font-mono w-14 focus:border-sand outline-none"
              disabled={hasMoved}
            />
            <Button
              onClick={handleMove}
              className="text-xs flex-1 py-1"
              disabled={hasMoved || !moveFrom || !moveTo || moveCount < 1 || moveCount > sourceTotal}
            >
              Move {moveCount}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
