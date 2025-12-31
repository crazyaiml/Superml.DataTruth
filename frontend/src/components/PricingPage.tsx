import { useNavigate } from 'react-router-dom'
import { useState } from 'react'

export default function PricingPage() {
  const navigate = useNavigate()
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('monthly')

  const plans = [
    {
      name: 'Starter',
      description: 'Perfect for small teams getting started',
      monthlyPrice: 99,
      annualPrice: 990,
      features: [
        'Up to 5 users',
        '2 database connections',
        '1,000 queries/month',
        'Basic insights & analytics',
        'Email support',
        'Community access',
        'Data quality monitoring',
        'Standard security'
      ],
      cta: 'Start Free Trial',
      highlighted: false
    },
    {
      name: 'Professional',
      description: 'For growing teams with advanced needs',
      monthlyPrice: 299,
      annualPrice: 2990,
      features: [
        'Up to 25 users',
        '10 database connections',
        '10,000 queries/month',
        'Advanced AI insights',
        'Priority email & chat support',
        'Advanced anomaly detection',
        'Custom calculated metrics',
        'API access',
        'SSO integration',
        'Audit logs & compliance'
      ],
      cta: 'Start Free Trial',
      highlighted: true
    },
    {
      name: 'Enterprise',
      description: 'Custom solutions for large organizations',
      monthlyPrice: null,
      annualPrice: null,
      features: [
        'Unlimited users',
        'Unlimited database connections',
        'Unlimited queries',
        'White-glove onboarding',
        '24/7 phone & email support',
        'Dedicated account manager',
        'Custom integrations',
        'On-premise deployment',
        'Advanced security & compliance',
        'Custom SLA',
        'Training & workshops'
      ],
      cta: 'Contact Sales',
      highlighted: false
    }
  ]

  const dataSources = [
    { name: 'PostgreSQL', supported: true },
    { name: 'MySQL', supported: true },
    { name: 'Microsoft SQL Server', supported: true },
    { name: 'Oracle Database', supported: true },
    { name: 'Amazon RDS', supported: true },
    { name: 'Azure SQL', supported: true },
    { name: 'Google Cloud SQL', supported: true },
    { name: 'MongoDB', supported: false, coming: true },
    { name: 'Snowflake', supported: false, coming: true },
    { name: 'BigQuery', supported: false, coming: true },
    { name: 'Redshift', supported: false, coming: true },
    { name: 'Real-time Streaming', supported: false, coming: true }
  ]

  const getPrice = (plan: typeof plans[0]) => {
    if (plan.monthlyPrice === null) return 'Custom'
    const price = billingCycle === 'monthly' ? plan.monthlyPrice : plan.annualPrice
    return `$${price}`
  }

  const getSavings = (plan: typeof plans[0]) => {
    if (plan.monthlyPrice === null) return null
    const monthlyCost = plan.monthlyPrice * 12
    const savings = monthlyCost - (plan.annualPrice || 0)
    return savings > 0 ? `Save $${savings}/year` : null
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
              <p className="text-xs text-gray-500">Pricing & Features</p>
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
            Simple, Transparent
            <span className="block mt-2 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Pricing
            </span>
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
            Choose the perfect plan for your team. All plans include a 14-day free trial with no credit card required.
          </p>

          {/* Billing Toggle */}
          <div className="inline-flex items-center bg-white rounded-full p-1 shadow-sm border border-gray-200">
            <button
              onClick={() => setBillingCycle('monthly')}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${
                billingCycle === 'monthly'
                  ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-md'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingCycle('annual')}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${
                billingCycle === 'annual'
                  ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-md'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Annual <span className="text-xs ml-1">(Save 17%)</span>
            </button>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-3 gap-8 mb-20">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`relative bg-white rounded-2xl p-8 ${
                plan.highlighted
                  ? 'shadow-2xl border-2 border-blue-500 scale-105'
                  : 'shadow-lg border border-gray-100'
              }`}
            >
              {plan.highlighted && (
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                  <span className="px-4 py-1 bg-gradient-to-r from-blue-600 to-purple-600 text-white text-sm font-semibold rounded-full shadow-lg">
                    Most Popular
                  </span>
                </div>
              )}
              
              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-gray-900 mb-2">{plan.name}</h3>
                <p className="text-gray-600 text-sm mb-4">{plan.description}</p>
                <div className="mb-2">
                  <span className="text-5xl font-bold text-gray-900">{getPrice(plan)}</span>
                  {plan.monthlyPrice !== null && (
                    <span className="text-gray-600 text-lg">/{billingCycle === 'monthly' ? 'mo' : 'yr'}</span>
                  )}
                </div>
                {billingCycle === 'annual' && getSavings(plan) && (
                  <p className="text-green-600 text-sm font-semibold">{getSavings(plan)}</p>
                )}
              </div>

              <button
                onClick={() => navigate('/')}
                className={`w-full py-3 rounded-xl font-semibold mb-6 transition-all ${
                  plan.highlighted
                    ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:from-blue-700 hover:to-purple-700 shadow-md'
                    : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                }`}
              >
                {plan.cta}
              </button>

              <ul className="space-y-3">
                {plan.features.map((feature, idx) => (
                  <li key={idx} className="flex items-start text-sm">
                    <svg
                      className="w-5 h-5 text-green-500 mr-3 flex-shrink-0 mt-0.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    <span className="text-gray-700">{feature}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Supported Data Sources */}
        <div className="mb-20">
          <div className="text-center mb-12">
            <h3 className="text-3xl font-bold text-gray-900 mb-4">Supported Data Sources</h3>
            <p className="text-lg text-gray-600">Connect to your existing databases with zero data movement</p>
          </div>

          <div className="grid md:grid-cols-3 lg:grid-cols-4 gap-6">
            {dataSources.map((source) => (
              <div
                key={source.name}
                className={`bg-white rounded-xl p-6 border ${
                  source.supported
                    ? 'border-green-200 bg-green-50/30'
                    : 'border-gray-200 bg-gray-50/30'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-gray-900 font-medium">{source.name}</span>
                  {source.supported ? (
                    <svg className="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  ) : (
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full font-semibold">
                      Coming Soon
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-8 bg-blue-50 border border-blue-200 rounded-xl p-6">
            <div className="flex items-start">
              <svg className="w-6 h-6 text-blue-600 mr-3 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <h4 className="font-semibold text-gray-900 mb-2">Real-Time Streaming Support</h4>
                <p className="text-gray-700 text-sm">
                  Currently, DataTruth works with batch/OLTP databases. Real-time streaming data sources 
                  (Kafka, Kinesis, etc.) are on our roadmap for Q2 2026. Contact us if this is critical for your use case.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="mb-20">
          <h3 className="text-3xl font-bold text-gray-900 text-center mb-12">Frequently Asked Questions</h3>
          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
              <h4 className="font-semibold text-gray-900 mb-2">What happens after the free trial?</h4>
              <p className="text-gray-600 text-sm">
                Your 14-day free trial includes full access to all features in your chosen plan. 
                You won't be charged until the trial ends, and you can cancel anytime.
              </p>
            </div>
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
              <h4 className="font-semibold text-gray-900 mb-2">Can I change plans later?</h4>
              <p className="text-gray-600 text-sm">
                Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately, 
                and we'll prorate any charges or credits.
              </p>
            </div>
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
              <h4 className="font-semibold text-gray-900 mb-2">What if I exceed my query limit?</h4>
              <p className="text-gray-600 text-sm">
                We'll notify you when you reach 80% of your limit. You can purchase additional query packs 
                or upgrade to a higher tier. We never stop your service unexpectedly.
              </p>
            </div>
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
              <h4 className="font-semibold text-gray-900 mb-2">Is my data secure?</h4>
              <p className="text-gray-600 text-sm">
                Absolutely. We never store your actual data—only metadata for schema discovery. 
                All queries run directly in your database with enterprise-grade encryption.
              </p>
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl p-12 text-white text-center">
          <h3 className="text-3xl font-bold mb-4">Ready to get started?</h3>
          <p className="text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
            Join hundreds of teams already using DataTruth to make data-driven decisions faster
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
              Contact Sales
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
