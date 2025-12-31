import { useNavigate } from 'react-router-dom'

export default function CaseStudiesPage() {
  const navigate = useNavigate()

  const caseStudies = [
    {
      company: 'TechCorp Analytics',
      industry: 'SaaS Technology',
      size: '500+ employees',
      logo: '🚀',
      challenge: 'Data scattered across 15 PostgreSQL databases with no unified view. Business analysts spent 60% of their time writing SQL queries instead of analyzing data.',
      solution: 'Deployed DataTruth to connect all databases with a unified semantic layer. Enabled natural language queries for non-technical teams.',
      results: [
        '70% reduction in time spent on data queries',
        '3x increase in data-driven decision making',
        'Analysts now spend 80% time on insights vs. query writing',
        'Discovered $2M in revenue optimization opportunities'
      ],
      testimonial: {
        quote: 'DataTruth transformed how our team works with data. What used to take hours now takes minutes. Our analysts are finally doing what they were hired to do—analyze, not wrangle SQL.',
        author: 'Sarah Chen',
        title: 'VP of Data & Analytics'
      },
      color: 'blue'
    },
    {
      company: 'HealthFirst Medical',
      industry: 'Healthcare',
      size: '2,000+ employees',
      logo: '🏥',
      challenge: 'HIPAA compliance requirements made data access complex. Clinical teams needed insights but couldn\'t access databases directly due to security constraints.',
      solution: 'Implemented DataTruth with role-based access control and audit logging. Enabled secure, governed data access with complete audit trails.',
      results: [
        '100% HIPAA compliance maintained',
        'Reduced data request turnaround from 3 days to 5 minutes',
        'Enabled 200+ clinical staff to self-serve data insights',
        'Improved patient outcome tracking by 45%'
      ],
      testimonial: {
        quote: 'Security and compliance were non-negotiable for us. DataTruth delivered enterprise-grade governance while making data accessible to our clinical teams. It\'s the best of both worlds.',
        author: 'Dr. Michael Rodriguez',
        title: 'Chief Medical Information Officer'
      },
      color: 'green'
    },
    {
      company: 'RetailMax Inc.',
      industry: 'E-commerce Retail',
      size: '10,000+ employees',
      logo: '🛍️',
      challenge: 'Real-time inventory and sales data across 500 stores. Business teams couldn\'t identify trends or anomalies until weekly reports, missing critical opportunities.',
      solution: 'Connected DataTruth to their data warehouse with automated anomaly detection and trend analysis across all stores and product categories.',
      results: [
        'Detected inventory issues 5 days earlier than before',
        'Identified $5M in lost revenue from pricing anomalies',
        'Automated 90% of standard analytics reports',
        'Reduced stockout incidents by 38%'
      ],
      testimonial: {
        quote: 'The AI-powered anomaly detection has been a game-changer. We now catch problems before they impact revenue. The ROI paid for itself in the first quarter.',
        author: 'James Patterson',
        title: 'Chief Operations Officer'
      },
      color: 'purple'
    }
  ]

  const useCases = [
    {
      title: 'Financial Services',
      icon: '💰',
      description: 'Transaction monitoring, fraud detection, and compliance reporting',
      benefits: ['Real-time fraud alerts', 'Automated compliance reporting', 'Risk pattern identification']
    },
    {
      title: 'Manufacturing',
      icon: '🏭',
      description: 'Supply chain optimization and quality control analytics',
      benefits: ['Production bottleneck detection', 'Quality trend analysis', 'Supplier performance tracking']
    },
    {
      title: 'Education',
      icon: '🎓',
      description: 'Student performance analysis and institutional planning',
      benefits: ['Early intervention identification', 'Resource allocation optimization', 'Enrollment trend forecasting']
    },
    {
      title: 'Marketing & Sales',
      icon: '📊',
      description: 'Campaign performance and customer behavior insights',
      benefits: ['ROI tracking by channel', 'Customer journey analysis', 'Churn prediction modeling']
    }
  ]

  const metrics = [
    { value: '500+', label: 'Enterprise Customers' },
    { value: '10M+', label: 'Queries Processed' },
    { value: '70%', label: 'Avg. Time Savings' },
    { value: '98%', label: 'Customer Satisfaction' }
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
              <p className="text-xs text-gray-500">Customer Success Stories</p>
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
          <h2 className="text-5xl font-bold text-gray-900 mb-4">
            Real Results From
            <span className="block mt-2 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Real Companies
            </span>
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            See how organizations across industries are transforming their data analytics with DataTruth
          </p>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-20">
          {metrics.map((metric) => (
            <div key={metric.label} className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100 text-center">
              <div className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
                {metric.value}
              </div>
              <div className="text-gray-600 text-sm">{metric.label}</div>
            </div>
          ))}
        </div>

        {/* Case Studies */}
        {caseStudies.map((study, index) => (
          <div key={study.company} className={`mb-20 ${index % 2 === 1 ? 'bg-gray-50' : ''} rounded-3xl p-8 md:p-12`}>
            <div className="max-w-6xl mx-auto">
              {/* Header */}
              <div className="flex items-start justify-between mb-8">
                <div className="flex items-center space-x-4">
                  <div className={`w-16 h-16 bg-${study.color}-100 rounded-2xl flex items-center justify-center text-3xl`}>
                    {study.logo}
                  </div>
                  <div>
                    <h3 className="text-3xl font-bold text-gray-900">{study.company}</h3>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-gray-600">{study.industry}</span>
                      <span className="text-gray-400">•</span>
                      <span className="text-gray-600">{study.size}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-8 mb-8">
                {/* Challenge */}
                <div>
                  <h4 className="text-xl font-bold text-gray-900 mb-3 flex items-center">
                    <svg className="w-6 h-6 text-red-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    The Challenge
                  </h4>
                  <p className="text-gray-700 leading-relaxed">{study.challenge}</p>
                </div>

                {/* Solution */}
                <div>
                  <h4 className="text-xl font-bold text-gray-900 mb-3 flex items-center">
                    <svg className="w-6 h-6 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    The Solution
                  </h4>
                  <p className="text-gray-700 leading-relaxed">{study.solution}</p>
                </div>
              </div>

              {/* Results */}
              <div className="bg-white rounded-2xl p-6 mb-8">
                <h4 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                  <svg className="w-6 h-6 text-blue-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                  Results & Impact
                </h4>
                <div className="grid md:grid-cols-2 gap-4">
                  {study.results.map((result, idx) => (
                    <div key={idx} className="flex items-start">
                      <svg className="w-5 h-5 text-green-500 mr-3 flex-shrink-0 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-gray-700">{result}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Testimonial */}
              <div className={`bg-gradient-to-br from-${study.color}-600 to-${study.color}-700 rounded-2xl p-8 text-white`}>
                <svg className="w-10 h-10 text-white/30 mb-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10h-9.983zm-14.017 0v-7.391c0-5.704 3.748-9.57 9-10.609l.996 2.151c-2.433.917-3.996 3.638-3.996 5.849h3.983v10h-9.983z" />
                </svg>
                <p className="text-xl leading-relaxed mb-6 italic">
                  "{study.testimonial.quote}"
                </p>
                <div>
                  <div className="font-bold text-lg">{study.testimonial.author}</div>
                  <div className="text-white/80">{study.testimonial.title}</div>
                </div>
              </div>
            </div>
          </div>
        ))}

        {/* Use Cases */}
        <div className="mb-20">
          <div className="text-center mb-12">
            <h3 className="text-3xl font-bold text-gray-900 mb-4">More Industries We Serve</h3>
            <p className="text-lg text-gray-600">DataTruth adapts to your industry's unique needs</p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            {useCases.map((useCase) => (
              <div key={useCase.title} className="bg-white rounded-2xl p-8 shadow-lg border border-gray-100">
                <div className="flex items-center mb-4">
                  <div className="text-4xl mr-4">{useCase.icon}</div>
                  <div>
                    <h4 className="text-xl font-bold text-gray-900">{useCase.title}</h4>
                    <p className="text-gray-600 text-sm">{useCase.description}</p>
                  </div>
                </div>
                <ul className="space-y-2">
                  {useCase.benefits.map((benefit, idx) => (
                    <li key={idx} className="flex items-start text-sm">
                      <svg className="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-gray-700">{benefit}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* CTA Section */}
        <div className="bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl p-12 text-white text-center">
          <h3 className="text-3xl font-bold mb-4">Ready to write your success story?</h3>
          <p className="text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
            Join these companies and hundreds more transforming their data analytics
          </p>
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={() => navigate('/')}
              className="px-8 py-4 bg-white text-blue-600 font-semibold rounded-xl hover:bg-gray-100 transition-all duration-300 shadow-lg"
            >
              Start Free Trial
            </button>
            <button
              onClick={() => navigate('/')}
              className="px-8 py-4 bg-transparent border-2 border-white text-white font-semibold rounded-xl hover:bg-white/10 transition-all duration-300"
            >
              Request Demo
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
