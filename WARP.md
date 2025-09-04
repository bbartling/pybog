# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

PyBOG Workbench is a Niagara N4-style application for generating Building Automation System (BAS) control logic files (.bog format). It combines:
- React frontend with Tridium N4 Workbench UI styling
- FastAPI backend for BOG file generation
- N8N workflow engine for AI-powered document processing
- PostgreSQL with pgvector for data and embeddings storage

## Common Development Commands

### Quick Start
```bash
# Initial setup
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Start all services
docker-compose up --build -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f          # All services
docker-compose logs -f api      # API only
docker-compose logs -f frontend # Frontend only
docker-compose logs -f n8n      # N8N workflow engine
```

### Frontend Development
```bash
cd frontend
npm install
npm start                        # Development server on port 3000
npm run build                    # Production build
```

### Backend Development
```bash
# Install Python dependencies locally
pip install -r requirements.txt

# Run API server locally (without Docker)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Run inside Docker with hot reload
docker-compose up api
```

### Service Management
```bash
# Restart specific service
docker-compose restart api
docker-compose restart frontend
docker-compose restart n8n

# Rebuild specific service
docker-compose up --build api

# Clean restart (removes volumes)
docker-compose down -v
docker-compose up --build
```

### Testing BOG Generation
```bash
# The README mentions test_integration.py and test_core_functionality.py
# but these files don't exist yet. Create them for:
# - API endpoint testing
# - BOG file generation validation
# - N8N workflow integration testing
```

## Architecture & Key Components

### Service Ports
- **Frontend**: http://localhost:3000 (React Workbench UI)
- **API**: http://localhost:8000 (FastAPI with /docs for Swagger)
- **N8N**: http://localhost:5678 (Workflow automation engine)
- **PostgreSQL**: localhost:5432 (Database)
- **Redis**: localhost:6379 (Caching layer)

### Core BOG Builder (`bog_builder/`)
The heart of the system that generates Niagara-compatible .bog files:

- **`builder.py`**: Main `BogFolderBuilder` class
  - Handles component creation and linking
  - Manages sub-folder organization
  - Generates XML structure for .bog archives
  - Layout engine with intelligent positioning (X_COLUMN_WIDTH=20, Y_INCREMENT=10)
  
- **`models.py`**: Pydantic validation models
  - `ComponentDefinition`, `LinkDefinition`, `ReductionBlockDefinition`
  - Component slot mappings for Niagara compatibility
  - Time parsing utilities
  
- **`analyzer.py`**: BOG file analysis utilities

### API Structure (`api/main.py`)
FastAPI application with WebSocket support:

**Key Models:**
- `SensorInput`: Input sensor definitions (temperature, pressure, flow, humidity, CO2)
- `ActuatorOutput`: Output actuator definitions (valve, damper, VFD, relay)
- `ControlSequence`: Control logic sequences (startup, shutdown, normal, safety)
- `BogGenerationRequest/Response`: Main generation endpoints

**WebSocket Manager:**
- Real-time progress updates during BOG generation
- Session-based connection management
- Analysis completion and BOG ready notifications

**Main Endpoints:**
- `POST /api/generate-bog`: Generate BOG file from specifications
- `POST /api/validate-schema`: Validate HVAC schema before generation
- `GET /api/download/{session_id}/{filename}`: Download generated BOG files
- `WebSocket /ws/{session_id}`: Real-time updates

### Frontend Architecture (`frontend/src/`)
React application with Niagara N4 Workbench styling:

**Components:**
- `N4WorkbenchLayout.tsx`: Main workbench container
- `WireSheetChat.tsx`: Chat interface with HVAC context
- `AnalysisBlock.tsx`: Document analysis display
- `ChatFlow.tsx`: Conversation flow management
- `ProjectNavigator.tsx`: File/project navigation

**Services:**
- `apiService.ts`: REST API communication
- `n8nIntegration.ts`: N8N workflow triggers
- `n8nWorkflowMap.ts`: Workflow mapping configuration

### N8N Workflows (`workflow_data/`)
Pre-configured workflows for document processing:
- Document ingestion (PDF/DOCX)
- AI-powered text analysis with OpenAI
- Control sequence extraction
- BOG generation triggers

### Data Flow
```
User Upload → Frontend → API → N8N Workflow → OpenAI Analysis 
    ↓                                              ↓
Document Storage                          Extracted Components
    ↓                                              ↓
PostgreSQL ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← Validation
    ↓
BOG Builder → XML Generation → .bog Archive → Download
```

## Environment Configuration

Required environment variables (from `.env.example`):
- `OPENAI_API_KEY`: Required for AI document analysis
- `N8N_USER/N8N_PASSWORD`: N8N admin credentials
- `POSTGRES_DB/USER/PASSWORD`: Database configuration
- `JWT_SECRET`: Authentication secret (change in production)
- Service ports: `API_PORT=8000`, `FRONTEND_PORT=3000`, `N8N_PORT=5678`

## Important Implementation Notes

### BOG Builder Constraints
- Component names must match pattern: `^[A-Za-z_][A-Za-z0-9_]*$`
- Layout constants are visually tuned: DO NOT modify X_COLUMN_WIDTH (20) or Y_INCREMENT (10)
- Sub-folders help manage complex logic organization
- Enum ranges must be pre-defined before use

### Frontend State Management
- No Redux/Zustand - uses React Context for workflow and document state
- WebSocket for real-time updates during processing
- Session-based tracking for multi-step workflows

### Docker Networking
- All services communicate via `pybog-network` bridge
- Internal service names: `api`, `frontend`, `n8n`, `postgres`, `redis`
- N8N can reach API at `http://api:8000` internally

### File Storage
- Uploads: `./data/uploads/`
- Generated BOGs: `./data/outputs/`
- N8N workflows: `./workflow_data/`
- Volumes persist data between container restarts

## Troubleshooting Common Issues

1. **N8N workflow not triggering**: Verify workflow is activated and webhook URL is correct
2. **Frontend can't reach API**: Check CORS settings and ensure API is running on port 8000
3. **BOG generation fails**: Check component name validation and input/output definitions
4. **Database connection issues**: Ensure PostgreSQL healthcheck passes before starting dependent services
5. **OpenAI errors**: Verify API key is set and has sufficient quota

## N8N Workflow Import
After starting services:
1. Access N8N at http://localhost:5678
2. Navigate to Workflows → Import from file
3. Import workflows from `workflow_data/` directory
4. Activate the imported workflows
5. Test webhook endpoints are accessible from API service
