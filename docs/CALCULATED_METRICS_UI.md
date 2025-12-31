# Calculated Metrics - UI Integration

## Overview

The system now supports **saving and displaying calculated metrics** through both the UI and database backend. Calculated metrics (like "profit = revenue - cost") are stored in the PostgreSQL database and displayed in the Semantic Layer configuration interface.

## Architecture

### Database Storage
- **Table**: `calculated_metrics` in PostgreSQL (`datatruth_internal` database)
- **Schema**:
  ```sql
  CREATE TABLE calculated_metrics (
      id SERIAL PRIMARY KEY,
      connection_id VARCHAR(100),
      metric_name VARCHAR(255) NOT NULL,
      display_name VARCHAR(255) NOT NULL,
      description TEXT,
      formula TEXT NOT NULL,              -- SQL formula: 'SUM(amount - cost)'
      base_table VARCHAR(255) NOT NULL,
      aggregation VARCHAR(50),
      data_type VARCHAR(50),
      format_type VARCHAR(50),
      synonyms TEXT[],
      filters JSONB,
      is_active BOOLEAN DEFAULT true,
      created_by INTEGER,
      created_at TIMESTAMP,
      updated_at TIMESTAMP
  );
  ```

### API Endpoints

#### 1. Save/Update Calculated Metric
```
POST /api/v1/fieldmap/save
```
**Request Body:**
```json
{
  "connection_id": "demo-sales-db",
  "table_name": "transactions",
  "field_name": "profit",
  "display_name": "Profit",
  "description": "Revenue minus cost",
  "formula": "SUM(amount - cost)",
  "default_aggregation": "sum",
  "is_custom": true
}
```

**Behavior:**
- Saves field mapping to vector database (for semantic search)
- **NEW**: Also saves calculated metrics with formulas to `calculated_metrics` table
- Updates if metric already exists, inserts if new

#### 2. Get Calculated Metrics
```
GET /api/v1/calculated-metrics?connection_id={id}&base_table={table}
```
**Response:**
```json
{
  "connection_id": "demo-sales-db",
  "base_table": "transactions",
  "count": 2,
  "metrics": [
    {
      "metric_name": "profit",
      "display_name": "Profit",
      "description": "Revenue minus cost",
      "formula": "SUM(transactions.amount - transactions.cost)",
      "base_table": "transactions",
      "aggregation": "sum",
      "data_type": "decimal",
      "format_type": "currency",
      "synonyms": ["net_profit", "earnings"],
      "filters": []
    }
  ]
}
```

#### 3. Delete Calculated Metric
```
DELETE /api/v1/calculated-metrics/{metric_name}?connection_id={id}
```
**Response:**
```json
{
  "success": true,
  "message": "Calculated metric 'profit' deleted successfully"
}
```

**Note**: Uses soft delete (sets `is_active = false`)

## UI Integration

### Accessing the Semantic Layer UI

1. Navigate to: **http://localhost:3000/workspace?section=configuration**
2. Click on the **"Semantic Layer"** tab
3. Select a **connection** and **table**

### UI Features

#### Display Calculated Metrics
- Calculated metrics from the database are displayed with a purple calculator icon
- Formula is shown in the "Formula" column
- Marked as "Custom" fields with `is_custom: true`

#### Create New Calculated Metric
1. Click the **"+ Add Custom Field"** button
2. Fill in the form:
   - **Name**: Internal name (e.g., `profit`)
   - **Display Name**: User-friendly name (e.g., "Profit")
   - **Description**: Business description
   - **Formula**: SQL expression (e.g., `SUM(amount - cost)`)
   - **Aggregation**: Sum, AVG, etc.
3. Click **"Add Field"**
4. Click **"Save Changes"** to persist to database

#### Edit Calculated Metric
- Modify **Display Name**, **Description**, or **Aggregation** in the table
- Click **"Save Changes"** to update the database

#### Delete Calculated Metric
- Click the **trash icon** next to a custom field
- Confirm deletion
- Metric is soft-deleted from database (sets `is_active = false`)

### Code Flow

#### Loading Fields (frontend/src/components/SemanticLayer.tsx)
```typescript
const loadFields = async () => {
  // 1. Load regular schema columns
  const schemaResponse = await axios.get(`/connections/${id}/schema/${table}`);
  
  // 2. Load field mappings from vector DB
  for (const col of columns) {
    const mapping = await axios.get(`/fieldmap/${table}/${col}`);
    // ... add to fields array
  }
  
  // 3. Load calculated metrics from database
  const metricsResponse = await axios.get(
    `/calculated-metrics?connection_id=${id}&base_table=${table}`
  );
  
  // 4. Add calculated metrics as custom fields
  for (const metric of metrics) {
    fields.push({
      name: metric.metric_name,
      is_custom: true,
      formula: metric.formula,
      // ...
    });
  }
};
```

