# PyBOG FastAPI Application

This directory contains the core FastAPI application for the PyBOG backend.

## Structure

- `main.py` - Main FastAPI application with WebSocket endpoints, error handling, and background tasks

## Features

### ✅ Task 4 Implementation Complete

1. **FastAPI App with CORS Middleware**
   - Configured CORS middleware with configurable origins
   - Health check endpoint at `/api/health`
   - Root endpoint at `/`

2. **WebSocket Endpoint with Session-Based Connection Handling**
   - WebSocket endpoint at `/ws/{session_id}`
   - Session-based connection management
   - Event replay for session resume
   - Message envelope system for consistent formatting

3. **Startup Event Handler for Background Cleanup Task**
   - FastAPI lifespan context for startup/shutdown
   - Background cleanup task running every hour
   - Graceful task cancellation on shutdown

4. **Standardized Error Handling**
   - Four standard error codes: `FILE`, `ANALYSIS`, `DB`, `STREAM`
   - Centralized `ErrorHandler` class
   - Error events published to event bus
   - Global exception handlers

## Key Components

### WebSocket Manager
- Manages active WebSocket connections per session
- Handles connection/disconnection lifecycle
- Broadcasts events to session-specific connections
- Session resume with event replay

### Error Handler
- Standardized error response format
- Error event publishing
- Contextual error logging
- Recovery suggestions

### Event Bus Integration
- WebSocket messages use event bus for decoupling
- Services emit events, WebSocket manager consumes them
- Event replay buffer for session resume
- Clean separation of concerns

## Usage

```python
# Start the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# WebSocket connection
ws://localhost:8000/ws/{session_id}

# Health check
GET http://localhost:8000/api/health
```

## Message Format

WebSocket messages use a consistent envelope format:

```json
{
  "type": "chat|progress|bog_generated|error|system",
  "session_id": "string",
  "data": {},
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Error Codes

- `FILE` - File upload/processing errors
- `ANALYSIS` - LLM/analysis errors  
- `DB` - Database connection/query errors
- `STREAM` - WebSocket/streaming errors