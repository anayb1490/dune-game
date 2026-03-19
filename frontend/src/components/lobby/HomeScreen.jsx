import { useState } from 'react'
import Button from '../ui/Button.jsx'

export default function HomeScreen({ onCreateGame, onJoinGame }) {
  const [name, setName] = useState('')
  const [joinCode, setJoinCode] = useState('')
  const [mode, setMode] = useState('basic')
  const [tab, setTab] = useState('create') // 'create' or 'join'

  function handleCreate(e) {
    e.preventDefault()
    if (!name.trim()) return
    onCreateGame(name.trim(), mode)
  }

  function handleJoin(e) {
    e.preventDefault()
    if (!name.trim() || !joinCode.trim()) return
    onJoinGame(name.trim(), joinCode.trim().toUpperCase())
  }

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-60px)]">
      <div className="w-full max-w-md">
        {/* Title */}
        <div className="text-center mb-8">
          <h2 className="text-sand text-3xl font-bold tracking-wider mb-2">DUNE</h2>
          <p className="text-gray-400 text-sm">A Game of Conquest, Diplomacy & Betrayal</p>
        </div>

        {/* Tab switcher */}
        <div className="flex border-b border-[#3a3020] mb-6">
          <button
            onClick={() => setTab('create')}
            className={`flex-1 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === 'create'
                ? 'border-sand text-sand'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            Create Game
          </button>
          <button
            onClick={() => setTab('join')}
            className={`flex-1 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === 'join'
                ? 'border-sand text-sand'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            Join Game
          </button>
        </div>

        {/* Name input (shared) */}
        <div className="mb-4">
          <label className="block text-gray-400 text-xs uppercase tracking-wide mb-1">Your Name</label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="Enter your name"
            className="w-full px-3 py-2 bg-[#1c1a14] border border-[#3a3020] rounded text-gray-200 placeholder-gray-600 focus:outline-none focus:border-sand"
            maxLength={30}
          />
        </div>

        {tab === 'create' ? (
          <form onSubmit={handleCreate}>
            {/* Mode selector */}
            <div className="mb-6">
              <label className="block text-gray-400 text-xs uppercase tracking-wide mb-1">Game Mode</label>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setMode('basic')}
                  className={`flex-1 py-2 px-3 rounded border text-sm ${
                    mode === 'basic'
                      ? 'border-sand text-sand bg-sand/10'
                      : 'border-[#3a3020] text-gray-500 hover:text-gray-300'
                  }`}
                >
                  Basic
                </button>
                <button
                  type="button"
                  onClick={() => setMode('advanced')}
                  className={`flex-1 py-2 px-3 rounded border text-sm ${
                    mode === 'advanced'
                      ? 'border-sand text-sand bg-sand/10'
                      : 'border-[#3a3020] text-gray-500 hover:text-gray-300'
                  }`}
                >
                  Advanced
                </button>
              </div>
            </div>

            <Button type="submit" variant="primary" className="w-full" disabled={!name.trim()}>
              Create Game
            </Button>
          </form>
        ) : (
          <form onSubmit={handleJoin}>
            {/* Join code input */}
            <div className="mb-6">
              <label className="block text-gray-400 text-xs uppercase tracking-wide mb-1">Join Code</label>
              <input
                type="text"
                value={joinCode}
                onChange={e => setJoinCode(e.target.value.toUpperCase())}
                placeholder="ABCD12"
                className="w-full px-3 py-2 bg-[#1c1a14] border border-[#3a3020] rounded text-gray-200 placeholder-gray-600 focus:outline-none focus:border-sand font-mono text-center text-lg tracking-widest"
                maxLength={6}
              />
            </div>

            <Button type="submit" variant="primary" className="w-full" disabled={!name.trim() || !joinCode.trim()}>
              Join Game
            </Button>
          </form>
        )}
      </div>
    </div>
  )
}
