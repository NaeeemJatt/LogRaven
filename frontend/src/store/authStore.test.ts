import { beforeEach, describe, expect, it } from 'vitest'
import { queryClient } from '../queryClient'
import { useAuthStore } from './authStore'

describe('authStore', () => {
  beforeEach(() => useAuthStore.getState().logout())

  it('derives authentication from the current user', () => {
    const user = { id: 'user-1', email: 'analyst@example.com', tier: 'pro' }

    useAuthStore.getState().setUser(user)

    expect(useAuthStore.getState()).toMatchObject({ user, isAuthenticated: true })
  })

  it('clears the authenticated session', () => {
    useAuthStore.getState().setUser({ id: 'user-1', email: 'analyst@example.com', tier: 'free' })

    useAuthStore.getState().logout()

    expect(useAuthStore.getState()).toMatchObject({ user: null, isAuthenticated: false })
  })

  it('clears cached tenant data when the identity changes', () => {
    useAuthStore.getState().setUser({ id: 'user-1', email: 'a@example.com', tier: 'free' })
    queryClient.setQueryData(['findings', 'user-1'], [{ id: 'secret-a' }])

    useAuthStore.getState().setUser({ id: 'user-2', email: 'b@example.com', tier: 'free' })

    expect(queryClient.getQueryData(['findings', 'user-1'])).toBeUndefined()
  })
})
