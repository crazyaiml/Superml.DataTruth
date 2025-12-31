# RLS Configuration System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RLS Configuration System                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                              Frontend Layer                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  RLS Configuration UI (/rls-config)                                 │     │
│  │  ┌────────────────┐  ┌────────────────┐  ┌───────────────────┐    │     │
│  │  │ User Selector  │  │ Role Selector  │  │ Filter Editor     │    │     │
│  │  │                │  │                │  │                   │    │     │
│  │  │ - Dropdown     │  │ - ADMIN        │  │ - Table selector  │    │     │
│  │  │ - Search       │  │ - ANALYST      │  │ - Column selector │    │     │
│  │  │ - User list    │  │ - VIEWER       │  │ - Operator        │    │     │
│  │  │                │  │ - EXTERNAL     │  │ - Value input     │    │     │
│  │  └────────────────┘  └────────────────┘  └───────────────────┘    │     │
│  │                                                                     │     │
│  │  ┌──────────────────────────────────────────────────────────┐     │     │
│  │  │ Filter List                                               │     │     │
│  │  │ ┌───────────────────────────────────────────────────┐    │     │     │
│  │  │ │ companies.region = "Region 1"         [Edit] [X]  │    │     │     │
│  │  │ └───────────────────────────────────────────────────┘    │     │     │
│  │  │ ┌───────────────────────────────────────────────────┐    │     │     │
│  │  │ │ transactions.date >= "2024-01-01"     [Edit] [X]  │    │     │     │
│  │  │ └───────────────────────────────────────────────────┘    │     │     │
│  │  └──────────────────────────────────────────────────────────┘     │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                               │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
                                        │ HTTP/REST API
                                        │
