// vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/gmail': 'http://localhost:8000',
      '/oauth2': 'http://localhost:8000'
    }
  }
})
