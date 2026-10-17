import axios, { type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '../store/authStore'
import client from './client'

const originalAdapter = client.defaults.adapter

function response(config: InternalAxiosRequestConfig, data: unknown): AxiosResponse {
  return {
    config,
    data,
    headers: {},
    status: 200,
    statusText: 'OK',
  }
}

afterEach(() => {
  client.defaults.adapter = originalAdapter
  window.history.replaceState({}, '', '/')
  useAuthStore.getState().logout()
  vi.restoreAllMocks()
})

describe('API session refresh', () => {
  it('coalesces concurrent 401 refreshes and retries both requests', async () => {
    const attempts = new Map<string, number>()
    client.defaults.adapter = vi.fn(async (config) => {
      const url = String(config.url)
      const attempt = (attempts.get(url) ?? 0) + 1
      attempts.set(url, attempt)

      if (attempt === 1) {
        return Promise.reject({
          config,
          response: { status: 401 },
        })
      }

      return response(config, { url })
    })

    let finishRefresh!: () => void
    const refresh = new Promise<AxiosResponse>((resolve) => {
      finishRefresh = () => resolve({} as AxiosResponse)
    })
    const refreshSpy = vi.spyOn(axios, 'post').mockImplementation(() => refresh)

    const requests = Promise.all([client.get('/first'), client.get('/second')])

    await vi.waitFor(() => expect(refreshSpy).toHaveBeenCalledTimes(1))
    finishRefresh()

    const results = await requests
    expect(results.map((result) => result.data)).toEqual([{ url: '/first' }, { url: '/second' }])
    expect(attempts).toEqual(
      new Map([
        ['/first', 2],
        ['/second', 2],
      ]),
    )
  })

  it('does not refresh a rejected login request', async () => {
    client.defaults.adapter = vi.fn((config) =>
      Promise.reject({
        config,
        response: { status: 401 },
      }),
    )
    const refreshSpy = vi.spyOn(axios, 'post')

    await expect(client.post('/auth/login')).rejects.toMatchObject({
      response: { status: 401 },
    })
    expect(refreshSpy).not.toHaveBeenCalled()
  })

  it('clears auth state when refreshing the session fails', async () => {
    window.history.replaceState({}, '', '/login')
    useAuthStore.getState().setUser({
      id: 'user-1',
      email: 'analyst@example.com',
      tier: 'pro',
    })
    client.defaults.adapter = vi.fn((config) =>
      Promise.reject({
        config,
        response: { status: 401 },
      }),
    )
    vi.spyOn(axios, 'post').mockRejectedValue(new Error('Refresh failed'))

    await expect(client.get('/protected')).rejects.toMatchObject({
      response: { status: 401 },
    })
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })

  it('does not redirect anonymous public pages when the session probe fails', async () => {
    window.history.replaceState({}, '', '/privacy')
    client.defaults.adapter = vi.fn((config) =>
      Promise.reject({
        config,
        response: { status: 401 },
      }),
    )
    vi.spyOn(axios, 'post').mockRejectedValue(new Error('No refresh cookie'))

    await expect(client.get('/auth/me')).rejects.toMatchObject({
      response: { status: 401 },
    })
    expect(window.location.pathname).toBe('/privacy')
  })

  it('does clear auth when a protected PATCH to /auth/me cannot refresh', async () => {
    window.history.replaceState({}, '', '/login')
    useAuthStore.getState().setUser({
      id: 'user-1',
      email: 'analyst@example.com',
      tier: 'pro',
    })
    client.defaults.adapter = vi.fn((config) =>
      Promise.reject({
        config,
        response: { status: 401 },
      }),
    )
    vi.spyOn(axios, 'post').mockRejectedValue(new Error('Expired'))

    await expect(client.patch('/auth/me', { name: 'Analyst' })).rejects.toMatchObject({
      response: { status: 401 },
    })
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })
})
