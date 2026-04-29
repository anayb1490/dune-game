/**
 * PhaseMessagesPanel — displays ephemeral phase_messages from the server.
 *
 * These messages describe what just happened during an automated phase
 * (storm damage, spice blow results, CHOAM charity, spice collection, etc.).
 * They are cleared by the server each time the phase advances.
 */

function msgColor(msg) {
  const m = msg.toLowerCase()
  if (m.includes('storm') || m.includes('destroyed'))    return 'text-blue-300'
  if (m.includes('shai-hulud') || m.includes('worm'))    return 'text-orange-400'
  if (m.includes('killed') || m.includes('loses'))       return 'text-red-400'
  if (m.includes('spice blow') || m.includes('spice placed')) return 'text-yellow-400'
  if (m.includes('collects') || m.includes('receives') || m.includes('charity')) return 'text-green-400'
  if (m.includes('no spice') || m.includes('no faction') || m.includes('no forces')) return 'text-gray-500'
  return 'text-sand-light'
}

function msgIcon(msg) {
  const m = msg.toLowerCase()
  if (m.includes('storm') || m.includes('destroyed'))    return '🌪'
  if (m.includes('shai-hulud') || m.includes('worm'))   return '🐛'
  if (m.includes('killed') || m.includes('loses'))      return '💀'
  if (m.includes('spice blow'))                         return '◆'
  if (m.includes('collects') || m.includes('receives') || m.includes('charity')) return '✦'
  return '›'
}

export default function PhaseMessagesPanel({ messages = [] }) {
  if (!messages || messages.length === 0) return null

  return (
    <div className="bg-surface border border-sand/30 rounded p-2 space-y-1">
      <p className="text-sand text-[10px] uppercase tracking-wider px-1 font-bold">
        Phase Results
      </p>
      <div className="space-y-0.5">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-1.5 items-baseline text-[11px] leading-snug ${msgColor(msg)}`}
          >
            <span className="shrink-0 text-[10px] opacity-70">{msgIcon(msg)}</span>
            <span>{msg}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
