# Chart Visualization Feature

## Overview

The DataTruth application now includes interactive chart visualization for query results. Users can toggle between table and chart views to better understand their data through visual representations.

## Features

### View Toggle
- **Table View**: Traditional tabular display of query results
- **Chart View**: Visual representation using interactive charts
- Easy toggle between views with dedicated buttons

### Supported Chart Types

#### 1. Bar Chart
- Best for: Comparing values across categories
- Use case: Sales by region, counts by department, etc.
- Features: Color-coded bars, grid lines, tooltips

#### 2. Line Chart
- Best for: Time series data, trends over time
- Use case: Daily revenue, monthly growth, etc.
- Features: Smooth lines, data points, trend visualization

#### 3. Pie Chart
- Best for: Part-to-whole relationships
- Use case: Market share, percentage breakdowns
- Features: Percentage labels, legend, top 8 categories

### Smart Chart Selection

The DataChart component automatically analyzes your data structure to:
- Identify numeric columns (for Y-axis values)
- Identify categorical columns (for X-axis labels)
- Suggest the most appropriate chart type
- Handle edge cases (no numeric data, single values, etc.)

### Data Requirements

For optimal chart visualization:
- **Minimum**: At least one numeric column
- **Recommended**: Mix of categorical and numeric columns
- **Limit**: Charts display up to 20 data points (to prevent overcrowding)

### Features

1. **Automatic Type Detection**: The component intelligently detects column types
2. **Multiple Metrics**: Can visualize multiple numeric columns simultaneously
3. **Interactive Tooltips**: Hover over data points for detailed information
4. **Responsive Design**: Charts adapt to container width
5. **Color Palette**: Professional color scheme with 8 distinct colors

## Usage

### Basic Query Example

```sql
-- This query will display well as a bar chart
SELECT 
  agent_name, 
  COUNT(*) as total_calls,
  AVG(call_duration) as avg_duration
FROM calls
GROUP BY agent_name
ORDER BY total_calls DESC
LIMIT 10;
```

### Time Series Example

```sql
-- This query is perfect for line charts
SELECT 
  DATE(call_timestamp) as date,
  COUNT(*) as call_count,
  AVG(call_duration) as avg_duration
FROM calls
WHERE call_timestamp >= DATE('now', '-30 days')
GROUP BY DATE(call_timestamp)
ORDER BY date;
```

### Percentage Example

```sql
-- This works well with pie charts
SELECT 
  call_status,
  COUNT(*) as count
FROM calls
GROUP BY call_status;
```

## User Interface

### Toggle Buttons

Located above the data display:
- **Table Button**: Shows grid icon, switches to tabular view
- **Chart Button**: Shows bar chart icon, switches to chart view
- Active button is highlighted with white background

### Chart Type Selector

Within chart view, choose from:
- Bar Chart (vertical bars)
- Line Chart (connected data points)
- Pie Chart (circular segments)

## Technical Details

### Dependencies

- **Recharts**: React charting library
  - Version: Latest (installed via npm)
  - Components: BarChart, LineChart, PieChart
  - Features: Responsive, animated, customizable

### Component Structure

```
ChatMessage
├── View Toggle (Table/Chart)
└── Conditional Display
    ├── Table View → DataTable component
    └── Chart View → DataChart component
        ├── Chart Type Selector
        └── Responsive Chart Container
            ├── BarChart
            ├── LineChart
            └── PieChart
```

### Data Transformation

The DataChart component:
1. Receives raw query results as array of objects
2. Analyzes column types (string vs numeric)
3. Transforms data into chart-friendly format
4. Selects appropriate X-axis (categorical) and Y-axis (numeric) columns
5. Limits to top 20 records for performance
6. Renders selected chart type with styling

## Edge Cases Handled

1. **No Data**: Shows "No data to visualize" message
2. **No Numeric Columns**: Shows warning with explanation
3. **Single Row**: Displays as single bar in chart
4. **Too Many Categories**: Limits to top 20, shows note
5. **Missing Values**: Filters out null/undefined values
6. **Mixed Data Types**: Intelligently categorizes columns

## Best Practices

### For Users

1. **Start with Table View**: Understand data structure first
2. **Choose Appropriate Queries**: Group and aggregate for better charts
3. **Limit Results**: Use LIMIT clause for cleaner visualizations
4. **Use Meaningful Labels**: Column names appear in charts
5. **Experiment with Chart Types**: Different charts reveal different insights

### For Developers

1. **Data Preparation**: Ensure clean data from SQL queries
2. **Performance**: Limit data points displayed (current: 20)
3. **Accessibility**: Maintain color contrast, provide tooltips
4. **Error Handling**: Graceful degradation for unsupported data
5. **Testing**: Test with various query result structures

## Troubleshooting

### "No numeric data found" Error

**Problem**: All columns in query results are text/string type

**Solution**: Include numeric columns in your query:
```sql
-- Instead of:
SELECT customer_name, order_date FROM orders;

-- Use:
SELECT customer_name, COUNT(*) as order_count FROM orders GROUP BY customer_name;
```

### Chart Shows Only a Few Items

**Reason**: Chart displays top 20 items to prevent overcrowding

**Solution**: 
- Use more specific WHERE clauses
- Apply better filtering in SQL
- Use LIMIT clause strategically

### Colors Look Similar

**Reason**: More than 8 data series (exceeds color palette)

**Solution**: Reduce number of metrics or categories:
```sql
-- Instead of multiple metrics:
SELECT category, metric1, metric2, metric3, ... FROM table;

-- Use separate queries:
SELECT category, metric1 FROM table;
```

## Future Enhancements

Planned features:
1. **Additional Chart Types**: Scatter, area, radar charts
2. **Chart Customization**: User-selectable colors, labels
3. **Export Options**: Download as PNG, SVG, or data
4. **Drill-Down**: Click chart elements to filter data
5. **Comparison Mode**: Side-by-side chart comparisons
6. **Annotations**: Add notes and markers to charts
7. **Real-time Updates**: Live data refresh in charts

## Examples Gallery

### Example 1: Sales by Region (Bar Chart)
```sql
SELECT region, SUM(amount) as total_sales 
FROM transactions 
GROUP BY region 
ORDER BY total_sales DESC;
```
→ Shows regions on X-axis, sales on Y-axis as colored bars

### Example 2: Monthly Trend (Line Chart)
```sql
SELECT 
  strftime('%Y-%m', date) as month,
  SUM(revenue) as monthly_revenue
FROM sales
GROUP BY month
ORDER BY month;
```
→ Shows time progression with connected data points

### Example 3: Call Status Distribution (Pie Chart)
```sql
SELECT status, COUNT(*) as count
FROM calls
GROUP BY status;
```
→ Shows percentage breakdown of call statuses

## Conclusion

The chart visualization feature transforms DataTruth from a query tool into a complete analytics platform. By making data more visual and interactive, users can:
- Identify trends faster
- Spot anomalies easily
- Communicate insights better
- Make data-driven decisions confidently

For questions or feedback, please refer to the main documentation or submit an issue.
