# DataTruth Architecture

**Version:** 1.0  
**Last Updated:** December 31, 2025

---

## Table of Contents

1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Technology Stack](#technology-stack)
6. [Infrastructure Architecture](#infrastructure-architecture)
7. [Security Architecture](#security-architecture)
8. [Deployment Architecture](#deployment-architecture)
9. [Scalability & Performance](#scalability--performance)
10. [Integration Architecture](#integration-architecture)

---

## System Overview

DataTruth is an AI-powered analytics SaaS platform that enables natural language queries over relational databases. The system transforms business questions into SQL queries using Large Language Models (LLMs), executes them safely, and returns results with visualizations and insights.

### Core Principles

- **Data Correctness**: No hallucinated numbers, only real database results
- **Security First**: Read-only access, SQL injection prevention, audit trails
- **Governed Analytics**: Semantic layer ensures consistent business definitions
- **Explainability**: Every answer is traceable and auditable
- **Adaptive Learning**: System learns from user interactions and feedback

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface Layer                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Web App   │  │  Mobile App │  │   REST API  │            │
│  │  (React)    │  │  (Planned)  │  │  Clients    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ HTTPS / WebSocket
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      API Gateway & Auth Layer                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI + JWT Auth + Rate Limiting + CORS               │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                     Application Service Layer                    │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Query       │  │   User       │  │  Connection  │          │
│  │  Orchestrator│  │   Manager    │  │  Manager     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Analytics   │  │   Activity   │  │   Insights   │          │
│  │  Engine      │  │   Tracker    │  │   Generator  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
┌───────────────▼──────┐   ┌───────────▼──────────────────────────┐
│   AI/ML Layer        │   │    Data Processing Layer             │
│                      │   │                                       │
│  ┌────────────────┐ │   │  ┌──────────────┐  ┌──────────────┐ │
│  │  LLM Client    │ │   │  │  Semantic    │  │  SQL Builder │ │
│  │  (OpenAI/Azure)│ │   │  │  Layer       │  │  & Validator │ │
│  └────────────────┘ │   │  └──────────────┘  └──────────────┘ │
│                      │   │                                       │
│  ┌────────────────┐ │   │  ┌──────────────┐  ┌──────────────┐ │
│  │  Vector Store  │ │   │  │  Query       │  │  Data        │ │
│  │  (ChromaDB)    │ │   │  │  Planner     │  │  Quality     │ │
│  └────────────────┘ │   │  └──────────────┘  └──────────────┘ │
│                      │   │                                       │
│  ┌────────────────┐ │   │  ┌──────────────┐  ┌──────────────┐ │
│  │  Learning      │ │   │  │  Fuzzy       │  │  Field       │ │
│  │  Agent         │ │   │  │  Matcher     │  │  Mapper      │ │
│  └────────────────┘ │   │  └──────────────┘  └──────────────┘ │
└──────────────────────┘   └───────────────────────────────────────┘
                                            │
                                            │
┌───────────────────────────────────────────▼───────────────────────┐
│                        Data Storage Layer                          │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐│
│  │  Internal DB     │  │  Client Database │  │  Vector DB      ││
│  │  (PostgreSQL)    │  │  (PostgreSQL/    │  │  (ChromaDB)     ││
│  │                  │  │   MySQL/Other)   │  │                 ││
│  │  - Users         │  │  - Customer Data │  │  - Embeddings   ││
│  │  - Config        │  │  - Business Data │  │  - Synonyms     ││
│  │  - Audit Logs    │  │  - Analytics     │  │  - Learned      ││
│  │  - Semantic      │  │                  │  │    Patterns     ││
│  │    Layer         │  │                  │  │                 ││
│  └──────────────────┘  └──────────────────┘  └─────────────────┘│
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐                      │
│  │  Cache Layer     │  │  Object Storage  │                      │
│  │  (Redis)         │  │  (S3/Azure Blob) │                      │
│  │  - Query Cache   │  │  - Exports       │                      │
│  │  - Session Cache │  │  - Backups       │                      │
│  │  - Rate Limits   │  │  - Attachments   │                      │
│  └──────────────────┘  └──────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. Frontend Layer (React + TypeScript)

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── AdminPanel.tsx
│   │   ├── ChatInterface.tsx
│   │   ├── DataChart.tsx
│   │   ├── DataTable.tsx
│   │   ├── SearchAndAsk.tsx
│   │   ├── SemanticLayer.tsx
│   │   ├── UserManagement.tsx
│   │   └── Setup/
│   │       └── SetupWizard.tsx
│   ├── api/                 # API client layer
│   │   └── client.ts
│   ├── contexts/            # React contexts
│   │   └── AuthContext.tsx
│   ├── config.ts            # Frontend configuration
│   └── App.tsx              # Main application
```

**Key Features:**
- Single Page Application (SPA) with React Router
- TailwindCSS for responsive design
- Recharts for data visualization
- Real-time updates via WebSocket (planned)
- Progressive Web App (PWA) capabilities

### 2. API Gateway Layer (FastAPI)

```python
src/api/
├── app.py              # Main FastAPI application
├── routes.py           # Primary API endpoints
├── auth.py             # Authentication & authorization
├── rate_limit.py       # Rate limiting middleware
├── setup.py            # Setup wizard endpoints
├── vector_routes.py    # Vector search endpoints
└── models.py           # Request/response models
```

**Endpoints:**

```
Authentication
POST   /api/auth/login          - User login
POST   /api/auth/logout         - User logout
POST   /api/auth/refresh        - Refresh JWT token
GET    /api/auth/me             - Get current user

Query Execution
POST   /api/query               - Execute natural language query
GET    /api/query/{id}          - Get query results
POST   /api/chat                - Chat-based query interface
GET    /api/chat/sessions       - Get chat sessions
GET    /api/chat/history        - Get chat history

Semantic Layer
GET    /api/semantic/metrics    - List all metrics
POST   /api/semantic/metrics    - Create new metric
PUT    /api/semantic/metrics/{id} - Update metric
DELETE /api/semantic/metrics/{id} - Delete metric
GET    /api/semantic/dimensions - List dimensions

Data Management
GET    /api/connections         - List database connections
POST   /api/connections         - Create connection
POST   /api/connections/test    - Test connection
GET    /api/schema              - Get database schema
POST   /api/fieldmap            - Create field mapping

User Management
GET    /api/users               - List users
POST   /api/users               - Create user
PUT    /api/users/{id}          - Update user
DELETE /api/users/{id}          - Delete user
GET    /api/users/{id}/activity - User activity logs

Analytics & Insights
GET    /api/insights            - Get AI insights
GET    /api/quality             - Data quality scores
GET    /api/activity/analytics  - Platform analytics
GET    /api/suggestions         - Query suggestions

Setup & Configuration
GET    /api/setup/status        - Check setup status
POST   /api/setup/initialize    - Initialize platform
POST   /api/setup/test-database - Test DB connection
POST   /api/setup/test-openai   - Test OpenAI API

Health & Monitoring
GET    /health                  - Health check
GET    /metrics                 - Prometheus metrics
```

### 3. Query Orchestrator

**Purpose:** Coordinates the entire query execution pipeline

```python
class QueryOrchestrator:
    """
    Pipeline Stages:
    1. Load semantic layer
    2. Extract intent with LLM
    3. Generate SQL
    4. Validate SQL for security
    5. Execute query (read-only)
    6. Calculate analytics
    7. Format response
    """
```

**Components:**
- **Semantic Loader**: Retrieves business definitions
- **Intent Extractor**: Uses LLM to understand user question
- **Query Planner**: Creates structured query plan
- **SQL Builder**: Generates SQL from plan
- **SQL Validator**: Security validation
- **Query Executor**: Safe execution with timeouts
- **Plan Cache**: Caches query plans for similar questions
- **Result Cache**: Caches query results

### 4. Semantic Layer

```python
src/semantic/
├── loader.py           # Load semantic definitions
├── models.py           # Metric & dimension models
├── search_index.py     # Vector-based semantic search
├── ai_synonyms.py      # AI-learned synonyms
├── versioning.py       # Semantic layer versioning
└── realtime_metrics.py # Real-time calculated metrics
```

**Semantic Layer Model:**

```python
class Metric:
    name: str                    # e.g., "revenue"
    aggregation: str             # e.g., "SUM(amount)"
    table: str                   # Source table
    filters: List[FilterDef]     # Default filters
    description: str             # Business definition
    
class Dimension:
    name: str                    # e.g., "customer_name"
    field: str                   # Database field
    table: str                   # Source table
    data_type: str               # Data type
    friendly_name: str           # Display name
```

### 5. LLM Client (AI Layer)

```python
src/llm/
├── client.py           # OpenAI/Azure OpenAI client
└── prompts.py          # Prompt templates
```

**Capabilities:**
- Intent extraction from natural language
- Field description generation
- Query suggestion generation
- Synonym learning
- Error explanation

**Models Supported:**
- OpenAI GPT-4 / GPT-4 Turbo
- OpenAI GPT-3.5 Turbo
- Azure OpenAI (all models)
- Future: Local models (Llama, Mistral)

### 6. Vector Store (ChromaDB)

```python
src/vector/
└── vector_store.py     # ChromaDB management
```

**Collections:**
- **semantic_fields**: Database fields with metadata
- **metrics**: Business metrics definitions
- **learned_synonyms**: User terminology learned over time

**Use Cases:**
- Semantic search for fields and metrics
- Typo-tolerant matching
- Business term to technical field mapping
- Cross-database field discovery
- Continuous learning from user queries

### 7. Data Quality Engine

```python
src/quality/
├── profiler.py         # Data profiling
└── scorer.py           # Quality scoring
```

**6 Quality Dimensions:**

1. **Freshness**: How recent is the data?
2. **Completeness**: Percentage of non-null values
3. **Accuracy**: Statistical anomaly detection
4. **Consistency**: Value format consistency
5. **Validity**: Data type and constraint validation
6. **Uniqueness**: Duplicate detection

### 8. Fuzzy Matching Engine

```python
src/matching/
├── fuzzy_matcher.py    # Typo-tolerant matching
└── entity_matcher.py   # Multi-source entity resolution
```

**Match Types:**

1. **Exact Match**: Direct string match
2. **Fuzzy Match**: Levenshtein distance (typos)
3. **Phonetic Match**: Soundex algorithm
4. **Abbreviation Match**: "rev" → "revenue"

### 9. Analytics Engine

```python
src/analytics/
├── statistics.py       # Statistical analysis
├── time_intelligence.py # Time-based calculations
├── forecasting.py      # Predictive analytics
├── anomaly.py          # Anomaly detection
└── attribution.py      # Attribution modeling
```

**Capabilities:**
- Year-over-year (YoY) calculations
- Moving averages
- Trend detection
- Forecasting (ARIMA, Prophet)
- Anomaly detection (Z-score, IQR, Isolation Forest)

### 10. User Management

```python
src/user/
├── manager.py          # User CRUD operations
└── models.py           # User models
```

**Role Hierarchy:**

```
Admin
  ├─ Full platform access
  ├─ User management
  ├─ Connection management
  └─ System configuration

Analyst
  ├─ Create queries
  ├─ Create metrics
  ├─ View all data
  └─ Export results

Executive
  ├─ View dashboards
  ├─ Run saved queries
  └─ View insights

Developer
  ├─ API access
  ├─ Query plans
  └─ Technical metrics
```

### 11. Activity Tracking

```python
src/activity/
├── logger.py           # Activity logging
├── analyzer.py         # Usage analytics
└── models.py           # Activity models
```

**Tracked Events:**
- User login/logout
- Query execution
- Data access
- Configuration changes
- Export operations
- Error occurrences

---

## Data Flow

### Query Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  1. User asks: "Top 10 customers by revenue last quarter"      │
│                                                                  │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. API Gateway                                                  │
│     - Authenticate JWT token                                     │
│     - Rate limit check                                           │
│     - Log request                                                │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Query Orchestrator                                           │
│     - Check plan cache (cache hit?)                             │
│     - Load semantic layer                                        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Intent Extraction (LLM)                                      │
│     Prompt: "Extract intent from question"                      │
│     Response:                                                    │
│     {                                                            │
│       "metric": "revenue",                                       │
│       "dimensions": ["customer_name"],                          │
│       "time_range": {"period": "last_quarter"},                │
│       "limit": 10,                                               │
│       "sort": {"field": "revenue", "order": "DESC"}            │
│     }                                                            │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. Semantic Layer Resolution                                    │
│     - revenue → SUM(sales.amount)                               │
│     - customer_name → customers.name                            │
│     - last_quarter → 2024-10-01 to 2024-12-31                  │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. SQL Generation                                               │
│     SELECT                                                       │
│         c.name AS customer_name,                                │
│         SUM(s.amount) AS revenue                                │
│     FROM sales s                                                 │
│     JOIN customers c ON s.customer_id = c.id                    │
│     WHERE s.sale_date >= '2024-10-01'                           │
│       AND s.sale_date <= '2024-12-31'                           │
│     GROUP BY c.name                                              │
│     ORDER BY revenue DESC                                        │
│     LIMIT 10                                                     │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  7. SQL Validation                                               │
│     ✓ Only SELECT allowed                                       │
│     ✓ No dangerous functions                                    │
│     ✓ No multi-statement                                        │
│     ✓ Timeout set (30s)                                         │
│     ✓ Row limit (10k)                                           │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  8. Query Execution                                              │
│     - Execute on read-only connection                           │
│     - Apply timeout                                              │
│     - Stream results                                             │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  9. Analytics Calculation                                        │
│     - Calculate statistics                                       │
│     - Detect anomalies                                          │
│     - Generate insights                                          │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  10. Response Formatting                                         │
│      - Format results as JSON                                   │
│      - Generate visualization config                            │
│      - Add explanation                                           │
│      - Cache result                                              │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  11. Return to User                                              │
│      {                                                           │
│        "question": "...",                                        │
│        "sql": "SELECT ...",                                      │
│        "results": [...],                                         │
│        "visualization": {...},                                   │
│        "insights": [...],                                        │
│        "explanation": "..."                                      │
│      }                                                           │
└──────────────────────────────────────────────────────────────────┘
```

### Learning Flow

```
User Query → Feedback → Vector Store → Improved Future Queries

1. User asks: "Show me revenu"
2. System matches to "revenue" (fuzzy)
3. User confirms correction
4. System stores: "revenu" → "revenue" in vector DB
5. Next user: "revenu" → instant match
```

---

## Technology Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI (async, high performance)
- **ORM**: SQLAlchemy 2.0
- **Validation**: Pydantic v2
- **Task Queue**: Celery (planned)
- **Background Jobs**: APScheduler

### Frontend
- **Framework**: React 18
- **Language**: TypeScript 5.x
- **Build Tool**: Vite
- **Styling**: TailwindCSS 3.x
- **Charts**: Recharts
- **State Management**: React Context + Hooks
- **HTTP Client**: Axios
- **Routing**: React Router v7

### Databases
- **Internal DB**: PostgreSQL 16
- **Client DBs**: PostgreSQL, MySQL, SQL Server, Oracle
- **Vector DB**: ChromaDB (persistent)
- **Cache**: Redis 7
- **Object Storage**: S3/Azure Blob (planned)

### AI/ML
- **LLM**: OpenAI GPT-4, GPT-3.5, Azure OpenAI
- **Embeddings**: OpenAI text-embedding-ada-002
- **Vector Search**: ChromaDB with HNSW index
- **Fuzzy Matching**: RapidFuzz
- **Forecasting**: Prophet, ARIMA

### DevOps & Infrastructure
- **Containerization**: Docker, Docker Compose
- **Orchestration**: Kubernetes (planned)
- **Web Server**: Nginx
- **Reverse Proxy**: Nginx
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana (planned)
- **Logging**: ELK Stack (planned)

### Security
- **Authentication**: JWT (RS256)
- **Password Hashing**: bcrypt
- **Encryption**: TLS 1.3, AES-256
- **Secret Management**: HashiCorp Vault (planned)

---

## Infrastructure Architecture

### Containerized Deployment

```yaml
services:
  # Frontend
  frontend:
    image: datatruth-frontend:latest
    ports: ["3000:80"]
    depends_on: [backend]
    
  # Backend API
  backend:
    image: datatruth-backend:latest
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL
      - OPENAI_API_KEY
      - JWT_SECRET
    depends_on: [postgres, redis, chroma]
    
  # Internal Database
  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
  # Cache
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes:
      - redis_data:/data
      
  # Vector Database
  chroma:
    image: ghcr.io/chroma-core/chroma:latest
    ports: ["8001:8001"]
    volumes:
      - chroma_data:/chroma/chroma
      
  # Reverse Proxy
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    depends_on: [frontend, backend]
```

### Cloud Deployment Options

#### AWS Architecture

```
Route 53 (DNS)
    ↓
CloudFront (CDN)
    ↓
Application Load Balancer
    ↓
┌─────────────────────────────────────────┐
│  ECS Cluster (Fargate)                  │
│  ├─ Frontend Service (Auto-scaling)     │
│  ├─ Backend Service (Auto-scaling)      │
│  └─ Worker Service (Background jobs)    │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Data Layer                              │
│  ├─ RDS PostgreSQL (Multi-AZ)           │
│  ├─ ElastiCache Redis (Cluster mode)    │
│  ├─ S3 (Object storage)                  │
│  └─ EC2 (ChromaDB - persistent volume)  │
└─────────────────────────────────────────┘
```

#### Azure Architecture

```
Azure Front Door
    ↓
Application Gateway
    ↓
┌─────────────────────────────────────────┐
│  AKS Cluster (Kubernetes)                │
│  ├─ Frontend Pods (HPA)                  │
│  ├─ Backend Pods (HPA)                   │
│  └─ Worker Pods                          │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Data Layer                              │
│  ├─ Azure Database for PostgreSQL       │
│  ├─ Azure Cache for Redis                │
│  ├─ Azure Blob Storage                   │
│  └─ AKS Persistent Volume (ChromaDB)    │
└─────────────────────────────────────────┘
```

---

## Security Architecture

### Defense in Depth

```
Layer 1: Network Security
├─ TLS 1.3 encryption
├─ IP whitelisting
├─ DDoS protection (CloudFlare/AWS Shield)
└─ VPC isolation

Layer 2: Application Security
├─ JWT authentication (RS256)
├─ Rate limiting (per user, per IP)
├─ CORS protection
├─ Input validation (Pydantic)
└─ XSS/CSRF protection

Layer 3: Database Security
├─ Read-only database user
├─ SQL injection prevention
├─ Query timeout enforcement
├─ Row limit enforcement
└─ Connection pooling with limits

Layer 4: Data Security
├─ Data at rest encryption (AES-256)
├─ Data in transit encryption (TLS)
├─ No sensitive data in logs
├─ PII masking
└─ Secure credential storage

Layer 5: Monitoring & Audit
├─ Complete audit trail
├─ Real-time alerting
├─ Anomaly detection
├─ Security event logging
└─ Compliance reporting
```

### SQL Security Guardrails

```python
class SQLValidator:
    """
    Security validation before execution:
    
    1. Statement Type Check
       ✓ SELECT, WITH allowed
       ✗ INSERT, UPDATE, DELETE blocked
       
    2. Dangerous Function Check
       ✗ pg_read_file() blocked
       ✗ COPY blocked
       ✗ Dynamic SQL (EXECUTE) blocked
       
    3. Multi-Statement Check
       ✗ Multiple statements (;) blocked
       
    4. Timeout & Limits
       ✓ 30 second timeout
       ✓ 10,000 row limit
       
    5. Connection Security
       ✓ Read-only user
       ✓ Limited permissions
       ✓ Connection pooling
    """
```

---

## Deployment Architecture

### SaaS Deployment Model

```
┌─────────────────────────────────────────────────────────────┐
│  Multi-Tenant Architecture                                   │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Tenant A    │  │  Tenant B    │  │  Tenant C    │     │
│  │              │  │              │  │              │     │
│  │  Users       │  │  Users       │  │  Users       │     │
│  │  Connections │  │  Connections │  │  Connections │     │
│  │  Semantic    │  │  Semantic    │  │  Semantic    │     │
│  │  Layer       │  │  Layer       │  │  Layer       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │             │
│         └──────────────────┴──────────────────┘             │
│                            │                                │
│                            ▼                                │
│              ┌──────────────────────────┐                   │
│              │  Shared Application      │                   │
│              │  Infrastructure          │                   │
│              └──────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

**Tenant Isolation:**
- Logical separation (shared DB, separate schemas)
- Row-level security policies
- Tenant ID in all queries
- Separate encryption keys per tenant
- Audit log segregation

### Setup Wizard Flow

```
Step 1: Welcome
  ↓
Step 2: Select Internal Database
  ├─ Use Docker database (default)
  └─ Connect to existing PostgreSQL
  ↓
Step 3: Configure LLM
  ├─ OpenAI API key
  └─ Model selection (GPT-4, GPT-3.5)
  ↓
Step 4: Test Connections
  ├─ Test database connectivity
  └─ Test OpenAI API
  ↓
Step 5: Initialize Platform
  ├─ Run database migrations
  ├─ Create admin user
  ├─ Initialize semantic layer
  └─ Start services
  ↓
Step 6: Connect Client Database (Optional)
  ├─ Database type
  ├─ Connection details
  └─ Schema introspection
  ↓
Setup Complete → Redirect to Dashboard
```

---

## Scalability & Performance

### Horizontal Scaling

```
Load Balancer
    ↓
┌─────────────────────────────────────────┐
│  Backend Service (N instances)          │
│  ├─ Instance 1                          │
│  ├─ Instance 2                          │
│  ├─ Instance 3                          │
│  └─ Instance N                          │
└─────────────────────────────────────────┘
```

**Auto-scaling Triggers:**
- CPU > 70%
- Memory > 80%
- Request queue depth > 100
- Response time > 2s

### Caching Strategy

```
┌─────────────────────────────────────────┐
│  Multi-Level Cache                      │
│                                         │
│  L1: In-Memory Cache (LRU)              │
│      - Query plans (10 min TTL)        │
│      - Semantic layer (5 min TTL)      │
│                                         │
│  L2: Redis Cache                        │
│      - Query results (1 hour TTL)      │
│      - User sessions (24 hour TTL)     │
│      - Rate limits (1 min TTL)         │
│                                         │
│  L3: Database Query Cache               │
│      - Materialized views              │
│      - Aggregation tables              │
└─────────────────────────────────────────┘
```

### Performance Optimizations

1. **Query Optimization**
   - Query plan caching
   - Result caching
   - Connection pooling
   - Prepared statements

2. **API Optimization**
   - Response compression (gzip)
   - Pagination for large results
   - Async I/O (FastAPI)
   - Request batching

3. **Database Optimization**
   - Proper indexing
   - Query timeout enforcement
   - Row limit enforcement
   - Read replicas for analytics

4. **Frontend Optimization**
   - Code splitting
   - Lazy loading
   - Virtual scrolling for large tables
   - CDN for static assets

### Performance Metrics

**Target SLAs:**
- API Response Time: < 500ms (p95)
- Query Execution: < 5s (p95)
- Page Load Time: < 2s
- Uptime: 99.9%
- Concurrent Users: 10,000+

---

## Integration Architecture

### REST API

```
Base URL: https://api.datatruth.ai/v1

Authentication: Bearer Token (JWT)
Header: Authorization: Bearer <token>

Rate Limits:
- Free: 100 requests/hour
- Pro: 1,000 requests/hour
- Enterprise: Unlimited
```

### Webhooks (Planned)

```python
{
    "event": "query.completed",
    "timestamp": "2025-12-31T10:00:00Z",
    "data": {
        "query_id": "q_123",
        "user_id": "u_456",
        "status": "success",
        "execution_time_ms": 234
    }
}
```

### Database Connectors

**Supported:**
- PostgreSQL 12+
- MySQL 8+
- SQL Server 2019+
- Oracle 19c+
- AWS RDS (all engines)
- Azure SQL
- Google Cloud SQL

**Planned:**
- Snowflake
- BigQuery
- Redshift
- MongoDB
- Databricks

### Export Formats

- JSON
- CSV
- Excel (XLSX)
- PDF (reports)
- PNG (charts)

---

## Monitoring & Observability

### Metrics to Track

**Application Metrics:**
- Request rate (requests/sec)
- Error rate (%)
- Response time (p50, p95, p99)
- Active users
- Query execution time
- Cache hit rate

**Business Metrics:**
- Queries per user
- Popular metrics
- Active tenants
- Feature adoption
- User satisfaction (NPS)

**Infrastructure Metrics:**
- CPU utilization
- Memory usage
- Disk I/O
- Network bandwidth
- Database connections
- Queue depth

### Logging Strategy

```
Application Logs → Structured JSON → Elasticsearch → Kibana

Log Levels:
- DEBUG: Detailed debugging info
- INFO: General information
- WARNING: Warning messages
- ERROR: Error messages
- CRITICAL: Critical errors

Log Retention:
- DEBUG: 7 days
- INFO: 30 days
- WARNING: 90 days
- ERROR: 1 year
- CRITICAL: Indefinite
```

### Alerting

**Critical Alerts:**
- Service down (page ops team)
- Database connection failure
- API error rate > 5%
- Response time > 5s (p95)

**Warning Alerts:**
- High memory usage (> 80%)
- High CPU usage (> 70%)
- Cache miss rate > 50%
- Queue depth growing

---

## Future Enhancements

### Q2 2025
- [ ] Scheduled queries and alerts
- [ ] Advanced visualizations (maps, sankey)
- [ ] Slack/Teams integration
- [ ] Custom dashboard builder
- [ ] Mobile apps (iOS/Android)

### Q3 2025
- [ ] Snowflake connector
- [ ] BigQuery connector
- [ ] dbt integration
- [ ] Advanced ML predictions
- [ ] Real-time streaming data

### Q4 2025
- [ ] Multi-language support
- [ ] Voice queries (Alexa, Google Home)
- [ ] Embedded analytics SDK
- [ ] Marketplace for custom integrations
- [ ] White-label solution

---

## Appendix

### Architecture Decision Records (ADRs)

**ADR-001: Why FastAPI over Flask?**
- Better async support
- Automatic OpenAPI documentation
- Type hints with Pydantic
- Better performance

**ADR-002: Why PostgreSQL for internal DB?**
- JSON support for flexible schemas
- Full-text search
- Array types for tags
- Mature and reliable

**ADR-003: Why ChromaDB for vectors?**
- Simple Python API
- Persistent storage
- Good performance
- Easy deployment

**ADR-004: Why React over Vue/Angular?**
- Larger ecosystem
- Better TypeScript support
- More third-party components
- Team familiarity

---

## Glossary

**Semantic Layer**: Business-friendly definitions of metrics and dimensions

**Query Plan**: Structured representation of a user's question

**Intent Extraction**: Converting natural language to structured format

**Vector Embedding**: Numerical representation of text for similarity search

**Fuzzy Matching**: Typo-tolerant text matching

**RBAC**: Role-Based Access Control

**JWT**: JSON Web Token for authentication

**LLM**: Large Language Model (e.g., GPT-4)

---

**Document Version:** 1.0  
**Last Updated:** December 31, 2025  
**Maintained By:** DataTruth Architecture Team