#### Saving Fields (frontend/src/components/SemanticLayer.tsx)
```typescript
const saveSemanticLayer = async () => {
  for (const field of fields) {
    await axios.post('/fieldmap/save', {
      connection_id,
      table_name,
      field_name: field.name,
      display_name: field.display_name,
      description: field.description,
      is_custom: field.is_custom,
      formula: field.formula  // Saved to calculated_metrics table if is_custom=true
    });
  }
};
```

#### Deleting Fields (frontend/src/components/SemanticLayer.tsx)
```typescript
const deleteCustomField = async (fieldName: string) => {
  // Remove from UI
  setFields(prev => prev.filter(f => f.name !== fieldName));
  
  // Delete from database
  await axios.delete(`/calculated-metrics/${fieldName}?connection_id=${id}`);
};
```

## Query Execution

When a user asks "Show me quarterly profits from last 5 years":

1. **Intent Extraction**: LLM extracts `metric: "profit"`, `time_grain: "quarter"`
2. **Semantic Layer Lookup**: System loads calculated metrics from database
3. **Query Plan**: Includes profit metric with formula `SUM(amount - cost)`
4. **SQL Generation**: 
   ```sql
   SELECT 
     TO_CHAR(DATE_TRUNC('quarter', transaction_date), 'YYYY-"Q"Q') as period,
     SUM(transactions.amount - transactions.cost) as profit
   FROM transactions
   WHERE transaction_date >= CURRENT_DATE - INTERVAL '5 years'
   GROUP BY DATE_TRUNC('quarter', transaction_date)
   ORDER BY period
   ```

## Testing

### Test Scenario 1: Create Profit Metric via UI

1. Go to http://localhost:3000/workspace?section=configuration
2. Click "Semantic Layer" tab
3. Select connection: `demo-sales-db`, table: `transactions`
4. Click "+ Add Custom Field"
5. Enter:
   - Name: `profit`
   - Display Name: `Profit`
   - Description: `Net profit after costs`
   - Formula: `SUM(amount - cost)`
   - Aggregation: `SUM`
6. Click "Add Field"
7. Click "Save Changes"

**Expected Result**: 
- Profit appears in the field list with calculator icon
- Saved to `calculated_metrics` table
- Available for queries like "show me profit by month"

### Test Scenario 2: Query Uses Calculated Metric

Ask in chat: **"Show me quarterly profits from last 5 years"**

**Expected Result**:
- System finds "profit" metric from database
- Generates SQL with `SUM(amount - cost)`
- Returns chart with quarterly profit values

### Test Scenario 3: Delete Calculated Metric

1. In Semantic Layer tab, find the "profit" custom field
2. Click trash icon
3. Confirm deletion

**Expected Result**:
- Field removed from UI
- Database record set to `is_active = false`
- Metric no longer available for queries

## Migration from YAML to Database

Previously, metrics were stored in YAML files (`config/semantic-layer/metrics.yaml`). The system now uses the database approach:

### Old System (YAML)
```yaml
# config/semantic-layer/metrics.yaml
- name: profit
  formula: "SUM(amount - cost)"
  base_table: transactions
```

### New System (Database)
```sql
INSERT INTO calculated_metrics (
  metric_name, formula, base_table, connection_id
) VALUES (
  'profit', 'SUM(amount - cost)', 'transactions', 'demo-sales-db'
);
```

**Benefits**:
- ✅ Dynamic: No file editing required
- ✅ User-specific: Can track who created metrics
- ✅ Connection-scoped: Different metrics per connection
- ✅ UI-managed: Create/edit through web interface
- ✅ Soft deletes: Can restore metrics if needed
- ✅ Audit trail: Timestamps for created/updated

## Troubleshooting

### Issue: Calculated metrics don't appear in UI

**Solution**: Check if metrics are in database:
```sql
SELECT * FROM calculated_metrics 
WHERE connection_id = 'demo-sales-db' AND is_active = true;
```

### Issue: Formula not used in queries

**Solution**: Verify semantic layer loads metrics from database in `_build_semantic_layer_from_schema()` function (src/api/routes.py line ~380)

### Issue: Save button doesn't persist metrics

**Solution**: Check browser console for API errors. Verify `/fieldmap/save` endpoint saves to `calculated_metrics` table when `is_custom=true` and `formula` is present.

## Future Enhancements

- [ ] Add formula validation (parse SQL before saving)
- [ ] Add formula builder UI (visual formula editor)
- [ ] Support table joins in formulas
- [ ] Add calculated dimension support (not just metrics)
- [ ] Add metric dependencies (metric A uses metric B)
- [ ] Add versioning for metric definitions
- [ ] Add bulk import/export of metrics
- [ ] Add metric usage analytics
