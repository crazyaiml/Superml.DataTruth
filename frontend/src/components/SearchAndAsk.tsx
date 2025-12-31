import { useState, useRef, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import axios from 'axios'
import { API_URL } from '../config'
import ChatMessage from './ChatMessage'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  data?: any[]
  metadata?: any
  loading?: boolean
  error?: boolean
}

interface Suggestion {
  text: string
  type: 'metric' | 'dimension' | 'filter' | 'query' | 'complete'
  icon: string
  description?: string
}

interface Connection {
  id: string
  name: string
  type: string
  database: string
  is_active: boolean
}

interface ColumnMetadata {
  name: string
  data_type: string
  is_measure: boolean
  is_dimension: boolean
  default_aggregation?: string
  display_name?: string
  description?: string
}

interface TableMetadata {
  name: string
  table_type: string
  row_count: number
  columns: ColumnMetadata[]
  primary_keys: string[]
}

interface SchemaData {
  connection_id: string
  schema_name: string
  table_count: number
  relationship_count: number
  tables: { [key: string]: TableMetadata }
  relationships: any[]
}

interface SearchAndAskProps {
  selectedConnectionId: string
  onConnectionChange: (id: string) => void
}

export default function SearchAndAsk({ selectedConnectionId, onConnectionChange }: SearchAndAskProps) {
  const { token } = useAuth()
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [suggestionsLoading, setSuggestionsLoading] = useState(false)
  const [conversationContext, setConversationContext] = useState<string[]>([])
  const [connections, setConnections] = useState<Connection[]>([])
  const [schema, setSchema] = useState<SchemaData | null>(null)
  const [schemaLoading, setSchemaLoading] = useState(false)
  const [adminExamples, setAdminExamples] = useState<Suggestion[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const suggestionsTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const suggestionsContainerRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Load connections on mount
  useEffect(() => {
    if (token) {
      loadConnections()
    }
  }, [token])

  // Load schema when connection changes
  useEffect(() => {
    if (selectedConnectionId && token) {
      loadSchema()
      fetchAdminExamples()
      // Create new session when connection changes
      createNewSession()
    }
  }, [selectedConnectionId, token])

  const fetchAdminExamples = async () => {
    if (!selectedConnectionId || !token) return
    
    try {
      const response = await axios.get(
        `${API_URL}/api/v1/connections/${selectedConnectionId}/examples`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      const examples = response.data.examples || []
      // Convert to Suggestion format
      setAdminExamples(examples.map((ex: any) => ({
        text: ex.text,
        icon: ex.icon,
        description: ex.description,
        type: 'query'
      })))
    } catch (error) {
      console.error('Failed to fetch admin examples:', error)
      setAdminExamples([])
    }
  }

  // Handle click outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsContainerRef.current &&
        !suggestionsContainerRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false)
      }
    }

    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowSuggestions(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscapeKey)

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscapeKey)
    }
  }, [])

  const loadConnections = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/connections`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      const conns = response.data.connections || response.data || []
      setConnections(conns)
      // Auto-select first connection if none selected
      if (!selectedConnectionId && conns.length > 0) {
        onConnectionChange(conns[0].id)
      }
    } catch (error) {
      console.error('Failed to load connections:', error)
    }
  }

  const loadSchema = async () => {
    try {
      setSchemaLoading(true)
      const response = await axios.post(
        `${API_URL}/api/v1/connections/${selectedConnectionId}/discover`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setSchema(response.data)
    } catch (error) {
      console.error('Failed to load schema:', error)
    } finally {
      setSchemaLoading(false)
    }
  }

  const createNewSession = async () => {
    if (!selectedConnectionId || !token) return
    
    try {
      const response = await axios.post(
        `${API_URL}/api/v1/chat/sessions`,
        { connection_id: selectedConnectionId },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setCurrentSessionId(response.data.id)
      setMessages([])
      setConversationContext([])
    } catch (error) {
      console.error('Failed to create session:', error)
    }
  }

  const saveMessage = async (role: string, content: string, extraData?: any) => {
    if (!currentSessionId || !token) return
    
    try {
      await axios.post(
        `${API_URL}/api/v1/chat/sessions/${currentSessionId}/messages`,
        {
          role,
          content,
          sql_query: extraData?.sql_query,
          result_data: extraData?.data,
          result_metadata: extraData?.metadata,
          processing_time_ms: extraData?.processing_time_ms,
          error_message: extraData?.error ? content : null
        },
        { headers: { Authorization: `Bearer ${token}` } }
      )
    } catch (error) {
      console.error('Failed to save message:', error)
    }
  }

  // Load intelligent suggestions from API with debouncing
  const fetchSuggestions = useCallback(async (query: string) => {
    if (!selectedConnectionId || !token) {
      setSuggestions([])
      return
    }

    // Clear any pending request
    if (suggestionsTimeoutRef.current) {
      clearTimeout(suggestionsTimeoutRef.current)
    }

    // For empty query, show example queries immediately
    if (!query.trim()) {
      try {
        setSuggestionsLoading(true)
        const response = await axios.post(
          `${API_URL}/api/v1/connections/${selectedConnectionId}/suggestions`,
          null,
          {
            params: { partial_query: '', max_suggestions: 4, use_llm: false },
            headers: { Authorization: `Bearer ${token}` }
          }
        )
        setSuggestions(response.data.suggestions || [])
      } catch (error) {
        console.error('Failed to fetch suggestions:', error)
        setSuggestions([])
      } finally {
        setSuggestionsLoading(false)
      }
      return
    }

    // For short queries (1-2 chars), use fast autocomplete
    if (query.length <= 2) {
      try {
        setSuggestionsLoading(true)
        const response = await axios.post(
          `${API_URL}/api/v1/connections/${selectedConnectionId}/suggestions`,
          null,
          {
            params: { partial_query: query, max_suggestions: 6, use_llm: false },
            headers: { Authorization: `Bearer ${token}` }
          }
        )
        setSuggestions(response.data.suggestions || [])
      } catch (error) {
        console.error('Failed to fetch autocomplete:', error)
        setSuggestions([])
      } finally {
        setSuggestionsLoading(false)
      }
      return
    }

    // For longer queries, debounce and use LLM
    setSuggestionsLoading(true)
    suggestionsTimeoutRef.current = setTimeout(async () => {
      try {
        const response = await axios.post(
          `${API_URL}/api/v1/connections/${selectedConnectionId}/suggestions`,
          null,
          {
            params: { partial_query: query, max_suggestions: 6, use_llm: true },
            headers: { Authorization: `Bearer ${token}` }
          }
        )
        setSuggestions(response.data.suggestions || [])
      } catch (error) {
        console.error('Failed to fetch LLM suggestions:', error)
        // Fallback to autocomplete on error
        try {
          const fallbackResponse = await axios.post(
            `${API_URL}/api/v1/connections/${selectedConnectionId}/suggestions`,
            null,
            {
              params: { partial_query: query, max_suggestions: 6, use_llm: false },
              headers: { Authorization: `Bearer ${token}` }
            }
          )
          setSuggestions(fallbackResponse.data.suggestions || [])
        } catch (fallbackError) {
          setSuggestions([])
        }
      } finally {
        setSuggestionsLoading(false)
      }
    }, 500) // 500ms debounce for LLM calls
  }, [selectedConnectionId, token])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setInput(value)
    
    // Hide suggestions if input is empty
    if (!value.trim()) {
      setShowSuggestions(false)
      setSuggestions([])
      return
    }
    
    setShowSuggestions(true)
    // Fetch intelligent suggestions from API
    fetchSuggestions(value)
  }

  const handleSuggestionClick = (suggestion: Suggestion) => {
    if (suggestion.type === 'query' || suggestion.type === 'complete') {
      // Complete query suggestions - auto-submit
      setInput(suggestion.text)
      setShowSuggestions(false)
      setTimeout(() => handleSubmit(new Event('submit') as any, suggestion.text), 100)
    } else {
      // Append metric/dimension/filter to current input
      const currentInput = input.trim()
      const newInput = currentInput 
        ? `${currentInput} ${suggestion.text}` 
        : suggestion.text
      setInput(newInput)
      // Fetch new suggestions based on updated input
      fetchSuggestions(newInput)
      inputRef.current?.focus()
    }
  }

  const handleSubmit = async (e: React.FormEvent, customInput?: string) => {
    e.preventDefault()
    const question = customInput || input.trim()
    if (!question || loading) return

    setInput('')
    setShowSuggestions(false)

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: question,
    }
    setMessages((prev) => [...prev, userMessage])
    
    // Save user message to session
    await saveMessage('user', question)

    // Update conversation context for follow-ups
    setConversationContext((prev) => [...prev, question])

    // Add loading message
    const loadingMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      loading: true,
    }
    setMessages((prev) => [...prev, loadingMessage])
    setLoading(true)

    try {
      const response = await axios.post(
        `${API_URL}/api/v1/query/natural`,
        { 
          question,
          connection_id: selectedConnectionId,
          context: conversationContext.slice(-3) // Send last 3 queries for context
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      const { data, metadata, success, needs_clarification, questions: clarificationQuestions } = response.data

      // Remove loading message and add response
      setMessages((prev) => {
        const filtered = prev.filter((m) => m.id !== loadingMessage.id)
        
        if (needs_clarification && clarificationQuestions) {
          const clarificationMsg = `I need clarification:\n\n${clarificationQuestions.join('\n')}`
          // Save clarification message
          saveMessage('assistant', clarificationMsg)
          
          return [
            ...filtered,
            {
              id: Date.now().toString(),
              role: 'assistant',
              content: clarificationMsg,
            },
          ]
        }
        
        if (success && data && data.length > 0) {
          const resultMsg = `Found ${data.length} result${data.length !== 1 ? 's' : ''}`
          // Save successful query result
          saveMessage('assistant', resultMsg, {
            sql_query: response.data.sql_query,
            data: data.slice(0, 100),
            metadata: {
              ...metadata,
              row_count: data.length
            }
          })
          
          return [
            ...filtered,
            {
              id: Date.now().toString(),
              role: 'assistant',
              content: resultMsg,
              data,
              metadata,
            },
          ]
        }

        const noResultMsg = response.data.message || 'No results found'
        saveMessage('assistant', noResultMsg)
        
        return [
          ...filtered,
          {
            id: Date.now().toString(),
            role: 'assistant',
            content: noResultMsg,
          },
        ]
      })
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || 'An error occurred'
      // Save error message
      await saveMessage('assistant', errorMsg, { error: true })
      
      setMessages((prev) => {
        const filtered = prev.filter((m) => m.id !== loadingMessage.id)
        return [
          ...filtered,
          {
            id: Date.now().toString(),
            role: 'assistant',
            content: errorMsg,
            error: true,
          },
        ]
      })
    } finally {
      setLoading(false)
    }
  }

  const exampleQueries = (() => {
    // First priority: Admin-generated examples
    if (adminExamples.length > 0) {
      return adminExamples.map(ex => ({
        text: ex.text,
        icon: ex.icon
      }))
    }
    
    // Second priority: Schema-based auto-generated examples
    if (schema) {
      const tableNames = Object.keys(schema.tables)
      const examples: { text: string; icon: string }[] = []
      
      if (tableNames.length > 0) {
        const firstTable = tableNames[0]
        const table = schema.tables[firstTable]
        const measures = table.columns.filter(c => c.is_measure)
        const dimensions = table.columns.filter(c => c.is_dimension)

        if (measures.length > 0) {
          const measure = measures[0].display_name || measures[0].name
          examples.push({
            text: `Show top 10 ${firstTable} by ${measure}`,
            icon: '📊'
          })
          
          if (dimensions.length > 0) {
            const dimension = dimensions[0].display_name || dimensions[0].name
            examples.push({
              text: `Total ${measure} by ${dimension}`,
              icon: '🗺️'
            })
          }
          
          examples.push({
            text: `Average ${measure} this month`,
            icon: '⏱️'
          })
        }
        
        if (measures.length > 1) {
          const measure2 = measures[1].display_name || measures[1].name
          examples.push({
            text: `Compare ${measure2} by ${firstTable}`,
            icon: '📈'
          })
        }
      }
      
      return examples.length > 0 ? examples : [
        { text: 'Show all records', icon: '📋' },
        { text: 'Count total rows', icon: '🔢' },
      ]
    }
    
    // Fallback: Loading state
    return [{ text: 'Loading examples...', icon: '⏳' }]
  })()

  return (
    <div className="flex flex-col h-full bg-gradient-to-b from-gray-50 to-white">
      {messages.length === 0 ? (
        /* Empty State - Centerpiece Search */
        <div className="flex-1 flex items-center justify-center px-6">
          <div className="max-w-4xl w-full">
            {/* Header */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl mb-6 shadow-lg">
                <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h1 className="text-4xl font-bold text-gray-900 mb-3">
                Ask Anything About Your Data
              </h1>
              <p className="text-lg text-gray-600 mb-4">
                Natural language queries with intelligent suggestions and follow-up context
              </p>
              
              {/* Connection Selector */}
              <div className="flex items-center justify-center space-x-3 mb-2">
                <label className="text-sm text-gray-600 font-medium">Database:</label>
                <select
                  value={selectedConnectionId}
                  onChange={(e) => onConnectionChange(e.target.value)}
                  className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                >
                  {connections.length === 0 && <option>Loading...</option>}
                  {connections.map((conn) => (
                    <option key={conn.id} value={conn.id}>
                      {conn.name} ({conn.database})
                    </option>
                  ))}
                </select>
                {schemaLoading && (
                  <svg className="w-4 h-4 text-blue-600 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                )}
              </div>
              
              {/* Schema Status */}
              {schema && (
                <div className="text-xs text-gray-500">
                  {schema.table_count} tables • {Object.values(schema.tables).reduce((sum, t) => sum + t.columns.length, 0)} columns loaded
                </div>
              )}
            </div>

            {/* Search Bar */}
            <div className="relative mb-8">
              <form onSubmit={handleSubmit} className="relative">
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-6 flex items-center pointer-events-none">
                    <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                  <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={handleInputChange}
                    onFocus={() => setShowSuggestions(true)}
                    placeholder="e.g., top agents by revenue last quarter..."
                    className="w-full pl-16 pr-32 py-5 text-lg border-2 border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-100 focus:border-blue-500 transition shadow-lg hover:shadow-xl"
                  />
                  <button
                    type="submit"
                    disabled={loading || !input.trim()}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 px-6 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl font-medium hover:from-blue-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
                  >
                    Ask
                  </button>
                </div>
              </form>

              {/* Suggestions Dropdown */}
              {showSuggestions && (suggestions.length > 0 || suggestionsLoading) && (
                <div ref={suggestionsContainerRef} className="absolute z-10 w-full mt-2 bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden">
                  {suggestionsLoading && suggestions.length === 0 ? (
                    <div className="px-6 py-4 flex items-center space-x-3 text-gray-500">
                      <svg className="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      <span className="text-sm">Generating suggestions...</span>
                    </div>
                  ) : (
                    suggestions.map((suggestion, index) => (
                      <button
                        key={index}
                        onClick={() => handleSuggestionClick(suggestion)}
                        className="w-full px-6 py-4 text-left hover:bg-blue-50 transition flex items-start space-x-3 border-b border-gray-100 last:border-b-0"
                      >
                        <span className="text-2xl flex-shrink-0">{suggestion.icon}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-gray-900 font-medium truncate">{suggestion.text}</div>
                          {suggestion.description && (
                            <div className="text-xs text-gray-500 mt-0.5">{suggestion.description}</div>
                          )}
                          <div className="text-xs text-blue-600 capitalize mt-1">
                            {suggestion.type === 'complete' ? '✨ Complete query' : suggestion.type}
                          </div>
                        </div>
                        <svg className="w-4 h-4 text-gray-400 flex-shrink-0 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Example Queries */}
            <div className="space-y-3">
              <p className="text-sm text-gray-500 font-medium">Try these examples:</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {exampleQueries.map((query, index) => (
                  <button
                    key={index}
                    onClick={() => {
                      setInput(query.text)
                      setTimeout(() => handleSubmit(new Event('submit') as any, query.text), 100)
                    }}
                    className="text-left p-4 bg-white rounded-xl border-2 border-gray-200 hover:border-blue-400 hover:shadow-md transition group"
                  >
                    <div className="flex items-center space-x-3">
                      <span className="text-2xl group-hover:scale-110 transition">{query.icon}</span>
                      <span className="text-gray-700 group-hover:text-blue-600 transition">{query.text}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Features */}
            <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">AI-Powered Suggestions</h3>
                <p className="text-sm text-gray-600">Intelligent query completions from your database schema and LLM</p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">Context-Aware</h3>
                <p className="text-sm text-gray-600">Suggestions adapt to selected database and available metrics</p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">Fast & Affordable</h3>
                <p className="text-sm text-gray-600">Debounced LLM calls with instant autocomplete fallback</p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Conversation View */
        <>
          {/* Connection Bar */}
          <div className="border-b border-gray-200 bg-white px-6 py-3">
            <div className="max-w-4xl mx-auto flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                </svg>
                <select
                  value={selectedConnectionId}
                  onChange={(e) => onConnectionChange(e.target.value)}
                  className="px-3 py-1.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                >
                  {connections.map((conn) => (
                    <option key={conn.id} value={conn.id}>
                      {conn.name} ({conn.database})
                    </option>
                  ))}
                </select>
              </div>
              {schema && (
                <div className="text-xs text-gray-500">
                  {schema.table_count} tables • {Object.values(schema.tables).reduce((sum, t) => sum + t.columns.length, 0)} columns
                </div>
              )}
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto px-6 py-6">
            <div className="max-w-4xl mx-auto space-y-6">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Sticky Input Bar */}
          <div className="border-t border-gray-200 bg-white px-6 py-4 shadow-lg">
            <div className="max-w-4xl mx-auto">
              <div className="relative">
                <form onSubmit={handleSubmit}>
                  <div className="relative">
                    <input
                      ref={inputRef}
                      type="text"
                      value={input}
                      onChange={handleInputChange}
                      onFocus={() => setShowSuggestions(true)}
                      placeholder="Ask a follow-up question..."
                      className="w-full pl-6 pr-32 py-4 text-base border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                      disabled={loading}
                    />
                    <button
                      type="submit"
                      disabled={loading || !input.trim()}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loading ? (
                        <svg className="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                      ) : (
                        'Ask'
                      )}
                    </button>
                  </div>
                </form>

                {/* Suggestions Dropdown in conversation view */}
                {showSuggestions && suggestions.length > 0 && (
                  <div className="absolute bottom-full mb-2 z-10 w-full bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden">
                    {suggestions.map((suggestion, index) => (
                      <button
                        key={index}
                        onClick={() => handleSuggestionClick(suggestion)}
                        className="w-full px-4 py-3 text-left hover:bg-gray-50 transition flex items-center space-x-3 border-b border-gray-100 last:border-b-0"
                      >
                        <span className="text-xl">{suggestion.icon}</span>
                        <div className="flex-1">
                          <div className="text-gray-900 text-sm font-medium">{suggestion.text}</div>
                          <div className="text-xs text-gray-500 capitalize">{suggestion.type}</div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {conversationContext.length > 0 && (
                <div className="mt-3 text-xs text-gray-500">
                  Context: {conversationContext.length} previous {conversationContext.length === 1 ? 'query' : 'queries'}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
