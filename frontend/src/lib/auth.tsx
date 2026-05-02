/* eslint-disable react-refresh/only-export-components, react-hooks/set-state-in-effect */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { apiFetch, getToken, setToken } from '@/lib/api'

export interface CurrentUser {
  id: string
  email: string
  full_name: string | null
  first_name: string | null
  last_name: string | null
  is_active: boolean
  is_admin: boolean
  abilities: string[]
}

interface AuthContextValue {
  user: CurrentUser | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
  /** Returns true if the user is an admin or has the named ability explicitly granted. */
  hasAbility: (key: string) => boolean
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const me = await apiFetch<CurrentUser>('/auth/me')
      setUser(me)
    } catch {
      setToken(null)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const login = useCallback(async (email: string, password: string) => {
    const form = new URLSearchParams()
    form.set('username', email)
    form.set('password', password)
    const { access_token } = await apiFetch<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: form,
    })
    setToken(access_token)
    const me = await apiFetch<CurrentUser>('/auth/me')
    setUser(me)
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  const hasAbility = useCallback(
    (key: string) => {
      if (!user) return false
      if (user.is_admin) return true
      return user.abilities.includes(key)
    },
    [user],
  )

  const value = useMemo(
    () => ({ user, loading, login, logout, refresh, hasAbility }),
    [user, loading, login, logout, refresh, hasAbility],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
