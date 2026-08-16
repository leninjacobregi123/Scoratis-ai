import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Local-machine-only override: port 8000 is occupied by an unrelated project
// on this dev box, so the Scoratis backend runs on 8001 here instead.
// Intentionally NOT committed - every other environment (and production,
// which doesn't use this dev proxy at all) uses the default 8000 above.
const BACKEND_URL = 'http://localhost:8001'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: BACKEND_URL,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/auth': {
        target: BACKEND_URL,
        changeOrigin: true
      },
      '/chat': {
        target: BACKEND_URL,
        changeOrigin: true
      },
      '/agent': {
        target: BACKEND_URL,
        changeOrigin: true
      },
      '/subjects': {
        target: BACKEND_URL,
        changeOrigin: true
      },
      '/v1': {
        target: BACKEND_URL,
        changeOrigin: true
      },
      '/health': {
        target: BACKEND_URL,
        changeOrigin: true
      },
      '/generated_videos': {
        target: BACKEND_URL,
        changeOrigin: true
      },
      '/audio': {
        target: BACKEND_URL,
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})
