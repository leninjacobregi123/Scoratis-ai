import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { getAccessToken, setTokens, clearTokens } from '../utils/auth'

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

  const fetchMe = useCallback(async () => {
    const token = getAccessToken()
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const response = await fetch('/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (response.ok) {
        setUser(await response.json())
      } else {
        clearTokens()
        setUser(null)
      }
    } catch {
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

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
  }, [])

  const value = { user, loading, isAuthenticated: !!user, login, signup, logout }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
