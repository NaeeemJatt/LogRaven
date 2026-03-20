// LogRaven — Vite Configuration
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq, req) => {
            console.log(`\x1b[36m→ proxy\x1b[0m ${req.method?.padEnd(6)} ${req.url}`)
          })
          proxy.on('proxyRes', (proxyRes, req) => {
            const s = proxyRes.statusCode ?? 0
            const color = s < 300 ? '\x1b[32m' : s < 500 ? '\x1b[33m' : '\x1b[31m'
            console.log(`\x1b[36m← proxy\x1b[0m ${color}${s}\x1b[0m ${req.method?.padEnd(6)} ${req.url}`)
          })
        },
      },
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq, req) => {
            console.log(`\x1b[36m→ proxy\x1b[0m ${req.method?.padEnd(6)} ${req.url}`)
          })
          proxy.on('proxyRes', (proxyRes, req) => {
            const s = proxyRes.statusCode ?? 0
            const color = s < 300 ? '\x1b[32m' : s < 500 ? '\x1b[33m' : '\x1b[31m'
            console.log(`\x1b[36m← proxy\x1b[0m ${color}${s}\x1b[0m ${req.method?.padEnd(6)} ${req.url}`)
          })
        },
      },
      '/files': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})

