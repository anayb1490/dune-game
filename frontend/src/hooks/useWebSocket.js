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

    const url = `ws://${window.location.host}/ws/${gameId}/${playerId}`
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
