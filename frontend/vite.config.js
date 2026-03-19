import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite is our development server and build tool.
//
// The proxy section solves the CORS problem during development:
// Instead of your React app (localhost:5173) calling localhost:8000
// directly (which the browser would block), it calls itself at /api/...
// and Vite silently forwards those requests to FastAPI.
//
// From the browser's perspective, everything is on the same origin.

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // REST API calls: /api/... → http://localhost:8000/api/...
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // WebSocket connections: /ws/... → ws://127.0.0.1:8000/ws/...
      '/ws': {
        target: 'http://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
        // Suppress ECONNRESET noise from stale WS tunnels during broadcasts
        configure: (proxy) => {
          proxy.on('error', (err) => {
            if (err.code !== 'ECONNRESET') {
              console.error('[ws proxy]', err)
            }
          })
        },
      },
    },
  },
})
