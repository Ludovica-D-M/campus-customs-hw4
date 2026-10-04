import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export type User = {
  id: number
  name: string
  first_name: string | null
  last_name: string | null
  email: string
  created_at: string
}

type AuthValue = {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (fields: RegisterFields) => Promise<void>
  logout: () => Promise<void>
}

export type RegisterFields = {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

const AuthContext = createContext<AuthValue | null>(null)

/** Pull a readable message out of FastAPI's error shapes. */
async function errorMessage(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg
  } catch {
    /* fall through */
  }
  return fallback
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // Ask the server who we are on first load — the session lives in an
  // HttpOnly cookie, so JavaScript cannot read it directly.
  useEffect(() => {
    fetch('/api/auth/me', { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : { user: null }))
      .then((data) => setUser(data.user))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      credentials: 'include',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) throw new Error(await errorMessage(res, 'We could not sign you in.'))
    setUser((await res.json()).user)
  }, [])

  const register = useCallback(async (fields: RegisterFields) => {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      credentials: 'include',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(fields),
    })
    if (!res.ok) throw new Error(await errorMessage(res, 'We could not create your account.'))
    setUser((await res.json()).user)
  }, [])

  const logout = useCallback(async () => {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>')
  return value
}

/** First name when we have one, otherwise the first word of the display name. */
export function greetingName(user: User): string {
  return user.first_name?.trim() || user.name.split(' ')[0] || user.email
}
