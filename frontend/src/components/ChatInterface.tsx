import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import QualityDashboard from './QualityDashboard'
import FuzzyMatchTester from './FuzzyMatchTester'
import SearchAndAsk from './SearchAndAsk'
import ConnectionManager from './ConnectionManager'
import SchemaExplorer from './SchemaExplorer'
import SemanticLayer from './SemanticLayer'

type SectionType = 'visualization' | 'configuration'
type VisualizationTabType = 'search' | 'quality' | 'matching'
type ConfigurationTabType = 'connections' | 'schema' | 'semantic'

export default function ChatInterface() {
  const { username, logout, isAdmin } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  
  // Initialize section from URL parameter
  const initialSection = (searchParams.get('section') as SectionType) || 'visualization'
  
  // Block non-admin users from accessing configuration
  useEffect(() => {
    if (initialSection === 'configuration' && !isAdmin) {
      navigate('/workspace?section=visualization')
    }
  }, [initialSection, isAdmin, navigate])
  
  const [activeSection] = useState<SectionType>(initialSection)
  const [visualizationTab, setVisualizationTab] = useState<VisualizationTabType>('search')
  const [configurationTab, setConfigurationTab] = useState<ConfigurationTabType>('connections')
  const [selectedConnectionId, setSelectedConnectionId] = useState<string>('')

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => navigate('/')}
              className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-xl flex items-center justify-center hover:scale-105 transition-transform"
            >
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </button>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">DataTruth</h1>
              <p className="text-sm text-gray-500">
                {activeSection === 'visualization' && visualizationTab === 'search' && 'Natural language search with intelligent suggestions'}
                {activeSection === 'visualization' && visualizationTab === 'quality' && 'Monitor data quality'}
                {activeSection === 'visualization' && visualizationTab === 'matching' && 'Test fuzzy matching'}
                {activeSection === 'configuration' && configurationTab === 'connections' && 'Manage database connections'}
                {activeSection === 'configuration' && configurationTab === 'schema' && 'Explore database schema'}
                {activeSection === 'configuration' && configurationTab === 'semantic' && 'Define semantic layer'}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">{username}</span>
            <button
              onClick={logout}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="px-6 mt-4">
          {/* Sub-tabs for Visualization */}
          {activeSection === 'visualization' && (
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setVisualizationTab('search')}
                className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 transition ${
                  visualizationTab === 'search'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <span>Search & Ask</span>
              </button>
              
              <button
                onClick={() => setVisualizationTab('quality')}
                className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 transition ${
                  visualizationTab === 'quality'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Data Quality</span>
              </button>
              
              <button
                onClick={() => setVisualizationTab('matching')}
                className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 transition ${
                  visualizationTab === 'matching'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <span>Fuzzy Matching</span>
              </button>
            </nav>
          )}

          {/* Sub-tabs for Configuration */}
          {activeSection === 'configuration' && (
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setConfigurationTab('connections')}
                className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 transition ${
                  configurationTab === 'connections'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                </svg>
                <span>Connections</span>
              </button>
              
              <button
                onClick={() => setConfigurationTab('schema')}
                className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 transition ${
                  configurationTab === 'schema'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
                </svg>
                <span>Schema Explorer</span>
              </button>

              <button
                onClick={() => setConfigurationTab('semantic')}
                className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 transition ${
                  configurationTab === 'semantic'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                </svg>
                <span>Semantic Layer</span>
              </button>
            </nav>
          )}
        </div>
      </header>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto">
        {/* Visualization Section */}
        {activeSection === 'visualization' && (
          <>
            {visualizationTab === 'search' && (
              <SearchAndAsk 
                selectedConnectionId={selectedConnectionId}
                onConnectionChange={setSelectedConnectionId}
              />
            )}
            
            {visualizationTab === 'quality' && (
              <div className="flex-1 overflow-hidden">
                <QualityDashboard 
                  connectionId={selectedConnectionId}
                  onConnectionChange={setSelectedConnectionId}
                />
              </div>
            )}

            {visualizationTab === 'matching' && (
              <div className="px-6 py-6">
                <div className="max-w-7xl mx-auto">
                  <FuzzyMatchTester />
                </div>
              </div>
            )}
          </>
        )}

        {/* Configuration Section */}
        {activeSection === 'configuration' && (
          <>
            {configurationTab === 'connections' && (
              <ConnectionManager />
            )}

            {configurationTab === 'schema' && (
              <SchemaExplorer 
                connectionId={selectedConnectionId}
                onConnectionChange={setSelectedConnectionId}
              />
            )}

            {configurationTab === 'semantic' && (
              <SemanticLayer />
            )}
          </>
        )}
      </div>
    </div>
  )
}
