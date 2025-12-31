# User Activity Tracking & Personalized Suggestions

## Overview

This system tracks user interactions (queries, chats, suggestion clicks, feedback) to provide personalized query suggestions based on learned patterns, user role, and preferences.

## Features

### 🎯 Personalized Query Suggestions
- **Learning from history**: Analyzes user's past queries to identify patterns
- **Role-based suggestions**: Leverages common patterns from users with same role
- **Preference-aware**: Respects user's preferred/excluded metrics and dimensions
- **Smart caching**: Caches suggestions for 1 hour to reduce LLM API calls
- **Hybrid approach**: Combines learned patterns with LLM intelligence

### 📊 Activity Tracking
- **Query logging**: Records all queries with results and execution metadata
- **Suggestion tracking**: Logs which suggestions users click
- **Feedback collection**: Captures user ratings and comments
- **Contextual metadata**: Stores user role, goals, department at time of activity

### 🧠 Pattern Learning
- **User-specific patterns**: Learns individual query templates
- **Role-based patterns**: Identifies common queries per role (analyst, trader, executive, etc.)
- **Template extraction**: Generalizes queries (e.g., "top 10 stocks" → "top {N} {entity}")
- **Success tracking**: Monitors query success rate and response times
- **Auto-updating**: Patterns update automatically as users make queries

### ⚙️ User Preferences
- **Preferred query types**: comparison, trend, ranking, aggregation
- **Preferred metrics**: Prioritize specific metrics in suggestions
- **Excluded metrics**: Remove unwanted metrics from suggestions
- **Preferred dimensions**: Prioritize specific dimensions
- **Advanced queries toggle**: Show/hide complex multi-step queries
- **Suggestion count**: Configure how many suggestions to show (1-12)

## Database Schema

### Tables Created (Migration 004)

#### 1. `user_activity`
Stores all user interactions for learning.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| user_id | VARCHAR(100) | References users table |
| activity_type | VARCHAR(50) | 'query', 'chat', 'suggestion_click', 'feedback' |
| query_text | TEXT | User's query or message |
| response_data | JSONB | Full response with SQL, results, metadata |
| suggestion_clicked | TEXT | Which suggestion was clicked |
| feedback_rating | INTEGER | Rating 1-5 if feedback |
| metadata | JSONB | Context: role, preferences, goals, etc. |
| created_at | TIMESTAMP | When activity occurred |

**Indexes:**
- `idx_user_activity_user_id` on user_id
- `idx_user_activity_type` on activity_type  
- `idx_user_activity_created_at` on created_at DESC
- `idx_user_activity_user_type` on (user_id, activity_type)

#### 2. `query_patterns`
Learned query templates aggregated by user or role.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| pattern_type | VARCHAR(50) | 'role_based', 'user_specific', or 'global' |
| target_id | VARCHAR(100) | user_id or role name |
| query_template | TEXT | Generalized query template |
| frequency | INTEGER | How often this pattern appears |
| success_rate | FLOAT | Percentage of successful queries (0-1) |
| avg_response_time | FLOAT | Average response time in seconds |
| last_used | TIMESTAMP | Last time pattern was used |
| metadata | JSONB | Pattern details (metrics, dimensions used) |
| created_at | TIMESTAMP | When pattern was created |
| updated_at | TIMESTAMP | Last update time |

**Indexes:**
- `idx_query_patterns_type` on pattern_type
- `idx_query_patterns_target` on target_id
- `idx_query_patterns_frequency` on frequency DESC
- `idx_query_patterns_success` on success_rate DESC

#### 3. `suggestion_cache`
Caches generated suggestions to reduce LLM costs.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| user_id | VARCHAR(100) | References users table |
| context_hash | VARCHAR(64) | MD5 hash of (user_id + role + partial_query) |
| suggestions | JSONB | Array of suggestion objects |
| generated_at | TIMESTAMP | When suggestions were generated |
| expires_at | TIMESTAMP | Expiration time (default +1 hour) |
| hit_count | INTEGER | How many times cache was used |

**Indexes:**
- `idx_suggestion_cache_user_id` on user_id
- `idx_suggestion_cache_hash` on context_hash
- `idx_suggestion_cache_expires` on expires_at

#### 4. `user_suggestion_preferences`
User-specific preferences for suggestions.

| Column | Type | Description |
|--------|------|-------------|
| user_id | VARCHAR(100) | Primary key, references users |
| preferred_query_types | JSONB | Array of preferred types |
| excluded_metrics | JSONB | Metrics to exclude |
| preferred_metrics | JSONB | Metrics to prioritize |
| preferred_dimensions | JSONB | Dimensions to prioritize |
| show_advanced_queries | BOOLEAN | Show complex queries |
| max_suggestions | INTEGER | How many suggestions (default 6) |
| updated_at | TIMESTAMP | Last update time |

