// LogRaven — useAuth Hook
import { useNavigate } from 'react-router-dom'
import { authApi } from '../api/auth'
import { useAuthStore } from '../store/authStore'

export function useAuth() {
  const store = useAuthStore()
  const navigate = useNavigate()

  const login = async (email: string, password: string) => {
    const response = await authApi.login(email, password)
    if (response.data.user) {
      store.setUser(response.data.user)
    } else {
      const me = await authApi.me()
      store.setUser(me.data)
    }
    navigate('/dashboard')
  }

  const register = async (email: string, password: string) => {
    const response = await authApi.register(email, password)
    if (response.data.user) {
      store.setUser(response.data.user)
    } else {
      const me = await authApi.me()
      store.setUser(me.data)
    }
    navigate('/dashboard')
  }

  const logout = async () => {
    try {
      await authApi.logout()
    } catch {
      /* still clear client state */
    }
    store.logout()
    navigate('/login')
  }

  return {
    user: store.user,
    isAuthenticated: store.isAuthenticated,
    login,
    register,
    logout,
  }
}
