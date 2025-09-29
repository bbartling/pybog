# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

PyBOG is an AI-powered HVAC Control Builder that generates Niagara-compatible BOG files from HVAC control sequences. The system features a neo-brutalism React Flow interface, FastAPI backend with WebSocket support, and PostgreSQL/Redis data layers.

## Development Commands

### Backend (FastAPI)
```bash
# Install dependencies
cd backend && pip install -r requirements.txt

# Run backend in development mode (with hot reload)
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
cd backend && pytest

# Run specific test
cd backend && pytest tests/test_specific.py::test_function
```

### Frontend (React/TypeScript)
```bash
# Install dependencies
cd frontend && npm install

# Start development server
cd frontend && npm start

# Build for production
cd frontend && npm run build

# Run tests
cd frontend && npm test
```

### Docker Development
```bash
# Start all services in development mode
docker-compose up -d

# View service logs
docker-compose logs -f [service-name]

# Restart specific service
docker-compose restart [service-name]

# Stop all services
docker-compose down
```

## Architecture

### Backend Structure
- **app/main.py**: FastAPI application entry point with WebSocket management
- **core/**: Core infrastructure (config, database, events, error handling)
- **services/**: Business logic services (analysis engine, file service, session management, WebSocket manager)
- **models/**: Pydantic models for API contracts and data validation
- **bog_builder/**: PyBOG file generation engine with manifest creation

### Frontend Structure
- **src/App.tsx**: Main application with React Flow chat canvas
- **src/components/**: UI components including specialized node types for chat interface
- **src/services/**: API services, WebSocket management, and session persistence
- **src/theme/**: Neo-brutalism design system

### Key Services
1. **Event Bus System** (`core/events.py`): Centralized event handling for real-time updates
2. **WebSocket Manager** (`services/websocket_manager.py`): Manages real-time client connections and message broadcasting
3. **Analysis Engine** (`services/analysis_engine.py`): AI-powered document processing and I/O extraction
4. **Session Service** (`services/session_service.py`): Persistent chat session management
5. **File Service** (`services/file_service.py`): File upload, storage, and metadata management
6. **PyBOG Agent** (`services/pybog_agent.py`): Orchestrates the BOG file generation workflow

## Development Environment

### Required Environment Variables
```bash
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql://pybog:pybog123@postgres:5432/pybog
REDIS_URL=redis://redis:6379/0
```

### Service Ports (Docker)
- Frontend: http://localhost:3847
- Backend API: http://localhost:8847
- PostgreSQL: localhost:5433
- pgAdmin: http://localhost:5847

### Database Schema
The system uses PostgreSQL with separate tables for:
- Sessions and conversation history
- File metadata and storage tracking
- Analysis results and BOG generation status
- User preferences and system configuration

## Key Patterns

### WebSocket Communication
The system uses a structured WebSocket protocol with typed messages:
- Chat messages for user interactions
- Progress messages for long-running operations
- Error messages with specific error codes
- Status updates for workflow stages

### React Flow Integration
The frontend uses React Flow to render chat conversations as an interactive node graph:
- UserNode components for user messages
- SystemNode components for AI responses
- ProgressNode components for workflow status
- Custom edge styling for conversation flow

### File Processing Workflow
1. File upload through multipart form data
2. Metadata extraction and storage
3. AI analysis for I/O point extraction
4. Human review and approval workflow
5. BOG file generation with PyBOG integration
6. Secure file serving and download

## Testing

### Backend Tests
- Unit tests for individual services and models
- Integration tests for API endpoints
- Async test support with pytest-asyncio
- Mock external dependencies (OpenAI API)

### Frontend Tests
- Component testing with React Testing Library
- Service layer testing for API interactions
- WebSocket connection testing

## BOG File Generation

The BOG generation process involves:
1. Document analysis to extract HVAC sequences
2. I/O point identification (sensors, actuators, control points)
3. Control logic extraction and pseudocode generation
4. PyBOG manifest creation with proper metadata
5. Wire sheet logic compilation for Niagara Workbench compatibility

## Development Notes

- Use TypeScript strictly - avoid `any` types
- Follow the existing neo-brutalism design patterns
- WebSocket messages must conform to the defined schema
- All file operations should be session-scoped
- Database operations use async/await patterns
- Error handling follows centralized error middleware
- Session persistence uses local storage with Redis backup