## API Endpoints

### Personalized Suggestions

#### `POST /api/v1/connections/{connection_id}/suggestions/personalized`
Get personalized query suggestions based on user history.

**Parameters:**
- `connection_id` (path): Database connection ID
- `partial_query` (query, optional): User's current input
- `max_suggestions` (query, default=6): Maximum suggestions

**Response:**
```json
{
  "connection_id": "my-database",
  "partial_query": "show me profit",
  "suggestions": [
    {
      "text": "Show me quarterly profits from last 5 years",
      "type": "complete",
      "description": "Time-series profit analysis",
      "icon": "📈"
    },
    {
      "text": "Top 10 products by profit margin",
      "type": "ranking",
      "description": "Highest profit margins",
      "icon": "🏆"
    }
  ],
  "source": "llm_with_patterns",
  "user_patterns": [
    "show me {metric} for {timeframe}",
    "top {N} {entity} by {metric}"
  ],
  "role_patterns": [
    "compare {metric} across {dimension}"
  ],
  "count": 6
}
```

**Sources:**
- `cached`: Returned from cache (fastest, no LLM cost)
- `llm_with_patterns`: Generated with LLM using learned patterns
- `llm_fallback`: Basic LLM without patterns (error recovery)

### Activity Logging

#### `POST /api/v1/activity/log`
Log user activity for learning and personalization.

**Request Body:**
```json
{
  "activity_type": "query",
  "query_text": "Show me quarterly profits from last 5 years",
  "response_data": {
    "data": [...],
    "metadata": {
      "generated_sql": "SELECT ...",
      "execution_time_ms": 245,
      "row_count": 20
    }
  },
  "metadata": {
    "connection_id": "my-database"
  }
}
```

**Activity Types:**
- `query`: User executed a query
- `chat`: User sent a chat message
- `suggestion_click`: User clicked a suggestion
- `feedback`: User provided rating/feedback

**Response:**
```json
{
  "success": true,
  "activity_id": 12345,
  "activity_type": "query"
}
```

#### `GET /api/v1/activity/history`
Get user's activity history.

**Parameters:**
- `activity_type` (query, optional): Filter by type
- `limit` (query, default=100): Max activities to return

**Response:**
```json
{
  "user_id": "analyst001",
  "activities": [
    {
      "id": 12345,
      "user_id": "analyst001",
      "activity_type": "query",
      "query_text": "Show me quarterly profits",
      "created_at": "2025-12-29T10:30:00Z"
    }
  ],
  "count": 15
}
```

### Pattern Management

#### `GET /api/v1/activity/patterns`
Get learned query patterns for current user.

**Parameters:**
- `limit` (query, default=10): Max patterns per type

**Response:**
```json
{
  "user_id": "analyst001",
  "user_patterns": [
    {
      "id": 1,
      "pattern_type": "user_specific",
      "target_id": "analyst001",
      "query_template": "show me {metric} for {timeframe}",
      "frequency": 25,
      "success_rate": 0.96,
      "avg_response_time": 0.245
    }
  ],
  "role_patterns": [
    {
      "id": 2,
      "pattern_type": "role_based",
      "target_id": "analyst",
      "query_template": "compare {metric} across {dimension}",
      "frequency": 150,
      "success_rate": 0.92
    }
  ],
  "user_pattern_count": 5,
  "role_pattern_count": 8
}
```

### Preference Management

#### `GET /api/v1/activity/preferences`
Get user's suggestion preferences.

**Response:**
```json
{
  "user_id": "analyst001",
  "preferred_query_types": ["comparison", "trend", "ranking"],
  "excluded_metrics": ["internal_id", "debug_field"],
  "preferred_metrics": ["profit", "revenue", "margin"],
  "preferred_dimensions": ["quarter", "product", "region"],
  "show_advanced_queries": false,
  "max_suggestions": 6,
  "updated_at": "2025-12-29T10:00:00Z"
}
```

#### `PUT /api/v1/activity/preferences`
Update user's suggestion preferences.

**Request Body:**
```json
{
  "preferred_query_types": ["comparison", "trend"],
  "excluded_metrics": ["internal_id"],
  "max_suggestions": 8
}
```

**Response:**
```json
{
  "success": true,
  "preferences": {
    "user_id": "analyst001",
    "preferred_query_types": ["comparison", "trend"],
    ...
  }
}
```

## Implementation Guide

### 1. Run Database Migration

```bash
# Run migration to create tables
psql -U <user> -d datatruth_internal -f migrations/004_add_user_activity_tracking.sql

# Or via Docker
docker exec -i <postgres-container> psql -U datatruth -d datatruth_internal < migrations/004_add_user_activity_tracking.sql
```

### 2. Add API Routes

The routes are defined in `/src/activity/routes_to_add.py`. 

