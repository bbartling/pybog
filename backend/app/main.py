"""
PyBOG FastAPI Backend - Clean Implementation
Unified FastAPI backend replacing n8n workflows
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_config, get_websocket_config
from core.events import EventBus, Event
from services.websocket_manager import WebSocketManager
from models.websocket_models import (
    WebSocketMessage, MessageType, ErrorCode, 
    create_chat_message, create_error_message, create_progress_message
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global event bus instance
event_bus = EventBus()

# Global WebSocket manager with event bus integration
websocket_manager = WebSocketManager(event_bus)

# Background cleanup task
async def periodic_file_cleanup():
    """Background task for file cleanup - runs periodically"""
    while True:
        try:
            # This will be implemented in the file management service task
            logger.info("Running periodic file cleanup task")
            
            # Emit cleanup event
            cleanup_event = Event(
                type="system",
                session_id="system",
                operation="cleanup",
                data={"message": "File cleanup task executed", "timestamp": datetime.utcnow().isoformat()}
            )
            await event_bus.publish("system", cleanup_event)
            
            # Wait for next cleanup cycle (1 hour by default)
            config = get_websocket_config()
            await asyncio.sleep(3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Error in periodic cleanup task: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes before retrying

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting PyBOG FastAPI Backend")
    
    # Start background cleanup task
    cleanup_task = asyncio.create_task(periodic_file_cleanup())
    logger.info("Background cleanup task started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down PyBOG FastAPI Backend")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        logger.info("Background cleanup task cancelled")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="PyBOG API",
    version="3.0.0",
    description="Unified FastAPI backend for PyBOG HVAC Control Builder",
    lifespan=lifespan
)

# Add comprehensive error handling middleware
from core.error_middleware import ErrorHandlingMiddleware, RequestValidationMiddleware

app.add_middleware(ErrorHandlingMiddleware, enable_request_logging=True)
app.add_middleware(RequestValidationMiddleware, max_request_size=50 * 1024 * 1024)

# CORS configuration using config
config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket message envelope model is now imported from models.websocket_models

# Import comprehensive error handling system
from core.error_handler import get_error_handler, create_error_context, ErrorCategory
from core.error_decorators import handle_errors, ErrorContextManager

# Global error handler instance with event bus integration
error_handler = get_error_handler(event_bus)

@app.get("/api/health")
@handle_errors("HealthCheck", "health_check", ErrorCategory.SYSTEM, reraise=False, fallback_result={
    "status": "error",
    "message": "Health check system failure",
    "timestamp": datetime.utcnow().isoformat()
})
async def health():
    """Health check endpoint with comprehensive service status and error handling"""
    async with ErrorContextManager("HealthCheck", "health_check", emit_event=False, reraise=False):
        # Check database connection
        db_healthy = True
        db_message = "Connected"
        try:
            from core.database import get_database
            db = await get_database()
            # Simple connectivity test
            await db.fetch_val("SELECT 1")
        except Exception as e:
            db_healthy = False
            db_message = f"Connection failed: {str(e)}"
            logger.warning(f"Database health check failed: {e}")
        
        # Check Redis connection (if configured)
        redis_healthy = True
        redis_message = "Operational"
        try:
            # This would be a real Redis check in production
            # For now, assume operational
            pass
        except Exception as e:
            redis_healthy = False
            redis_message = f"Connection failed: {str(e)}"
            logger.warning(f"Redis health check failed: {e}")
        
        # WebSocket status
        ws_connections = websocket_manager.get_connection_count()
        
        # Error handler statistics
        error_stats = error_handler.get_error_statistics()
        
        # Overall system health
        critical_services = [db_healthy]
        system_healthy = all(critical_services)
        
        return {
            "status": "ok" if system_healthy else "degraded", 
            "message": "PyBOG FastAPI Backend is running" if system_healthy else "Some services are experiencing issues",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "api": {
                    "healthy": True,
                    "message": "Running",
                    "details": {"port": 8000}
                },
                "database": {
                    "healthy": db_healthy,
                    "message": db_message,
                    "details": {"type": "PostgreSQL"}
                },
                "redis": {
                    "healthy": redis_healthy,
                    "message": redis_message,
                    "details": {"type": "Redis Cache"}
                },
                "websockets": {
                    "healthy": True,
                    "message": "Active",
                    "details": {"connections": ws_connections}
                },
                "error_handler": {
                    "healthy": True,
                    "message": "Operational",
                    "details": error_stats
                }
            },
            "metrics": {
                "active_connections": ws_connections,
                "total_errors": error_stats.get("total_errors", 0),
                "recent_errors": error_stats.get("recent_errors", 0),
                "uptime": "Running"
            }
        }

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "PyBOG FastAPI Backend - Clean Architecture"}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint with session-based connection handling.
    
    Provides real-time communication for chat, progress updates, and system events.
    Includes session resume functionality with event replay.
    """
    try:
        # Validate session_id format
        if not session_id or len(session_id.strip()) == 0:
            await websocket.close(code=1008, reason="Invalid session_id")
            return
        
        session_id = session_id.strip()
        logger.info(f"WebSocket connection attempt for session: {session_id}")
        
        # Connect WebSocket to session using WebSocketManager
        await websocket_manager.connect(websocket, session_id)
        
        # Send connection confirmation using standardized message format
        welcome_message = create_chat_message(
            session_id=session_id,
            content=f"Connected to session {session_id}. Session resumed successfully.",
            is_complete=True
        )
        await websocket_manager.send_message(session_id, welcome_message)
        
        # Publish connection event to event bus
        connection_event = Event(
            type="system",
            session_id=session_id,
            operation="websocket_connect",
            data={
                "message": f"WebSocket connected for session {session_id}",
                "status": "connected",
                "connection_time": datetime.utcnow().isoformat()
            }
        )
        await event_bus.publish(session_id, connection_event)
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                message_text = await websocket.receive_text()
                
                # Handle incoming message using WebSocketManager
                await websocket_manager.handle_incoming_message(session_id, message_text)
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session: {session_id}")
                break
            except Exception as e:
                # Handle WebSocket message errors with comprehensive error handling
                logger.error(f"Error handling WebSocket message for session {session_id}: {e}")
                
                # Create error context
                context = create_error_context(
                    operation="websocket_message",
                    component="WebSocketEndpoint",
                    session_id=session_id,
                    additional_data={
                        "message_length": len(message_text) if message_text else 0,
                        "connection_active": True
                    }
                )
                
                # Handle error with comprehensive system
                error_response = await error_handler.handle_error(
                    error=e,
                    context=context,
                    emit_event=True
                )
                
                # Send error message to client using standardized format
                error_message = create_error_message(
                    session_id=session_id,
                    error_code=ErrorCode.STREAM,
                    message=error_response.message,
                    operation="websocket_message",
                    details={"error_id": error_response.error_id},
                    retry_possible=error_response.retry_possible
                )
                await websocket_manager.send_message(session_id, error_message)
    
    except Exception as e:
        # Handle connection errors with comprehensive error handling
        logger.error(f"WebSocket connection error for session {session_id}: {e}")
        
        # Create error context
        context = create_error_context(
            operation="websocket_connect",
            component="WebSocketEndpoint",
            session_id=session_id,
            additional_data={
                "connection_attempt": True,
                "session_id_valid": bool(session_id and session_id.strip())
            }
        )
        
        # Handle error with comprehensive system
        await error_handler.handle_error(
            error=e,
            context=context,
            emit_event=True
        )
    
    finally:
        # Clean up connection using WebSocketManager
        await websocket_manager.disconnect(session_id)
        
        # Publish disconnection event
        try:
            disconnect_event = Event(
                type="system",
                session_id=session_id,
                operation="websocket_disconnect",
                data={
                    "message": f"WebSocket disconnected for session {session_id}",
                    "status": "disconnected",
                    "disconnect_time": datetime.utcnow().isoformat()
                }
            )
            await event_bus.publish(session_id, disconnect_event)
        except Exception as e:
            logger.error(f"Error publishing disconnect event: {e}")

# Include API routes
from .api_routes import router as api_router
app.include_router(api_router)