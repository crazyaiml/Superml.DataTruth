# SuperML DataTruth

**Governed natural-language analytics over PostgreSQL with AI-powered data quality**

Ask questions in plain English. Get answers from verified data — not guesses.

---

## 🎉 **NEW: SaaS Deployment Mode**

Deploy DataTruth as a complete SaaS product with **web-based setup wizard**!

```bash
# One command deployment
./deploy-saas.sh

# Important Commands
# View logs
docker-compose -f docker-compose.saas.yml logs -f

# Stop services
docker-compose -f docker-compose.saas.yml stop

# Restart services
docker-compose -f docker-compose.saas.yml restart

# Check service status
docker-compose -f docker-compose.saas.yml ps

# Open http://localhost:3000
# Configure through beautiful UI
# No .env editing required!
```

**Features:**
- ✅ Web-based configuration wizard
- ✅ Real-time connection testing
- ✅ One-command deployment
- ✅ No manual setup needed
- ✅ Production ready in 5 minutes

📖 **[Full SaaS Deployment Guide →](SAAS_DEPLOYMENT.md)**

---

## 📚 Documentation

- **[SaaS Deployment](SAAS_DEPLOYMENT.md)** - Web-based setup wizard (NEW!)
- **[Production Deployment](DEPLOYMENT.md)** - Traditional deployment guide
- **[Security Guide](SECURITY.md)** - Security hardening checklist
- **[Quick Start Guide](docs/QUICKSTART.md)** - Get running in 5 minutes
- **[Complete Guide](docs/COMPLETE_GUIDE.md)** - Full documentation
- **[Database Schema](docs/database-schema.md)** - Database structure

---

## 🚀 Quick Start

### Option 1: SaaS Mode (Recommended) 🆕

```bash
# Deploy with Docker (no configuration needed!)
./deploy-saas.sh

# Open browser at http://localhost:3000
# Follow setup wizard to configure
```

### Option 2: Traditional Setup

```bash
# One-time setup
python -m venv .venv && source .venv/bin/activate
pip install -e .
cd frontend && npm install && cd ..
./setup-databases.sh

# Start application
./start.sh
```

Open http://localhost:3000 and login with `admin/admin123`

---

## Overview

SuperML DataTruth is an AI-powered analytics platform that enables business users to query relational databases using natural language. Unlike generic LLM chatbots, DataTruth prioritizes:

- ✅ **Data correctness** - No hallucinated numbers
- 🔒 **Security** - Read-only, SQL injection-proof
- 📊 **Governed metrics** - One version of truth
- 🔍 **Explainability** - Every answer is auditable
- 🎯 **Typo tolerance** - Fuzzy matching for user input
- 📈 **Data quality** - Multi-dimensional quality assessment
- 🔌 **Dynamic connections** - ThoughtSpot-like schema discovery

---

## Key Features

### Core Features
- **Natural Language Queries**: "Top 10 agents by revenue last quarter"
- **Semantic Layer**: Define metrics once, use everywhere
- **SQL Guardrails**: Prevent unsafe queries automatically
- **Structured Planning**: LLM generates query plans, not raw SQL
- **Audit Trail**: Every query is logged with full context
- **Explainable Results**: See metric definitions and filters used

### Phase 2: AI-Powered Intelligence
- **AI Synonym Learning**: Automatically learn user terminology
- **Smart Search**: Fast semantic search across metrics and dimensions
- **Feedback Loop**: Learn from user interactions and corrections
- **Auto-learning**: Continuously improve based on usage patterns

### Phase 3: Data Quality & Matching
- **Data Quality Scoring**: 6-dimensional quality assessment (freshness, completeness, accuracy, consistency, validity, uniqueness)
- **Fuzzy Matching**: Typo-tolerant search with 4 match types (exact, fuzzy, phonetic, abbreviation)
- **Data Profiling**: Automatic pattern discovery and statistics
- **Entity Matching**: Multi-source entity resolution with conflict detection

### Phase 4: ThoughtSpot-like Features ✨
- **Dynamic Connections**: Connect to any database (PostgreSQL, MySQL, Snowflake, etc.)
- **Auto Schema Discovery**: Introspect tables, columns, and foreign key relationships
- **Field Mapping**: Map technical field names to business-friendly names
- **AI Field Descriptions**: Generate intelligent descriptions for any field
- **Generalized Aggregations**: Define once how fields aggregate (revenue = sum(amount))
- **Business Name Search**: Search using friendly names, not technical names
- **Vector DB Integration**: ChromaDB for persistent semantic search and cross-database field discovery
- **Continuous Learning**: Learned patterns survive restarts and improve over time