┌───────────────────────────────────────▼───────────────────────────────────────┐
│                               Backend Layer                                    │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ REST API Endpoints (/api/v1/rls/*)                                      │ │
│  │                                                                          │ │
│  │  POST   /rls/filters              - Create RLS filter                   │ │
│  │  GET    /rls/filters/user/{id}    - Get user filters                   │ │
│  │  PUT    /rls/filters/{id}         - Update filter                      │ │
│  │  DELETE /rls/filters/{id}         - Delete filter                      │ │
│  │                                                                          │ │
│  │  POST   /rls/roles                - Assign role                        │ │
│  │  GET    /rls/roles/user/{id}      - Get user roles                     │ │
│  │                                                                          │ │
│  │  GET    /rls/config/user/{id}/connection/{id}  - Get complete config   │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ RLS Loader (src/user/rls_loader.py)                                     │ │
│  │                                                                          │ │
│  │  load_user_rls_context()  ────►  Loads from Database                   │ │
│  │         │                                                                │ │
│  │         ├──► Fetch user role                                            │ │
│  │         ├──► Fetch RLS filters                                          │ │
│  │         ├──► Fetch table permissions                                    │ │
│  │         └──► Build UserContext                                          │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ Query Execution Flow                                                     │ │
│  │                                                                          │ │
│  │  1. User Query ──────────────────────────────────────────┐              │ │
│  │                                                           │              │ │
│  │  2. Load RLS Context (from DB) ◄──────────────────────── │              │ │
│  │     │                                                     │              │ │
│  │     ├─ user_rls_filters                                  │              │ │
│  │     ├─ user_connection_roles                             │              │ │
│  │     └─ user_table_permissions                            │              │ │
│  │                                                           │              │ │
│  │  3. Create UserContext ◄────────────────────────────────┘              │ │
│  │     │                                                                    │ │
│  │     ├─ user_id, username, roles                                         │ │
│  │     ├─ permissions (QUERY_DATA, VIEW_METRICS, etc.)                    │ │
│  │     ├─ rls_filters (region = "Region 1", etc.)                         │ │
│  │     └─ table_permissions (allowed columns, etc.)                       │ │
│  │                                                                          │ │
│  │  4. Execute Query ◄─────────────────────────────────────────┐          │ │
│  │     │                                                         │          │ │
│  │     ├─ Validate permissions                                  │          │ │
│  │     ├─ Inject RLS filters (WHERE clauses)                   │          │ │
│  │     ├─ Restrict columns                                      │          │ │
│  │     └─ Execute filtered SQL                                  │          │ │
│  │                                                               │          │ │
│  │  5. Return Filtered Results ◄───────────────────────────────┘          │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                                │
└────────────────────────────────────────┬───────────────────────────────────────┘
                                         │
                                         │ SQL Queries
                                         │
┌────────────────────────────────────────▼───────────────────────────────────────┐
│                              Database Layer                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐ │
│  │ RLS Configuration Tables                                                  │ │
│  │                                                                            │ │
│  │  ┌────────────────────┐     ┌──────────────────────┐                     │ │
│  │  │ user_rls_filters   │     │ user_connection_roles│                     │ │
│  │  ├────────────────────┤     ├──────────────────────┤                     │ │
│  │  │ id                 │     │ id                   │                     │ │
│  │  │ user_id            │     │ user_id              │                     │ │
│  │  │ connection_id      │     │ connection_id        │                     │ │
│  │  │ table_name         │     │ role (ANALYST, etc.) │                     │ │
│  │  │ column_name        │     │ is_active            │                     │ │
│  │  │ operator (=, IN)   │     │ created_at           │                     │ │
│  │  │ filter_value       │     └──────────────────────┘                     │ │
│  │  │ is_active          │                                                   │ │
│  │  └────────────────────┘     ┌──────────────────────────┐                 │ │
│  │                              │ user_table_permissions   │                 │ │
│  │  ┌─────────────────────────┐├──────────────────────────┤                 │ │
│  │  │rls_configuration_audit  ││ id                       │                 │ │
│  │  ├─────────────────────────┤│ user_id                  │                 │ │
│  │  │ id                      ││ connection_id            │                 │ │
│  │  │ user_id                 ││ table_name               │                 │ │
│  │  │ connection_id           ││ can_read / can_write     │                 │ │
│  │  │ action (CREATE/UPDATE)  ││ allowed_columns (JSON)   │                 │ │
│  │  │ entity_type             ││ denied_columns (JSON)    │                 │ │
│  │  │ old_value / new_value   │└──────────────────────────┘                 │ │
│  │  │ performed_by            │                                              │ │
│  │  │ performed_at            │                                              │ │
│  │  └─────────────────────────┘                                              │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                         Example: Query Execution                             │
└─────────────────────────────────────────────────────────────────────────────┘

User: Bhanu
Query: "Show me all companies"

Step 1: Load RLS Configuration
┌───────────────────────────────────────┐
│ Database Query:                       │
│ SELECT * FROM user_rls_filters        │
│ WHERE user_id = 1                     │
│   AND connection_id = 1               │
│   AND is_active = TRUE                │
│                                       │
│ Result:                               │
│ - table: companies                    │
│ - column: region                      │
│ - operator: =                         │
│ - value: "Region 1"                   │
└───────────────────────────────────────┘

Step 2: Create UserContext
┌───────────────────────────────────────┐
│ UserContext(                          │
│   user_id="1",                        │
│   username="bhanu",                   │
│   roles=[Role.ANALYST],               │
│   rls_filters=[                       │
│     RLSFilter(                        │
│       table="companies",              │
│       column="region",                │
│       operator="=",                   │
│       value="Region 1"                │
│     )                                 │
│   ]                                   │
│ )                                     │
└───────────────────────────────────────┘

Step 3: Original SQL Query
┌───────────────────────────────────────┐
│ SELECT id, name, region, industry    │
│ FROM companies                        │
└───────────────────────────────────────┘

Step 4: Apply RLS Filter (Inject WHERE)
┌───────────────────────────────────────┐
│ SELECT id, name, region, industry    │
│ FROM companies                        │
│ WHERE region = 'Region 1'            │
│       ^^^^^^^^^^^^^^^^^^^             │
│       Injected by RLS engine          │
└───────────────────────────────────────┘

Step 5: Execute & Return Results
┌───────────────────────────────────────┐
│ Results (only Region 1 companies):   │
│                                       │
│ | id | name     | region    |...     │
│ |----|----------|-----------|...     │
│ | 1  | Acme Inc | Region 1  |...     │
│ | 2  | Tech Co  | Region 1  |...     │
│ | 5  | Data LLC | Region 1  |...     │
│                                       │
│ (Region 2, 3, 4 companies filtered   │
│  out by RLS)                          │
└───────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                    Multi-User Scenario Comparison                            │
└─────────────────────────────────────────────────────────────────────────────┘

                     Same Query: "Show me all companies"

┌──────────────────────────┐              ┌──────────────────────────┐
│ User: Bhanu              │              │ User: ANBCD              │
├──────────────────────────┤              ├──────────────────────────┤
│ Role: ANALYST            │              │ Role: ANALYST            │
│ RLS: region = "Region 1" │              │ RLS: region = "Region 2" │
└──────────────────────────┘              └──────────────────────────┘
           │                                         │
           │                                         │
           ▼                                         ▼
┌──────────────────────────┐              ┌──────────────────────────┐
│ SQL Query:               │              │ SQL Query:               │
│                          │              │                          │
│ SELECT ...               │              │ SELECT ...               │
│ FROM companies           │              │ FROM companies           │
│ WHERE region = 'Region 1'│              │ WHERE region = 'Region 2'│
└──────────────────────────┘              └──────────────────────────┘
           │                                         │
           │                                         │
           ▼                                         ▼
┌──────────────────────────┐              ┌──────────────────────────┐
│ Results:                 │              │ Results:                 │
│                          │              │                          │
│ - Acme Inc (Region 1)    │              │ - Global Corp (Region 2) │
│ - Tech Co (Region 1)     │              │ - Asia Ltd (Region 2)    │
│ - Data LLC (Region 1)    │              │ - Euro GmbH (Region 2)   │
│                          │              │                          │
│ Total: 3 companies       │              │ Total: 4 companies       │
└──────────────────────────┘              └──────────────────────────┘

         Same Query → Different Filters → Different Results


┌─────────────────────────────────────────────────────────────────────────────┐
│                         Configuration Hierarchy                              │
└─────────────────────────────────────────────────────────────────────────────┘

System Level
    │
    ├─► Connection Level (Database 1, Database 2, etc.)
    │       │
    │       ├─► User Level (Bhanu, ANBCD, etc.)
    │       │       │
    │       │       ├─► Role (ANALYST, VIEWER, etc.)
    │       │       │       │
    │       │       │       └─► Permissions
    │       │       │           - QUERY_DATA
    │       │       │           - VIEW_METRICS
    │       │       │           - VIEW_INSIGHTS
    │       │       │
    │       │       ├─► RLS Filters
    │       │       │       │
    │       │       │       ├─► Filter 1: companies.region = "Region 1"
    │       │       │       ├─► Filter 2: transactions.date >= "2024-01-01"
    │       │       │       └─► Filter N: ...
    │       │       │
    │       │       └─► Table Permissions
    │       │               │
    │       │               ├─► Table 1: companies
    │       │               │   - allowed_columns: [id, name, region]
    │       │               │   - denied_columns: [internal_notes]
    │       │               │
    │       │               └─► Table 2: transactions
    │       │                   - allowed_columns: [*]
    │       │                   - denied_columns: [credit_card]
    │       │
    │       └─► (Other users...)
    │
    └─► (Other connections...)


┌─────────────────────────────────────────────────────────────────────────────┐
│                              Security Flow                                   │
└─────────────────────────────────────────────────────────────────────────────┘

1. Authentication
   ┌────────────────────────┐
   │ User Login (JWT)       │
   │ Token Validation       │
   └────────┬───────────────┘
            │
            ▼
2. Load RLS Configuration
   ┌────────────────────────┐
   │ Query Database         │
   │ - Roles                │
   │ - Filters              │
   │ - Permissions          │
   └────────┬───────────────┘
            │
            ▼
3. Authorization Check
   ┌────────────────────────┐
   │ Validate Permissions   │
   │ - Can query data?      │
   │ - Can access table?    │
   │ - Can access columns?  │
   └────────┬───────────────┘
            │
            ▼
4. Apply RLS Filters
   ┌────────────────────────┐
   │ Inject WHERE clauses   │
   │ Modify SQL query       │
   └────────┬───────────────┘
            │
            ▼
5. Execute Query
   ┌────────────────────────┐
   │ Run filtered SQL       │
   │ Return filtered data   │
   └────────┬───────────────┘
            │
            ▼
6. Audit Logging
   ┌────────────────────────┐
   │ Log query execution    │
   │ Log data access        │
   └────────────────────────┘
