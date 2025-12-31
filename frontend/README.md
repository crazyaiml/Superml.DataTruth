# DataTruth Frontend

Modern React + TypeScript frontend for DataTruth Natural Language Analytics with SaaS-ready setup wizard.

## 🎉 NEW: SaaS Setup Wizard

- **Zero-configuration first launch** - Setup everything via web interface
- **5-step guided setup** - Database, OpenAI, Admin user configuration
- **Real-time connection testing** - Validate credentials before saving
- **Beautiful UI** - Professional wizard with progress tracking

## Features

- 🎨 Modern UI with Tailwind CSS & Headless UI
- ⚡ Fast development with Vite
- 🔒 Secure authentication with JWT
- ��‍♂️ **Setup Wizard** - First-time configuration via web
- 💬 Real-time chat interface for natural language queries
- 📊 Interactive charts and data visualizations (Recharts)
- 🔍 Semantic search with vector database
- 📈 AI-powered insights and analytics
- 🎯 Intelligent query suggestions
- 👥 User management and role-based access
- 🔌 Connection management for multiple databases
- 📐 Semantic layer for dimensions and metrics

## Development

```bash
# Install dependencies
npm install

# Start development server (runs on port 3000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

The development server proxies API requests to http://localhost:8000.

## Project Structure

```
src/
├── components/              # React components
│   ├── Setup/              # SaaS Setup Wizard
│   │   └── SetupWizard.tsx    # 5-step configuration wizard
│   ├── ChatInterface.tsx      # Natural language query interface
│   ├── ChatMessage.tsx        # Message display with markdown
│   ├── ConnectionManager.tsx  # Database connection management
│   ├── DataChart.tsx          # Chart visualizations
│   ├── DataTable.tsx          # Data table rendering
│   ├── ExampleQuestions.tsx   # Quick start examples
│   ├── HomePage.tsx           # Main workspace
│   ├── InsightsScreen.tsx     # AI insights dashboard
│   ├── LoginPage.tsx          # Authentication
│   ├── QualityDashboard.tsx   # Data quality monitoring
│   ├── SchemaExplorer.tsx     # Database schema viewer
│   ├── SearchAndAsk.tsx       # Search interface
│   ├── SemanticLayer.tsx      # Dimension/metric management
│   ├── UserManagement.tsx     # User admin panel
│   └── FuzzyMatchTester.tsx   # Testing tool
├── contexts/               # React contexts
│   └── AuthContext.tsx        # Authentication state
├── App.tsx                # Main app component
├── main.tsx              # App entry point
└── index.css             # Global styles
```

## Technologies

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first styling
- **Vite** - Fast build tool
- **React Router** - Client-side routing
- **Axios** - HTTP client
- **Recharts** - Chart library
- **Headless UI** - Accessible components
- **Lucide React** - Icon library
- **React Markdown** - Markdown rendering

## Key Features

### Setup Wizard (New!)
First-time users are automatically directed to the setup wizard which guides through:
1. Welcome & Overview
2. Database Configuration (PostgreSQL)
3. OpenAI API Configuration
4. Admin Account Creation
5. Review & Initialize

### Authentication
- JWT-based secure authentication
- Role-based access control (Admin, Analyst, Viewer)
- Protected routes and API calls

### Natural Language Queries
- Chat-like interface for asking questions
- AI-powered SQL generation
- Query history and suggestions
- Interactive data tables and charts

### Advanced Analytics
- Augmented insights with AI explanations
- Anomaly detection
- Forecasting and trend analysis
- Time intelligence

### Data Management
- Multi-database connections
- Schema exploration
- Semantic layer for business logic
- Vector-based semantic search

---

For SaaS deployment, see [SAAS_DEPLOYMENT.md](../docs/SAAS_DEPLOYMENT.md)
