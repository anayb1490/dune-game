import { useEffect, useRef } from 'react'

// Colour-code log entries by keywords in the message
function entryColor(msg) {
  const m = msg.toLowerCase()
  if (m.includes('storm'))                          return 'text-blue-300'
  if (m.includes('shai-hulud') || m.includes('worm')) return 'text-orange-400'
  if (m.includes('lost') || m.includes('destroy'))  return 'text-red-400'
  if (m.includes('spice blow') || m.includes('spice placed')) return 'text-yellow-400'
  if (m.includes('collects') || m.includes('receives')) return 'text-green-400'
  if (m.includes('no faction') || m.includes('no spice') || m.includes('no winner')) return 'text-gray-500'
  return 'text-gray-300'
}

// Small bullet colored by entry type
function entryIcon(msg) {
  const m = msg.toLowerCase()
  if (m.includes('storm'))                             return '🌪'
  if (m.includes('shai-hulud') || m.includes('worm')) return '🐛'
  if (m.includes('lost') || m.includes('destroy'))    return '💀'
  if (m.includes('spice'))                             return '◆'
  if (m.includes('collects') || m.includes('receives')) return '+'
  return '›'
}

export default function GameLog({ entries = [] }) {
  const bottomRef = useRef(null)

  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [entries.length])

  if (entries.length === 0) return null

  // Show last 30 entries
  const visible = entries.slice(-30)

  return (
    <div className="bg-surface border border-[#3a3020] rounded p-2">
      <p className="text-gray-500 text-[10px] uppercase tracking-wider mb-1 px-1">Event Log</p>
      <div className="overflow-y-auto max-h-36 space-y-0.5 pr-1">
        {visible.map((msg, i) => (
          <div key={i} className={`flex gap-1.5 items-baseline text-xs leading-snug ${entryColor(msg)}`}>
            <span className="shrink-0 text-[10px] opacity-60">{entryIcon(msg)}</span>
            <span>{msg}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
