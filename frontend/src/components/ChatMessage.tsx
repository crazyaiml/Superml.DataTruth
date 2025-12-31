import { useState } from 'react'
import DataTable from './DataTable'
import DataChart from './DataChart'
import { useAuth } from '../contexts/AuthContext'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  data?: any[]
  metadata?: any
  loading?: boolean
  error?: boolean
}

interface Props {
  message: Message
}

// Helper function to generate human-readable query explanation from SQL
function explainSQL(sql: string): string {
  if (!sql) return 'Query executed successfully'
  
  // Extract key components from SQL
  const selectMatch = sql.match(/SELECT\s+(.+?)\s+FROM/is)
  const fromMatch = sql.match(/FROM\s+(\w+)/i)
  const whereMatch = sql.match(/WHERE\s+(.+?)(?:GROUP BY|ORDER BY|LIMIT|$)/is)
  const groupMatch = sql.match(/GROUP BY\s+(.+?)(?:ORDER BY|LIMIT|$)/is)
  const orderMatch = sql.match(/ORDER BY\s+(.+?)(?:LIMIT|$)/is)
  const limitMatch = sql.match(/LIMIT\s+(\d+)/i)
  
  let explanation = 'This query '
  
  // What we're getting
  if (selectMatch) {
    const fields = selectMatch[1]
    if (fields.includes('SUM(') || fields.includes('AVG(') || fields.includes('COUNT(')) {
      if (fields.includes('SUM(') && fields.includes('-')) {
        explanation += 'calculates profit '
      } else if (fields.includes('SUM(')) {
        explanation += 'calculates total '
      } else if (fields.includes('AVG(')) {
        explanation += 'calculates average '
      } else if (fields.includes('COUNT(')) {
        explanation += 'counts '
      }
    } else {
      explanation += 'retrieves '
    }
  }
  
  // From where
  if (fromMatch) {
    const table = fromMatch[1]
    explanation += `from ${table} `
  }
  
  // Filters
  if (whereMatch) {
    const conditions = whereMatch[1].trim()
    if (conditions.includes('BETWEEN')) {
      explanation += 'for a specific time period '
    } else {
      explanation += 'with applied filters '
    }
  }
  
  // Grouping
  if (groupMatch) {
    const groupBy = groupMatch[1]
    if (groupBy.includes('DATE_TRUNC')) {
      if (groupBy.includes('quarter')) {
        explanation += 'grouped by quarter '
      } else if (groupBy.includes('month')) {
        explanation += 'grouped by month '
      } else if (groupBy.includes('year')) {
        explanation += 'grouped by year '
      } else if (groupBy.includes('week')) {
        explanation += 'grouped by week '
      } else {
        explanation += 'grouped by time period '
      }
    } else {
      explanation += 'grouped by category '
    }
  }
  
  // Ordering
  if (orderMatch) {
    explanation += 'and sorted '
  }
  
  // Limit
  if (limitMatch) {
    explanation += `(showing up to ${limitMatch[1]} results)`
  }
  
  return explanation.trim() + '.'
}

export default function ChatMessage({ message }: Props) {
  const [viewMode, setViewMode] = useState<'table' | 'chart'>('table')
  const { isAdmin } = useAuth()

  if (message.loading) {
    return (
      <div className="flex items-start space-x-4">
        <div className="flex-shrink-0 w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
          <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </div>
        <div className="flex-1 bg-gray-100 rounded-2xl px-5 py-3">
          <div className="flex space-x-2">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
          </div>
        </div>
      </div>
    )
  }

  if (message.role === 'user') {
    return (
      <div className="flex items-start space-x-4 justify-end">
        <div className="bg-blue-600 text-white rounded-2xl px-5 py-3 max-w-2xl">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start space-x-4">
      <div className="flex-shrink-0 w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
        <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      </div>
      <div className="flex-1">
        <div className={`rounded-2xl px-5 py-3 ${message.error ? 'bg-red-50 border border-red-200' : 'bg-gray-100'}`}>
          <p className={`whitespace-pre-wrap ${message.error ? 'text-red-700' : 'text-gray-900'}`}>
            {message.content}
          </p>
        </div>
        
        {message.data && message.data.length > 0 && (
          <div className="mt-4">
            {/* View Toggle */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex space-x-2 bg-gray-200 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('table')}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition ${
                    viewMode === 'table'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <span className="flex items-center space-x-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <span>Table</span>
                  </span>
                </button>
                <button
                  onClick={() => setViewMode('chart')}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition ${
                    viewMode === 'chart'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <span className="flex items-center space-x-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                    <span>Chart</span>
                  </span>
                </button>
              </div>
            </div>

            {/* Data Display */}
            {viewMode === 'table' ? (
              <DataTable data={message.data} />
            ) : (
              <DataChart data={message.data} />
            )}
          </div>
        )}

        {message.metadata && (
          <div className="mt-3 text-xs text-gray-500">
            {/* Execution Stats */}
            <div className="flex items-center space-x-4">
              {message.metadata.execution_time_ms !== undefined && (
                <span className="flex items-center space-x-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <span>{message.metadata.execution_time_ms.toFixed(2)}ms</span>
                </span>
              )}
              {message.metadata.row_count !== undefined && (
                <span className="flex items-center space-x-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  <span>{message.metadata.row_count} rows</span>
                </span>
              )}
              {message.metadata.from_cache && (
                <span className="flex items-center space-x-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                  </svg>
                  <span>Cached</span>
                </span>
              )}
            </div>
            
            {/* SQL Query / Query Explanation */}
            {message.metadata.generated_sql && (
              <>
                {isAdmin ? (
                  // Admin: Show raw SQL query
                  <details className="mt-2 group">
                    <summary className="cursor-pointer text-gray-600 hover:text-gray-900 font-medium flex items-center space-x-1">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                      </svg>
                      <span>View SQL Query</span>
                      <svg className="w-3 h-3 transition-transform group-open:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </summary>
                    <div className="mt-2 bg-gray-900 text-gray-100 rounded-lg p-3 overflow-x-auto">
                      <pre className="text-xs font-mono whitespace-pre-wrap break-words">
                        {message.metadata.generated_sql}
                      </pre>
                    </div>
                  </details>
                ) : (
                  // Regular User: Show explainable query description
                  <div className="mt-2 bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <div className="flex items-start space-x-2">
                      <svg className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <div className="flex-1">
                        <p className="text-xs text-blue-900 font-medium">How this was calculated:</p>
                        <p className="text-xs text-blue-800 mt-1">
                          {explainSQL(message.metadata.generated_sql)}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
