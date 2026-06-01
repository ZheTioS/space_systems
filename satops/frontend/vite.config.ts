import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const backendUrl = process.env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // `ws: true` is essential — without it, WebSocket upgrade requests to
      // `/api/sdr/audio` (and any other /api WS endpoint) silently fail.
      '/api': { target: backendUrl, ws: true, changeOrigin: true },
    },
  },
})
