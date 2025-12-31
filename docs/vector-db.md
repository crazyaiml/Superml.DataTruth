# Vector DB Integration (Phase 3 & 4)

## Overview

DataTruth now uses **ChromaDB** for persistent semantic search and cross-database field discovery.

## Features

### Phase 3: Persistent Semantic Search
- **Field Embeddings**: All metrics and dimensions are embedded and stored
- **Learned Synonyms**: User query patterns are persisted across restarts
- **Query History**: Successful queries are tracked for pattern learning
- **Fast Search**: Optimized vector similarity search

### Phase 4: Cross-Database Discovery
- **Unified Search**: Find similar fields across all connections
- **Semantic Intelligence**: "price change" in stocks helps match "price_change_24h" in crypto
- **Admin Visibility**: Inspect and manage learned patterns via API

## Architecture

```
User Query → Intent Extraction → Semantic Matching
                                       ↓
                            1. Exact match
                            2. Vector DB search (persistent)
                            3. Embedding-based match (in-memory)
                            4. Token-based fallback
                                       ↓
                            SQL Generation → Execution
                                       ↓
                            Record Success → Update Vector DB
```

## Configuration

Add to `.env`:

```env
# Vector DB Configuration
VECTOR_DB_ENABLED=true
VECTOR_DB_PERSIST_PATH=./data/chroma
```

## API Endpoints

### Get Vector DB Stats
```bash
GET /api/v1/vector/stats
```

Response:
```json
{
  "fields_count": 150,
  "learned_synonyms_count": 45,
  "queries_count": 320,
  "persist_directory": "./data/chroma"
}
```

### Search Fields (Cross-Database Discovery)
```bash
POST /api/v1/vector/search/fields
Content-Type: application/json

{
  "query": "price change",
  "connection_id": "stock-data",  // optional
  "field_type": "metric",          // optional: "metric" or "dimension"
  "top_k": 10
}
```

Response:
```json
{
  "query": "price change",
  "matches": [
    {
      "field_id": "stock-data:stockprice.change",
      "connection_id": "stock-data",
      "table_name": "stockprice",
      "column_name": "change",
      "display_name": "Price Change 24h",
      "field_type": "metric",
      "data_type": "numeric",
      "similarity": 0.92,
      "matched_text": "Field: Price Change 24h | Column: change | Description: ..."
    },
    {
      "field_id": "crypto-data:crypto_prices.price_change_24h",
      "connection_id": "crypto-data",
      "table_name": "crypto_prices",
      "column_name": "price_change_24h",
      "display_name": "Price Change 24h",
      "field_type": "metric",
      "data_type": "numeric",
      "similarity": 0.89,
      "matched_text": "Field: Price Change 24h | Column: price_change_24h | ..."
    }
  ],
  "count": 2
}
```

### Get Learned Synonyms
```bash
GET /api/v1/vector/synonyms/stock-data?field_type=metric
```

Response:
```json
{
  "connection_id": "stock-data",
  "synonyms": {
    "Price Change 24h": [
      "daily change",
      "change 24h",
      "price movement"
    ],
    "Volume": [
      "trading volume",
      "traded volume"
    ]
  }
}
```

### Reset Vector Store (Development Only)
```bash
DELETE /api/v1/vector/reset
```

Response:
```json
{
  "message": "Vector store reset successfully",
  "warning": "All learned patterns and embeddings have been deleted"
}
```

### Health Check
```bash
GET /api/v1/vector/health
```

Response:
```json
{
  "status": "healthy",
  "stats": {
    "fields_count": 150,
    "learned_synonyms_count": 45,
    "queries_count": 320
  }
}
```

## Collections

ChromaDB maintains 3 collections:

### 1. semantic_fields
- **Purpose**: Store field embeddings with metadata
- **Contents**: All metrics and dimensions from all connections
- **Metadata**: connection_id, table_name, column_name, display_name, field_type, data_type
- **Search**: Semantic similarity search for field discovery

### 2. learned_synonyms
- **Purpose**: Store learned synonym mappings
- **Contents**: User terms → canonical field names
- **Metadata**: connection_id, user_term, matched_field, field_type
- **Usage**: Improve matching accuracy over time

### 3. query_history
- **Purpose**: Track successful query patterns
- **Contents**: User queries with resolved metrics/dimensions
- **Metadata**: connection_id, metric, dimension_count
- **Usage**: Pattern analysis and learning

## Integration Points

### Field Mapping Save
When a field is saved via `/api/v1/fieldmap/save`, it's automatically:
1. Added to the field mapper (in-memory)
2. Embedded and stored in vector DB (persistent)

### Query Execution
When a query succeeds:
1. Learned synonyms are persisted to vector DB
2. Query pattern is recorded for analysis
3. Next similar query benefits immediately

### Semantic Matcher
The `SemanticMatcher` now uses a 4-tier strategy:
1. **Exact match**: Check learned synonyms
2. **Vector DB search**: Query persistent embeddings
3. **Embedding match**: Use in-memory sentence-transformers
4. **Token-based fallback**: Jaccard similarity

## Data Persistence

Vector data is stored in `./data/chroma/` by default:

```
./data/chroma/
├── chroma.sqlite3          # Metadata database
└── [collection_uuid]/      # Embedding data
    ├── data_level0.bin
    └── index_metadata.pickle
```

**Backup Strategy**: Back up entire `./data/chroma/` directory to preserve learned intelligence.

## Performance

- **Vector Search**: ~10-50ms for similarity search across 1000s of fields
- **Embedding Generation**: ~5ms per field (cached in-memory)
- **Storage**: ~1KB per field embedding
- **Scalability**: Handles millions of fields efficiently

## Monitoring

Check vector DB health:

```bash
# Stats
curl http://localhost:8000/api/v1/vector/stats

# Health
curl http://localhost:8000/api/v1/vector/health

# View learned synonyms
curl http://localhost:8000/api/v1/vector/synonyms/stock-data
```

## Development

### Reset Vector DB
```bash
curl -X DELETE http://localhost:8000/api/v1/vector/reset
```

### Disable Vector DB
Set in `.env`:
```env
VECTOR_DB_ENABLED=false
```

System falls back to in-memory semantic matching.

## Migration Notes

### Existing Systems
- **No migration needed**: Vector DB is opt-in
- **Automatic population**: Fields are added as queries are executed
- **Gradual learning**: System gets smarter with each query

### New Installations
1. Set `VECTOR_DB_ENABLED=true` in `.env`
2. Start application - ChromaDB auto-initializes
3. Execute queries - fields are embedded automatically
4. Monitor `/api/v1/vector/stats` to see learning progress

## Troubleshooting

### ChromaDB Not Initializing
```bash
pip install chromadb
```

Verify:
```bash
python -c "import chromadb; print('OK')"
```

### Slow Embedding Generation
- Sentence-transformers downloads ~90MB model on first run
- Model is cached in `~/.cache/torch/sentence_transformers/`
- Subsequent runs are fast

### High Memory Usage
- In-memory embedding cache grows with unique fields
- Clear cache by restarting application
- Consider `VECTOR_DB_ENABLED=false` for memory-constrained environments

## Future Enhancements

- [ ] Bulk field import/export
- [ ] Embedding model configuration (different models per use case)
- [ ] Cross-connection synonym sharing
- [ ] Confidence scoring and manual override
- [ ] Vector DB replication for HA deployments
- [ ] Integration with external vector DBs (Pinecone, Weaviate)
