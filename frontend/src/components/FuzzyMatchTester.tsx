import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import axios from 'axios'
import { API_URL } from '../config'

interface MatchResult {
  matched_value: string
  score: number
  match_type: string
}

interface Correction {
  original: string
  suggestion: string
  score: number
}

export default function FuzzyMatchTester() {
  const { token } = useAuth()
  const [query, setQuery] = useState('')
  const [candidates, setCandidates] = useState('revenue\nprofit\ncost\ncustomer\nquantity')
  const [threshold, setThreshold] = useState(0.75)
  const [matches, setMatches] = useState<MatchResult[]>([])
  const [corrections, setCorrections] = useState<Correction[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'match' | 'correct'>('match')

  const handleFuzzyMatch = async () => {
    if (!query.trim()) return

    setLoading(true)
    try {
      const candidateList = candidates.split('\n').map((c) => c.trim()).filter(Boolean)
      const response = await axios.post(
        `${API_URL}/api/v1/matching/fuzzy-match`,
        {
          query: query.trim(),
          candidates: candidateList,
          threshold,
          max_results: 10,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      )

      setMatches(response.data.matches || [])
    } catch (error) {
      console.error('Failed to fetch matches:', error)
      setMatches([])
    } finally {
      setLoading(false)
    }
  }

  const handleSuggestCorrections = async () => {
    if (!query.trim()) return

    setLoading(true)
    try {
      const validTerms = candidates.split('\n').map((c) => c.trim()).filter(Boolean)
      const response = await axios.post(
        `${API_URL}/api/v1/matching/corrections`,
        {
          text: query.trim(),
          valid_terms: validTerms,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      )

      setCorrections(response.data.corrections || [])
    } catch (error) {
      console.error('Failed to fetch corrections:', error)
      setCorrections([])
    } finally {
      setLoading(false)
    }
  }

  const getMatchTypeColor = (type: string) => {
    switch (type) {
      case 'exact':
        return 'bg-green-100 text-green-800'
      case 'abbreviation':
        return 'bg-blue-100 text-blue-800'
      case 'fuzzy':
        return 'bg-yellow-100 text-yellow-800'
      case 'phonetic':
        return 'bg-purple-100 text-purple-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 0.9) return 'text-green-600'
    if (score >= 0.75) return 'text-yellow-600'
    return 'text-orange-600'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Fuzzy Matching Tester</h2>
        <p className="text-sm text-gray-600 mt-1">Test typo-tolerant string matching with multiple strategies</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('match')}
            className={`py-4 px-1 border-b-2 font-medium text-sm transition ${
              activeTab === 'match'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Fuzzy Match
          </button>
          <button
            onClick={() => setActiveTab('correct')}
            className={`py-4 px-1 border-b-2 font-medium text-sm transition ${
              activeTab === 'correct'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Suggest Corrections
          </button>
        </nav>
      </div>

      {/* Input Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Query Text</label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., revenu, kalifornia, tot"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-gray-500">Enter text with typos or abbreviations</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Valid Terms (one per line)</label>
            <textarea
              value={candidates}
              onChange={(e) => setCandidates(e.target.value)}
              rows={8}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
            />
            <p className="mt-1 text-xs text-gray-500">List of valid terms to match against</p>
          </div>

          {activeTab === 'match' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Similarity Threshold: {(threshold * 100).toFixed(0)}%
              </label>
              <input
                type="range"
                min="0.5"
                max="1.0"
                step="0.05"
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>50%</span>
                <span>75%</span>
                <span>100%</span>
              </div>
            </div>
          )}

          <button
            onClick={activeTab === 'match' ? handleFuzzyMatch : handleSuggestCorrections}
            disabled={loading || !query.trim()}
            className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Processing...
              </span>
            ) : activeTab === 'match' ? (
              'Find Matches'
            ) : (
              'Suggest Corrections'
            )}
          </button>
        </div>

        {/* Results Section */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            {activeTab === 'match' ? 'Match Results' : 'Correction Suggestions'}
          </h3>

          {activeTab === 'match' ? (
            matches.length > 0 ? (
              <div className="space-y-3">
                {matches.map((match, idx) => (
                  <div key={idx} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-gray-900">{match.matched_value}</span>
                      <span className={`text-sm font-semibold ${getScoreColor(match.score)}`}>
                        {(match.score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${getMatchTypeColor(match.match_type)}`}>
                        {match.match_type}
                      </span>
                      <div className="flex-1 mx-4 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${match.score * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <p className="mt-4 text-sm text-gray-600">
                  {query ? 'No matches found above threshold' : 'Enter a query to find matches'}
                </p>
              </div>
            )
          ) : corrections.length > 0 ? (
            <div className="space-y-3">
              {corrections.map((correction, idx) => (
                <div key={idx} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="flex items-center space-x-3 mb-2">
                    <span className="text-gray-500 line-through">{correction.original}</span>
                    <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                    <span className="font-medium text-gray-900">{correction.suggestion}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="flex-1 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-green-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${correction.score * 100}%` }}
                      ></div>
                    </div>
                    <span className={`text-sm font-semibold ${getScoreColor(correction.score)}`}>
                      {(correction.score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="mt-4 text-sm text-gray-600">
                {query ? 'No corrections needed' : 'Enter text to get correction suggestions'}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Info Section */}
      <div className="bg-blue-50 rounded-xl border border-blue-200 p-6">
        <h4 className="text-sm font-semibold text-blue-900 mb-3">Match Types Explained</h4>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="inline-block px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-medium mb-2">
              Exact
            </span>
            <p className="text-gray-700">Case-insensitive exact match (100% score)</p>
          </div>
          <div>
            <span className="inline-block px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium mb-2">
              Abbreviation
            </span>
            <p className="text-gray-700">Expands common abbreviations like "rev" → "revenue"</p>
          </div>
          <div>
            <span className="inline-block px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs font-medium mb-2">
              Fuzzy
            </span>
            <p className="text-gray-700">Similarity-based matching for typos</p>
          </div>
          <div>
            <span className="inline-block px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs font-medium mb-2">
              Phonetic
            </span>
            <p className="text-gray-700">Sound-based matching for misspellings</p>
          </div>
        </div>
      </div>
    </div>
  )
}
