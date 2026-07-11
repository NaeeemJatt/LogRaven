import type { Page, Route } from '@playwright/test'

export const mockUser = {
  id: 'user-1',
  email: 'analyst@example.com',
  tier: 'pro',
  email_verified: true,
}

type ApiHandler = (route: Route, url: URL) => Promise<boolean>

interface MockApiOptions {
  authenticated?: boolean
  handleApi?: ApiHandler
  onLogin?: (credentials: { email: string; password: string }) => void
}

export async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

export async function mockApi(page: Page, options: MockApiOptions = {}) {
  let authenticated = options.authenticated ?? false

  await page.route('**/*', async (route) => {
    const request = route.request()
    const url = new URL(request.url())

    if (url.pathname === '/auth/me') {
      await fulfillJson(
        route,
        authenticated ? mockUser : { detail: 'Not authenticated' },
        authenticated ? 200 : 401,
      )
      return
    }

    if (url.pathname === '/auth/refresh') {
      await fulfillJson(
        route,
        authenticated ? {} : { detail: 'Refresh token required' },
        authenticated ? 200 : 401,
      )
      return
    }

    if (url.pathname === '/auth/login' && request.method() === 'POST') {
      const credentials = request.postDataJSON() as { email: string; password: string }
      options.onLogin?.(credentials)
      authenticated = true
      await fulfillJson(route, { token_type: 'bearer', user: mockUser })
      return
    }

    if (options.handleApi && (await options.handleApi(route, url))) {
      return
    }

    if (url.pathname === '/api/v1/meta/stats') {
      await fulfillJson(route, {
        detection_rules: 2_000,
        log_formats: 5,
        mitre_techniques: 300,
      })
      return
    }

    if (url.pathname === '/api/v1/investigations' && request.method() === 'GET') {
      await fulfillJson(route, [])
      return
    }

    if (url.pathname.startsWith('/api/')) {
      await fulfillJson(route, { detail: `Unmocked request: ${url.pathname}` }, 404)
      return
    }

    await route.continue()
  })
}
