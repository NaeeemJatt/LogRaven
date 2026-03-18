// LogRaven — useAuth Hook
import { useNavigate } from 'react-router-dom'
import { authApi } from '../api/auth'
import { useAuthStore } from '../store/authStore'

export function useAuth() {
  const store = useAuthStore()
  const navigate = useNavigate()

  const login = async (email: string, password: string) => {
    const res = await authApi.login(email, password)
    store.setTokens(res.data.access_token, res.data.refresh_token)
    const me = await authApi.me()
    store.setUser(me.data)
    navigate('/dashboard')
  }

  const register = async (email: string, password: string) => {
    const res = await authApi.register(email, password)
    store.setTokens(res.data.access_token, res.data.refresh_token)
    const me = await authApi.me()
    store.setUser(me.data)
    navigate('/dashboard')
  }

  const logout = () => {
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
