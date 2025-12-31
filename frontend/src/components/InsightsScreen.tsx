import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { API_URL } from '../config'

interface Insight {
  id: string
  type: string
  severity: string
  title: string
  description: string
  facts: string[]
  metric_value?: number
  metric_label?: string
  change_percent?: number
  confidence: number
  timestamp: string
  forecast_data?: any
  attribution_data?: any
  impact_score?: number
  impact_level?: string
}

interface InsightCard {
  insight: Insight
  narrative: string
  suggested_actions: string[]
  related_insights: string[]
}

interface InsightsResponse {
  connection_id: string
  connection_name: string
  insights: InsightCard[]
  generated_at: string
  analysis_summary: string
}

interface Connection {
  id: string
  name: string
  type: string
  host: string
  database: string
}

const InsightsScreen = () => {
  const navigate = useNavigate()
  const { token, username, logout, isAdmin } = useAuth()
  const [connections, setConnections] = useState<Connection[]>([])
  const [selectedConnection, setSelectedConnection] = useState<string>('')
  const [userRole, setUserRole] = useState<string>('')
  const [insights, setInsights] = useState<InsightsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedTypes, setSelectedTypes] = useState<string[]>([])
  const [availableTypes, setAvailableTypes] = useState<any[]>([])

  // Fetch connections on mount
  useEffect(() => {
    fetchConnections()
    fetchInsightTypes()
  }, [])

  const fetchConnections = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/connections`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setConnections(data.connections || [])
        if (data.connections?.length > 0) {
          setSelectedConnection(data.connections[0].id)
        }
      }
    } catch (err) {
      console.error('Failed to fetch connections:', err)
    }
  }

  const fetchInsightTypes = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/insights/types`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setAvailableTypes(data.types || [])
      }
    } catch (err) {
      console.error('Failed to fetch insight types:', err)
    }
  }

  const generateInsights = async () => {
    if (!selectedConnection) {
      setError('Please select a connection')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        connection_id: selectedConnection,
        time_range_days: '7',
        max_insights: '10',
        min_confidence: '0.6',
      })

      if (userRole) {
        params.append('user_role', userRole)
      }

      if (selectedTypes.length > 0) {
        selectedTypes.forEach(type => params.append('insight_types', type))
      }

      const response = await fetch(`${API_URL}/api/v1/insights/generate?${params}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        const data = await response.json()
        setInsights(data)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to generate insights')
      }
    } catch (err) {
      setError('Failed to generate insights. Please try again.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const toggleInsightType = (type: string) => {
    setSelectedTypes(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    )
  }

  const recordFeedback = async (insightId: string, action: string) => {
    try {
      await fetch(`${API_URL}/api/v1/insights/feedback?insight_id=${insightId}&action=${action}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
    } catch (err) {
      console.error('Failed to record feedback:', err)
    }
  }

  const getImpactBadge = (impactLevel?: string) => {
    const badges = {
      high: 'bg-red-100 text-red-800 border-red-300',
      medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      low: 'bg-blue-100 text-blue-800 border-blue-300',
    }
    if (!impactLevel) return null
    return (
      <span className={`text-xs px-2 py-1 rounded-full border ${badges[impactLevel as keyof typeof badges] || badges.low}`}>
        {impactLevel.toUpperCase()} IMPACT
      </span>
    )
  }

  const getSeverityColor = (severity: string) => {
    const colors = {
      critical: 'bg-red-100 border-red-500 text-red-800',
      high: 'bg-orange-100 border-orange-500 text-orange-800',
      medium: 'bg-yellow-100 border-yellow-500 text-yellow-800',
      low: 'bg-blue-100 border-blue-500 text-blue-800',
      info: 'bg-gray-100 border-gray-500 text-gray-800',
    }
    return colors[severity as keyof typeof colors] || colors.info
  }

  const getSeverityIcon = (severity: string) => {
    const icons = {
      critical: '🚨',
      high: '⚠️',
      medium: '⚡',
      low: 'ℹ️',
      info: '📊',
    }
    return icons[severity as keyof typeof icons] || '📊'
  }

  const getTypeIcon = (type: string) => {
    const icons = {
      pattern: '🔍',
      anomaly: '⚠️',
      trend: '📈',
      comparison: '⚖️',
      attribution: '🎯',
      forecast: '🔮',
      performance: '⚡',
      quality: '✓',
      usage: '📊',
    }
    return icons[type as keyof typeof icons] || '📊'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Navigation Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-xl flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                DataTruth
              </h1>
              <p className="text-xs text-gray-500">Modern Data Analytics Platform</p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate('/')}
              className="px-3 py-2 text-sm font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              Home
            </button>
            <button
              onClick={() => navigate('/workspace')}
              className="px-3 py-2 text-sm font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              Workspace
            </button>
            <button
              className="px-3 py-2 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-indigo-600 rounded-lg shadow-sm flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Insights
            </button>
            {isAdmin && (
              <button
                onClick={() => navigate('/users')}
                className="px-3 py-2 text-sm font-medium text-white bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 rounded-lg transition flex items-center gap-2 shadow-sm"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                Users
              </button>
            )}
            <div className="h-6 w-px bg-gray-300"></div>
            <span className="text-sm text-gray-600">Welcome, {username}</span>
            <button
              onClick={logout}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-white/50 rounded-lg transition"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Page Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Insights</h1>
              <p className="text-gray-600 mt-1">Automated insights and patterns from your data</p>
            </div>
            <div className="flex items-center gap-4">
              <select
                value={selectedConnection}
                onChange={(e) => setSelectedConnection(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select connection...</option>
                {connections.map(conn => (
                  <option key={conn.id} value={conn.id}>
                    {conn.name}
                  </option>
                ))}
              </select>
              <select
                value={userRole}
                onChange={(e) => setUserRole(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="">All Roles (Generic)</option>
                <option value="executive">👔 Executive/Director</option>
                <option value="trader">📊 Trader</option>
                <option value="investor">💰 Investor</option>
                <option value="analyst">🔬 Analyst</option>
                <option value="manager">👥 Manager</option>
                <option value="sales">🎯 Sales</option>
                <option value="operations">⚙️ Operations</option>
                <option value="finance">💵 Finance</option>
                <option value="agent">🎧 Agent</option>
              </select>
              <button
                onClick={generateInsights}
                disabled={loading || !selectedConnection}
                className="px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-md hover:shadow-lg"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Generating...
                  </span>
                ) : (
                  'Generate Insights'
                )}
              </button>
            </div>
          </div>

          {/* Insight Type Filters */}
          {availableTypes.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="text-sm text-gray-600 self-center mr-2">Filter by type:</span>
              {availableTypes.map(type => (
                <button
                  key={type.value}
                  onClick={() => toggleInsightType(type.value)}
                  className={`px-3 py-1 rounded-full text-sm transition-all ${
                    selectedTypes.includes(type.value)
                      ? 'bg-blue-600 text-white'
                      : 'bg-white border border-gray-300 text-gray-700 hover:border-blue-400'
                  }`}
                >
                  {getTypeIcon(type.value)} {type.label}
                </button>
              ))}
              {selectedTypes.length > 0 && (
                <button
                  onClick={() => setSelectedTypes([])}
                  className="px-3 py-1 text-sm text-gray-600 hover:text-gray-900"
                >
                  Clear all
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
            {error}
          </div>
        )}

        {insights && (
          <>
            {/* Summary */}
            <div className="mb-6 p-6 bg-white rounded-lg shadow-md border border-gray-200">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 mb-2">
                    {insights.connection_name}
                  </h2>
                  <p className="text-gray-600">{insights.analysis_summary}</p>
                  <p className="text-sm text-gray-500 mt-2">
                    Generated {new Date(insights.generated_at).toLocaleString()}
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold text-blue-600">{insights.insights.length}</div>
                  <div className="text-sm text-gray-600">Insights Found</div>
                </div>
              </div>
            </div>

            {/* Insight Cards */}
            {insights.insights.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg shadow-md">
                <p className="text-gray-600 text-lg">No insights found for the selected criteria.</p>
                <p className="text-gray-500 text-sm mt-2">Try adjusting your filters or time range.</p>
              </div>
            ) : (
              <div className="grid gap-6 md:grid-cols-2">
                {insights.insights.map((card) => (
                  <div
                    key={card.insight.id}
                    className={`p-6 rounded-lg border-l-4 shadow-md hover:shadow-lg transition-shadow ${getSeverityColor(card.insight.severity)}`}
                  >
                    {/* Card Header */}
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <span className="text-3xl">{getSeverityIcon(card.insight.severity)}</span>
                        <div>
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className="text-xs font-semibold uppercase tracking-wide opacity-75">
                              {getTypeIcon(card.insight.type)} {card.insight.type}
                            </span>
                            <span className="text-xs bg-white bg-opacity-50 px-2 py-0.5 rounded">
                              {(card.insight.confidence * 100).toFixed(0)}% confidence
                            </span>
                            {getImpactBadge(card.insight.impact_level)}
                          </div>
                          <h3 className="text-lg font-bold">{card.insight.title}</h3>
                        </div>
                      </div>
                      {/* Action buttons */}
                      <div className="flex gap-2">
                        <button
                          onClick={() => recordFeedback(card.insight.id, 'acted_on')}
                          className="text-gray-400 hover:text-green-600 transition"
                          title="Mark as acted on"
                        >
                          ✓
                        </button>
                        <button
                          onClick={() => recordFeedback(card.insight.id, 'dismissed')}
                          className="text-gray-400 hover:text-red-600 transition"
                          title="Dismiss"
                        >
                          ✕
                        </button>
                      </div>
                    </div>

                    {/* Metric Display */}
                    {card.insight.metric_value !== undefined && (
                      <div className="mb-4 p-3 bg-white bg-opacity-50 rounded">
                        <div className="text-2xl font-bold">
                          {card.insight.metric_value.toLocaleString()}
                          {card.insight.change_percent !== undefined && (
                            <span className={`text-lg ml-2 ${card.insight.change_percent > 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {card.insight.change_percent > 0 ? '↑' : '↓'} {Math.abs(card.insight.change_percent).toFixed(1)}%
                            </span>
                          )}
                        </div>
                        {card.insight.metric_label && (
                          <div className="text-sm opacity-75">{card.insight.metric_label}</div>
                        )}
                      </div>
                    )}

                    {/* Forecast Visualization */}
                    {card.insight.forecast_data && (
                      <div className="mb-4 p-3 bg-white bg-opacity-50 rounded">
                        <div className="text-xs font-semibold uppercase tracking-wide opacity-75 mb-2">
                          📈 Forecast (Next 7 Days)
                        </div>
                        <div className="flex gap-1 items-end h-16">
                          {card.insight.forecast_data.predictions?.slice(0, 7).map((pred: any, idx: number) => (
                            <div key={idx} className="flex-1 flex flex-col items-center">
                              <div 
                                className="w-full bg-blue-400 rounded-t transition-all hover:bg-blue-500"
                                style={{ height: `${(pred.confidence || 0.5) * 100}%` }}
                                title={`${pred.period}: ${pred.value.toFixed(1)} (${(pred.confidence * 100).toFixed(0)}% confidence)`}
                              />
                              <div className="text-xs mt-1 opacity-75">+{idx + 1}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Attribution Display */}
                    {card.insight.attribution_data && (
                      <div className="mb-4 p-3 bg-white bg-opacity-50 rounded">
                        <div className="text-xs font-semibold uppercase tracking-wide opacity-75 mb-2">
                          🎯 Key Drivers
                        </div>
                        <div className="space-y-2">
                          {card.insight.attribution_data.factors?.slice(0, 3).map((factor: any, idx: number) => (
                            <div key={idx} className="flex items-center gap-2">
                              <div className="text-lg font-bold text-blue-600">#{idx + 1}</div>
                              <div className="flex-1">
                                <div className="text-sm font-medium">{factor.name}</div>
                                <div className="flex items-center gap-2">
                                  <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                                    <div
                                      className={`h-1.5 rounded-full ${
                                        factor.direction === 'positive' ? 'bg-green-500' : 'bg-red-500'
                                      }`}
                                      style={{ width: `${Math.abs(factor.correlation) * 100}%` }}
                                    />
                                  </div>
                                  <span className="text-xs opacity-75">
                                    {factor.direction === 'positive' ? '+' : ''}
                                    {(factor.correlation * 100).toFixed(0)}%
                                  </span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Narrative */}
                    <p className="text-sm mb-4 leading-relaxed">{card.narrative}</p>

                    {/* Facts */}
                    <div className="mb-4">
                      <div className="text-xs font-semibold uppercase tracking-wide opacity-75 mb-2">Key Facts</div>
                      <ul className="text-sm space-y-1">
                        {card.insight.facts.map((fact, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="opacity-50 mt-0.5">•</span>
                            <span>{fact}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Suggested Actions */}
                    {card.suggested_actions.length > 0 && (
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-wide opacity-75 mb-2">Suggested Actions</div>
                        <ul className="text-sm space-y-1">
                          {card.suggested_actions.map((action, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <span className="opacity-50">→</span>
                              <span>{action}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* Empty State */}
        {!loading && !insights && !error && (
          <div className="text-center py-20 bg-white rounded-lg shadow-md">
            <div className="text-6xl mb-4">🔍</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Ready to discover insights</h3>
            <p className="text-gray-600 mb-6">Select a connection and click "Generate Insights" to begin</p>
            <div className="text-sm text-gray-500">
              <p>Insights include:</p>
              <div className="flex justify-center gap-4 mt-2 flex-wrap">
                <span>📈 Trends</span>
                <span>⚠️ Anomalies</span>
                <span>🔍 Patterns</span>
                <span>⚖️ Comparisons</span>
                <span>✓ Quality</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default InsightsScreen
