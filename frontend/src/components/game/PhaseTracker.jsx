/**
 * PhaseTracker — compact phase list showing the current phase.
 */

const PHASES = [
  { key: 'storm',                   label: 'I. Storm' },
  { key: 'spice_blow',              label: 'II. Spice Blow' },
  { key: 'nexus',                   label: 'II½. Nexus', optional: true },
  { key: 'choam_charity',           label: 'III. CHOAM Charity' },
  { key: 'bidding',                 label: 'IV. Bidding' },
  { key: 'revival',                 label: 'V. Revival' },
  { key: 'shipment_and_movement',   label: 'VI. Ship & Move' },
  { key: 'battle',                  label: 'VII. Battle' },
  { key: 'spice_collection',        label: 'VIII. Spice Collect' },
  { key: 'mentat_pause',            label: 'IX. Mentat Pause' },
]

export default function PhaseTracker({ currentPhase }) {
  return (
    <div className="bg-surface border border-[#3a3020] rounded p-2">
      <h2 className="text-sand text-[10px] font-bold uppercase tracking-widest mb-1 px-1">Phases</h2>
      <ol className="space-y-px">
        {PHASES.map((phase) => {
          const isActive = phase.key === currentPhase
          return (
            <li
              key={phase.key}
              className={`text-xs px-2 py-1 rounded transition-colors ${
                isActive
                  ? 'bg-sand text-black font-bold'
                  : phase.optional
                    ? 'text-gray-600 italic'
                    : 'text-gray-500'
              }`}
            >
              {phase.label}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
