import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Get API target from environment or default to localhost
const API_TARGET = process.env.VITE_API_TARGET || 'http://localhost:8000'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/auth': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/openapi.json': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
})

