"""
Enhanced session management with file upload and persistence
"""
from datetime import datetime
from typing import List, Optional
from pathlib import Path
import json
import uuid
import aiofiles
import os

from fastapi import APIRouter, HTTPException, Query, UploadFile, File as FastAPIFile, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from api.database import get_session
from api.models import Session, Message, File, AnalysisResult, BOGFile


router = APIRouter(prefix="/api/sessions", tags=["enhanced-sessions"])

# File storage configuration
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

BOG_DIR = Path(os.getenv("BOG_DIR", "./data/bog_files"))
BOG_DIR.mkdir(parents=True, exist_ok=True)


class SessionCreate(BaseModel):
    name: str = "New Session"
    initial_message: Optional[str] = None


class SessionUpdate(BaseModel):
    name: Optional[str] = None
    state: Optional[str] = None
    metadata: Optional[dict] = None


class MessageCreate(BaseModel):
    message_id: str
    type: str  # user, assistant, system
    content: str
    message_type: Optional[str] = None
    metadata: Optional[dict] = None
    session_state: Optional[str] = None
    name: Optional[str] = None  # For session rename


class SessionResponse(BaseModel):
    session_id: str
    name: str
    state: str
    created_at: datetime
    last_activity: datetime
    message_count: int = 0
    file_count: int = 0
    has_analysis: bool = False
    has_bog_files: bool = False


