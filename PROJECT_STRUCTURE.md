# PyBOG Project Structure

## Active Project Files

```
pybog/
├── api/                        # Backend FastAPI Service
│   ├── __init__.py
│   ├── main.py                 # Main API endpoints
│   ├── n8n_integration.py      # n8n webhook integration
│   ├── n8n_resume.py           # Resume workflow handling
│   └── routes/
│       └── conversation.py     # Conversation endpoints
│
├── bog_builder/                # BOG Generation Logic
│   ├── __init__.py
│   ├── analyzer.py             # HVAC analysis logic
│   ├── builder.py              # BOG file builder
│   └── models.py               # Data models
│
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatCanvas.tsx        # Chat message display
│   │   │   ├── ConsolePanel.tsx      # Debug console
│   │   │   ├── HealthStatus.tsx      # Service health monitor
│   │   │   ├── SimplifiedWorkbench.tsx # Main workbench UI
│   │   │   └── SimplifiedWorkbench.css
│   │   ├── services/
│   │   │   ├── apiService.ts         # API communication
│   │   │   └── n8nIntegrationUnified.ts # n8n workflow service
│   │   ├── shared/
│   │   │   └── constants.ts          # Shared constants
│   │   ├── types/
│   │   │   └── analysis.ts           # TypeScript types
│   │   ├── App.tsx                   # Main App component
│   │   ├── App.css
│   │   ├── index.tsx                 # Entry point
│   │   └── index.css
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── Dockerfile                    # Production build
│   ├── Dockerfile.dev                # Development build
│   └── nginx.conf
│
├── data/                       # Runtime Data Storage
│   ├── outputs/               # Generated BOG files
│   └── uploads/               # Uploaded documents
│
├── docker/                    # Docker Configuration
│   └── db/
│       └── init.sql          # Database initialization
│
├── archive/                   # Archived/Old Code
│   ├── docs/                 # Old documentation
│   ├── frontend/             # Old frontend components
│   ├── test/                 # Test files
│   ├── workflows/            # Old n8n workflows
│   └── old_scripts/          # Old scripts
│
├── docker-compose.yml         # Main service configuration
├── docker-compose.override.yml # Development overrides
├── Dockerfile                 # API container
├── requirements.txt           # Python dependencies
├── .env                      # Environment variables (not in git)
├── .gitignore
├── LICENSE
├── README.md                 # Main documentation
└── PROJECT_STRUCTURE.md      # This file
```

## Service Architecture

### Frontend (Port 3001)
- React application with TypeScript
- Health monitoring dashboard
- Debug console for development
- SimplifiedWorkbench as main UI component

### Backend API (Port 8000)
- FastAPI application
- Handles document processing
- Manages n8n workflow integration
- BOG file generation

### n8n (Port 5678)
- Workflow automation
- OpenAI integration for analysis
- Document text extraction
- Webhook endpoints

### PostgreSQL (Port 5432)
- Session storage
- Chat memory
- File metadata

### Redis (Port 6379)
- Caching layer
- Session management

## Key Files

- `frontend/src/App.tsx` - Main React component
- `frontend/src/components/SimplifiedWorkbench.tsx` - Primary UI
- `api/main.py` - Core API endpoints
- `bog_builder/builder.py` - BOG generation logic
- `docker-compose.yml` - Service orchestration

## Development Workflow

1. All active code is in root directories
2. Archived code is in `archive/` for reference
3. Use docker-compose for local development
4. Frontend hot-reload enabled via docker-compose.override.yml
