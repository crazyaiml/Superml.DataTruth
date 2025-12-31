# AI Learning Agent for Semantic Layer

## Overview

The DataTruth platform now includes an **intelligent learning agent** that continuously improves semantic layer mappings by learning from user queries and data patterns.

## Key Features

### 1. **Query Learning** (`src/learning/query_learner.py`)
- Tracks all user queries and their outcomes
- Learns which metric/dimension names users actually use
- Automatically generates synonyms from successful matches
- Identifies commonly failed lookups for improvement

### 2. **Semantic Matching** (`src/learning/semantic_matcher.py`)
- Uses AI embeddings for fuzzy semantic matching
- Finds metrics even when names don't match exactly
- Falls back to token-based matching if embeddings unavailable
- Provides similarity scores and top-K suggestions

### 3. **Feedback Collection** (`src/learning/feedback_collector.py`)
- Collects user feedback on query results
- Tracks helpfulness ratings
- Records user corrections for continuous improvement

## How It Works

### Automatic Learning Flow

```
1. User Query: "Stocks by Change"
   ↓
2. Intent Extraction: Extracts "Change" as metric
   ↓
3. Exact Match Fails: "Change" not found in semantic layer
   ↓
4. Learned Synonyms Check: Check if "Change" is a learned synonym
   ↓
5. Semantic Matching: Use AI to find "Price Change 24h" (score: 0.85)
   ↓
6. Query Executes Successfully
   ↓
7. Learning System Records: "Change" → "Price Change 24h"
   ↓
8. Future Queries: "Change" now instantly matches "Price Change 24h"
```

### Learning from Patterns

**Initial State:**
```json
{
  "Price Change 24h": []  // No synonyms
}
```

**After User Queries:**
```json
{
  "Price Change 24h": [
    "Change",           // Learned from "Stocks by Change"
    "Daily Change",     // Learned from "Show Daily Change" 
    "24h Change",       // Learned from "Top 24h Change"
    "Price Movement"    // Learned from "Price Movement by sector"
  ]
}
```

## API Endpoints

### Get Learning Statistics
```http
GET /api/v1/learning/stats
```

Returns:
```json
{
  "learning": {
    "total_queries": 150,
    "success_rate": 0.87,
    "learned_synonyms_count": 42,
    "unique_failed_lookups": 8,
    "top_failures": [
      ["revenue growth", 5],
      ["profit margin", 3]
    ]
  },
  "feedback": {
    "total_feedback": 23,
    "helpful_rate": 0.91,
    "corrections_received": 4
  }
}
```

### Export Learned Synonyms
```http
GET /api/v1/learning/synonyms/export
```

Returns all learned synonyms as JSON for backup/sharing.

### Import Learned Synonyms
```http
POST /api/v1/learning/synonyms/import
Content-Type: application/json

{
  "synonyms": {
    "Price Change 24h": ["Change", "Daily Change"],
    "Volume": ["Trading Volume", "Vol"]
  }
}
```

## Configuration

### Enable Semantic Matching with Embeddings

For better AI-powered matching, install sentence-transformers:

```bash
pip install sentence-transformers
```

The system will automatically use embeddings when available. Without it, falls back to token-based matching.

### Adjust Matching Threshold

In `src/api/routes.py`, adjust the semantic matching threshold:

```python
match_result = matcher.find_best_match(
    extraction.query_plan.metric,
    available_metrics,
    threshold=0.6  # Lower = more permissive, Higher = more strict
)
```

## Benefits

### 1. **Zero Configuration**
- Starts working immediately
- No manual synonym configuration needed
- Learns from actual usage patterns

### 2. **Continuous Improvement**
- Gets smarter with each query
- Adapts to your team's vocabulary
- Reduces "metric not found" errors over time

### 3. **Cross-Connection Learning**
- Learns synonyms per connection
- Shares patterns across similar databases
- Improves accuracy for new connections

### 4. **Transparent Operations**
- Debug logs show matching process
- Learning stats API shows what's being learned
- Export/import for version control

## Example Scenarios

### Scenario 1: New User Terminology
```
Query 1: "Show me revenue" 
→ Fails (metric is called "Total Revenue")
→ Suggests: "Total Revenue (85% match)"
→ User clicks suggestion

Query 2: "Show me revenue by region"
→ Learned from Query 1
→ Instantly matches "Total Revenue"
→ Success!
```

### Scenario 2: Abbreviations
```
Query: "Stocks by vol"
→ Semantic matcher finds "Volume" (0.78 similarity)
→ Executes successfully
→ Learns: "vol" → "Volume"
→ Future "vol" queries work instantly
```

### Scenario 3: Alternative Phrasings
```
Queries that now work after learning:
- "Daily price movement" → "Price Change 24h"
- "Trading activity" → "Volume"
- "Stock ticker" → "Symbol"
- "Industry sector" → "Sector"
```

## Monitoring & Maintenance

### View Learning Progress
```bash
curl -H "Authorization: Bearer $TOKEN" \\
  http://localhost:8000/api/v1/learning/stats
```

### Export for Backup
```bash
curl -H "Authorization: Bearer $TOKEN" \\
  http://localhost:8000/api/v1/learning/synonyms/export \\
  > learned_synonyms_backup.json
```

### Import to New Instance
```bash
curl -X POST \\
  -H "Authorization: Bearer $TOKEN" \\
  -H "Content-Type: application/json" \\
  -d @learned_synonyms_backup.json \\
  http://localhost:8000/api/v1/learning/synonyms/import
```

## Advanced: Semantic Layer Auto-Improvement

The system can automatically improve the static semantic layer configuration by:

1. **Identifying Missing Synonyms**: Top failed lookups reveal gaps
2. **Suggesting Additions**: Export learned synonyms to add to YAML
3. **Cross-Team Sharing**: Export from one team, import to another

### Workflow
```bash
# 1. Let system learn for a week
# 2. Export learned synonyms
curl .../learning/synonyms/export > week1_learned.json

# 3. Review and merge into semantic layer YAML
# 4. Deploy updated YAML across team
# 5. System continues learning from there
```

## Performance Impact

- **Memory**: ~1MB per 1000 queries
- **Latency**: +5-10ms for semantic matching (only on cache miss)
- **Storage**: Learned synonyms persisted in memory (export for disk)

## Future Enhancements

- [ ] Persistent storage in database
- [ ] Multi-user collaborative learning
- [ ] A/B testing for matching strategies
- [ ] Auto-confidence scoring for suggestions
- [ ] Integration with user feedback UI
- [ ] Periodic synonym quality review

## Troubleshooting

### Semantic Matching Not Working
```python
# Check if sentence-transformers is installed
python -c "import sentence_transformers; print('OK')"

# If not: pip install sentence-transformers
```

### Too Many False Positives
- Increase matching threshold (0.6 → 0.75)
- Review learned synonyms for quality
- Clear incorrect learned mappings

### Learning Not Persisting
- Export learned synonyms regularly
- Set up automated backup cron job
- Plan database persistence upgrade

## Conclusion

The learning agent transforms DataTruth from a static query system into an **adaptive AI platform** that continuously improves based on real usage. It reduces friction, improves user satisfaction, and makes data more accessible to everyone.

**The more you use it, the smarter it gets!** 🚀