@router.post("/")
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_session)
):
    """Create a new session with optional initial message"""
    try:
        # Generate session ID
        session_id = f"session_{int(datetime.utcnow().timestamp() * 1000)}"
        
        # Create session
        new_session = Session(
            session_id=session_id,
            name=payload.name,
            state='idle'
        )
        db.add(new_session)
        
        # Add initial message if provided
        if payload.initial_message:
            message_id = f"msg_{session_id}_{int(datetime.utcnow().timestamp() * 1000)}"
            init_message = Message(
                message_id=message_id,
                session_id=session_id,
                type='system',
                content=payload.initial_message,
                meta={"kind": "init"}
            )
            db.add(init_message)
        
        await db.commit()
        
        return {
            "session_id": session_id,
            "name": payload.name,
            "created": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent")
async def get_recent_sessions(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_session)
):
    """Get most recent sessions"""
    try:
        result = await db.execute(
            select(Session)
            .order_by(desc(Session.last_activity))
            .limit(limit)
        )
        sessions = result.scalars().all()
        
        return {
            "sessions": [
                {
                    "session_id": s.session_id,
                    "name": s.name,
                    "state": s.state,
                    "last_activity": s.last_activity.isoformat() if s.last_activity else None
                }
                for s in sessions
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/full")
async def get_full_session(
    session_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Get complete session with messages, files, and analysis"""
    try:
        # Get session with all relationships
        result = await db.execute(
            select(Session)
            .options(
                selectinload(Session.messages),
                selectinload(Session.files),
                selectinload(Session.analysis_results),
                selectinload(Session.bog_files)
            )
            .where(Session.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get latest analysis
        analysis = None
        if session.analysis_results:
            latest_analysis = max(session.analysis_results, key=lambda a: a.created_at)
            analysis = {
                "analysis_id": latest_analysis.analysis_id,
                "analysis_data": latest_analysis.analysis_data,
                "status": latest_analysis.status
            }
        
        return {
            "session": {
                "session_id": session.session_id,
                "name": session.name,
                "state": session.state,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "last_activity": session.last_activity.isoformat() if session.last_activity else None
            },
            "messages": [
                {
                    "message_id": m.message_id,
                    "type": m.type,
                    "content": m.content,
                    "created_at": m.timestamp.isoformat() if m.timestamp else None,
                    "metadata": m.meta
                }
                for m in sorted(session.messages, key=lambda m: m.timestamp)
            ],
            "files": [
                {
                    "file_id": f.file_id,
                    "filename": f.filename,
                    "file_type": f.file_type,
                    "file_size": f.file_size,
                    "preview_url": f"/api/files/{session_id}/{f.filename}?inline=1"
                }
                for f in session.files
            ],
            "bog_files": [
                {
                    "bog_id": b.bog_id,
                    "filename": b.filename,
                    "download_url": b.download_url
                }
                for b in session.bog_files
            ],
            "analysis": analysis
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/messages")
async def add_message(
    session_id: str,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_session)
):
    """Add a message to a session"""
    try:
        # Check session exists
        result = await db.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Create message
        new_message = Message(
            message_id=payload.message_id,
            session_id=session_id,
            type=payload.type,
            message_type=payload.message_type,
            content=payload.content,
            meta=payload.metadata or {}
        )
        db.add(new_message)
        
        # Update session state and activity
        session.last_activity = datetime.utcnow()
        if payload.session_state:
            session.state = payload.session_state
        if payload.name:
            session.name = payload.name
        
        await db.commit()
        
        return {
            "message_id": new_message.message_id,
            "created": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/upload")
async def upload_file(
    session_id: str,
    file: UploadFile = FastAPIFile(...),
    message_id: Optional[str] = None,
    db: AsyncSession = Depends(get_session)
):
    """Upload a file and associate it with a session"""
    try:
        # Check session exists
        result = await db.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Generate file ID and path
        file_id = f"file_{session_id}_{int(datetime.utcnow().timestamp() * 1000)}"
        file_ext = Path(file.filename).suffix
        safe_filename = f"{file_id}{file_ext}"
        file_path = UPLOAD_DIR / session_id / safe_filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save file to disk
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Create file record
        new_file = File(
            file_id=file_id,
            session_id=session_id,
            message_id=message_id,
            filename=file.filename,
            file_type=file.content_type,
            file_size=len(content),
            storage_path=str(file_path)
        )
        db.add(new_file)
        
        # Update session activity
        session.last_activity = datetime.utcnow()
        
        await db.commit()
        
        # Generate preview and download URLs
        preview_url = f"/api/files/{session_id}/{file.filename}?inline=1"
        download_url = f"/api/files/{session_id}/{file.filename}?download=1"
        
        return {
            "file_id": file_id,
            "filename": file.filename,
            "size": len(content),
            "preview_url": preview_url,
            "download_url": download_url,
            "status": "stored"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/files/{file_id}/download")
async def download_file(
    session_id: str,
    file_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Download a file from a session"""
    try:
        # Get file record
        result = await db.execute(
            select(File).where(
                and_(
                    File.session_id == session_id,
                    File.file_id == file_id
                )
            )
        )
        file_record = result.scalar_one_or_none()
        
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = Path(file_record.storage_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        return FileResponse(
            path=file_path,
            filename=file_record.filename,
            media_type=file_record.file_type or 'application/octet-stream'
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/analysis")
async def save_analysis(
    session_id: str,
    analysis_data: dict,
    message_id: Optional[str] = None,
    db: AsyncSession = Depends(get_session)
):
    """Save analysis results for a session"""
    try:
        # Check session exists
        result = await db.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Create analysis record
        analysis_id = f"analysis_{session_id}_{int(datetime.utcnow().timestamp() * 1000)}"
        new_analysis = AnalysisResult(
            analysis_id=analysis_id,
            session_id=session_id,
            message_id=message_id,
            analysis_data=analysis_data,
            status='complete'
        )
        db.add(new_analysis)
        
        # Update session state
        session.state = 'analysis_complete'
        session.last_activity = datetime.utcnow()
        
        await db.commit()
        
        return {
            "analysis_id": analysis_id,
            "saved": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{session_id}")
async def update_session(
    session_id: str,
    payload: SessionUpdate,
    db: AsyncSession = Depends(get_session)
):
    """Update session information"""
    try:
        # Get session
        result = await db.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update fields
        if payload.name is not None:
            session.name = payload.name
        if payload.state is not None:
            session.state = payload.state
        if payload.metadata is not None:
            session.meta = {**(session.meta or {}), **payload.metadata}
        
        session.last_activity = datetime.utcnow()
        
        await db.commit()
        
        return {
            "session_id": session_id,
            "updated": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Delete a session and all associated data"""
    try:
        # Get session
        result = await db.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Delete session (cascade will handle related records)
        await db.delete(session)
        await db.commit()
        
        # Clean up files from disk
        session_upload_dir = UPLOAD_DIR / session_id
        if session_upload_dir.exists():
            import shutil
            shutil.rmtree(session_upload_dir)
        
        return {
            "session_id": session_id,
            "deleted": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
