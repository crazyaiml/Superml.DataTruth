# DataTruth REST API Documentation

**Version:** 1.0  
**Base URL:** `https://api.datatruth.ai/v1` (or `http://localhost:8000` for local)  
**Last Updated:** December 31, 2025

---

## Table of Contents

1. [Authentication](#authentication)
2. [Rate Limiting](#rate-limiting)
3. [Error Handling](#error-handling)
4. [Endpoints](#endpoints)
   - [Health & Monitoring](#health--monitoring)
   - [Authentication](#authentication-endpoints)
   - [Query Execution](#query-execution)
   - [Chat Interface](#chat-interface)
   - [Semantic Layer](#semantic-layer)
   - [Database Connections](#database-connections)
   - [User Management](#user-management)
   - [Data Quality](#data-quality)
   - [Analytics & Insights](#analytics--insights)
   - [Setup & Configuration](#setup--configuration)
   - [Vector Search](#vector-search)
5. [Webhooks](#webhooks)
6. [SDKs](#sdks)

---

## Authentication

DataTruth uses JWT (JSON Web Token) authentication. Include your token in the Authorization header of all API requests.

### Getting a Token

```bash
POST /api/auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using the Token

Include the token in all subsequent requests:

```bash
GET /api/query
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Expiration

Tokens expire after **60 minutes**. Refresh your token using the `/api/auth/refresh` endpoint.

---

## Rate Limiting

API requests are rate-limited based on your subscription tier:

| Tier | Rate Limit |
|------|------------|
| **Free** | 100 requests/hour |
| **Professional** | 1,000 requests/hour |
| **Enterprise** | Unlimited |

**Rate Limit Headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

**Rate Limit Exceeded:**
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 3600

{
  "error": "Rate limit exceeded",
  "retry_after": 3600
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| **200** | Success |
| **201** | Created |
| **400** | Bad Request - Invalid input |
| **401** | Unauthorized - Invalid or missing token |
| **403** | Forbidden - Insufficient permissions |
| **404** | Not Found |
| **429** | Too Many Requests - Rate limit exceeded |
| **500** | Internal Server Error |
| **503** | Service Unavailable |

### Error Response Format

```json
{
  "error": "Error type",
  "message": "Detailed error message",
  "details": {
    "field": "Specific field error"
  },
  "request_id": "req_abc123"
}
```

---

## Endpoints

### Health & Monitoring

#### GET /health

Comprehensive health check of all system components.

**Request:**
```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-31T10:00:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 2
    },
    "vector_db": {
      "status": "healthy",
      "response_time_ms": 8
    },
    "openai": {
      "status": "healthy",
      "response_time_ms": 150
    }
  },
  "version": "1.0.0"
}
```

#### GET /ready

Readiness check for load balancers.

**Response:**
```json
{
  "status": "ready"
}
```

#### GET /alive

Liveness check for orchestrators.

**Response:**
```json
{
  "status": "alive"
}
```

#### GET /metrics

System metrics for monitoring (Prometheus format).

**Response:**
```json
{
  "requests_total": 12345,
  "requests_per_second": 25.5,
  "average_response_time_ms": 234,
  "error_rate": 0.01,
  "active_users": 45,
  "cache_hit_rate": 0.85,
  "database_connections": 20
}
```

---

### Authentication Endpoints

#### POST /api/auth/login

Authenticate and receive JWT token.

**Request:**
```json
{
  "username": "john.doe",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "user_123",
    "username": "john.doe",
    "email": "john@company.com",
    "role": "analyst",
    "full_name": "John Doe"
  }
}
```

#### POST /api/auth/logout

Invalidate current token.

**Request:**
```bash
POST /api/auth/logout
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "Successfully logged out"
}
```

#### POST /api/auth/refresh

Refresh expired or expiring token.

**Request:**
```bash
POST /api/auth/refresh
Authorization: Bearer <old_token>
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### GET /api/auth/me

Get current authenticated user information.

**Request:**
```bash
GET /api/auth/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "user_123",
  "username": "john.doe",
  "email": "john@company.com",
  "role": "analyst",
  "full_name": "John Doe",
  "created_at": "2025-01-01T00:00:00Z",
  "last_login": "2025-12-31T09:30:00Z",
  "permissions": ["query.execute", "metric.view", "export.data"]
}
```

---

### Query Execution

#### POST /api/query

Execute a natural language query.

**Request:**
```json
{
  "question": "Show me top 10 customers by revenue last quarter",
  "pagination": {
    "page": 1,
    "page_size": 10
  },
  "enable_analytics": true,
  "enable_caching": true,
  "context": {
    "department": "sales",
    "region": "west"
  }
}
```

**Response:**
```json
{
  "request_id": "req_abc123",
  "question": "Show me top 10 customers by revenue last quarter",
  "query_plan": {
    "metric": "revenue",
    "dimensions": ["customer_name"],
    "time_range": {
      "period": "last_quarter",
      "start_date": "2024-10-01",
      "end_date": "2024-12-31"
    },
    "limit": 10,
    "sort": {
      "field": "revenue",
      "order": "DESC"
    }
  },
  "sql": "SELECT c.name, SUM(s.amount) as revenue FROM sales s JOIN customers c ON s.customer_id = c.id WHERE s.sale_date >= '2024-10-01' AND s.sale_date <= '2024-12-31' GROUP BY c.name ORDER BY revenue DESC LIMIT 10",
  "results": [
    {
      "customer_name": "Acme Corp",
      "revenue": 1250000
    },
    {
      "customer_name": "TechCo Inc",
      "revenue": 980000
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_rows": 10,
    "has_more": false
  },
  "analytics": {
    "total": 5230000,
    "average": 523000,
    "median": 450000,
    "insights": [
      "Top customer contributes 24% of total revenue",
      "Revenue distribution is skewed with 20% of customers generating 80% of revenue"
    ]
  },
  "visualization": {
    "type": "bar_chart",
    "title": "Top 10 Customers by Revenue",
    "config": {
      "x_axis": "customer_name",
      "y_axis": "revenue",
      "color": "#4F46E5"
    }
  },
  "performance": {
    "intent_extraction_ms": 342,
    "sql_generation_ms": 45,
    "query_execution_ms": 123,
    "total_ms": 510
  },
  "explanation": "This query shows the top 10 customers by total revenue for Q4 2024 (October-December). Revenue is calculated as the sum of all sale amounts for each customer during this period.",
  "cached": false,
  "timestamp": "2025-12-31T10:00:00Z"
}
```

#### GET /api/query/{query_id}

Retrieve results of a previously executed query.

**Request:**
```bash
GET /api/query/req_abc123
Authorization: Bearer <token>
```

**Response:**
```json
{
  "query_id": "req_abc123",
  "status": "completed",
  "results": [...],
  "created_at": "2025-12-31T10:00:00Z"
}
```

---

### Chat Interface

#### POST /api/chat

Execute a query in conversational mode with follow-ups.

**Request:**
```json
{
  "message": "Show me revenue by month",
  "session_id": "session_abc123",
  "context": {
    "previous_queries": ["total revenue last year"]
  }
}
```

**Response:**
```json
{
  "session_id": "session_abc123",
  "message_id": "msg_456",
  "response": {
    "text": "Here's the revenue by month for 2024:",
    "results": [...],
    "visualization": {...}
  },
  "suggestions": [
    "Compare to previous year",
    "Show by region",
    "Identify top performing months"
  ],
  "timestamp": "2025-12-31T10:00:00Z"
}
```

#### GET /api/chat/sessions

List all chat sessions for the current user.

**Request:**
```bash
GET /api/chat/sessions?limit=20&offset=0
Authorization: Bearer <token>
```

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "session_abc123",
      "title": "Revenue Analysis Q4 2024",
      "created_at": "2025-12-31T09:00:00Z",
      "last_message": "2025-12-31T10:00:00Z",
      "message_count": 8
    }
  ],
  "total": 45,
  "limit": 20,
  "offset": 0
}
```

#### GET /api/chat/history/{session_id}

Get complete chat history for a session.

**Request:**
```bash
GET /api/chat/history/session_abc123
Authorization: Bearer <token>
```

**Response:**
```json
{
  "session_id": "session_abc123",
  "messages": [
    {
      "message_id": "msg_001",
      "role": "user",
      "content": "Show me revenue by month",
      "timestamp": "2025-12-31T09:00:00Z"
    },
    {
      "message_id": "msg_002",
      "role": "assistant",
      "content": "Here's the revenue by month...",
      "results": [...],
      "timestamp": "2025-12-31T09:00:05Z"
    }
  ],
  "total_messages": 8
}
```

---

### Semantic Layer

#### GET /api/semantic/metrics

List all available metrics.

**Request:**
```bash
GET /api/semantic/metrics?search=revenue
Authorization: Bearer <token>
```

**Response:**
```json
{
  "metrics": [
    {
      "id": "metric_001",
      "name": "revenue",
      "display_name": "Revenue",
      "aggregation": "SUM(amount)",
      "table": "sales",
      "description": "Total revenue from all sales",
      "data_type": "decimal",
      "format": "currency",
      "filters": [],
      "category": "financial"
    },
    {
      "id": "metric_002",
      "name": "average_revenue",
      "display_name": "Average Revenue",
      "aggregation": "AVG(amount)",
      "table": "sales",
      "description": "Average revenue per sale",
      "data_type": "decimal",
      "format": "currency"
    }
  ],
  "total": 45
}
```

#### POST /api/semantic/metrics

Create a new metric (Admin only).

**Request:**
```json
{
  "name": "customer_lifetime_value",
  "display_name": "Customer Lifetime Value",
  "aggregation": "SUM(amount)",
  "table": "sales",
  "description": "Total revenue from a customer over their lifetime",
  "filters": [
    {
      "field": "customer_id",
      "operator": "IS NOT NULL"
    }
  ],
  "category": "customer"
}
```

**Response:**
```json
{
  "id": "metric_003",
  "name": "customer_lifetime_value",
  "display_name": "Customer Lifetime Value",
  "created_at": "2025-12-31T10:00:00Z",
  "created_by": "user_123"
}
```

#### PUT /api/semantic/metrics/{metric_id}

Update an existing metric.

**Request:**
```json
{
  "display_name": "CLV",
  "description": "Updated description"
}
```

**Response:**
```json
{
  "id": "metric_003",
  "updated_at": "2025-12-31T10:05:00Z"
}
```

#### DELETE /api/semantic/metrics/{metric_id}

Delete a metric (Admin only).

**Response:**
```json
{
  "message": "Metric deleted successfully"
}
```

#### GET /api/semantic/dimensions

List all dimensions.

**Request:**
```bash
GET /api/semantic/dimensions
Authorization: Bearer <token>
```

**Response:**
```json
{
  "dimensions": [
    {
      "id": "dim_001",
      "name": "customer_name",
      "display_name": "Customer Name",
      "field": "customers.name",
      "table": "customers",
      "data_type": "string",
      "description": "Name of the customer"
    }
  ],
  "total": 32
}
```

---

### Database Connections

#### GET /api/connections

List all database connections.

**Request:**
```bash
GET /api/connections
Authorization: Bearer <token>
```

**Response:**
```json
{
  "connections": [
    {
      "id": "conn_001",
      "name": "Production DB",
      "type": "postgresql",
      "host": "prod-db.company.com",
      "port": 5432,
      "database": "sales_db",
      "status": "active",
      "last_tested": "2025-12-31T09:00:00Z",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 3
}
```

#### POST /api/connections

Create a new database connection (Admin only).

**Request:**
```json
{
  "name": "Analytics DB",
  "type": "postgresql",
  "host": "analytics.company.com",
  "port": 5432,
  "database": "analytics",
  "username": "readonly_user",
  "password": "secure_password",
  "ssl": true
}
```

**Response:**
```json
{
  "id": "conn_002",
  "name": "Analytics DB",
  "status": "pending",
  "created_at": "2025-12-31T10:00:00Z"
}
```

#### POST /api/connections/test

Test a database connection before saving.

**Request:**
```json
{
  "type": "postgresql",
  "host": "test-db.company.com",
  "port": 5432,
  "database": "test",
  "username": "test_user",
  "password": "test_password"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Connection successful",
  "response_time_ms": 45,
  "version": "PostgreSQL 16.1"
}
```

#### GET /api/schema

Get database schema for a connection.

**Request:**
```bash
GET /api/schema?connection_id=conn_001
Authorization: Bearer <token>
```

**Response:**
```json
{
  "connection_id": "conn_001",
  "tables": [
    {
      "name": "sales",
      "columns": [
        {
          "name": "id",
          "type": "integer",
          "nullable": false,
          "primary_key": true
        },
        {
          "name": "amount",
          "type": "decimal",
          "nullable": false
        },
        {
          "name": "sale_date",
          "type": "date",
          "nullable": false
        }
      ],
      "row_count": 1234567,
      "indexes": ["idx_sale_date", "idx_customer_id"]
    }
  ],
  "foreign_keys": [
    {
      "from_table": "sales",
      "from_column": "customer_id",
      "to_table": "customers",
      "to_column": "id"
    }
  ]
}
```

#### POST /api/fieldmap

Create field mappings (business-friendly names).

**Request:**
```json
{
  "connection_id": "conn_001",
  "mappings": [
    {
      "technical_name": "cust_nm",
      "business_name": "customer_name",
      "description": "Name of the customer"
    }
  ]
}
```

**Response:**
```json
{
  "created": 1,
  "message": "Field mappings created successfully"
}
```

---

### User Management

#### GET /api/users

List all users (Admin only).

**Request:**
```bash
GET /api/users?role=analyst&limit=20
Authorization: Bearer <token>
```

**Response:**
```json
{
  "users": [
    {
      "id": "user_123",
      "username": "john.doe",
      "email": "john@company.com",
      "role": "analyst",
      "full_name": "John Doe",
      "status": "active",
      "created_at": "2025-01-01T00:00:00Z",
      "last_login": "2025-12-31T09:00:00Z"
    }
  ],
  "total": 45,
  "limit": 20,
  "offset": 0
}
```

#### POST /api/users

Create a new user (Admin only).

**Request:**
```json
{
  "username": "jane.smith",
  "email": "jane@company.com",
  "password": "SecurePass123!",
  "role": "analyst",
  "full_name": "Jane Smith",
  "department": "sales"
}
```

**Response:**
```json
{
  "id": "user_124",
  "username": "jane.smith",
  "email": "jane@company.com",
  "role": "analyst",
  "created_at": "2025-12-31T10:00:00Z"
}
```

#### PUT /api/users/{user_id}

Update user information.

**Request:**
```json
{
  "role": "admin",
  "department": "engineering"
}
```

**Response:**
```json
{
  "id": "user_124",
  "updated_at": "2025-12-31T10:05:00Z"
}
```

#### DELETE /api/users/{user_id}

Delete a user (Admin only).

**Response:**
```json
{
  "message": "User deleted successfully"
}
```

#### GET /api/users/{user_id}/activity

Get user activity logs.

**Request:**
```bash
GET /api/users/user_123/activity?start_date=2025-12-01&limit=50
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user_id": "user_123",
  "activities": [
    {
      "id": "act_001",
      "type": "query_executed",
      "description": "Executed query: Show revenue by month",
      "timestamp": "2025-12-31T10:00:00Z",
      "metadata": {
        "query_id": "req_abc123",
        "execution_time_ms": 234
      }
    }
  ],
  "total": 156,
  "limit": 50
}
```

---

### Data Quality

#### GET /api/quality

Get data quality scores.

**Request:**
```bash
GET /api/quality?connection_id=conn_001&table=sales
Authorization: Bearer <token>
```

**Response:**
```json
{
  "connection_id": "conn_001",
  "table": "sales",
  "overall_score": 0.85,
  "dimensions": {
    "freshness": {
      "score": 0.95,
      "description": "Data is recent",
      "last_update": "2025-12-31T09:00:00Z",
      "details": "Latest record is less than 1 hour old"
    },
    "completeness": {
      "score": 0.88,
      "description": "Most fields have values",
      "null_percentage": 0.12,
      "incomplete_columns": ["phone", "address"]
    },
    "accuracy": {
      "score": 0.92,
      "description": "Values within expected ranges",
      "anomalies_detected": 3
    },
    "consistency": {
      "score": 0.80,
      "description": "Some format inconsistencies",
      "issues": ["Date format varies", "Phone number formats differ"]
    },
    "validity": {
      "score": 0.85,
      "description": "Most values follow constraints",
      "violations": 45
    },
    "uniqueness": {
      "score": 0.90,
      "description": "Few duplicates detected",
      "duplicate_count": 12
    }
  },
  "recommendations": [
    "Standardize phone number format",
    "Add NOT NULL constraint to critical fields",
    "Review and remove duplicate records"
  ],
  "measured_at": "2025-12-31T10:00:00Z"
}
```

#### GET /api/quality/profile/{table_name}

Get data profiling information.

**Request:**
```bash
GET /api/quality/profile/sales
Authorization: Bearer <token>
```

**Response:**
```json
{
  "table": "sales",
  "row_count": 1234567,
  "columns": [
    {
      "name": "amount",
      "type": "decimal",
      "statistics": {
        "min": 10.50,
        "max": 999999.99,
        "mean": 5234.56,
        "median": 2345.00,
        "std_dev": 8765.43
      },
      "null_count": 0,
      "null_percentage": 0.0,
      "unique_count": 456789,
      "top_values": []
    },
    {
      "name": "customer_name",
      "type": "string",
      "unique_count": 45678,
      "null_count": 123,
      "null_percentage": 0.01,
      "top_values": [
        {"value": "Acme Corp", "count": 234},
        {"value": "TechCo Inc", "count": 189}
      ]
    }
  ]
}
```

---

### Analytics & Insights

#### GET /api/insights

Get AI-generated insights.

**Request:**
```bash
GET /api/insights?connection_id=conn_001&type=trends
Authorization: Bearer <token>
```

**Response:**
```json
{
  "insights": [
    {
      "id": "insight_001",
      "type": "trend",
      "title": "Revenue Growth Acceleration",
      "description": "Revenue has increased 25% month-over-month for the last 3 months",
      "confidence": 0.92,
      "metrics": ["revenue"],
      "time_range": {
        "start": "2024-10-01",
        "end": "2024-12-31"
      },
      "recommendations": [
        "Identify factors driving growth",
        "Ensure capacity to maintain trajectory"
      ],
      "generated_at": "2025-12-31T10:00:00Z"
    },
    {
      "id": "insight_002",
      "type": "anomaly",
      "title": "Unusual Spike in Returns",
      "description": "Return rate increased to 15% (normal: 3%)",
      "confidence": 0.88,
      "severity": "high",
      "affected_products": ["Product A", "Product B"],
      "recommendations": [
        "Investigate product quality issues",
        "Review recent shipments"
      ]
    }
  ],
  "total": 8
}
```

#### GET /api/suggestions

Get query suggestions based on data and history.

**Request:**
```bash
GET /api/suggestions?context=revenue_analysis
Authorization: Bearer <token>
```

**Response:**
```json
{
  "suggestions": [
    {
      "question": "Show revenue by product category",
      "relevance": 0.95,
      "category": "revenue"
    },
    {
      "question": "Compare this month's revenue to last month",
      "relevance": 0.88,
      "category": "comparison"
    },
    {
      "question": "Show top 5 customers by revenue",
      "relevance": 0.82,
      "category": "ranking"
    }
  ]
}
```

#### GET /api/activity/analytics

Get platform usage analytics (Admin only).

**Request:**
```bash
GET /api/activity/analytics?start_date=2025-12-01&end_date=2025-12-31
Authorization: Bearer <token>
```

**Response:**
```json
{
  "period": {
    "start": "2025-12-01",
    "end": "2025-12-31"
  },
  "metrics": {
    "total_queries": 12345,
    "unique_users": 45,
    "average_queries_per_user": 274,
    "average_response_time_ms": 456,
    "cache_hit_rate": 0.67,
    "error_rate": 0.02
  },
  "top_queries": [
    {
      "question": "Show revenue by month",
      "count": 234
    }
  ],
  "top_users": [
    {
      "username": "john.doe",
      "query_count": 567
    }
  ],
  "popular_metrics": [
    {"name": "revenue", "usage_count": 890},
    {"name": "customer_count", "usage_count": 456}
  ]
}
```

---

### Setup & Configuration

#### GET /api/setup/status

Check if platform setup is complete.

**Request:**
```bash
GET /api/setup/status
```

**Response:**
```json
{
  "is_configured": true,
  "needs_setup": false,
  "setup_step": null,
  "version": "1.0.0"
}
```

#### POST /api/setup/initialize

Initialize the platform (first-time setup).

**Request:**
```json
{
  "database": {
    "use_docker_db": true,
    "host": "postgres",
    "port": 5432,
    "name": "datatruth_internal",
    "user": "datatruth_app",
    "password": "secure_password"
  },
  "openai": {
    "api_key": "sk-proj-...",
    "model": "gpt-4o-mini",
    "temperature": 0.7
  },
  "admin_user": {
    "username": "admin",
    "password": "SecurePass123!",
    "email": "admin@company.com",
    "full_name": "System Administrator"
  },
  "app_name": "DataTruth"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Platform initialized successfully",
  "admin_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "next_steps": [
    "Login with admin credentials",
    "Connect your database",
    "Create additional users"
  ]
}
```

#### POST /api/setup/test-database

Test database connection during setup.

**Request:**
```json
{
  "host": "postgres",
  "port": 5432,
  "database": "datatruth",
  "username": "test_user",
  "password": "test_password"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Connection successful",
  "version": "PostgreSQL 16.1",
  "response_time_ms": 45
}
```

#### POST /api/setup/test-openai

Test OpenAI API key during setup.

**Request:**
```json
{
  "api_key": "sk-proj-...",
  "model": "gpt-4o-mini"
}
```

**Response:**
```json
{
  "success": true,
  "message": "OpenAI API key is valid",
  "model": "gpt-4o-mini",
  "organization": "org-abc123"
}
```

---

### Vector Search

#### GET /api/v1/vector/stats

Get vector database statistics.

**Request:**
```bash
GET /api/v1/vector/stats
Authorization: Bearer <token>
```

**Response:**
```json
{
  "fields_count": 1234,
  "learned_synonyms_count": 567,
  "queries_count": 8901,
  "persist_directory": "./data/chroma"
}
```

#### POST /api/v1/vector/search/fields

Search for fields using semantic search.

**Request:**
```json
{
  "query": "customer revenue",
  "connection_id": "conn_001",
  "field_type": "metric",
  "top_k": 10
}
```

**Response:**
```json
{
  "query": "customer revenue",
  "matches": [
    {
      "field": "total_revenue",
      "table": "sales",
      "description": "Sum of all sales amounts",
      "score": 0.92,
      "metadata": {
        "type": "metric",
        "data_type": "decimal"
      }
    }
  ],
  "count": 10
}
```

#### GET /api/v1/vector/synonyms/{connection_id}

Get learned synonyms for a connection.

**Request:**
```bash
GET /api/v1/vector/synonyms/conn_001?field_type=metric
Authorization: Bearer <token>
```

**Response:**
```json
{
  "connection_id": "conn_001",
  "synonyms": {
    "revenu": ["revenue", "total_revenue"],
    "cust": ["customer", "customer_name"],
    "tot sal": ["total_sales", "sales_amount"]
  }
}
```

---

## Usage Examples

### Python with requests

```python
import requests

class DataTruthClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.token = None
    
    def login(self, username, password):
        """Authenticate and get JWT token"""
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        return data
    
    def _headers(self):
        """Get authorization headers"""
        if not self.token:
            raise ValueError("Not authenticated. Call login() first.")
        return {"Authorization": f"Bearer {self.token}"}
    
    def query(self, question, **kwargs):
        """Execute a natural language query"""
        response = requests.post(
            f"{self.base_url}/api/query",
            headers=self._headers(),
            json={"question": question, **kwargs}
        )
        response.raise_for_status()
        return response.json()
    
    def get_metrics(self):
        """Get all available metrics"""
        response = requests.get(
            f"{self.base_url}/api/semantic/metrics",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    def get_connections(self):
        """Get all database connections"""
        response = requests.get(
            f"{self.base_url}/api/connections",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

# Usage
client = DataTruthClient()
client.login("admin", "admin123")

# Execute query
result = client.query("Show me revenue by month")
print(f"Found {len(result['results'])} results")
for row in result['results']:
    print(row)

# Get metrics
metrics = client.get_metrics()
print(f"Available metrics: {len(metrics['metrics'])}")
```

### JavaScript/TypeScript with fetch

```javascript
class DataTruthClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    this.token = null;
  }

  async login(username, password) {
    const response = await fetch(`${this.baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    if (!response.ok) {
      throw new Error(`Login failed: ${response.statusText}`);
    }
    
    const data = await response.json();
    this.token = data.access_token;
    return data;
  }

  async query(question, options = {}) {
    const response = await fetch(`${this.baseUrl}/api/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`
      },
      body: JSON.stringify({ question, ...options })
    });
    
    if (!response.ok) {
      throw new Error(`Query failed: ${response.statusText}`);
    }
    
    return await response.json();
  }

  async getMetrics() {
    const response = await fetch(`${this.baseUrl}/api/semantic/metrics`, {
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to get metrics: ${response.statusText}`);
    }
    
    return await response.json();
  }
}

// Usage
const client = new DataTruthClient();
await client.login('admin', 'admin123');

const result = await client.query('Show me revenue by month');
console.log(result.results);
```

### cURL Examples

```bash
# Login and get token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Response: {"access_token":"eyJhbG...", "token_type":"bearer"}

# Execute a query
curl -X POST http://localhost:8000/api/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show top 10 customers by revenue",
    "enable_analytics": true
  }'

# Get metrics
curl -X GET http://localhost:8000/api/semantic/metrics \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create user (Admin only)
curl -X POST http://localhost:8000/api/users \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "jane.doe",
    "email": "jane@company.com",
    "password": "SecurePass123!",
    "role": "analyst"
  }'

# Get data quality scores
curl -X GET "http://localhost:8000/api/quality?connection_id=conn_001&table=sales" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test database connection
curl -X POST http://localhost:8000/api/connections/test \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "mydb",
    "username": "user",
    "password": "pass"
  }'
```

### Bash Script Example

Complete example script for querying DataTruth:

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"
USERNAME="admin"
PASSWORD="admin123"

# Login and extract token
echo "Logging in..."
RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo $RESPONSE | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo "Login failed"
    exit 1
fi

echo "Logged in successfully"

# Execute query
echo "Executing query..."
curl -s -X POST "$BASE_URL/api/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Show me revenue by month"}' \
  | jq '.results'
```

---

## Webhooks

*Coming Soon*

Configure webhooks to receive real-time notifications about events:

- `query.completed` - Query execution completed
- `insight.generated` - New insight generated  
- `alert.triggered` - Data quality alert triggered
- `user.created` - New user created

---

## Best Practices

### 1. Authentication
- Store API keys securely (environment variables, secret managers)
- Rotate tokens regularly
- Use separate keys for different environments

### 2. Error Handling
- Always check HTTP status codes
- Implement exponential backoff for rate limits
- Log errors with request IDs for debugging

### 3. Performance
- Enable caching for repeated queries
- Use pagination for large result sets
- Batch requests when possible

### 4. Security
- Use HTTPS in production
- Validate and sanitize all inputs
- Implement proper CORS policies

---

## Support

### API Issues
- 📧 Email: api-support@datatruth.ai
- 💬 Discord: [discord.gg/datatruth](https://discord.gg/datatruth)
- 📚 Docs: [docs.datatruth.ai](https://docs.datatruth.ai)

### Feature Requests
- Submit via [GitHub Issues](https://github.com/yourusername/datatruth/issues)

---

**API Version:** 1.0  
**Documentation Updated:** December 31, 2025  
**Maintained By:** DataTruth API Team
