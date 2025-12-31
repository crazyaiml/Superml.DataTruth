import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import axios from 'axios'
import toast from 'react-hot-toast'
import { API_URL } from '../config'

interface Connection {
  id: string
  name: string
  type: string
}

interface TableQuality {
  table_name: string
  overall_score: number
  row_count?: number
  column_count?: number
  issues_count?: number
  dimension_scores?: Record<string, number>
  error?: string
}

interface TableDetailQuality {
  entity_name: string
  entity_type: string
  connection_id: string
  overall_score: number
  dimension_scores: Record<string, number>
  issues: string[]
  recommendations: string[]
  profile: {
    row_count: number
    column_count: number
    columns: any[]
  }
}

interface QualityDashboardProps {
  connectionId?: string
  onConnectionChange?: (id: string) => void
}

export default function QualityDashboard({ connectionId: propConnectionId, onConnectionChange }: QualityDashboardProps) {
  const { token } = useAuth()
  const [connections, setConnections] = useState<Connection[]>([])
  const [selectedConnectionId, setSelectedConnectionId] = useState(propConnectionId || '')
  const [tables, setTables] = useState<TableQuality[]>([])
  const [loading, setLoading] = useState(false)
  const [assessing, setAssessing] = useState(false)
  const [selectedTable, setSelectedTable] = useState<TableDetailQuality | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  // Load connections on mount
  useEffect(() => {
    loadConnections()
  }, [token])

  // Update when prop changes
  useEffect(() => {
    if (propConnectionId) {
      setSelectedConnectionId(propConnectionId)
    }
  }, [propConnectionId])

  const loadConnections = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/connections`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      const conns = response.data.connections || response.data || []
      setConnections(conns)
      if (!selectedConnectionId && conns.length > 0) {
        setSelectedConnectionId(conns[0].id)
        onConnectionChange?.(conns[0].id)
      }
    } catch (error) {
      console.error('Failed to load connections:', error)
    }
  }

  const handleConnectionChange = (id: string) => {
    setSelectedConnectionId(id)
    setTables([])
    setSelectedTable(null)
    onConnectionChange?.(id)
  }

  const runQualityAssessment = async () => {
    if (!selectedConnectionId) {
      toast.error('Please select a connection first')
      return
    }

    setAssessing(true)
    setLoading(true)
    try {
      const response = await axios.post(
        `${API_URL}/api/v1/quality/assess-connection?connection_id=${selectedConnectionId}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setTables(response.data.tables || [])
      toast.success(`Quality assessment complete for ${response.data.table_count} tables`)
    } catch (error: any) {
      console.error('Failed to run quality assessment:', error)
      toast.error(error.response?.data?.detail || 'Quality assessment failed')
    } finally {
      setAssessing(false)
      setLoading(false)
    }
  }

  const viewTableDetail = async (tableName: string) => {
    setLoadingDetail(true)
    try {
      const response = await axios.post(
        `${API_URL}/api/v1/quality/assess-table?connection_id=${selectedConnectionId}&table_name=${tableName}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setSelectedTable(response.data)
    } catch (error: any) {
      console.error('Failed to load table quality:', error)
      toast.error(error.response?.data?.detail || 'Failed to load table quality')
    } finally {
      setLoadingDetail(false)
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600 bg-green-100'
    if (score >= 0.6) return 'text-yellow-600 bg-yellow-100'
    return 'text-red-600 bg-red-100'
  }

  const getScoreBarColor = (score: number) => {
    if (score >= 0.8) return 'bg-green-500'
    if (score >= 0.6) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const averageScore = tables.length > 0 
    ? tables.reduce((sum, t) => sum + (t.overall_score || 0), 0) / tables.length 
    : 0

  const lowQualityCount = tables.filter(t => t.overall_score < 0.7).length

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Data Quality Dashboard</h2>
            <p className="text-sm text-gray-500 mt-1">
              Assess and monitor data quality across your database tables
            </p>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-gray-700">Connection:</label>
            <select
              value={selectedConnectionId}
              onChange={(e) => handleConnectionChange(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select a connection...</option>
              {connections.map((conn) => (
                <option key={conn.id} value={conn.id}>
                  {conn.name}
                </option>
              ))}
            </select>
            <button
              onClick={runQualityAssessment}
              disabled={!selectedConnectionId || assessing}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {assessing ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                  Assessing...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Run Assessment
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {!selectedConnectionId ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                </svg>
              </div>
              <p className="text-gray-600">Select a connection to assess data quality</p>
            </div>
          </div>
        ) : tables.length === 0 && !loading ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Ready to Assess</h3>
              <p className="text-gray-600 mb-4">Click "Run Assessment" to analyze data quality for all tables</p>
              <button
                onClick={runQualityAssessment}
                className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Run Quality Assessment
              </button>
            </div>
          </div>
        ) : loading ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Analyzing data quality...</p>
              <p className="text-sm text-gray-500 mt-1">This may take a few moments</p>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Tables Assessed</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">{tables.length}</p>
                  </div>
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Average Quality</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">
                      {(averageScore * 100).toFixed(0)}%
                    </p>
                  </div>
                  <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${averageScore >= 0.8 ? 'bg-green-100' : averageScore >= 0.6 ? 'bg-yellow-100' : 'bg-red-100'}`}>
                    <svg className={`w-6 h-6 ${averageScore >= 0.8 ? 'text-green-600' : averageScore >= 0.6 ? 'text-yellow-600' : 'text-red-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Needs Attention</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">{lowQualityCount}</p>
                  </div>
                  <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            {/* Tables List */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Table Quality Scores</h3>
              </div>
              <div className="divide-y divide-gray-200">
                {tables.map((table) => (
                  <div
                    key={table.table_name}
                    className="px-6 py-4 hover:bg-gray-50 cursor-pointer transition"
                    onClick={() => viewTableDetail(table.table_name)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3">
                          <h4 className="text-sm font-medium text-gray-900">{table.table_name}</h4>
                          {table.row_count !== undefined && (
                            <span className="px-2 py-1 text-xs font-medium text-gray-600 bg-gray-100 rounded">
                              {table.row_count.toLocaleString()} rows
                            </span>
                          )}
                          {table.column_count !== undefined && (
                            <span className="px-2 py-1 text-xs font-medium text-gray-600 bg-gray-100 rounded">
                              {table.column_count} columns
                            </span>
                          )}
                        </div>
                        <div className="mt-2 flex items-center gap-4">
                          <div className="flex-1 max-w-xs">
                            <div className="bg-gray-200 rounded-full h-2">
                              <div
                                className={`h-2 rounded-full ${getScoreBarColor(table.overall_score)}`}
                                style={{ width: `${table.overall_score * 100}%` }}
                              ></div>
                            </div>
                          </div>
                          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${getScoreColor(table.overall_score)}`}>
                            {(table.overall_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                      <svg className="w-5 h-5 text-gray-400 ml-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Table Detail Modal */}
      {selectedTable && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between sticky top-0 bg-white">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{selectedTable.entity_name}</h3>
                <p className="text-sm text-gray-600">
                  {selectedTable.profile.row_count.toLocaleString()} rows • {selectedTable.profile.column_count} columns
                </p>
              </div>
              <button
                onClick={() => setSelectedTable(null)}
                className="text-gray-400 hover:text-gray-600 transition"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="px-6 py-4 space-y-6">
              {/* Overall Score */}
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">Overall Quality Score</label>
                <div className="flex items-center space-x-4">
                  <div className="flex-1 bg-gray-200 rounded-full h-4">
                    <div
                      className={`h-4 rounded-full ${getScoreBarColor(selectedTable.overall_score)}`}
                      style={{ width: `${selectedTable.overall_score * 100}%` }}
                    ></div>
                  </div>
                  <span className="text-lg font-semibold text-gray-900">
                    {(selectedTable.overall_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Dimension Scores */}
              <div>
                <label className="text-sm font-medium text-gray-700 mb-3 block">Quality Dimensions</label>
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(selectedTable.dimension_scores).map(([dimension, score]) => (
                    <div key={dimension} className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700 capitalize">{dimension}</span>
                        <span className={`text-sm font-semibold ${score >= 0.8 ? 'text-green-600' : score >= 0.6 ? 'text-yellow-600' : 'text-red-600'}`}>
                          {(score * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${getScoreBarColor(score)}`}
                          style={{ width: `${score * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Issues */}
              {selectedTable.issues.length > 0 && (
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">Issues Found ({selectedTable.issues.length})</label>
                  <ul className="space-y-2 bg-red-50 rounded-lg p-4">
                    {selectedTable.issues.map((issue, idx) => (
                      <li key={idx} className="flex items-start space-x-2 text-sm text-gray-700">
                        <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>{issue}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Recommendations */}
              {selectedTable.recommendations.length > 0 && (
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">Recommendations</label>
                  <ul className="space-y-2 bg-blue-50 rounded-lg p-4">
                    {selectedTable.recommendations.map((rec, idx) => (
                      <li key={idx} className="flex items-start space-x-2 text-sm text-gray-700">
                        <svg className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* No Issues */}
              {selectedTable.issues.length === 0 && selectedTable.recommendations.length === 0 && (
                <div className="text-center py-6">
                  <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                    <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-gray-600">No quality issues detected for this table</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Loading Detail Overlay */}
      {loadingDetail && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading table details...</p>
          </div>
        </div>
      )}
    </div>
  )
}
