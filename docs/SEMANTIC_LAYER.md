# Semantic Layer - Database-Driven Architecture

## 🎯 Overview

DataTruth's semantic layer is **fully database-driven** - all metrics, dimensions, and business logic are stored in PostgreSQL and managed through the web UI.

## 🗄️ Database Tables

### 1. **calculated_metrics**
Custom metrics created by users via the UI:
- **What**: Business metrics like "Profit", "Revenue", "Profit Margin"
- **Contains**: Metric name, formula, aggregation type, synonyms, filters
- **Example**: `profit = SUM(amount - cost)` where status = 'completed'

### 2. **field_mappings**
AI-generated friendly names for database fields:
- **What**: Maps technical column names to business terms
- **Contains**: Display name, description, synonyms, data type, format
- **Example**: `txn_amt` → "Transaction Amount" (currency format)

### 3. **semantic_layer_cache**
Cached semantic configurations per connection:
- **What**: Performance cache for frequently used configurations
- **Contains**: Entities, relationships, metrics per connection
- **Purpose**: Fast query planning and SQL generation

## 🎨 User Interface

Users manage the semantic layer through the **SemanticLayer UI** component:

1. **Navigate**: HomePage → Semantic Layer tab
2. **Create Metrics**: Define custom calculated metrics
3. **Set Formulas**: SQL formulas with aggregations
4. **Add Synonyms**: Alternative names for better search
5. **Apply Filters**: Default filters for metrics
6. **Format Output**: Currency, percentage, number formats

## ✅ Benefits of Database-Driven Approach

### 1. **Dynamic & Real-time**
- Changes take effect immediately
- No server restart required
- No deployment needed

### 2. **Multi-tenant Ready**
- Different metrics per connection
- Per-user/per-team customization
- Isolated configurations

### 3. **No Code Required**
- Everything via web UI
- No YAML editing
- No file management

### 4. **Version Controlled via Database**
- Audit trail of all changes
- Who created/modified what
- Rollback capabilities via backups

### 5. **Scalable**
- Handles thousands of metrics
- Efficient database queries
- Cached for performance

## 🚫 What Was Removed

Previously, DataTruth used YAML files (`config/semantic-layer/*.yaml`) for:
- Default metrics (revenue, profit)
- Default dimensions (agent, client, company)
- Join definitions
- Synonyms

**These are now removed** - Everything is user-created in the database!

## 📊 How It Works

```
User creates metric in UI
        ↓
Saved to PostgreSQL (calculated_metrics table)
        ↓
API reads from database
        ↓
SQL Generator uses metric formula
        ↓
Query executed with custom metrics
```

## 🔧 For Developers

### Load Metrics from Database:
```python
from src.database.connection import get_internal_db_connection

# Get custom metrics for a connection
with get_internal_db_connection() as conn:
    metrics = conn.execute(
        "SELECT * FROM calculated_metrics WHERE connection_id = %s",
        (connection_id,)
    ).fetchall()
```

### Semantic Layer Loader:
```python
from src.semantic.loader import get_semantic_layer

# Returns empty structure (legacy compatibility)
semantic_layer = get_semantic_layer()

# All real data comes from database tables
```

## 🎓 Best Practices

1. **Create Meaningful Names**: Use business terms, not technical jargon
2. **Add Synonyms**: Include common variations (revenue = sales = income)
3. **Document Formulas**: Add clear descriptions
4. **Use Filters Wisely**: Default filters should be common use cases
5. **Format Consistently**: Use currency/percentage formats appropriately

---

**For SaaS users:** Simply use the Semantic Layer UI - no technical knowledge required!
