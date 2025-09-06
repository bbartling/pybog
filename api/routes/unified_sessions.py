"""
Unified session management that bridges n8n workflow requirements with new enhanced features
This ensures seamless integration between existing n8n workflows and new UI features
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import os

from fastapi import APIRouter, HTTPException, Query, UploadFile, File as FastAPIFile, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete

from api.database import get_session, get_raw_connection
from api.models import Session, Message, File, AnalysisResult, BOGFile


router = APIRouter(prefix="/api/unified", tags=["unified-sessions"])


class UnifiedMessage(BaseModel):
    message_id: str
    type: str
    content: str
    metadata: Optional[dict] = None
    session_state: Optional[str] = None


class UnifiedSessionCreate(BaseModel):
    name: str = "New Session"
    initial_message: Optional[str] = None


@router.post("/sessions")
async def create_unified_session(
    payload: UnifiedSessionCreate,
    db: AsyncSession = Depends(get_session)
):
    """
    Create a session that works with both n8n workflows and new UI
    - Creates entry in sessions table (for both systems)
    - Optionally adds initial message to both message tables
    """
    conn = await get_raw_connection()
    try:
        session_id = f"session_{int(datetime.utcnow().timestamp() * 1000)}"
        
        # Create in sessions table (both systems use this)
        await conn.execute("""
            INSERT INTO sessions (session_id, name, current_state, state, created_at, last_activity)
            VALUES ($1, $2, 'idle', 'idle', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, session_id, payload.name)
        
        # Add initial message if provided (to both tables via trigger)
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


@router.post("/sessions/{session_id}/messages")
async def add_unified_message(
    session_id: str,
    payload: UnifiedMessage
):
    """
    Add a message that will be visible to both n8n workflows and new UI
    - Inserts into session_messages (n8n uses this)
    - Triggers sync to messages table (new UI uses this)
    """
    conn = await get_raw_connection()
    try:
        # Check session exists
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM sessions WHERE session_id = $1)",
            session_id
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Insert into session_messages (n8n table)
        await conn.execute("""
            INSERT INTO session_messages (session_id, message_id, type, content, metadata)
            VALUES ($1, $2, $3, $4, $5)
        """, session_id, payload.message_id, payload.type, payload.content, 
            json.dumps(payload.metadata) if payload.metadata else '{}')
        
        # Update session state if provided
        if payload.session_state:
            await conn.execute("""
                UPDATE sessions 
                SET current_state = $1, state = $1, last_activity = CURRENT_TIMESTAMP
                WHERE session_id = $2
            """, payload.session_state, session_id)
        else:
            await conn.execute("""
                UPDATE sessions SET last_activity = CURRENT_TIMESTAMP
                WHERE session_id = $1
            """, session_id)
        
        return {
            "message_id": payload.message_id,
            "created": True
        }
    finally:
        await conn.close()


@router.post("/sessions/{session_id}/analysis")
async def save_unified_analysis(
    session_id: str,
    analysis_data: dict,
    message_id: Optional[str] = None
):
    """
    Save analysis that works with both n8n workflows and new UI
    - Saves to hvac_analysis_state (n8n uses this)
    - Also saves to analysis_results (new UI can use this)
    """
    conn = await get_raw_connection()
    try:
        # Check session exists
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM sessions WHERE session_id = $1)",
            session_id
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Insert into hvac_analysis_state (for n8n)
        analysis_id = await conn.fetchval("""
            INSERT INTO hvac_analysis_state 
            (session_id, state, analysis_data, message_id, created_at, updated_at)
            VALUES ($1, 'complete', $2, $3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
        """, session_id, json.dumps(analysis_data), message_id)
        
        # Also insert into analysis_results (for new UI)
        new_analysis_id = f"analysis_{session_id}_{int(datetime.utcnow().timestamp() * 1000)}"
        await conn.execute("""
            INSERT INTO analysis_results 
            (analysis_id, session_id, message_id, analysis_data, status)
            VALUES ($1, $2, $3, $4, 'complete')
        """, new_analysis_id, session_id, message_id, json.dumps(analysis_data))
        
        # Update session state
        await conn.execute("""
            UPDATE sessions 
            SET current_state = 'analysis_complete', 
                state = 'analysis_complete',
                last_activity = CURRENT_TIMESTAMP
            WHERE session_id = $1
        """, session_id)
        
        return {
            "analysis_id": analysis_id,
            "new_analysis_id": new_analysis_id,
            "saved": True
        }
    finally:
        await conn.close()


