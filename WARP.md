# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

PyBOG Control Builder is a dockerized application that converts HVAC control sequence documents into Niagara Workbench BOG (Building Object Graph) files using AI-powered analysis. The system uses a microservices architecture with React frontend, FastAPI backend, n8n workflow engine, PostgreSQL database, and Redis cache.

## Essential Commands

### Development

```bash
# Start all services with hot-reload
docker-compose -f docker-compose.yml -f docker-compose.override.yml up

# Start services in background
docker-compose up -d

# View logs for specific service
docker-compose logs -f [api|frontend|n8n|postgres|redis]

# Stop all services
docker-compose down

# Rebuild specific service
docker-compose build [service-name]

# Access service shells
docker-compose exec api bash
docker-compose exec frontend sh
docker-compose exec n8n sh
```

### Testing & Debugging

```bash
# Run backend tests
docker-compose exec api pytest

# Run frontend tests  
docker-compose exec frontend npm test

# Check API endpoints
curl http://localhost:8000/docs

# Monitor n8n workflows
open http://localhost:5678
```

## Service Architecture & Ports

| Service | Port | Internal URL | Purpose |
|---------|------|--------------|---------|
| Frontend | 3001 (dev), 3000 (prod) | http://frontend:80 | React UI with ReactFlow visualization |
| API | 8000 | http://api:8000 | FastAPI backend, BOG generation |
| n8n | 5678 | http://n8n:5678 | Workflow automation, OpenAI integration |
| PostgreSQL | 5432 | postgres:5432 | Primary database + pgvector |
| Redis | 6379 | redis:6379 | Cache layer |

## Core Architecture

### Request Flow
1. **User Upload**: Frontend sends document to API via `/api/conversation/message`
2. **n8n Processing**: API forwards to n8n webhook `/webhook/pybog-analyze`
3. **AI Analysis**: n8n extracts text, calls OpenAI for HVAC analysis
4. **WebSocket Updates**: Real-time status updates via WebSocket
5. **Review**: User reviews extracted I/O points and sequences
6. **BOG Generation**: Approval triggers `BogFolderBuilder` to create Niagara file

### Key Integration Points

#### n8n Webhooks
- **Analysis**: `/webhook/pybog-analyze` - Document processing and AI analysis
- **Approval**: `/webhook/pybog-approve` - Triggers BOG generation
- **Resume**: `/webhook/pybog-resume` - Continues interrupted workflows

#### WebSocket Events
- `analysis_complete` - AI analysis ready for review
- `bog_generated` - BOG file ready for download
- `process_step` - Real-time workflow progress

#### Session Management
The system uses session IDs to track conversations across:
- PostgreSQL: Persistent storage in `sessions` and `session_files` tables
- Redis: Fast session cache
- Frontend: Local state management
- n8n: Workflow context preservation

### BOG Generation Engine

The `BogFolderBuilder` class (`bog_builder/builder.py`) creates Niagara-compatible XML structures:
- Automatic component layout with X/Y positioning
- Sub-folder organization for complex systems
- Link management between components
- Enum range definitions for control states
- Validation via Pydantic models

## Key Files & Modules

### Backend Structure
```
api/
├── main.py                 # Core API endpoints, WebSocket manager
├── n8n_integration.py      # n8n webhook communication
├── n8n_resume.py          # Resume URL storage for interrupted flows
└── routes/
    └── conversation.py    # Chat endpoints (approve/request-changes)

bog_builder/
├── builder.py            # BogFolderBuilder - XML generation logic
├── analyzer.py          # HVAC analysis utilities
└── models.py            # Pydantic models for validation
```

### Frontend Structure
```
frontend/src/
├── components/
│   ├── SimplifiedWorkbench.tsx  # Main UI container
│   ├── ChatCanvas.tsx          # ReactFlow conversation visualization
│   ├── HealthStatus.tsx        # Service monitoring
│   └── ConsolePanel.tsx        # Debug console
├── services/
│   ├── apiService.ts           # Backend API client
│   └── n8nIntegrationUnified.ts # n8n workflow service
└── types/
    └── analysis.ts             # TypeScript interfaces
```

## Development Patterns

### Adding New n8n Workflows
1. Create workflow in n8n UI (http://localhost:5678)
2. Add webhook trigger node
3. Update `api/n8n_integration.py` with new endpoint
4. Add corresponding API route in `api/main.py`

### Extending BOG Components
1. Define new component in `bog_builder/models.py`
2. Add builder method in `BogFolderBuilder` class
3. Update COMPONENT_SLOT_MAP for proper XML generation
4. Test with sample HVAC document

### Frontend Message Flow
Messages flow through `ChatCanvas` component using ReactFlow nodes:
- User messages: Left-aligned purple nodes
- Assistant responses: Right-aligned blue nodes  
- Process steps: Center mini-nodes showing workflow progress
- Analysis results: Green expandable nodes with I/O details

## Environment Variables

Required in `.env`:
```
OPENAI_API_KEY=your-api-key-here
N8N_ENCRYPTION_KEY=dev_encryption_key_change_me  # Change in production
WEBHOOK_USERNAME=webhook_user                     # n8n webhook auth
WEBHOOK_PASSWORD=webhook_pass_change_me
```

## Database Schema

The system maintains minimal tables for flexibility:
```sql
sessions(
  session_id TEXT PRIMARY KEY,
  description TEXT,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

session_files(
  id SERIAL PRIMARY KEY,
  session_id TEXT REFERENCES sessions,
  filename TEXT,
  mime_type TEXT,
  size BIGINT,
  path TEXT,
  uploaded_at TIMESTAMPTZ
)
```

## Common Troubleshooting

### n8n Webhook Not Responding
- Verify workflow is active in n8n UI
- Check webhook URL matches: `http://n8n:5678/webhook/pybog-analyze`
- Confirm n8n container can reach API container

### Frontend Hot Reload Not Working
- Ensure using `docker-compose.override.yml`
- Check CHOKIDAR_USEPOLLING=true is set
- Verify volume mounts in override file

### BOG Generation Fails
- Check OPENAI_API_KEY is valid
- Verify PostgreSQL has analysis data for session
- Review `docker-compose logs api` for validation errors
