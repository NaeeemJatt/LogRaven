import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authApi } from '../../api/auth'
import { useAuthStore, type AuthUser } from '../../store/authStore'
import AuthBootstrap from './AuthBootstrap'

vi.mock('../../api/auth', () => ({
  authApi: { me: vi.fn() },
}))

const user: AuthUser = {
  id: 'user-1',
  email: 'analyst@example.com',
  tier: 'pro',
}

describe('AuthBootstrap', () => {
  beforeEach(() => {
    vi.mocked(authApi.me).mockReset()
    useAuthStore.getState().logout()
  })

  it('restores the authenticated user before rendering children', async () => {
    vi.mocked(authApi.me).mockResolvedValue({ data: user } as Awaited<
      ReturnType<typeof authApi.me>
    >)

    render(
      <AuthBootstrap>
        <p>Application ready</p>
      </AuthBootstrap>,
    )

    expect(screen.queryByText('Application ready')).not.toBeInTheDocument()
    expect(await screen.findByText('Application ready')).toBeInTheDocument()
    expect(useAuthStore.getState()).toMatchObject({
      user,
      isAuthenticated: true,
    })
  })

  it('clears stale auth state when the session cannot be restored', async () => {
    useAuthStore.getState().setUser(user)
    vi.mocked(authApi.me).mockRejectedValue(new Error('Unauthorized'))

    render(
      <AuthBootstrap>
        <p>Application ready</p>
      </AuthBootstrap>,
    )

    expect(await screen.findByText('Application ready')).toBeInTheDocument()
    expect(useAuthStore.getState()).toMatchObject({
      user: null,
      isAuthenticated: false,
    })
  })

  it('clears auth state when the session returns an HTML fallback string', async () => {
    vi.mocked(authApi.me).mockResolvedValue({
      data: '<!doctype html><html><body>Error</body></html>',
    } as unknown as Awaited<ReturnType<typeof authApi.me>>)

    render(
      <AuthBootstrap>
        <p>Application ready</p>
      </AuthBootstrap>,
    )

    expect(await screen.findByText('Application ready')).toBeInTheDocument()
    expect(useAuthStore.getState()).toMatchObject({
      user: null,
      isAuthenticated: false,
    })
  })
})
