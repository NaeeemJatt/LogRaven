// LogRaven — Vite Configuration
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { normalizeApiBase } from './src/api/normalizeApiBase'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

/** Shared proxy for `vite dev` and `vite preview` so /api and /auth hit the FastAPI backend. */
function createApiProxy(apiTarget: string) {
  const logProxy = (label: string) => (proxy: { on: (ev: string, fn: (...args: unknown[]) => void) => void }) => {
    proxy.on('proxyReq', (_proxyReq, req) => {
      const r = req as { method?: string; url?: string }
      console.log(`\x1b[36m→ ${label}\x1b[0m ${r.method?.padEnd(6)} ${r.url}`)
    })
    proxy.on('proxyRes', (proxyRes, req) => {
      const res = proxyRes as { statusCode?: number }
      const r = req as { method?: string; url?: string }
      const s = res.statusCode ?? 0
      const color = s < 300 ? '\x1b[32m' : s < 500 ? '\x1b[33m' : '\x1b[31m'
      console.log(`\x1b[36m← ${label}\x1b[0m ${color}${s}\x1b[0m ${r.method?.padEnd(6)} ${r.url}`)
    })
  }

  return {
    '/api': {
      target: apiTarget,
      changeOrigin: true,
      configure: logProxy('proxy'),
    },
    '/auth': {
      target: apiTarget,
      changeOrigin: true,
      configure: logProxy('proxy'),
    },
    '/health': { target: apiTarget, changeOrigin: true },
  }
}

export default defineConfig(({ mode }) => {
  // Merge repo-root .env then frontend/.env so VITE_DEV_API_PROXY_TARGET works from either place.
  const repoRoot = path.resolve(__dirname, '..')
  const env = { ...loadEnv(mode, repoRoot, ''), ...loadEnv(mode, __dirname, '') }
  // Prefer 127.0.0.1 on Windows so the dev proxy does not hit ::1 while uvicorn listens on IPv4 only.
  const apiTarget = env.VITE_DEV_API_PROXY_TARGET || 'http://127.0.0.1:8000'
  const apiProxy = createApiProxy(apiTarget)

  return {
    define: {
      // Root .env + frontend/.env merged above; strip mistaken /api/v1 suffix so requests are not doubled.
      'import.meta.env.VITE_API_URL': JSON.stringify(normalizeApiBase(env.VITE_API_URL)),
    },
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: apiProxy,
    },
    preview: {
      proxy: apiProxy,
    },
  }
})
