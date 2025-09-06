from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import asyncpg
import os
import json

router = APIRouter(prefix="/api/sessions", tags=["session-management"])

# Database connection helper
async def get_db_connection():
    """Get PostgreSQL database connection"""
    DB_HOST = os.getenv("DB_HOST", "postgres")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "pybog")
    DB_USER = os.getenv("DB_USER", "pybog")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "pybog123")
    
    connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return await asyncpg.connect(connection_string)


class SessionCreate(BaseModel):
    name: Optional[str] = "New Session"
    initial_message: Optional[str] = None


class SessionUpdate(BaseModel):
    name: Optional[str] = None
    current_state: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    name: str
    current_state: str
    created_at: datetime
    last_activity: datetime
    message_count: Optional[int] = 0
    has_analysis: bool = False
    has_bog_files: bool = False


@router.post("/")
async def create_session(payload: SessionCreate):
    """Create a new session with optional initial message"""
    conn = await get_db_connection()
    try:
        # Generate session ID
        session_id = f"session_{int(datetime.utcnow().timestamp() * 1000)}"
        
        # Create session
        await conn.execute("""
            INSERT INTO sessions (session_id, name, current_state, created_at, last_activity)
            VALUES ($1, $2, 'idle', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, session_id, payload.name)
        
        # Add initial message if provided
        if payload.initial_message:
            message_id = f"msg_{session_id}_{int(datetime.utcnow().timestamp() * 1000)}"
            await conn.execute("""
                INSERT INTO session_messages (session_id, message_id, type, content, metadata)
                VALUES ($1, $2, 'system', $3, $4)
            """, session_id, message_id, payload.initial_message, json.dumps({"kind": "init"}))
        
        return {
            "session_id": session_id,
            "name": payload.name,
            "created": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    finally:
        await conn.close()


@router.get("/")
async def list_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_stats: bool = Query(True)
):
    """List all sessions with optional statistics"""
    conn = await get_db_connection()
    try:
        # Get sessions
        sessions_query = """
            SELECT 
                s.session_id, 
                s.name, 
                s.current_state,
                s.created_at,
                s.last_activity,
                COUNT(DISTINCT sm.id) as message_count,
                COUNT(DISTINCT has.id) > 0 as has_analysis,
                COUNT(DISTINCT sbf.id) > 0 as has_bog_files
            FROM sessions s
            LEFT JOIN session_messages sm ON s.session_id = sm.session_id
            LEFT JOIN hvac_analysis_state has ON s.session_id = has.session_id
            LEFT JOIN session_bog_files sbf ON s.session_id = sbf.session_id
            GROUP BY s.session_id, s.name, s.current_state, s.created_at, s.last_activity
            ORDER BY s.last_activity DESC
            LIMIT $1 OFFSET $2
        """
        
        rows = await conn.fetch(sessions_query, limit, offset)
        
        sessions = []
        for row in rows:
            session_data = {
                "session_id": row["session_id"],
                "name": row["name"],
                "current_state": row["current_state"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "last_activity": row["last_activity"].isoformat() if row["last_activity"] else None,
            }
            
            if include_stats:
                session_data.update({
                    "message_count": row["message_count"],
                    "has_analysis": row["has_analysis"],
                    "has_bog_files": row["has_bog_files"]
                })
            
            sessions.append(session_data)
        
        # Get total count
        total_count = await conn.fetchval("SELECT COUNT(*) FROM sessions")
        
        return {
            "sessions": sessions,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
    finally:
        await conn.close()


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get detailed information about a specific session"""
    conn = await get_db_connection()
    try:
        # Get session details
        session = await conn.fetchrow("""
            SELECT 
                s.*,
                COUNT(DISTINCT sm.id) as message_count,
                COUNT(DISTINCT has.id) as analysis_count,
                COUNT(DISTINCT sbf.id) as bog_file_count
            FROM sessions s
            LEFT JOIN session_messages sm ON s.session_id = sm.session_id
            LEFT JOIN hvac_analysis_state has ON s.session_id = has.session_id
            LEFT JOIN session_bog_files sbf ON s.session_id = sbf.session_id
            WHERE s.session_id = $1
            GROUP BY s.session_id
        """, session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get recent messages
        messages = await conn.fetch("""
            SELECT message_id, type, content, metadata, created_at
            FROM session_messages
            WHERE session_id = $1
            ORDER BY created_at DESC
            LIMIT 10
        """, session_id)
        
        # Get analysis if exists
        analysis = await conn.fetchrow("""
            SELECT state, analysis_data, created_at, updated_at
            FROM hvac_analysis_state
            WHERE session_id = $1
            ORDER BY updated_at DESC
            LIMIT 1
        """, session_id)
        
        # Get BOG files if exist
        bog_files = await conn.fetch("""
            SELECT bog_name, download_url, generated_at
            FROM session_bog_files
            WHERE session_id = $1
            ORDER BY generated_at DESC
        """, session_id)
        
        return {
            "session": {
                "session_id": session["session_id"],
                "name": session["name"],
                "current_state": session["current_state"],
                "created_at": session["created_at"].isoformat() if session["created_at"] else None,
                "last_activity": session["last_activity"].isoformat() if session["last_activity"] else None,
                "message_count": session["message_count"],
                "analysis_count": session["analysis_count"],
                "bog_file_count": session["bog_file_count"]
            },
            "recent_messages": [
                {
                    "message_id": m["message_id"],
                    "type": m["type"],
                    "content": m["content"],
                    "metadata": json.loads(m["metadata"]) if m["metadata"] else {},
                    "created_at": m["created_at"].isoformat() if m["created_at"] else None
                } for m in messages
            ],
            "analysis": {
                "state": analysis["state"],
                "data": json.loads(analysis["analysis_data"]) if analysis and analysis["analysis_data"] else None,
                "updated_at": analysis["updated_at"].isoformat() if analysis and analysis["updated_at"] else None
            } if analysis else None,
            "bog_files": [
                {
                    "name": bf["bog_name"],
                    "url": bf["download_url"],
                    "generated_at": bf["generated_at"].isoformat() if bf["generated_at"] else None
                } for bf in bog_files
            ]
        }
    finally:
        await conn.close()


@router.patch("/{session_id}")
async def update_session(session_id: str, payload: SessionUpdate):
    """Update session name or state"""
    conn = await get_db_connection()
    try:
        # Check if session exists
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM sessions WHERE session_id = $1)",
            session_id
        )
        
        if not exists:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Build update query
        updates = []
        values = []
        param_count = 1
        
        if payload.name is not None:
            updates.append(f"name = ${param_count}")
            values.append(payload.name)
            param_count += 1
        
        if payload.current_state is not None:
            updates.append(f"current_state = ${param_count}")
            values.append(payload.current_state)
            param_count += 1
        
        # Always update last_activity
        updates.append(f"last_activity = CURRENT_TIMESTAMP")
        
        if not updates:
            return {"message": "No updates provided"}
        
        # Execute update
        values.append(session_id)
        query = f"""
            UPDATE sessions 
            SET {', '.join(updates)}
            WHERE session_id = ${param_count}
        """
        
        await conn.execute(query, *values)
        
        # Get updated session
        updated_session = await conn.fetchrow(
            "SELECT * FROM sessions WHERE session_id = $1",
            session_id
        )
        
        return {
            "session_id": updated_session["session_id"],
            "name": updated_session["name"],
            "current_state": updated_session["current_state"],
            "last_activity": updated_session["last_activity"].isoformat() if updated_session["last_activity"] else None,
            "updated": True
        }
    finally:
        await conn.close()


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all related data"""
    conn = await get_db_connection()
    try:
        # Check if session exists
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM sessions WHERE session_id = $1)",
            session_id
        )
        
        if not exists:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Delete session (cascades to related tables)
        await conn.execute("DELETE FROM sessions WHERE session_id = $1", session_id)
        
        return {
            "session_id": session_id,
            "deleted": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    finally:
        await conn.close()


@router.post("/{session_id}/duplicate")
async def duplicate_session(session_id: str, new_name: Optional[str] = None):
    """Duplicate a session with its messages but not analysis"""
    conn = await get_db_connection()
    try:
        # Get original session
        original = await conn.fetchrow(
            "SELECT * FROM sessions WHERE session_id = $1",
            session_id
        )
        
        if not original:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Generate new session ID
        new_session_id = f"session_{int(datetime.utcnow().timestamp() * 1000)}"
        new_session_name = new_name or f"{original['name']} (Copy)"
        
        # Create new session
        await conn.execute("""
            INSERT INTO sessions (session_id, name, current_state, created_at, last_activity)
            VALUES ($1, $2, 'idle', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, new_session_id, new_session_name)
        
        # Copy messages
        await conn.execute("""
            INSERT INTO session_messages (session_id, message_id, type, content, metadata, created_at)
            SELECT 
                $1,
                'msg_' || $1 || '_' || row_number() OVER (ORDER BY created_at),
                type,
                content,
                metadata,
                created_at
            FROM session_messages
            WHERE session_id = $2
        """, new_session_id, session_id)
        
        return {
            "original_session_id": session_id,
            "new_session_id": new_session_id,
            "name": new_session_name,
            "duplicated": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    finally:
        await conn.close()


@router.get("/{session_id}/export")
async def export_session(session_id: str):
    """Export session data for backup or sharing"""
    conn = await get_db_connection()
    try:
        # Get session
        session = await conn.fetchrow(
            "SELECT * FROM sessions WHERE session_id = $1",
            session_id
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get all messages
        messages = await conn.fetch("""
            SELECT * FROM session_messages
            WHERE session_id = $1
            ORDER BY created_at
        """, session_id)
        
        # Get analysis
        analysis = await conn.fetch("""
            SELECT * FROM hvac_analysis_state
            WHERE session_id = $1
            ORDER BY created_at
        """, session_id)
        
        # Get BOG files
        bog_files = await conn.fetch("""
            SELECT * FROM session_bog_files
            WHERE session_id = $1
            ORDER BY generated_at
        """, session_id)
        
        return {
            "export_version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "session": {
                "session_id": session["session_id"],
                "name": session["name"],
                "current_state": session["current_state"],
                "created_at": session["created_at"].isoformat() if session["created_at"] else None,
                "last_activity": session["last_activity"].isoformat() if session["last_activity"] else None
            },
            "messages": [
                {
                    "message_id": m["message_id"],
                    "type": m["type"],
                    "content": m["content"],
                    "metadata": json.loads(m["metadata"]) if m["metadata"] else {},
                    "created_at": m["created_at"].isoformat() if m["created_at"] else None
                } for m in messages
            ],
            "analysis": [
                {
                    "state": a["state"],
                    "analysis_data": json.loads(a["analysis_data"]) if a["analysis_data"] else None,
                    "bog_data": json.loads(a["bog_data"]) if a["bog_data"] else None,
                    "feedback": a["feedback"],
                    "created_at": a["created_at"].isoformat() if a["created_at"] else None,
                    "updated_at": a["updated_at"].isoformat() if a["updated_at"] else None
                } for a in analysis
            ],
            "bog_files": [
                {
                    "bog_name": bf["bog_name"],
                    "file_path": bf["file_path"],
                    "download_url": bf["download_url"],
                    "generated_at": bf["generated_at"].isoformat() if bf["generated_at"] else None,
                    "metadata": json.loads(bf["metadata"]) if bf["metadata"] else {}
                } for bf in bog_files
            ]
        }
    finally:
        await conn.close()
