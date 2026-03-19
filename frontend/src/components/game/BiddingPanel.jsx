import { useState } from 'react'
import Button from '../ui/Button.jsx'

const CARD_TYPE_LABELS = {
  weapon: { label: 'Weapon', style: 'text-red-400 bg-red-950/40 border-red-800' },
  defense: { label: 'Defense', style: 'text-blue-400 bg-blue-950/40 border-blue-800' },
  special: { label: 'Special', style: 'text-purple-400 bg-purple-950/40 border-purple-800' },
  worthless: { label: 'Worthless', style: 'text-gray-500 bg-gray-900/40 border-gray-700' },
}

const FACTION_LABELS = {
  atreides: 'Atreides', harkonnen: 'Harkonnen', bene_gesserit: 'Bene Gesserit',
  fremen: 'Fremen', spacing_guild: 'Guild', emperor: 'Emperor',
}

export default function BiddingPanel({ biddingState, players, playerId, onPlaceBid, onPassBid }) {
  const [bidAmount, setBidAmount] = useState(1)
  if (!biddingState) return null

  const {
    cards_up_for_bid, current_card_index,
    current_high_bidder, current_high_bid,
    current_bidder, factions_passed,
  } = biddingState

  const currentBidderPlayer = players.find(p => p.faction === current_bidder)
  const minBid = current_high_bid + 1
  const isMyTurn = currentBidderPlayer?.id === playerId

  function handleBid() {
    if (isMyTurn && bidAmount >= minBid) {
      onPlaceBid(bidAmount)
      setBidAmount(minBid + 1)
    }
  }

  function handlePass() {
    if (isMyTurn) onPassBid()
  }

  if (bidAmount < minBid) setBidAmount(minBid)

  return (
    <div className="bg-surface border border-[#3a3020] rounded p-2 space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between px-1">
        <h2 className="text-sand text-xs font-bold uppercase tracking-wider">Auction</h2>
        <span className="text-gray-500 text-[10px]">{current_card_index + 1}/{cards_up_for_bid.length}</span>
      </div>

      {/* Card — face-down during auction (identity hidden) */}
      <div className="border border-[#3a3020] rounded p-3 text-center bg-[#1a1810]">
        <div className="text-2xl mb-1 opacity-60">?</div>
        <p className="text-gray-400 text-xs italic">Treachery Card</p>
        <p className="text-gray-600 text-[10px] mt-1">Card identity is hidden</p>
      </div>

      {/* Bid status */}
      <div className="grid grid-cols-2 gap-1.5">
        <div className="border border-[#3a3020] rounded p-1.5 text-center">
          <p className="text-gray-500 text-[10px] uppercase">High</p>
          <p className="text-spice text-sm font-mono font-bold">
            {current_high_bid > 0 ? `◆${current_high_bid}` : '—'}
          </p>
          {current_high_bidder && (
            <p className="text-gray-400 text-[10px]">{FACTION_LABELS[current_high_bidder]}</p>
          )}
        </div>
        <div className="border border-[#3a3020] rounded p-1.5 text-center">
          <p className="text-gray-500 text-[10px] uppercase">Bidding</p>
          <p className="text-sand-light text-xs font-bold">{FACTION_LABELS[current_bidder]}</p>
          <p className="text-gray-500 text-[10px]">◆{currentBidderPlayer?.spice ?? 0}</p>
        </div>
      </div>

      {/* Controls */}
      <div className="space-y-1.5">
        {isMyTurn ? (
          <>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={minBid}
                max={currentBidderPlayer?.spice ?? 0}
                value={bidAmount}
                onChange={(e) => setBidAmount(Math.max(minBid, parseInt(e.target.value) || minBid))}
                className="bg-[#0f0e0b] border border-[#3a3020] rounded px-2 py-1 text-sand-light text-xs font-mono w-16 focus:border-sand outline-none"
              />
              <span className="text-gray-500 text-[10px]">min {minBid}</span>
            </div>
            <div className="flex gap-1.5">
              <Button onClick={handleBid} disabled={bidAmount > (currentBidderPlayer?.spice ?? 0)} className="text-xs flex-1 py-1">
                Bid ◆{bidAmount}
              </Button>
              <Button onClick={handlePass} variant="secondary" className="text-xs flex-1 py-1">
                Pass
              </Button>
            </div>
          </>
        ) : (
          <p className="text-gray-500 text-[10px] text-center py-1">
            Waiting for {FACTION_LABELS[current_bidder] ?? current_bidder} to bid...
          </p>
        )}
      </div>

      {factions_passed.length > 0 && (
        <p className="text-gray-600 text-[10px] border-t border-[#3a3020] pt-1">
          Passed: {factions_passed.map(f => FACTION_LABELS[f] ?? f).join(', ')}
        </p>
      )}
    </div>
  )
}