📖 **[Full ThoughtSpot Features Guide →](THOUGHTSPOT_QUICKSTART.md)**

---

## Architecture

```
User Question (NL)
    ↓
Intent Extraction (LLM)
    ↓
Query Plan (JSON)
    ↓
SQL Generation (Template-based)
    ↓
SQL Validation (Guardrails)
    ↓
Execution (Read-only)
    ↓
Formatted Result + Explanation
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- OpenAI API key (or Azure OpenAI)

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd Superml.DataTruth

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install

# Start PostgreSQL
docker-compose up -d postgres

# Set environment variables
cp .env.example .env
# Edit .env with your OpenAI API key and database credentials

# Run migrations/seed data
docker-compose exec postgres psql -U datatruth_admin -d datatruth -f /docker-entrypoint-initdb.d/01-schema.sql

# Run the application
uvicorn src.api.app:app --reload
```

### Test the API

```bash
# Health check
curl http://localhost:8000/health

# Ask a question
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Top 10 agents by revenue last quarter"}'
```

---

## Project Status

**Current Phase:** Phase 3 Complete ✅

- ✅ **Phase 1:** Agentic Semantic Layer - Core query engine
- ✅ **Phase 2:** AI Synonyms & Auto-learning - Intelligent search
- ✅ **Phase 3:** Data Quality & Matching - Quality monitoring and fuzzy search
- 🚧 **Phase 4:** Snowflake Integration & dbt Support (Planned)

See [ROADMAP.md](ROADMAP.md) for detailed planning.

---

## Quick Demos

### Run Phase 3 Demo (Data Quality & Matching)

```bash
# Start the server
./start.sh
### Query Assistant
```
✅ "Top 10 agents by revenue last quarter"
✅ "Company-wise revenue and profit for 2024"
✅ "Last 5-year revenue growth with YoY and CAGR"
✅ "Revenue trend by month for Acme Corp"
✅ "Profit margin by agent and region"
```

### Fuzzy Matching Examples
```
✅ "revenu" → matches "revenue" (typo tolerance)
✅ "prof" → matches "profit" (abbreviation)
✅ "kalifornia" → matches "California" (phonetic)
✅ "tot rev" → matches "total revenue" (multi-word)
- ✅ Data quality assessment with 6 dimensions
- ✅ Fuzzy matching with typo tolerance
- ✅ Abbreviation expansion (rev → revenue)
- ✅ Dimension value matching
- ✅ Correction suggestions
- ✅ Data profiling

### Access the Web UI

```bash
# Start both backend and frontend
./start.sh

# Access at http://localhost:5173
# Try these features:
#   - Query Assistant: Ask natural language questions
#   - Data Quality: Monitor data quality metrics
#   - Fuzzy Matching: Test typo-tolerant matching
```

---

## Documentation

- [Architecture](docs/architecture.md) - System design and data flow
- [Semantic Layer](docs/semantic-layer.md) - Metrics and dimension definitions
- [API Reference](docs/api.md) - Endpoint documentation
- [Security](docs/security.md) - Threat model and guardrails
- [Developer Guide](docs/developer-guide.md) - Setup and contribution guide

---

## Example Questions

```
✅ "Top 10 agents by revenue last quarter"
✅ "Company-wise revenue and profit for 2024"
✅ "Last 5-year revenue growth with YoY and CAGR"
✅ "Revenue trend by month for Acme Corp"
✅ "Profit margin by agent and region"
```

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test suite
pytest tests/unit/
pytest tests/integration/
pytest tests/security/

# Run golden test suite (30+ regression tests)
pytest tests/golden/
```

---

## Security

DataTruth implements multiple security layers:

1. **Read-only database user** - No write permissions
2. **SQL allowlist** - Only SELECT/WITH allowed
3. **Query timeouts** - 30s maximum execution
4. **Row limits** - 10k max rows per query
5. **Tenant isolation** - Automatic filter enforcement
6. **No multi-statement** - Prevents SQL injection

See [docs/security.md](docs/security.md) for details.

---

## Contributing

1. Create a feature branch
2. Make changes with tests
3. Run `pytest` and ensure all tests pass
4. Run `pre-commit run --all-files`
5. Submit a pull request

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

## Support

For questions or issues, please open a GitHub issue or contact the SuperML team.

---

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [PostgreSQL](https://www.postgresql.org/)
- [OpenAI](https://openai.com/)
- [sqlparse](https://github.com/andialbrecht/sqlparse)
