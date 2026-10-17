import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { afterEach, describe, expect, it, vi } from 'vitest'
import client from './client'
import { investigationsApi } from './investigations'

const originalAdapter = client.defaults.adapter

afterEach(() => {
  client.defaults.adapter = originalAdapter
  vi.restoreAllMocks()
})

describe('investigations API', () => {
  it('patches the correlation setting with the exact boolean body', async () => {
    let captured: InternalAxiosRequestConfig | undefined
    client.defaults.adapter = vi.fn(async (config) => {
      captured = config
      return {
        config,
        data: {},
        headers: {},
        status: 200,
        statusText: 'OK',
      } satisfies AxiosResponse
    })

    await investigationsApi.update('investigation-1', { correlation_enabled: false })

    expect(captured?.method).toBe('patch')
    expect(captured?.url).toBe('/api/v1/investigations/investigation-1')
    expect(JSON.parse(String(captured?.data))).toEqual({ correlation_enabled: false })
  })
})
