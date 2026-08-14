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
// access token on success, or null if the refresh could not be completed
// (callers should treat null as "this request failed").
//
// Only an actual credential rejection (401/403) clears the stored tokens.
// A network error or a 5xx means the SERVER is unavailable, not that the
// refresh token is bad - wiping credentials there logs the user out for
// what is usually a few seconds of backend downtime (a restart, a deploy),
// and they lose their session with no way to tell why. Those cases keep the
// tokens so the next attempt can succeed.
export async function refreshAccessToken() {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return null

  let response
  try {
    response = await fetch('/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
  } catch {
    return null // network/server unreachable - keep credentials, retry later
  }

  if (response.status === 401 || response.status === 403) {
    clearTokens() // genuinely rejected - this session is over
    return null
  }
  if (!response.ok) {
    return null // 5xx etc - transient, keep credentials
  }

  try {
    const data = await response.json()
    setTokens(data)
    return data.access_token
  } catch {
    return null
  }
}
