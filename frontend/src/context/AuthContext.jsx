import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { getAccessToken, setTokens, clearTokens, refreshAccessToken, getRefreshToken } from '../utils/auth'

const AuthContext = createContext(null)

async function parseErrorDetail(response) {
  try {
    const data = await response.json()
    if (typeof data.detail === 'string') return data.detail
    if (data.detail?.message) return data.detail.message
    return 'Request failed'
  } catch {
    return 'Request failed'
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Bootstraps the session on app load. This runs on every mount, so it is
  // the single most important place NOT to over-react to a failure: the dev
  // proxy turns an unreachable backend into a 500 (the request resolves, it
  // doesn't throw), so a blanket `else { clearTokens() }` here silently ends
  // a perfectly valid session every time the backend restarts.
  //
  // Only a genuine credential rejection ends the session, and a 401 gets one
  // refresh attempt first - the access token is short-lived (30min) and
  // expiring mid-session is normal, not a reason to log anyone out.
  const fetchMe = useCallback(async () => {
    const token = getAccessToken()
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }

    const requestMe = (bearer) =>
      fetch('/auth/me', { headers: { Authorization: `Bearer ${bearer}` } })

    try {
      let response = await requestMe(token)

      if (response.status === 401) {
        const newToken = await refreshAccessToken()
        if (newToken) {
          response = await requestMe(newToken)
        }
      }

      if (response.ok) {
        setUser(await response.json())
      } else if (response.status === 401 || response.status === 403) {
        clearTokens() // credentials really are dead
        setUser(null)
      } else {
        // 5xx / proxy error - backend is down, not the session. Keep the
        // tokens so the next mount recovers once it's back.
        setUser(null)
      }
    } catch {
      // Network-level failure - same reasoning, keep credentials.
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMe()
  }, [fetchMe])

  const login = useCallback(async (usernameOrEmail, password) => {
    const body = new URLSearchParams()
    body.set('username', usernameOrEmail)
    body.set('password', password)

    const response = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    })
    if (!response.ok) {
      throw new Error(await parseErrorDetail(response))
    }
    const tokens = await response.json()
    setTokens(tokens)
    await fetchMe()
  }, [fetchMe])

  const signup = useCallback(async (username, email, password) => {
    const response = await fetch('/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password }),
    })
    if (!response.ok) {
      throw new Error(await parseErrorDetail(response))
    }
    const tokens = await response.json()
    setTokens(tokens)
    await fetchMe()
  }, [fetchMe])

  const loginWithGoogle = useCallback(async (credential) => {
    const response = await fetch('/auth/google', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential }),
    })
    if (!response.ok) {
      throw new Error(await parseErrorDetail(response))
    }
    const tokens = await response.json()
    setTokens(tokens)
    await fetchMe()
  }, [fetchMe])

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
  }, [])

  const value = { user, loading, isAuthenticated: !!user, login, signup, loginWithGoogle, logout }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
