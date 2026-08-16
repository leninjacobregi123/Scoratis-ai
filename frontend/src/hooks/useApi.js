import { useMemo, useCallback } from 'react'
import axios from 'axios'
import { getAccessToken, refreshAccessToken, clearTokens, getRefreshToken } from '../utils/auth'

const API_BASE = '/api'

// Create axios instance once
const instance = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json'
  }
})

instance.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// On a 401, try exactly one refresh-and-retry before giving up and forcing
// a logout (redirect to /login) - avoids infinite retry loops.
instance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retried) {
      original._retried = true
      const newToken = await refreshAccessToken()
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`
        return instance(original)
      }
      // refreshAccessToken() only clears the stored tokens when the refresh
      // was genuinely rejected. If one is still there the failure was
      // transient (backend restarting, network blip) - fail this one request
      // rather than throwing the user out of a session that's still valid.
      if (!getRefreshToken()) {
        clearTokens()
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export function useApi() {
  const get = useCallback(async (endpoint) => {
    const response = await instance.get(endpoint)
    return response.data
  }, [])

  const post = useCallback(async (endpoint, data) => {
    const response = await instance.post(endpoint, data)
    return response.data
  }, [])

  const put = useCallback(async (endpoint, data) => {
    const response = await instance.put(endpoint, data)
    return response.data
  }, [])

  const patch = useCallback(async (endpoint, data) => {
    const response = await instance.patch(endpoint, data)
    return response.data
  }, [])

  const del = useCallback(async (endpoint) => {
    const response = await instance.delete(endpoint)
    return response.data
  }, [])

  return useMemo(
    () => ({ get, post, put, patch, del, delete: del }),
    [get, post, put, patch, del]
  )
}