**To integrate:**
1. Copy the route definitions from `routes_to_add.py`
2. Add them to `/src/api/routes.py` after the existing suggestions endpoint (around line 2985)
3. Ensure imports at the top of routes.py include:
   ```python
   from src.activity import get_activity_logger, get_pattern_analyzer, ActivityType
   ```

### 3. Update Query Endpoint to Log Activity

Modify the `/query` endpoint in routes.py to automatically log queries:

```python
@router.post("/query")
async def execute_natural_language_query(...):
    # ... existing code ...
    
    # After successful query execution, log it
    try:
        from src.activity import get_activity_logger
        from src.user import get_user_manager
        
        logger_instance = get_activity_logger()
        user_manager = get_user_manager()
        user_profile = user_manager.get_user(current_user.get("user_id", current_user["username"]))
        
        logger_instance.log_query(
            user_id=current_user.get("user_id", current_user["username"]),
            query_text=natural_query,
            response_data={
                "data": result.rows[:10],  # Sample rows
                "metadata": response["metadata"]
            },
            user_role=user_profile.role.value if user_profile else None,
            user_goals=user_profile.goals if user_profile else None
        )
    except Exception as e:
        logger.warning(f"Failed to log query activity: {e}")
    
    return response
```

### 4. Update Frontend to Use Personalized Suggestions

**In your chat/query input component:**

