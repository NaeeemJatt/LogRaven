import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authApi } from '../api/auth'
import { useAuthStore } from '../store/authStore'
import { useAuth } from './useAuth'

const navigate = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal<typeof import('react-router-dom')>()),
  useNavigate: () => navigate,
}))

vi.mock('../api/auth', () => ({
  authApi: {
    login: vi.fn(),
    register: vi.fn(),
    me: vi.fn(),
    logout: vi.fn(),
  },
}))

const user = { id: 'user-1', email: 'analyst@example.com', tier: 'pro' }

describe('useAuth', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
    navigate.mockReset()
  })

  it('logs in with the user returned by the session endpoint', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ data: { token_type: 'bearer', user } } as never)
    const { result } = renderHook(() => useAuth())

    await act(() => result.current.login(user.email, 'password-123'))

    expect(useAuthStore.getState().user).toEqual(user)
    expect(navigate).toHaveBeenCalledWith('/dashboard')
  })

  it('loads the current user when login omits it', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ data: { token_type: 'bearer' } } as never)
    vi.mocked(authApi.me).mockResolvedValue({ data: user } as never)
    const { result } = renderHook(() => useAuth())

    await act(() => result.current.login(user.email, 'password-123'))

    expect(authApi.me).toHaveBeenCalledOnce()
    expect(useAuthStore.getState().user).toEqual(user)
  })

  it('registers and stores the returned user', async () => {
    vi.mocked(authApi.register).mockResolvedValue({ data: { token_type: 'bearer', user } } as never)
    const { result } = renderHook(() => useAuth())

    await act(() => result.current.register(user.email, 'password-123'))

    expect(useAuthStore.getState().user).toEqual(user)
    expect(navigate).toHaveBeenCalledWith('/dashboard')
  })

  it('clears local state even when server logout fails', async () => {
    useAuthStore.getState().setUser(user)
    vi.mocked(authApi.logout).mockRejectedValue(new Error('offline'))
    const { result } = renderHook(() => useAuth())

    await act(() => result.current.logout())

    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(navigate).toHaveBeenCalledWith('/login')
  })
})
