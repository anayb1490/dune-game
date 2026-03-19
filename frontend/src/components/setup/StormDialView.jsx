import { useState } from 'react'
import Button from '../ui/Button.jsx'

export default function StormDialView({ gameState, playerId, onSubmitDial }) {
  const [number, setNumber] = useState(10)
  const setup = gameState?.setup_state
  if (!setup) return null

  const isDialPlayer = setup.storm_dial_players?.includes(playerId)
  const hasSubmitted = playerId in (setup.storm_dial_submissions || {})
  const submittedCount = Object.keys(setup.storm_dial_submissions || {}).length

  function handleSubmit() {
    onSubmitDial(number)
  }

  // Not a dial player — just wait
  if (!isDialPlayer) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-60px)]">
        <div className="text-center">
          <h2 className="text-sand text-2xl font-bold mb-4">Storm Placement</h2>
          <p className="text-gray-400 mb-2">Two players are secretly dialing the storm position...</p>
          <p className="text-gray-500 text-sm">{submittedCount} / 2 submitted</p>
        </div>
      </div>
    )
  }

  // Already submitted — wait for the other player
  if (hasSubmitted) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-60px)]">
        <div className="text-center">
          <h2 className="text-sand text-2xl font-bold mb-4">Number Submitted</h2>
          <p className="text-gray-400 mb-2">Waiting for the other player to submit their number...</p>
          <p className="text-gray-500 text-sm">{submittedCount} / 2 submitted</p>
        </div>
      </div>
    )
  }

  // Show the dial
  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-60px)]">
      <div className="w-full max-w-sm">
        <div className="text-center mb-6">
          <h2 className="text-sand text-2xl font-bold mb-2">Storm Dial</h2>
          <p className="text-gray-400 text-sm">
            Secretly choose a number from 0 to 20. Both players' numbers will be
            added together to determine where the storm starts.
          </p>
        </div>

        {/* Number display */}
        <div className="text-center mb-4">
          <span className="text-sand text-6xl font-bold font-mono">{number}</span>
        </div>

        {/* Slider */}
        <div className="mb-6 px-4">
          <input
            type="range"
            min={0}
            max={20}
            value={number}
            onChange={e => setNumber(parseInt(e.target.value))}
            className="w-full accent-[#c9a84c]"
          />
          <div className="flex justify-between text-xs text-gray-600 mt-1">
            <span>0</span>
            <span>10</span>
            <span>20</span>
          </div>
        </div>

        <div className="text-center">
          <Button variant="primary" onClick={handleSubmit} className="px-8">
            Submit Number
          </Button>
        </div>
      </div>
    </div>
  )
}
