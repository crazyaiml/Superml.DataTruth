import { useNavigate } from 'react-router-dom'

export default function RoadmapPage() {
  const navigate = useNavigate()

  const roadmapItems = [
    {
      quarter: 'Q1 2026',
      status: 'In Progress',
      color: 'blue',
      features: [
        {
          title: 'Advanced Collaboration',
          description: 'Share dashboards, insights, and queries with team comments and annotations',
          icon: '👥',
          priority: 'high'
        },
        {
          title: 'Custom Visual Plugins',
          description: 'SDK for building custom visualizations and integrating third-party charting libraries',
          icon: '🎨',
          priority: 'high'
        },
        {
          title: 'Slack & Teams Integration',
          description: 'Receive alerts and query data directly from Slack/Teams',
          icon: '💬',
          priority: 'medium'
        }
      ]
    },
    {
      quarter: 'Q2 2026',
      status: 'Planned',
      color: 'purple',
      features: [
        {
          title: 'Real-Time Streaming Support',
          description: 'Connect to Kafka, Kinesis, and other streaming platforms for real-time analytics',
          icon: '⚡',
          priority: 'high'
        },
        {
          title: 'Snowflake & BigQuery Connectors',
          description: 'Native integrations with cloud data warehouses',
          icon: '☁️',
          priority: 'high'
        },
        {
          title: 'Advanced Forecasting',
          description: 'Prophet and ARIMA models for time-series forecasting',
          icon: '📈',
          priority: 'medium'
        },
        {
          title: 'Mobile App (iOS & Android)',
          description: 'Native mobile apps for on-the-go data access',
          icon: '📱',
          priority: 'medium'
        }
      ]
    },
    {
      quarter: 'Q3 2026',
      status: 'Planned',
      color: 'green',
      features: [
        {
          title: 'Multi-Database Queries',
          description: 'Join data across multiple databases in a single query',
          icon: '🔗',
          priority: 'high'
        },
        {
          title: 'Advanced RBAC',
          description: 'Row-level and column-level security with dynamic policies',
          icon: '🔐',
          priority: 'high'
        },
        {
          title: 'Embedded Analytics',
          description: 'Embed DataTruth dashboards into your own applications',
          icon: '🖼️',
          priority: 'medium'
        },
        {
          title: 'Automated Alerting',
          description: 'Set up custom alerts based on data thresholds and anomalies',
          icon: '🔔',
          priority: 'medium'
        }
      ]
    },
    {
      quarter: 'Q4 2026',
      status: 'Planned',
      color: 'orange',
      features: [
        {
          title: 'Python/R Notebooks Integration',
          description: 'Seamless integration with Jupyter and RStudio for advanced analytics',
          icon: '📓',
          priority: 'high'
        },
        {
          title: 'ML Model Deployment',
          description: 'Deploy and monitor ML models directly within DataTruth',
          icon: '🤖',
          priority: 'medium'
        },
        {
          title: 'Custom Data Transformations',
          description: 'Visual ETL builder for data preparation and transformation',
          icon: '🔄',
          priority: 'medium'
        },
        {
          title: 'Webhook API',
          description: 'Trigger external workflows based on data events',
          icon: '🪝',
          priority: 'low'
        }
      ]
    }
  ]

  const recentlyShipped = [
    {
      title: 'SaaS Deployment Mode',
      description: 'Web-based setup wizard with one-command deployment',
      date: 'December 2025',
      icon: '🚀'
    },
    {
      title: 'User Activity Tracking',
      description: 'Comprehensive audit logs and user behavior analytics',
      date: 'November 2025',
      icon: '📊'
    },
    {
      title: 'Calculated Metrics Engine',
      description: 'Create custom business metrics with SQL-like expressions',
      date: 'November 2025',
      icon: '🧮'
    },
    {
      title: 'Chat Sessions & History',
      description: 'Save and resume analysis sessions with full context',
      date: 'October 2025',
      icon: '💬'
    }
  ]

  const communityRequests = [
    {
      title: 'MongoDB Support',
      votes: 47,
      status: 'Under Review'
    },
    {
      title: 'Excel Export with Formatting',
      votes: 34,
      status: 'Planned'
    },
    {
      title: 'Dark Mode UI',
      votes: 28,
      status: 'In Progress'
    },
    {
      title: 'API Rate Limit Customization',
      votes: 19,
      status: 'Under Review'
    }
  ]

  const getPriorityBadge = (priority: string) => {
    const badges = {
      high: 'bg-red-100 text-red-700 border-red-200',
      medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      low: 'bg-green-100 text-green-700 border-green-200'
    }
    return badges[priority as keyof typeof badges] || badges.medium
  }

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
              <p className="text-xs text-gray-500">Product Roadmap</p>
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
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
          </div>
          <h2 className="text-5xl font-bold text-gray-900 mb-4">
            Our Vision for
            <span className="block mt-2 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              The Future
            </span>
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            We're constantly innovating to make data analytics more accessible, powerful, and intelligent. 
            Here's what's coming next.
          </p>
        </div>

        {/* Recently Shipped */}
        <div className="mb-20">
          <h3 className="text-3xl font-bold text-gray-900 mb-8 flex items-center">
            <svg className="w-8 h-8 text-green-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Recently Shipped
          </h3>
          
          <div className="grid md:grid-cols-2 gap-6">
            {recentlyShipped.map((item) => (
              <div key={item.title} className="bg-white rounded-xl p-6 shadow-lg border-2 border-green-200">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center">
                    <span className="text-3xl mr-3">{item.icon}</span>
                    <div>
                      <h4 className="text-lg font-bold text-gray-900">{item.title}</h4>
                      <p className="text-sm text-gray-500">{item.date}</p>
                    </div>
                  </div>
                  <span className="px-3 py-1 bg-green-100 text-green-700 text-xs font-semibold rounded-full">
                    Shipped ✓
                  </span>
                </div>
                <p className="text-gray-600 text-sm">{item.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Roadmap Timeline */}
        <div className="mb-20">
          <h3 className="text-3xl font-bold text-gray-900 mb-12 text-center">What's Next</h3>
          
          <div className="space-y-12">
            {roadmapItems.map((quarter, qIndex) => (
              <div key={quarter.quarter} className="relative">
                {/* Quarter Header */}
                <div className="flex items-center mb-6">
                  <div className={`bg-gradient-to-r from-${quarter.color}-600 to-${quarter.color}-700 text-white px-6 py-3 rounded-xl font-bold text-xl shadow-lg`}>
                    {quarter.quarter}
                  </div>
                  <div className="ml-4">
                    <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                      quarter.status === 'In Progress' 
                        ? 'bg-blue-100 text-blue-700' 
                        : 'bg-gray-100 text-gray-700'
                    }`}>
                      {quarter.status}
                    </span>
                  </div>
                </div>

                {/* Features Grid */}
                <div className="grid md:grid-cols-2 gap-6 ml-8">
                  {quarter.features.map((feature) => (
                    <div key={feature.title} className="bg-white rounded-xl p-6 shadow-md border border-gray-200 hover:shadow-lg transition-shadow">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center">
                          <span className="text-3xl mr-3">{feature.icon}</span>
                          <h4 className="text-lg font-bold text-gray-900">{feature.title}</h4>
                        </div>
                        <span className={`px-2 py-1 rounded border text-xs font-semibold ${getPriorityBadge(feature.priority)}`}>
                          {feature.priority.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-gray-600 text-sm">{feature.description}</p>
                    </div>
                  ))}
                </div>

                {/* Connector Line (except for last item) */}
                {qIndex < roadmapItems.length - 1 && (
                  <div className="absolute left-8 top-16 bottom-0 w-0.5 bg-gray-200 -z-10"></div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Community Requests */}
        <div className="mb-20">
          <h3 className="text-3xl font-bold text-gray-900 mb-8 text-center">Top Community Requests</h3>
          <p className="text-gray-600 text-center mb-8">Vote on features you'd like to see next</p>
          
          <div className="max-w-3xl mx-auto space-y-4">
            {communityRequests.map((request) => (
              <div key={request.title} className="bg-white rounded-xl p-6 shadow-md border border-gray-200 flex items-center justify-between hover:shadow-lg transition-shadow">
                <div className="flex items-center flex-1">
                  <div className="text-center mr-6">
                    <button className="w-12 h-12 bg-blue-50 hover:bg-blue-100 rounded-lg flex flex-col items-center justify-center transition">
                      <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                      </svg>
                      <span className="text-sm font-bold text-gray-900">{request.votes}</span>
                    </button>
                  </div>
                  <div>
                    <h4 className="text-lg font-bold text-gray-900">{request.title}</h4>
                  </div>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                  request.status === 'In Progress'
                    ? 'bg-blue-100 text-blue-700'
                    : request.status === 'Planned'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-gray-100 text-gray-700'
                }`}>
                  {request.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* CTA Section */}
        <div className="bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl p-12 text-white text-center">
          <h3 className="text-3xl font-bold mb-4">Have a feature request?</h3>
          <p className="text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
            We'd love to hear from you. Join our community and shape the future of DataTruth.
          </p>
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={() => navigate('/')}
              className="px-8 py-4 bg-white text-blue-600 font-semibold rounded-xl hover:bg-gray-100 transition-all duration-300 shadow-lg"
            >
              Submit Feature Request
            </button>
            <button
              onClick={() => navigate('/')}
              className="px-8 py-4 bg-transparent border-2 border-white text-white font-semibold rounded-xl hover:bg-white/10 transition-all duration-300"
            >
              Join Community
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
