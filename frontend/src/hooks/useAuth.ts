// LogRaven — useAuth Hook
// Provides login, logout, and current user from authStore.
// Handles token refresh transparently via Axios interceptor in api/client.ts
// TODO Month 1 Week 1: Implement.

export function useAuth() {
  return { user: null, login: async () => {}, logout: () => {}, isAuthenticated: false }
}
