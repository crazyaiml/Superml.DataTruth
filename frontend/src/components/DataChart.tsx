import { useState, useMemo } from 'react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface Props {
  data: any[]
}

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#84cc16']

export default function DataChart({ data }: Props) {
  const [chartType, setChartType] = useState<'bar' | 'line' | 'pie'>('bar')

  // Analyze data structure to determine best visualization
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return { chartData: [], keys: [], xKey: '' }

    const firstRow = data[0]
    const keys = Object.keys(firstRow)
    
    // Find the first string/category column for X-axis
    // Exclude columns that look like numbers or can be parsed as numbers
    const xKey = keys.find(key => {
      const value = firstRow[key]
      // Check if it's a string and not a numeric string
      if (typeof value === 'string') {
        // If it looks like a date (YYYY-MM, YYYY-Q#, YYYY-MM-DD, etc.), it can be X-axis
        if (/^\d{4}(-\d{2})?(-\d{2})?$/.test(value) || /^\d{4}-Q[1-4]$/.test(value)) {
          return true
        }
        // If it's purely numeric string, skip it (likely a metric)
        if (!isNaN(Number(value))) {
          return false
        }
        return true
      }
      return false
    }) || keys[0]
    
    // Find numeric columns for Y-axis
    // Include both actual numbers and strings that can be parsed as numbers (except the X-axis)
    const numericKeys = keys.filter(key => {
      if (key === xKey) return false
      const value = firstRow[key]
      // Check if it's a number or a numeric string
      if (typeof value === 'number') return true
      if (typeof value === 'string' && !isNaN(Number(value)) && value.trim() !== '') {
        return true
      }
      return false
    })

    // If no numeric columns, try to convert or use count
    if (numericKeys.length === 0) {
      // Create a count-based chart
      const counts = data.reduce((acc, row) => {
        const key = String(row[xKey])
        acc[key] = (acc[key] || 0) + 1
        return acc
      }, {} as Record<string, number>)

      return {
        chartData: Object.entries(counts).map(([name, value]) => ({
          name,
          count: value,
        })),
        keys: ['count'],
        xKey: 'name',
      }
    }

    // Transform data for charts
    const transformedData = data.slice(0, 20).map(row => {
      const transformed: any = { name: String(row[xKey]) }
      numericKeys.forEach(key => {
        // Convert to number, handling both number and string types
        const value = row[key]
        transformed[key] = typeof value === 'number' ? value : Number(value) || 0
      })
      return transformed
    })

    return {
      chartData: transformedData,
      keys: numericKeys,
      xKey: 'name',
    }
  }, [data])

  if (!data || data.length === 0) {
    return (
      <div className="bg-gray-50 rounded-lg p-8 text-center">
        <svg className="w-12 h-12 text-gray-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <p className="text-gray-600">No data to visualize</p>
      </div>
    )
  }

  if (chartData.keys.length === 0) {
    return (
      <div className="bg-yellow-50 rounded-lg p-8 text-center border border-yellow-200">
        <svg className="w-12 h-12 text-yellow-600 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <p className="text-yellow-800 font-medium mb-1">No numeric data found</p>
        <p className="text-yellow-700 text-sm">Charts require at least one numeric column</p>
      </div>
    )
  }

  // For pie chart, show only the first metric with top values
  const pieData = useMemo(() => {
    if (chartType !== 'pie') return []
    const key = chartData.keys[0]
    return chartData.chartData.slice(0, 8).map(item => ({
      name: item.name,
      value: item[key],
    }))
  }, [chartType, chartData])

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      {/* Chart Type Selector */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex space-x-2">
          <button
            onClick={() => setChartType('bar')}
            className={`p-2 rounded-lg transition ${
              chartType === 'bar'
                ? 'bg-blue-100 text-blue-600'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
            title="Bar Chart"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </button>
          <button
            onClick={() => setChartType('line')}
            className={`p-2 rounded-lg transition ${
              chartType === 'line'
                ? 'bg-blue-100 text-blue-600'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
            title="Line Chart"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
            </svg>
          </button>
          <button
            onClick={() => setChartType('pie')}
            className={`p-2 rounded-lg transition ${
              chartType === 'pie'
                ? 'bg-blue-100 text-blue-600'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
            title="Pie Chart"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
            </svg>
          </button>
        </div>
        <div className="text-xs text-gray-500">
          {chartData.chartData.length > 20 && 'Showing first 20 items'}
        </div>
      </div>

      {/* Chart Display */}
      <ResponsiveContainer width="100%" height={400}>
        {chartType === 'bar' ? (
          <BarChart data={chartData.chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey={chartData.xKey} 
              tick={{ fill: '#6b7280', fontSize: 12 }}
              angle={chartData.chartData.length > 10 ? -45 : 0}
              textAnchor={chartData.chartData.length > 10 ? 'end' : 'middle'}
              height={chartData.chartData.length > 10 ? 80 : 60}
            />
            <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#fff', 
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}
            />
            <Legend />
            {chartData.keys.map((key, index) => (
              <Bar 
                key={key} 
                dataKey={key} 
                fill={COLORS[index % COLORS.length]}
                radius={[8, 8, 0, 0]}
              />
            ))}
          </BarChart>
        ) : chartType === 'line' ? (
          <LineChart data={chartData.chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey={chartData.xKey} 
              tick={{ fill: '#6b7280', fontSize: 12 }}
              angle={chartData.chartData.length > 10 ? -45 : 0}
              textAnchor={chartData.chartData.length > 10 ? 'end' : 'middle'}
              height={chartData.chartData.length > 10 ? 80 : 60}
            />
            <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#fff', 
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}
            />
            <Legend />
            {chartData.keys.map((key, index) => (
              <Line 
                key={key} 
                type="monotone"
                dataKey={key} 
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                dot={{ fill: COLORS[index % COLORS.length], r: 4 }}
                activeDot={{ r: 6 }}
              />
            ))}
          </LineChart>
        ) : (
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name}: ${((percent || 0) * 100).toFixed(0)}%`}
              outerRadius={120}
              fill="#8884d8"
              dataKey="value"
            >
              {pieData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#fff', 
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}
            />
            <Legend />
          </PieChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}
