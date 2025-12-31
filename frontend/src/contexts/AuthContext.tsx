import React, { createContext, useContext, useState, useEffect } from 'react'
import axios from 'axios'
import { API_URL } from '../config'

interface AuthContextType {
  token: string | null
  username: string | null
  userRole: string | null
  isAdmin: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  loading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [username, setUsername] = useState<string | null>(null)
  const [userRole, setUserRole] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check for saved session
    const savedToken = localStorage.getItem('datatruth_token')
    const savedUsername = localStorage.getItem('datatruth_username')
    const savedRole = localStorage.getItem('datatruth_role')
    
    if (savedToken && savedUsername) {
      setToken(savedToken)
      setUsername(savedUsername)
      setUserRole(savedRole || 'user')
    }
    setLoading(false)
  }, [])

  // Fetch user profile when token exists
  useEffect(() => {
    if (token && !userRole) {
      fetchUserProfile()
    }
  }, [token])

  const fetchUserProfile = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/users/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const role = response.data.role || 'user'
      setUserRole(role)
      localStorage.setItem('datatruth_role', role)
    } catch (err) {
      console.error('Failed to fetch user profile:', err)
      setUserRole('user') // Default to user
    }
  }

  // Add axios interceptor to handle 401 errors
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token is invalid, logout
          logout()
        }
        return Promise.reject(error)
      }
    )

    return () => {
      axios.interceptors.response.eject(interceptor)
    }
  }, [])

  const login = async (username: string, password: string) => {
    const response = await axios.post(`${API_URL}/api/v1/auth/token`, {
      username,
      password,
    })

    const { access_token } = response.data
    setToken(access_token)
    setUsername(username)
    
    localStorage.setItem('datatruth_token', access_token)
    localStorage.setItem('datatruth_username', username)
    
    // Fetch user profile to get role
    try {
      const profileResponse = await axios.get(`${API_URL}/api/v1/users/me`, {
        headers: { 'Authorization': `Bearer ${access_token}` }
      })
      const role = profileResponse.data.role || 'user'
      setUserRole(role)
      localStorage.setItem('datatruth_role', role)
    } catch (err) {
      console.error('Failed to fetch user profile after login:', err)
      setUserRole('user') // Default to user
      localStorage.setItem('datatruth_role', 'user')
    }
  }

  const logout = () => {
    setToken(null)
    setUsername(null)
    setUserRole(null)
    localStorage.removeItem('datatruth_token')
    localStorage.removeItem('datatruth_username')
    localStorage.removeItem('datatruth_role')
  }

  const isAdmin = userRole?.toLowerCase() === 'admin'

  return (
    <AuthContext.Provider value={{ token, username, userRole, isAdmin, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
