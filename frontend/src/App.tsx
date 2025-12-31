import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { Toaster } from 'react-hot-toast'
import LoginPage from './components/LoginPage'
import HomePage from './components/HomePage'
import ChatInterface from './components/ChatInterface'
import InsightsScreen from './components/InsightsScreen'
import UserManagement from './components/UserManagement'
import SettingsScreen from './components/SettingsScreen'
import AdminPanel from './components/AdminPanel'
import SetupWizard from './components/Setup/SetupWizard'
import SecurityCompliancePage from './components/SecurityCompliancePage'
import PricingPage from './components/PricingPage'
import CaseStudiesPage from './components/CaseStudiesPage'
import TechnologyPage from './components/TechnologyPage'
import RoadmapPage from './components/RoadmapPage'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { API_URL } from './config'

function AppContent() {
  const { token } = useAuth()
  const [setupComplete, setSetupComplete] = useState<boolean | null>(null)
  const [checkingSetup, setCheckingSetup] = useState(true)

  useEffect(() => {
    checkSetupStatus()
  }, [])

  const checkSetupStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/api/setup/status`)
      const data = await response.json()
      setSetupComplete(data.is_configured)
    } catch (error) {
      console.error('Failed to check setup status:', error)
      // Assume setup is needed if check fails
      setSetupComplete(false)
    } finally {
      setCheckingSetup(false)
    }
  }

  // Show loading while checking
  if (checkingSetup) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Checking configuration...</p>
        </div>
      </div>
    )
  }

  // Show setup wizard if not configured
  if (!setupComplete) {
    return <SetupWizard />
  }

  if (!token) {
    return <LoginPage />
  }

  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/workspace" element={<ChatInterface />} />
        <Route path="/insights" element={<InsightsScreen />} />
        <Route path="/users" element={<UserManagement />} />
        <Route path="/settings" element={<SettingsScreen />} />
        <Route path="/admin" element={<AdminPanel />} />
        <Route path="/security" element={<SecurityCompliancePage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/case-studies" element={<CaseStudiesPage />} />
        <Route path="/technology" element={<TechnologyPage />} />
        <Route path="/roadmap" element={<RoadmapPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

function App() {
  return (
    <AuthProvider>
      <Toaster 
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 3000,
            iconTheme: {
              primary: '#10B981',
              secondary: '#fff',
            },
          },
          error: {
            duration: 5000,
            iconTheme: {
              primary: '#EF4444',
              secondary: '#fff',
            },
          },
        }}
      />
      <AppContent />
    </AuthProvider>
  )
}

export default App
