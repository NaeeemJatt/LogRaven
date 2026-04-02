/**
 * VITE_API_URL must be the API server root (scheme + host[:port]) only.
 * API calls use absolute paths like `/api/v1/...`; a base ending in `/api` or `/api/v1`
 * would duplicate that prefix and yield 404 (e.g. .../api/v1/api/v1/play-parser/...).
 */
export function normalizeApiBase(raw: unknown): string {
  if (raw == null || raw === '') return ''
  let u = String(raw).trim()
  if (!u) return ''

  let prev = ''
  while (prev !== u) {
    prev = u
    u = u.replace(/\/+$/, '')
    const versioned = u.match(/^(.*)\/api\/v\d+$/i)
    if (versioned) {
      u = versioned[1]
      continue
    }
    if (u.length >= 4 && u.slice(-4).toLowerCase() === '/api') {
      u = u.slice(0, -4)
      continue
    }
  }

  return u.replace(/\/+$/, '')
}
