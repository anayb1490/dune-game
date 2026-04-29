/**
 * RulesChat — floating RAG-powered Dune rules explainer.
 *
 * A "?" button in the bottom-right corner opens a chat panel.
 * Players type questions in plain English; Gemini answers using the
 * official rulebook.
 *
 * The panel is intentionally self-contained (no global state) so it can
 * be dropped into any layout without prop-drilling.
 */

import { useEffect, useRef, useState } from 'react'

// ---------------------------------------------------------------------------
// Types (JSDoc for autocomplete)
// ---------------------------------------------------------------------------
/**
 * @typedef {{ role: 'user'|'assistant'|'error', text: string, sources?: Array<{page:number,excerpt:string}> }} Message
 */

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SourcePill({ page, excerpt }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <button
      onClick={() => setExpanded(v => !v)}
      className="text-left mt-1 text-[9px] text-sand/60 hover:text-sand/90 transition-colors"
      title={expanded ? 'Collapse' : 'Show excerpt'}
    >
      📖 p.{page}
      {expanded && (
        <span className="block mt-0.5 text-gray-500 italic leading-snug">{excerpt}</span>
      )}
    </button>
  )
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  const isError = msg.role === 'error'

  if (isUser) {
    return (
      <div className="flex justify-end mb-2">
        <div className="bg-sand/20 border border-sand/30 rounded-lg rounded-tr-none px-3 py-2 max-w-[85%]">
          <p className="text-sand-light text-xs leading-relaxed">{msg.text}</p>
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="mb-2">
        <div className="bg-red-950/40 border border-red-800/50 rounded-lg px-3 py-2">
          <p className="text-red-400 text-xs">{msg.text}</p>
        </div>
      </div>
    )
  }

  // assistant
  return (
    <div className="mb-3">
      <div className="bg-[#1a1408] border border-[#3a3020] rounded-lg rounded-tl-none px-3 py-2">
        <p className="text-gray-200 text-xs leading-relaxed whitespace-pre-wrap">{msg.text}</p>
        {msg.sources && msg.sources.length > 0 && (
          <div className="mt-1.5 border-t border-[#3a3020] pt-1.5 flex flex-wrap gap-2">
            {msg.sources.map((s, i) => (
              <SourcePill key={i} page={s.page} excerpt={s.excerpt} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="mb-2">
      <div className="bg-[#1a1408] border border-[#3a3020] rounded-lg rounded-tl-none px-3 py-2 inline-flex items-center gap-1">
        {[0, 1, 2].map(i => (
          <span
            key={i}
            className="w-1.5 h-1.5 bg-sand/50 rounded-full animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function RulesChat() {
  const [open, setOpen] = useState(false)
  /** @type {[Message[], Function]} */
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'Ask me anything about the Dune rules — shipment costs, faction abilities, battle resolution, alliances…',
      sources: [],
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)

  // Scroll to bottom on new messages
  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading, open])

  // Focus input when panel opens
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 80)
  }, [open])

  async function handleSend() {
    const question = input.trim()
    if (!question || loading) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: question }])
    setLoading(true)

    try {
      const res = await fetch('/api/rules/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || 'Request failed')
      }

      const data = await res.json()
      setMessages(prev => [
        ...prev,
        { role: 'assistant', text: data.answer, sources: data.sources },
      ])
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: 'error', text: `Error: ${err.message}` },
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <>
      {/* ── Floating trigger button ─────────────────────────────────────── */}
      <button
        onClick={() => setOpen(v => !v)}
        title="Rules explainer"
        className={`
          fixed bottom-5 right-5 z-40 w-11 h-11 rounded-full
          flex items-center justify-center text-lg font-bold
          shadow-lg transition-all duration-200
          ${open
            ? 'bg-sand text-[#0f0e0b] rotate-45'
            : 'bg-[#1a1408] border border-sand/40 text-sand hover:border-sand hover:bg-[#2a2010]'
          }
        `}
      >
        {open ? '✕' : '?'}
      </button>

      {/* ── Chat panel ──────────────────────────────────────────────────── */}
      {open && (
        <div
          className="
            fixed bottom-20 right-5 z-40
            w-80 flex flex-col
            bg-[#0f0e0b] border border-[#3a3020] rounded-xl
            shadow-2xl overflow-hidden
          "
          style={{ maxHeight: 'min(520px, calc(100vh - 120px))' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-[#3a3020] bg-[#1a1408] shrink-0">
            <div className="flex items-center gap-2">
              <span className="text-sand text-sm">📖</span>
              <span className="text-sand-light text-xs font-bold uppercase tracking-wider">
                Rules Explainer
              </span>
            </div>
            <span className="text-gray-600 text-[9px]">Powered by Gemini</span>
          </div>

          {/* Message list */}
          <div className="flex-1 overflow-y-auto px-3 py-3 min-h-0 space-y-0.5">
            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} />
            ))}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>

          {/* Input row */}
          <div className="shrink-0 border-t border-[#3a3020] p-2 bg-[#0f0e0b] flex gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask a rules question…"
              rows={2}
              disabled={loading}
              className="
                flex-1 resize-none bg-[#1a1408] border border-[#3a3020]
                rounded-lg px-2 py-1.5 text-sand-light text-xs
                placeholder-gray-600 focus:border-sand/60 outline-none
                disabled:opacity-50
              "
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="
                self-end px-3 py-1.5 rounded-lg text-xs font-medium
                bg-sand/20 border border-sand/40 text-sand
                hover:bg-sand/30 disabled:opacity-30 disabled:cursor-not-allowed
                transition-colors shrink-0
              "
            >
              Ask
            </button>
          </div>
        </div>
      )}
    </>
  )
}
