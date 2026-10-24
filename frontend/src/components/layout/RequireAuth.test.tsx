import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authApi } from '../../api/auth'
import { useAuthStore, type AuthUser } from '../../store/authStore'
import RequireAuth from './RequireAuth'

vi.mock('../../api/auth', () => ({
  authApi: { me: vi.fn() },
}))

const user: AuthUser = {
  id: 'user-1',
  email: 'analyst@example.com',
  tier: 'pro',
}

function renderProtectedRoute() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route
            path="/protected"
            element={
              <RequireAuth>
                <p>Protected content</p>
              </RequireAuth>
            }
          />
          <Route path="/login" element={<p>Login page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('RequireAuth', () => {
  beforeEach(() => {
    vi.mocked(authApi.me).mockReset()
    useAuthStore.getState().logout()
  })

  it('renders protected content after server verification', async () => {
    vi.mocked(authApi.me).mockResolvedValue({ data: user } as Awaited<
      ReturnType<typeof authApi.me>
    >)

    renderProtectedRoute()

    expect(await screen.findByText('Protected content')).toBeInTheDocument()
    expect(useAuthStore.getState().user).toEqual(user)
  })

  it('redirects to login and clears stale auth after verification fails', async () => {
    useAuthStore.getState().setUser(user)
    vi.mocked(authApi.me).mockRejectedValue(new Error('Unauthorized'))

    renderProtectedRoute()

    expect(await screen.findByText('Login page')).toBeInTheDocument()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })

  it('redirects to login when /auth/me returns an HTML string instead of a valid user', async () => {
    vi.mocked(authApi.me).mockResolvedValue({
      data: '<!doctype html><html><body>Error</body></html>',
    } as unknown as Awaited<ReturnType<typeof authApi.me>>)

    renderProtectedRoute()

    expect(await screen.findByText('Login page')).toBeInTheDocument()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })
})
