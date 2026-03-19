import { useEffect, useRef } from 'react'

/**
 * useWebSocket — keeps a WebSocket connection alive for real-time game updates.
 *
 * @param {string|null} gameId - Connect when truthy, skip when null
 * @param {string|null} playerId - The player's ID (used in the URL for per-player filtering)
 * @param {function} onMessage - Called with parsed GameState on each update
 */
export function useWebSocket(gameId, playerId, onMessage) {
  const wsRef = useRef(null)
  const onMessageRef = useRef(onMessage)

  useEffect(() => {
    onMessageRef.current = onMessage
  }, [onMessage])

  useEffect(() => {
    if (!gameId || !playerId) return

    // Build the WebSocket URL.
    //
    // In development: VITE_WS_URL is not set, so we fall back to the same host.
    //   Vite's proxy forwards /ws/... to ws://localhost:8000/ws/...
    //
    // In production (Vercel + Render): Vercel's serverless rewrites cannot proxy
    //   WebSocket upgrade connections — only HTTP. So we MUST connect directly to
    //   the Render backend. Set VITE_WS_URL=wss://dune-game.onrender.com in the
    //   Vercel environment variables dashboard.
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsBase = import.meta.env.VITE_WS_URL || `${protocol}//${window.location.host}`;
    const url = `${wsBase}/ws/${gameId}/${playerId}`;

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      console.log(`[WebSocket] Connected to game ${gameId} as ${playerId}`)
    }

    ws.onmessage = (event) => {
      try {
        const gameState = JSON.parse(event.data)
        onMessageRef.current(gameState)
      } catch (err) {
        console.warn('[WebSocket] Failed to parse message:', err)
      }
    }

    ws.onclose = (event) => {
      console.log(`[WebSocket] Disconnected (code ${event.code})`)
    }

    ws.onerror = (err) => {
      console.error('[WebSocket] Error:', err)
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [gameId, playerId])
}