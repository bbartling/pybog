"""
Session Management Service for PyBOG Backend

This service handles session creation, retrieval, updating, and listing operations.
It integrates with the EventBus system for event emission and provides database
persistence for all session operations.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

from core.database import get_database, DatabaseOperationError
from core.events import EventBus, Event
from models.session_models import (
    Session, 
    SessionCreateRequest, 
    SessionUpdateRequest, 
    SessionWithFiles,
    SessionListResponse,
    SessionStatsResponse
)

logger = logging.getLogger(__name__)


class SessionService:
    """
    SessionService class for creating, retrieving, and updating sessions.
    Integrates with EventBus for event emission and provides database persistence.
    """
    
    def __init__(self, event_bus: EventBus):
        """
        Initialize the SessionService.
        
        Args:
            event_bus: EventBus instance for event emission
        """
        self.event_bus = event_bus
    
    async def create_session(self, request: SessionCreateRequest) -> Session:
        """
        Create a new session with database persistence.
        
        Args:
            request: Session creation request with session_id, name, and metadata
            
        Returns:
            Created Session object
            
        Raises:
            DatabaseOperationError: If session creation fails
            ValueError: If session_id already exists
        """
        try:
            db = await get_database()
            
            # Check if session already exists
            existing = await db.fetch_one(
                "SELECT session_id FROM sessions WHERE session_id = $1",
                request.session_id
            )
            
            if existing:
                raise ValueError(f"Session with ID '{request.session_id}' already exists")
            
            # Insert new session
            import json
            result = await db.fetch_one(
                """
                INSERT INTO sessions (session_id, name, metadata, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                RETURNING session_id, name, metadata, created_at, updated_at
                """,
                request.session_id,
                request.name,
                json.dumps(request.metadata)
            )
            
            if not result:
                raise DatabaseOperationError("Failed to create session")
            
            # Convert JSON string back to dict for Pydantic model
            import json
            session_data = dict(result)
            if isinstance(session_data.get('metadata'), str):
                session_data['metadata'] = json.loads(session_data['metadata'])
            session = Session(**session_data)
            
            # Emit session created event
            await self.event_bus.publish(
                session_id=session.session_id,
                event=Event(
                    type="session",
                    session_id=session.session_id,
                    operation="created",
                    data={
                        "session_id": session.session_id,
                        "name": session.name,
                        "metadata": session.metadata,
                        "created_at": session.created_at.isoformat() if session.created_at else None
                    }
                )
            )
            
            logger.info(f"Created session: {session.session_id}")
            return session
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to create session {request.session_id}: {e}")
            raise DatabaseOperationError(f"Session creation failed: {e}")
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        Retrieve a session by ID.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Session object if found, None otherwise
            
        Raises:
            DatabaseOperationError: If database query fails
        """
        try:
            db = await get_database()
            
            result = await db.fetch_one(
                """
                SELECT session_id, name, metadata, created_at, updated_at
                FROM sessions 
                WHERE session_id = $1
                """,
                session_id
            )
            
            if not result:
                return None
            
            # Convert JSON string back to dict for Pydantic model
            import json
            session_data = dict(result)
            if isinstance(session_data.get('metadata'), str):
                session_data['metadata'] = json.loads(session_data['metadata'])
            return Session(**session_data)
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise DatabaseOperationError(f"Session retrieval failed: {e}")
    
    async def update_session(self, session_id: str, request: SessionUpdateRequest) -> Optional[Session]:
        """
        Update an existing session.
        
        Args:
            session_id: The session identifier
            request: Session update request with optional name and metadata
            
        Returns:
            Updated Session object if found, None if session doesn't exist
            
        Raises:
            DatabaseOperationError: If database update fails
        """
        try:
            db = await get_database()
            
            # Build dynamic update query based on provided fields
            update_fields = []
            params = []
            param_count = 1
            
            if request.name is not None:
                update_fields.append(f"name = ${param_count}")
                params.append(request.name)
                param_count += 1
            
            if request.metadata is not None:
                import json
                update_fields.append(f"metadata = ${param_count}")
                params.append(json.dumps(request.metadata))
                param_count += 1
            
            if not update_fields:
                # No fields to update, just return current session
                return await self.get_session(session_id)
            
            # Add updated_at and session_id parameters
            update_fields.append(f"updated_at = NOW()")
            params.append(session_id)
            
            query = f"""
                UPDATE sessions 
                SET {', '.join(update_fields)}
                WHERE session_id = ${param_count}
                RETURNING session_id, name, metadata, created_at, updated_at
            """
            
            result = await db.fetch_one(query, *params)
            
            if not result:
                return None
            
            # Convert JSON string back to dict for Pydantic model
            import json
            session_data = dict(result)
            if isinstance(session_data.get('metadata'), str):
                session_data['metadata'] = json.loads(session_data['metadata'])
            session = Session(**session_data)
            
            # Emit session updated event
            await self.event_bus.publish(
                session_id=session.session_id,
                event=Event(
                    type="session",
                    session_id=session.session_id,
                    operation="updated",
                    data={
                        "session_id": session.session_id,
                        "name": session.name,
                        "metadata": session.metadata,
                        "updated_fields": {
                            "name": request.name is not None,
                            "metadata": request.metadata is not None
                        },
                        "updated_at": session.updated_at.isoformat() if session.updated_at else None
                    }
                )
            )
            
            logger.info(f"Updated session: {session.session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            raise DatabaseOperationError(f"Session update failed: {e}")
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all associated data.
        
        Args:
            session_id: The session identifier
            
        Returns:
            True if session was deleted, False if session didn't exist
            
        Raises:
            DatabaseOperationError: If database deletion fails
        """
        try:
            db = await get_database()
            
            # Delete session (CASCADE will handle related records)
            result = await db.execute_query(
                "DELETE FROM sessions WHERE session_id = $1",
                session_id
            )
            
            # Check if any rows were affected
            deleted = "DELETE 1" in result
            
            if deleted:
                # Emit session deleted event
                await self.event_bus.publish(
                    session_id=session_id,
                    event=Event(
                        type="session",
                        session_id=session_id,
                        operation="deleted",
                        data={
                            "session_id": session_id,
                            "deleted_at": datetime.now().isoformat()
                        }
                    )
                )
                
                # Clear session from event bus
                await self.event_bus.clear_session(session_id)
                
                logger.info(f"Deleted session: {session_id}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            raise DatabaseOperationError(f"Session deletion failed: {e}")
    
    async def list_sessions(self, limit: int = 50, offset: int = 0) -> SessionListResponse:
        """
        List sessions with associated file information.
        
        Args:
            limit: Maximum number of sessions to return (default: 50)
            offset: Number of sessions to skip (default: 0)
            
        Returns:
            SessionListResponse with sessions and total count
            
        Raises:
            DatabaseOperationError: If database query fails
        """
        try:
            db = await get_database()
            
            # Get sessions with file counts using the session_overview view
            sessions_result = await db.fetch_all(
                """
                SELECT 
                    session_id, name, created_at, updated_at, metadata,
                    message_count, file_count, upload_count, bog_count,
                    analysis_count, completed_analysis_count, active_analysis_count
                FROM session_overview
                ORDER BY updated_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit, offset
            )
            
            # Get total count
            total_count = await db.fetch_val(
                "SELECT COUNT(*) FROM sessions"
            )
            
            # Convert JSON strings back to dicts for Pydantic models
            import json
            sessions = []
            for row in sessions_result:
                session_data = dict(row)
                if isinstance(session_data.get('metadata'), str):
                    session_data['metadata'] = json.loads(session_data['metadata'])
                sessions.append(SessionWithFiles(**session_data))
            
            return SessionListResponse(
                sessions=sessions,
                total_count=total_count
            )
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            raise DatabaseOperationError(f"Session listing failed: {e}")
    
    async def get_session_stats(self) -> SessionStatsResponse:
        """
        Get overall session statistics.
        
        Returns:
            SessionStatsResponse with aggregate statistics
            
        Raises:
            DatabaseOperationError: If database query fails
        """
        try:
            db = await get_database()
            
            # Get aggregate statistics
            stats = await db.fetch_one(
                """
                SELECT 
                    COUNT(DISTINCT s.session_id) as total_sessions,
                    COUNT(DISTINCT CASE WHEN s.updated_at > NOW() - INTERVAL '24 hours' THEN s.session_id END) as active_sessions,
                    COUNT(DISTINCT cm.id) as total_messages,
                    COUNT(DISTINCT f.id) as total_files,
                    COUNT(DISTINCT ar.id) as total_analyses
                FROM sessions s
                LEFT JOIN chat_messages cm ON s.session_id = cm.session_id
                LEFT JOIN files f ON s.session_id = f.session_id
                LEFT JOIN analysis_results ar ON s.session_id = ar.session_id
                """
            )
            
            return SessionStatsResponse(**stats)
            
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            raise DatabaseOperationError(f"Session stats retrieval failed: {e}")
    
    async def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_id: The session identifier
            
        Returns:
            True if session exists, False otherwise
            
        Raises:
            DatabaseOperationError: If database query fails
        """
        try:
            db = await get_database()
            
            result = await db.fetch_val(
                "SELECT 1 FROM sessions WHERE session_id = $1",
                session_id
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to check session existence {session_id}: {e}")
            raise DatabaseOperationError(f"Session existence check failed: {e}")
    
    async def generate_session_id(self) -> str:
        """
        Generate a unique session ID.
        
        Returns:
            A unique session identifier
        """
        while True:
            session_id = f"session-{uuid4().hex[:8]}"
            
            # Check if this ID already exists
            if not await self.session_exists(session_id):
                return session_id