```typescript
// Use personalized endpoint instead of regular suggestions
const fetchSuggestions = async (partialQuery: string) => {
  try {
    const response = await fetch(
      `http://localhost:8000/api/v1/connections/${connectionId}/suggestions/personalized?partial_query=${encodeURIComponent(partialQuery)}&max_suggestions=6`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    const data = await response.json();
    setSuggestions(data.suggestions);
    
    // Optionally show source and patterns
    if (data.source === 'cached') {
      console.log('💾 Using cached suggestions');
    } else if (data.user_patterns.length > 0) {
      console.log('🧠 Personalized with patterns:', data.user_patterns);
    }
  } catch (error) {
    console.error('Failed to fetch suggestions:', error);
  }
};
```

**Log suggestion clicks:**

```typescript
const handleSuggestionClick = async (suggestion: string) => {
  setQuery(suggestion);
  
  // Log the click
  try {
    await fetch('http://localhost:8000/api/v1/activity/log', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        activity_type: 'suggestion_click',
        suggestion_clicked: suggestion
      })
    });
  } catch (error) {
    console.error('Failed to log suggestion click:', error);
  }
};
```

**Log query execution:**

```typescript
const handleQuerySubmit = async () => {
  const response = await executeQuery(query);
  
  // Log the query
  try {
    await fetch('http://localhost:8000/api/v1/activity/log', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        activity_type: 'query',
        query_text: query,
        response_data: {
          data: response.data,
          metadata: response.metadata
        }
      })
    });
  } catch (error) {
    console.error('Failed to log query:', error);
  }
};
```

### 5. Add Preferences UI (Optional)

Create a preferences panel where users can customize suggestions:

```typescript
const PreferencesPanel = () => {
  const [prefs, setPrefs] = useState<any>(null);
  
  useEffect(() => {
    fetchPreferences();
  }, []);
  
  const fetchPreferences = async () => {
    const response = await fetch('http://localhost:8000/api/v1/activity/preferences', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await response.json();
    setPrefs(data);
  };
  
  const updatePreferences = async (updates: any) => {
    await fetch('http://localhost:8000/api/v1/activity/preferences', {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(updates)
    });
    fetchPreferences();
  };
  
  return (
    <div>
      <h3>Suggestion Preferences</h3>
      {/* Add form controls for preferences */}
    </div>
  );
};
```

## How It Works

### Pattern Learning Flow

1. **User makes a query**: "Show me quarterly profits from last 5 years"
2. **Activity logged**: Stored in `user_activity` with role, goals, response metadata
3. **Pattern extracted**: Generalized to "Show me {metric} for {timeframe}"
4. **Pattern stored/updated**: In `query_patterns` with frequency and success rate
5. **Next time**: Suggestion engine uses this pattern for similar queries

### Suggestion Generation Flow

1. **User types partial query**: "show me prof..."
2. **Check cache**: Hash (user_id + role + query) and lookup in `suggestion_cache`
   - If found and not expired: Return cached suggestions ✅
3. **Get learned patterns**: 
   - Query `query_patterns` for user_specific patterns
   - Query `query_patterns` for role_based patterns
4. **Get preferences**: Load from `user_suggestion_preferences`
5. **Filter metrics/dimensions**: Apply preferred/excluded lists
6. **Generate with LLM**: Send to GPT-4o-mini with:
   - Available metrics/dimensions
   - User's learned patterns
   - Role's common patterns
   - Partial query
7. **Cache results**: Store in `suggestion_cache` with 1-hour expiry
8. **Return personalized suggestions**: With source indicator

### Template Generalization

Queries are generalized to identify patterns:

| Original Query | Generalized Template |
|----------------|----------------------|
| "Top 10 stocks by volume" | "Top {N} {entity} by {metric}" |
| "Show me profit for Q1 2024" | "Show me {metric} for {quarter} {year}" |
| "Compare revenue across regions" | "Compare {metric} across {dimension}" |
| "Average price by product category" | "Average {metric} by {dimension}" |

Numbers, dates, quarters, months are replaced with placeholders.

## Performance Optimizations

### Caching Strategy
- **1-hour cache** for identical contexts (user + role + query)
- **Hit count tracking** to identify popular suggestions
- **Auto-cleanup** of expired entries on insert

### Cost Reduction
- **Cache hit rate target**: 40-60% (reduces LLM calls by half)
- **Learned patterns first**: Use templates before LLM when possible
- **GPT-4o-mini**: Most affordable model (~$0.15 per 1M tokens)
- **Token limits**: Max 400 tokens per suggestion request

### Background Processing
- Pattern analysis triggered on query log (synchronous for now)
- **Future enhancement**: Use Celery/RQ for async pattern updates
- **Batch processing**: Analyze patterns for all users nightly

## Monitoring & Analytics

### Key Metrics to Track

```sql
-- Cache hit rate
SELECT 
  COUNT(*) FILTER (WHERE hit_count > 0) * 100.0 / COUNT(*) as cache_hit_rate_percent
FROM suggestion_cache
WHERE generated_at >= NOW() - INTERVAL '24 hours';

-- Most common patterns by role
SELECT 
  target_id as role,
  query_template,
  frequency,
  success_rate
FROM query_patterns
WHERE pattern_type = 'role_based'
ORDER BY frequency DESC
LIMIT 10;

-- User activity breakdown
SELECT 
  activity_type,
  COUNT(*) as count,
  COUNT(DISTINCT user_id) as unique_users
FROM user_activity
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY activity_type;

-- Average suggestions per user
SELECT 
  user_id,
  COUNT(*) as total_queries,
  COUNT(suggestion_clicked) as clicked_suggestions,
  COUNT(suggestion_clicked) * 100.0 / NULLIF(COUNT(*), 0) as click_through_rate
FROM user_activity
WHERE activity_type IN ('query', 'suggestion_click')
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY user_id
ORDER BY click_through_rate DESC;
```

## Future Enhancements

### Planned Features
- [ ] **Collaborative filtering**: "Users like you also queried..."
- [ ] **Temporal patterns**: Suggest queries based on time of day/week
- [ ] **Context awareness**: Consider previous queries in session
- [ ] **A/B testing**: Test different suggestion strategies
- [ ] **Feedback loop**: Use ratings to refine patterns
- [ ] **Export patterns**: Download learned patterns for analysis
- [ ] **Pattern similarity**: Find users with similar query patterns
- [ ] **Anomaly detection**: Flag unusual query patterns
- [ ] **Multi-language support**: Localize suggestions

### Integration Opportunities
- **Insights system**: Suggest insights based on query patterns
- **Data quality**: Identify frequently failed query patterns
- **Performance optimization**: Auto-index columns from common patterns
- **Training datasets**: Use patterns to generate synthetic queries

## Troubleshooting

### Patterns not updating
- Check if activity logging is working: `SELECT COUNT(*) FROM user_activity;`
- Verify pattern analyzer runs: Check logs for "Updated patterns for X users"
- Manually trigger: Call `/activity/patterns` endpoint

### Suggestions not personalized
- Verify user has activity history: `SELECT COUNT(*) FROM user_activity WHERE user_id = '...';`
- Check if patterns exist: `SELECT * FROM query_patterns WHERE target_id = '...';`
- Look for cache hits: `SELECT * FROM suggestion_cache WHERE user_id = '...';`

### Cache not working
- Check for context hash collisions: `SELECT context_hash, COUNT(*) FROM suggestion_cache GROUP BY context_hash HAVING COUNT(*) > 1;`
- Verify expiration: `SELECT COUNT(*) FROM suggestion_cache WHERE expires_at < NOW();`
- Clear cache: `DELETE FROM suggestion_cache;`

### High LLM costs
- Check cache hit rate (target: >40%)
- Increase cache expiration time
- Reduce max_suggestions
- Use autocomplete for short queries

## Summary

This system provides intelligent, personalized query suggestions by:

1. **Tracking** all user interactions in structured format
2. **Learning** query patterns at individual and role levels  
3. **Caching** suggestions to reduce costs and latency
4. **Respecting** user preferences for metrics/dimensions
5. **Combining** learned patterns with LLM intelligence
6. **Adapting** continuously as users interact with the system

The result is a smarter, more efficient query experience that learns from each user's unique workflow while leveraging collective intelligence from similar roles.