@router.post("/sessions/{session_id}/bog")
async def save_unified_bog(
    session_id: str,
    bog_name: str,
    file_path: str,
    download_url: str,
    analysis_id: Optional[int] = None,
    message_id: Optional[str] = None
):
    """
    Save BOG file that works with both n8n workflows and new UI
    - Saves to session_bog_files (n8n uses this)
    - Also saves to bog_files (new UI can use this)
    """
    conn = await get_raw_connection()
    try:
        # Check session exists
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM sessions WHERE session_id = $1)",
            session_id
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Insert into session_bog_files (for n8n)
        bog_file_id = await conn.fetchval("""
            INSERT INTO session_bog_files 
            (session_id, analysis_id, bog_name, file_path, download_url, generated_at)
            VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
            RETURNING id
        """, session_id, analysis_id, bog_name, file_path, download_url)
        
        # Also insert into bog_files (for new UI)
        new_bog_id = f"bog_{session_id}_{int(datetime.utcnow().timestamp() * 1000)}"
        await conn.execute("""
            INSERT INTO bog_files 
            (bog_id, session_id, message_id, filename, file_path, download_url)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, new_bog_id, session_id, message_id, bog_name, file_path, download_url)
        
        # Update session state
        await conn.execute("""
            UPDATE sessions 
            SET current_state = 'bog_generated', 
                state = 'bog_generated',
                last_activity = CURRENT_TIMESTAMP
            WHERE session_id = $1
        """, session_id)
        
        return {
            "bog_file_id": bog_file_id,
            "new_bog_id": new_bog_id,
            "saved": True
        }
    finally:
        await conn.close()


@router.get("/sessions/{session_id}/full")
async def get_unified_session(session_id: str):
    """
    Get session data from both n8n tables and new tables
    Returns unified view that works with both systems
    """
    conn = await get_raw_connection()
    try:
        # Get session
        session = await conn.fetchrow("""
            SELECT * FROM sessions WHERE session_id = $1
        """, session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get messages from unified view
        messages = await conn.fetch("""
            SELECT * FROM unified_messages 
            WHERE session_id = $1 
            ORDER BY timestamp DESC
        """, session_id)
        
        # Get analysis from hvac_analysis_state (n8n table)
        analysis = await conn.fetchrow("""
            SELECT * FROM hvac_analysis_state 
            WHERE session_id = $1 
            ORDER BY updated_at DESC 
            LIMIT 1
        """, session_id)
        
        # Get BOG files from unified view
        bog_files = await conn.fetch("""
            SELECT * FROM unified_bog_files 
            WHERE session_id = $1 
            ORDER BY created_at DESC
        """, session_id)
        
        # Get uploaded files
        files = await conn.fetch("""
            SELECT * FROM files 
            WHERE session_id = $1 
            ORDER BY upload_time DESC
        """, session_id)
        
        return {
            "session": {
                "session_id": session["session_id"],
                "name": session["name"],
                "state": session["state"] or session["current_state"],
                "created_at": session["created_at"].isoformat() if session["created_at"] else None,
                "last_activity": session["last_activity"].isoformat() if session["last_activity"] else None
            },
            "messages": [
                {
                    "message_id": m["message_id"],
                    "type": m["type"],
                    "content": m["content"],
                    "timestamp": m["timestamp"].isoformat() if m["timestamp"] else None,
                    "metadata": m["metadata"]
                }
                for m in messages
            ],
            "analysis": {
                "state": analysis["state"],
                "data": analysis["analysis_data"],
                "updated_at": analysis["updated_at"].isoformat() if analysis["updated_at"] else None
            } if analysis else None,
            "bog_files": [
                {
                    "bog_id": bf["bog_id"],
                    "filename": bf["filename"],
                    "download_url": bf["download_url"],
                    "created_at": bf["created_at"].isoformat() if bf["created_at"] else None
                }
                for bf in bog_files
            ],
            "files": [
                {
                    "file_id": f["file_id"],
                    "filename": f["filename"],
                    "file_type": f["file_type"],
                    "file_size": f["file_size"]
                }
                for f in files
            ] if files else []
        }
    finally:
        await conn.close()


@router.get("/sessions/recent")
async def get_recent_unified_sessions(limit: int = Query(10, ge=1, le=50)):
    """Get recent sessions with unified data"""
    conn = await get_raw_connection()
    try:
        sessions = await conn.fetch("""
            SELECT 
                s.session_id,
                s.name,
                COALESCE(s.state, s.current_state) as state,
                s.last_activity,
                COUNT(DISTINCT um.message_id) as message_count,
                COUNT(DISTINCT f.file_id) as file_count,
                EXISTS(SELECT 1 FROM hvac_analysis_state has WHERE has.session_id = s.session_id) as has_analysis,
                EXISTS(SELECT 1 FROM unified_bog_files ubf WHERE ubf.session_id = s.session_id) as has_bog
            FROM sessions s
            LEFT JOIN unified_messages um ON s.session_id = um.session_id
            LEFT JOIN files f ON s.session_id = f.session_id
            GROUP BY s.session_id, s.name, s.state, s.current_state, s.last_activity
            ORDER BY s.last_activity DESC
            LIMIT $1
        """, limit)
        
        return {
            "sessions": [
                {
                    "session_id": s["session_id"],
                    "name": s["name"],
                    "state": s["state"],
                    "last_activity": s["last_activity"].isoformat() if s["last_activity"] else None,
                    "message_count": s["message_count"],
                    "file_count": s["file_count"],
                    "has_analysis": s["has_analysis"],
                    "has_bog": s["has_bog"]
                }
                for s in sessions
            ]
        }
    finally:
        await conn.close()
