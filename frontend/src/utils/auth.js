// Shared JWT storage, framework-agnostic so both the axios instance in
// useApi.js and the raw fetch() calls in Chat.jsx/LLMSwitcher.jsx can attach
// the same Authorization header without threading React context into
// non-component modules.
const ACCESS_TOKEN_KEY = 'scoratis_access_token'
const REFRESH_TOKEN_KEY = 'scoratis_refresh_token'

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setTokens({ access_token, refresh_token }) {
  if (access_token) localStorage.setItem(ACCESS_TOKEN_KEY, access_token)
  if (refresh_token) localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token)
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function getAuthHeaders() {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// Refreshes the access token using the stored refresh token. Returns the new
// access token on success, or null if the refresh token is missing/invalid
// (callers should treat null as "log the user out").
export async function refreshAccessToken() {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return null

  try {
    const response = await fetch('/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!response.ok) {
      clearTokens()
      return null
    }
    const data = await response.json()
    setTokens(data)
    return data.access_token
  } catch {
    clearTokens()
    return null
  }
}
