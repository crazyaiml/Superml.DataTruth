import { useNavigate } from 'react-router-dom'

export default function TechnologyPage() {
  const navigate = useNavigate()

  const aiCapabilities = [
    {
      title: 'Advanced Anomaly Detection',
      icon: '🔍',
      description: 'Our proprietary ensemble model combines statistical methods with ML',
      techniques: [
        {
          name: 'Isolation Forest',
          use: 'Detects multivariate outliers in high-dimensional data'
        },
        {
          name: 'DBSCAN Clustering',
          use: 'Identifies density-based anomalies in behavioral patterns'
        },
        {
          name: 'Z-Score & IQR',
          use: 'Statistical baseline for univariate anomaly detection'
        },
        {
          name: 'Seasonal Decomposition',
          use: 'Identifies anomalies in time-series with trends & seasonality'
        }
      ],
      differentiator: 'Unlike simple threshold alerts, we adapt to your data patterns and reduce false positives by 85%'
    },
    {
      title: 'Intelligent Query Understanding',
      icon: '🧠',
      description: 'Context-aware NLP that understands your business domain',
      techniques: [
        {
          name: 'Semantic Layer Integration',
          use: 'Maps business terms to database schema automatically'
        },
        {
          name: 'Intent Classification',
          use: 'Understands whether you want aggregation, trends, or comparisons'
        },
        {
          name: 'Entity Recognition',
          use: 'Identifies tables, columns, and filters from natural language'
        },
        {
          name: 'Context Awareness',
          use: 'Remembers conversation history for follow-up questions'
        }
      ],
      differentiator: 'Most tools require perfect phrasing. We understand variations, synonyms, and context like a human analyst'
    },
    {
      title: 'Smart Data Quality Scoring',
      icon: '✅',
      description: 'Multi-dimensional quality assessment beyond simple null checks',
      techniques: [
        {
          name: 'Completeness Analysis',
          use: 'Null rates, missing patterns, and expected vs actual records'
        },
        {
          name: 'Consistency Checking',
          use: 'Cross-field validation and referential integrity'
        },
        {
          name: 'Accuracy Estimation',
          use: 'Pattern matching, format validation, and business rule checks'
        },
        {
          name: 'Timeliness Tracking',
          use: 'Data freshness and update frequency monitoring'
        }
      ],
      differentiator: 'We provide actionable quality scores with specific recommendations, not just red/green indicators'
    }
  ]

  const architectureFeatures = [
    {
      title: 'Zero Data Movement',
      description: 'Queries execute directly on your database. We never copy or cache your data.',
      icon: '🔒',
      color: 'blue'
    },
    {
      title: 'Optimized Query Engine',
      description: 'Intelligent query optimization reduces execution time by 10-50x compared to naive translations.',
      icon: '⚡',
      color: 'yellow'
    },
    {
      title: 'Vector Database for Semantics',
      description: 'ChromaDB stores schema embeddings for lightning-fast semantic search and matching.',
      icon: '🎯',
      color: 'purple'
    },
    {
      title: 'Incremental Learning',
      description: 'System learns from user feedback to improve query accuracy and suggestions over time.',
      icon: '📚',
      color: 'green'
    }
  ]

  const technicalSpecs = [
    {
      category: 'Performance',
      specs: [
        { label: 'Query Response Time', value: '< 2 seconds avg' },
        { label: 'Concurrent Users', value: '1000+' },
        { label: 'Database Size Support', value: 'Up to 100TB' },
        { label: 'Query Throughput', value: '10,000 queries/hour' }
      ]
    },
    {
      category: 'Reliability',
      specs: [
        { label: 'System Uptime', value: '99.9% SLA' },
        { label: 'Query Success Rate', value: '98.5%' },
        { label: 'Automatic Failover', value: '< 30 seconds' },
        { label: 'Data Consistency', value: 'Read-after-write' }
      ]
    },
    {
      category: 'Scalability',
      specs: [
        { label: 'Horizontal Scaling', value: 'Auto-scaling enabled' },
        { label: 'Load Balancing', value: 'Built-in' },
        { label: 'Caching Strategy', value: 'Multi-tier adaptive' },
        { label: 'Connection Pooling', value: 'Optimized per DB' }
      ]
    }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div 
            className="flex items-center space-x-3 cursor-pointer"
            onClick={() => navigate('/')}
          >
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-xl flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                DataTruth
              </h1>
              <p className="text-xs text-gray-500">Technology & Architecture</p>
            </div>
          </div>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-white/50 rounded-lg transition"
          >
            ← Back to Home
          </button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-16">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-600 to-purple-600 rounded-2xl mb-6">
            <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h2 className="text-5xl font-bold text-gray-900 mb-4">
            The Technology That
            <span className="block mt-2 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Powers Intelligence
            </span>
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Advanced AI algorithms and optimized architecture that sets DataTruth apart from generic analytics tools
          </p>
        </div>

        {/* AI Capabilities Deep Dive */}
        <div className="mb-20">
          <h3 className="text-3xl font-bold text-gray-900 text-center mb-12">
            AI That Actually Understands Your Data
          </h3>
          
          {aiCapabilities.map((capability, index) => (
            <div key={capability.title} className="mb-12">
              <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
                <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-6">
                  <div className="flex items-center text-white">
                    <span className="text-4xl mr-4">{capability.icon}</span>
                    <div>
                      <h4 className="text-2xl font-bold">{capability.title}</h4>
                      <p className="text-blue-100">{capability.description}</p>
                    </div>
                  </div>
                </div>
                
                <div className="p-8">
                  <div className="grid md:grid-cols-2 gap-6 mb-6">
                    {capability.techniques.map((technique) => (
                      <div key={technique.name} className="bg-gray-50 rounded-xl p-6 border border-gray-200">
                        <h5 className="font-bold text-gray-900 mb-2 flex items-center">
                          <svg className="w-5 h-5 text-blue-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          {technique.name}
                        </h5>
                        <p className="text-gray-600 text-sm">{technique.use}</p>
                      </div>
                    ))}
                  </div>
                  
                  <div className="bg-blue-50 border-l-4 border-blue-600 p-4 rounded">
                    <p className="text-gray-900 flex items-start">
                      <svg className="w-6 h-6 text-blue-600 mr-3 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                      <span><strong>What Makes Us Different:</strong> {capability.differentiator}</span>
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Architecture Features */}
        <div className="mb-20">
          <h3 className="text-3xl font-bold text-gray-900 text-center mb-12">
            Built for Performance & Security
          </h3>
          
          <div className="grid md:grid-cols-2 gap-8">
            {architectureFeatures.map((feature) => (
              <div key={feature.title} className="bg-white rounded-2xl p-8 shadow-lg border border-gray-100 hover:shadow-xl transition-shadow">
                <div className={`w-14 h-14 bg-${feature.color}-100 rounded-xl flex items-center justify-center text-3xl mb-4`}>
                  {feature.icon}
                </div>
                <h4 className="text-xl font-bold text-gray-900 mb-3">{feature.title}</h4>
                <p className="text-gray-600">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Technical Specifications */}
        <div className="mb-20">
          <h3 className="text-3xl font-bold text-gray-900 text-center mb-12">
            Technical Specifications
          </h3>
          
          <div className="grid md:grid-cols-3 gap-8">
            {technicalSpecs.map((category) => (
              <div key={category.category} className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
                <div className="bg-gradient-to-r from-gray-800 to-gray-900 p-6">
                  <h4 className="text-xl font-bold text-white">{category.category}</h4>
                </div>
                <div className="p-6">
                  <ul className="space-y-4">
                    {category.specs.map((spec) => (
                      <li key={spec.label} className="flex justify-between items-start">
                        <span className="text-gray-600 text-sm">{spec.label}</span>
                        <span className="font-semibold text-gray-900 text-sm">{spec.value}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Architecture Diagram Section */}
        <div className="mb-20">
          <h3 className="text-3xl font-bold text-gray-900 text-center mb-12">
            System Architecture
          </h3>
          
          <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-12">
            <div className="max-w-4xl mx-auto">
              <div className="text-center mb-8">
                <h4 className="text-xl font-bold text-gray-900 mb-2">Secure, Scalable, Fast</h4>
                <p className="text-gray-600">Every component optimized for enterprise performance</p>
              </div>
              
              {/* Simple architecture flow diagram */}
              <div className="flex flex-col gap-6">
                {/* User Layer */}
                <div className="bg-blue-50 rounded-xl p-6 border-2 border-blue-200">
                  <h5 className="font-bold text-blue-900 mb-2">Frontend Layer</h5>
                  <p className="text-sm text-gray-700">React + TypeScript • Real-time WebSocket • Responsive Design</p>
                </div>
                
                <div className="flex justify-center">
                  <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                  </svg>
                </div>
                
                {/* API Layer */}
                <div className="bg-purple-50 rounded-xl p-6 border-2 border-purple-200">
                  <h5 className="font-bold text-purple-900 mb-2">API & Intelligence Layer</h5>
                  <p className="text-sm text-gray-700">FastAPI • NLP Engine • Query Optimizer • Authentication & RBAC</p>
                </div>
                
                <div className="flex justify-center">
                  <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                  </svg>
                </div>
                
                {/* Data Layer */}
                <div className="grid grid-cols-2 gap-6">
                  <div className="bg-green-50 rounded-xl p-6 border-2 border-green-200">
                    <h5 className="font-bold text-green-900 mb-2">Metadata Store</h5>
                    <p className="text-sm text-gray-700">PostgreSQL • Schema Cache • User Prefs</p>
                  </div>
                  <div className="bg-indigo-50 rounded-xl p-6 border-2 border-indigo-200">
                    <h5 className="font-bold text-indigo-900 mb-2">Vector DB</h5>
                    <p className="text-sm text-gray-700">ChromaDB • Semantic Search • Embeddings</p>
                  </div>
                </div>
                
                <div className="flex justify-center">
                  <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                  </svg>
                </div>
                
                {/* Your Database */}
                <div className="bg-orange-50 rounded-xl p-6 border-2 border-orange-200">
                  <h5 className="font-bold text-orange-900 mb-2">Your Database (Zero Copy)</h5>
                  <p className="text-sm text-gray-700">Direct queries • No data movement • Secure connections</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl p-12 text-white text-center">
          <h3 className="text-3xl font-bold mb-4">See the technology in action</h3>
          <p className="text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
            Schedule a technical deep-dive with our engineering team
          </p>
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={() => navigate('/')}
              className="px-8 py-4 bg-white text-blue-600 font-semibold rounded-xl hover:bg-gray-100 transition-all duration-300 shadow-lg"
            >
              Request Technical Demo
            </button>
            <button
              onClick={() => navigate('/')}
              className="px-8 py-4 bg-transparent border-2 border-white text-white font-semibold rounded-xl hover:bg-white/10 transition-all duration-300"
            >
              View Documentation
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
