import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The FastAPI backend serves both the JSON API and the product images,
// so proxy them in dev and keep every fetch in the app a relative path.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5180,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/images': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
