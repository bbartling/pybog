# PyBOG Project Cleanup Plan

## 🎯 Goal
Create a lean foundation with only core components:
- FastAPI backend with WebSocket support
- PostgreSQL database
- React Flow chat canvas with neo-brutalism styling
- BOG builder/agent functionality

## 📦 Components to KEEP

### Backend (Core)
- `backend/app/` - FastAPI application
- `backend/core/` - Core utilities and config
- `backend/services/` - WebSocket and core services
- `backend/models/` - Database models
- `backend/bog_builder/` - BOG generation logic
- `backend/requirements.txt` - Dependencies (cleaned)
- `backend/Dockerfile` - Container setup

### Frontend (Core)
- `frontend/src/components/ChatCanvas/` - React Flow chat interface
- `frontend/src/styles/` - Neo-brutalism styling
- `frontend/src/hooks/` - WebSocket and core hooks
- `frontend/package.json` - Dependencies (cleaned)
- `frontend/Dockerfile.dev` - Development container

### Infrastructure
- `docker-compose.yml` - Core services only
- `.env.example` - Environment template
- `database_schema.sql` - Database structure
- `README.md` - Updated documentation

## 🗂️ Components to ARCHIVE

### Root Level Cleanup
- `bog_builder/` (duplicate - keep backend version)
- `data/` (move to backend/data)
- `database/` (consolidate with backend)
- `docs/` (outdated documentation)
- `manifests/` (k8s configs - not needed for core)
- `docker/` (separate docker configs)
- Various config files and logs

### Backend Cleanup
- `backend/examples/` - Example files
- `backend/tests/` - Move to archive, rebuild later
- `backend/scripts/` - Utility scripts
- `backend/public/` - Static files
- `backend/integration_test_results.log` - Log files

### Frontend Cleanup
- `frontend/build/` - Build artifacts
- `frontend/recovered_*` - Recovery files
- `frontend/restore-*` - Restore files

## 📁 New Clean Structure
```
pybog-clean/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   └── services/
│   ├── bog_builder/
│   ├── data/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── ChatCanvas/
│   │   ├── styles/
│   │   └── hooks/
│   ├── package.json
│   └── Dockerfile.dev
├── archive/
│   └── [all non-core components]
├── docker-compose.yml
├── .env.example
├── database_schema.sql
└── README.md
```

## 🚀 Implementation Steps
1. Create archive directory
2. Move non-core components to archive
3. Clean up dependencies
4. Update docker-compose for lean services
5. Update documentation
6. Test core functionality