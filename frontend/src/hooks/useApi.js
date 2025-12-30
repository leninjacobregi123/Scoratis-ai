import { useMemo, useCallback } from 'react'
import axios from 'axios'

const API_BASE = '/api'

// Create axios instance once
const instance = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json'
  }
})

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

  const del = useCallback(async (endpoint) => {
    const response = await instance.delete(endpoint)
    return response.data
  }, [])

  return useMemo(() => ({ get, post, put, del, delete: del }), [get, post, put, del])
}
