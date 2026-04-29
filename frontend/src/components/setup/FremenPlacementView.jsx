import { useState } from 'react'
import Button from '../ui/Button.jsx'

export default function FremenPlacementView({ gameState, playerId, onSubmitPlacement }) {
  const fremenPlayer = gameState?.players?.find(p => p.faction === 'fremen')
  const myPlayer = gameState?.players?.find(p => p.id === playerId)
  const isFremenPlayer = myPlayer?.faction === 'fremen'

  // Compute totals from the Fremen player's current forces
  const startingForces = fremenPlayer?.forces_on_board || []
  const totalRegular = startingForces.reduce((s, fg) => s + fg.regular_count, 0)
  const totalSpecial = startingForces.reduce((s, fg) => s + fg.special_count, 0)

  // Build the default rows from starting positions
  const defaultRows = startingForces.map(fg => ({
    territory: fg.territory_name,
    sector: fg.sector,
    regular_count: fg.regular_count,
    special_count: fg.special_count,
  }))

  const [rows, setRows] = useState(defaultRows)
  const [submitted, setSubmitted] = useState(false)

  if (!gameState?.setup_state) return null

  // Territories available for placement (not occupied by enemies)
  const occupiedByOthers = new Set()
  for (const p of (gameState.players || [])) {
    if (p.faction !== 'fremen') {
      for (const fg of (p.forces_on_board || [])) {
        occupiedByOthers.add(fg.territory_name)
      }
    }
  }

  const allTerritoryNames = Object.keys(gameState.territories || {})
    .filter(t => !occupiedByOthers.has(t))
    .sort()

  // Non-Fremen players see a waiting screen
  if (!isFremenPlayer) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-60px)]">
        <div className="text-center">
          <h2 className="text-sand text-2xl font-bold mb-4">Fremen Placement</h2>
          <p className="text-gray-400 mb-2">The Fremen are choosing where to begin...</p>
          <p className="text-gray-500 text-sm">Waiting for the Fremen player to place their forces.</p>
        </div>
      </div>
    )
  }

  if (submitted) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-60px)]">
        <div className="text-center">
          <h2 className="text-sand text-2xl font-bold mb-4">Forces Placed</h2>
          <p className="text-gray-400 text-sm">The Fremen forces have been positioned. The game is about to begin.</p>
        </div>
      </div>
    )
  }

  // Computed totals for placed forces
  const placedRegular = rows.reduce((s, r) => s + (parseInt(r.regular_count) || 0), 0)
  const placedSpecial = rows.reduce((s, r) => s + (parseInt(r.special_count) || 0), 0)
  const regularOk = placedRegular === totalRegular
  const specialOk = placedSpecial === totalSpecial
  const canSubmit = regularOk && specialOk && rows.every(r => r.territory)

  function updateRow(idx, field, value) {
    setRows(prev => prev.map((r, i) => i === idx ? { ...r, [field]: value } : r))
  }

  function addRow() {
    setRows(prev => [...prev, { territory: '', sector: 0, regular_count: 0, special_count: 0 }])
  }

  function removeRow(idx) {
    setRows(prev => prev.filter((_, i) => i !== idx))
  }

  async function handleConfirm() {
    if (!canSubmit) return
    const placements = rows
      .filter(r => r.territory && (parseInt(r.regular_count) || 0) + (parseInt(r.special_count) || 0) > 0)
      .map(r => ({
        territory: r.territory,
        sector: parseInt(r.sector) || 0,
        regular_count: parseInt(r.regular_count) || 0,
        special_count: parseInt(r.special_count) || 0,
      }))
    try {
      await onSubmitPlacement(placements)
      setSubmitted(true)
    } catch {
      // error handled in parent
    }
  }

  async function handleKeepDefault() {
    const placements = defaultRows
      .filter(r => r.regular_count + r.special_count > 0)
      .map(r => ({
        territory: r.territory,
        sector: r.sector,
        regular_count: r.regular_count,
        special_count: r.special_count,
      }))
    try {
      await onSubmitPlacement(placements)
      setSubmitted(true)
    } catch {
      // error handled in parent
    }
  }

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-60px)] py-8">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-6">
          <h2 className="text-sand text-2xl font-bold mb-2">Fremen Placement</h2>
          <p className="text-gray-400 text-sm">
            As the Fremen, you may freely redistribute your starting forces across
            any unoccupied territories. Distribute all your forces before confirming.
          </p>
        </div>

        {/* Force totals summary */}
        <div className="flex gap-4 justify-center mb-5">
          <div className={`px-4 py-2 rounded border text-sm ${regularOk ? 'border-green-700 text-green-400' : 'border-red-700 text-red-400'}`}>
            Regular: <strong>{placedRegular}</strong> / {totalRegular}
          </div>
          <div className={`px-4 py-2 rounded border text-sm ${specialOk ? 'border-green-700 text-green-400' : 'border-red-700 text-red-400'}`}>
            Fedaykin: <strong>{placedSpecial}</strong> / {totalSpecial}
          </div>
        </div>

        {/* Placement rows */}
        <div className="bg-[#1a160e] border border-[#3a3020] rounded-lg p-4 mb-4 space-y-3">
          {rows.map((row, idx) => {
            const territory = gameState.territories?.[row.territory]
            const sectors = territory?.sectors || [0]

            return (
              <div key={idx} className="flex gap-2 items-center flex-wrap">
                {/* Territory dropdown */}
                <select
                  value={row.territory}
                  onChange={e => {
                    const t = gameState.territories?.[e.target.value]
                    updateRow(idx, 'territory', e.target.value)
                    if (t?.sectors?.[0] !== undefined) {
                      updateRow(idx, 'sector', t.sectors[0])
                    }
                  }}
                  className="flex-1 min-w-[180px] bg-[#0f0c07] border border-[#3a3020] text-gray-200 text-sm rounded px-2 py-1.5 focus:border-sand/50 focus:outline-none"
                >
                  <option value="">— select territory —</option>
                  {allTerritoryNames.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>

                {/* Sector dropdown (only if territory has multiple sectors) */}
                {sectors.length > 1 && (
                  <select
                    value={row.sector}
                    onChange={e => updateRow(idx, 'sector', parseInt(e.target.value))}
                    className="bg-[#0f0c07] border border-[#3a3020] text-gray-200 text-sm rounded px-2 py-1.5 focus:border-sand/50 focus:outline-none"
                  >
                    {sectors.map(s => (
                      <option key={s} value={s}>Sector {s}</option>
                    ))}
                  </select>
                )}

                {/* Regular count */}
                <div className="flex items-center gap-1">
                  <label className="text-gray-500 text-xs">Reg</label>
                  <input
                    type="number"
                    min={0}
                    max={totalRegular}
                    value={row.regular_count}
                    onChange={e => updateRow(idx, 'regular_count', parseInt(e.target.value) || 0)}
                    className="w-16 bg-[#0f0c07] border border-[#3a3020] text-gray-200 text-sm rounded px-2 py-1.5 text-center focus:border-sand/50 focus:outline-none"
                  />
                </div>

                {/* Special count (Fedaykin) */}
                {totalSpecial > 0 && (
                  <div className="flex items-center gap-1">
                    <label className="text-yellow-600 text-xs">Fed</label>
                    <input
                      type="number"
                      min={0}
                      max={totalSpecial}
                      value={row.special_count}
                      onChange={e => updateRow(idx, 'special_count', parseInt(e.target.value) || 0)}
                      className="w-16 bg-[#0f0c07] border border-[#3a3020] text-yellow-700 text-sm rounded px-2 py-1.5 text-center focus:border-sand/50 focus:outline-none"
                    />
                  </div>
                )}

                {/* Remove row */}
                <button
                  onClick={() => removeRow(idx)}
                  className="text-red-600 hover:text-red-400 text-sm px-1"
                  title="Remove this placement"
                >
                  ✕
                </button>
              </div>
            )
          })}

          <button
            onClick={addRow}
            className="text-sand/60 hover:text-sand text-sm border border-dashed border-[#3a3020] hover:border-sand/40 rounded px-3 py-1.5 w-full transition-colors"
          >
            + Add placement
          </button>
        </div>

        {/* Buttons */}
        <div className="flex gap-3 justify-center">
          <Button
            variant="secondary"
            onClick={handleKeepDefault}
            className="px-6"
          >
            Keep Default
          </Button>
          <Button
            variant="primary"
            disabled={!canSubmit}
            onClick={handleConfirm}
            className="px-8"
          >
            Confirm Placement
          </Button>
        </div>

        {!canSubmit && (
          <p className="text-center text-red-400 text-xs mt-3">
            {!regularOk && `Regular forces: need ${totalRegular}, have ${placedRegular}. `}
            {!specialOk && `Fedaykin: need ${totalSpecial}, have ${placedSpecial}.`}
          </p>
        )}
      </div>
    </div>
  )
}
