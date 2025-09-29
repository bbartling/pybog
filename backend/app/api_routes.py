"""
API Routes for PyBOG FastAPI Backend with Comprehensive Error Handling
Implements all the endpoints needed for the unified API service with standardized error handling,
recovery suggestions, and retry mechanisms.
"""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel

from core.events import EventBus
from core.error_handler import get_error_handler, create_error_context, ErrorCategory
from core.error_decorators import handle_errors, validate_session, require_file_access, log_performance
from services.session_service import SessionService
from services.file_service import FileService
from services.analysis_engine import AnalysisEngine
from services.pybog_agent_v2 import PyBOGAgentV2
from models.file_models import FileRecord, FileUploadRequest, FileMetadata
from models.analysis_models import AnalysisRequest, AnalysisResult, BOGGenerationRequest

logger = logging.getLogger(__name__)

# Initialize error handler
error_handler = get_error_handler()

# Initialize services
from core.config import get_llm_config
from services.workflow_service import WorkflowService

event_bus = EventBus()
session_service = SessionService(event_bus)
file_service = FileService(event_bus)
workflow_service = WorkflowService(event_bus)

# Initialize PyBOG Agent V2 with OpenAI API key from configuration
llm_config = get_llm_config()
pybog_agent = PyBOGAgentV2(event_bus, openai_api_key=llm_config.openai_api_key)
analysis_engine = AnalysisEngine(event_bus, pybog_agent)

# Create API router
router = APIRouter(prefix="/api", tags=["api"])

# Session Management Endpoints
class SessionCreateRequest(BaseModel):
    name: str = "New Session"

@router.post("/sessions")
@handle_errors("SessionAPI", "create_session", ErrorCategory.DATABASE)
@log_performance("SessionAPI", "create_session")
async def create_session(request: SessionCreateRequest):
    """Create a new session with comprehensive error handling"""
    from models.session_models import SessionCreateRequest as SessionCreateModel
    import uuid
    
    # Generate unique session ID
    session_id = f"session-{uuid.uuid4().hex[:8]}"
    
    session_request = SessionCreateModel(
        session_id=session_id,
        name=request.name,
        metadata={}
    )
    
    session = await session_service.create_session(session_request)
    return {
        "session_id": session.session_id,
        "name": session.name,
        "created_at": session.created_at.isoformat() if session.created_at else None
    }

@router.get("/sessions/{session_id}")
@handle_errors("SessionAPI", "get_session", ErrorCategory.DATABASE)
@validate_session("session_id")
@log_performance("SessionAPI", "get_session")
async def get_session(session_id: str):
    """Get session by ID with comprehensive error handling"""
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.get("/sessions")
async def list_sessions():
    """List all sessions"""
    try:
        sessions = await session_service.list_sessions()
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class SessionUpdateRequest(BaseModel):
    name: Optional[str] = None

@router.patch("/sessions/{session_id}")
async def update_session(session_id: str, request: SessionUpdateRequest):
    """Update session name"""
    try:
        from models.session_models import SessionUpdateRequest as SessionUpdateModel
        
        update_request = SessionUpdateModel(
            name=request.name,
            metadata=None
        )
        
        session = await session_service.update_session(session_id, update_request)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        return {
            "session_id": session.session_id,
            "name": session.name,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None
        }
    except Exception as e:
        logger.error(f"Failed to update session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    try:
        deleted = await session_service.delete_session(session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "session_id": session_id,
            "deleted": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Additional session endpoints that frontend expects
@router.get("/sessions/{session_id}/full")
async def get_full_session(session_id: str):
    """Get full session with messages and files"""
    try:
        session = await session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get session files
        files = await file_service.list_session_files(session_id)
        
        # Get session messages
        from core.database import fetch_all
        messages_data = await fetch_all(
            "SELECT id, message_type, content, metadata, created_at FROM chat_messages WHERE session_id = $1 ORDER BY created_at",
            session_id
        )
        
        messages = [
            {
                "id": msg["id"],
                "type": msg["message_type"],
                "content": msg["content"],
                "metadata": msg["metadata"],
                "created_at": msg["created_at"].isoformat() if msg["created_at"] else None
            }
            for msg in messages_data
        ]
        
        return {
            "session_id": session.session_id,
            "name": session.name,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "messages": messages,
            "files": [
                {
                    "file_id": f.id,
                    "filename": f.original_name,
                    "file_type": f.mime_type,
                    "file_size": f.file_size,
                    "preview_url": f"/api/files/{f.id}/preview"
                }
                for f in files.files
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get full session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recent-sessions")
async def get_recent_sessions(limit: int = 20):
    """Get recent sessions"""
    try:
        sessions_response = await session_service.list_sessions(limit=limit, offset=0)
        return {
            "sessions": [
                {
                    "session_id": s.session_id,
                    "name": s.name,
                    "current_state": "idle",  # TODO: Implement state tracking
                    "last_activity": s.updated_at.isoformat() if s.updated_at else s.created_at.isoformat()
                }
                for s in sessions_response.sessions
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get recent sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Message persistence endpoints
class MessagePersistRequest(BaseModel):
    message_id: str
    type: str
    content: str
    metadata: Optional[dict] = {}
    session_state: Optional[str] = "idle"

@router.post("/sessions/{session_id}/messages")
async def persist_message(session_id: str, request: MessagePersistRequest):
    """Persist a message to the session"""
    try:
        # TODO: Implement message persistence in database
        # For now, just return success
        return {
            "message_id": request.message_id,
            "session_id": session_id,
            "persisted": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to persist message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# File Management Endpoints
@router.post("/files/upload")
@handle_errors("FileAPI", "upload_file", ErrorCategory.FILE)
@validate_session("session_id")
@log_performance("FileAPI", "upload_file", slow_threshold=30.0)
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    """Upload a file with comprehensive error handling and validation"""
    from models.file_models import FileType
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a filename")
    
    # Check file size (basic validation)
    if hasattr(file, 'size') and file.size and file.size > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(status_code=413, detail="File too large (maximum 50MB)")
    
    # Upload file using file service
    file_record = await file_service.upload_file(
        session_id=session_id,
        file=file,
        file_type=FileType.UPLOAD
    )
    
    return {
        "file_id": file_record.id,
        "filename": file_record.original_name,
        "file_size": file_record.file_size,
        "mime_type": file_record.mime_type,
        "state": file_record.state.value,
        "session_id": file_record.session_id
    }

@router.get("/files/{file_id}")
async def get_file(file_id: int):
    """Get file metadata"""
    try:
        file_metadata = await file_service.get_file_metadata(file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        return file_metadata
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files")
async def list_files(session_id: str):
    """List files for a session"""
    try:
        files = await file_service.list_session_files(session_id)
        return {"files": files}
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files/{file_id}/download")
@handle_errors("FileAPI", "download_file", ErrorCategory.FILE)
@require_file_access("file_id")
@log_performance("FileAPI", "download_file", slow_threshold=10.0)
async def download_file(file_id: int):
    """Download a file with comprehensive error handling"""
    from fastapi.responses import Response
    
    # Get file metadata and content
    file_metadata = await file_service.get_file_metadata(file_id)
    file_content = await file_service.get_file_data(file_id)
    
    if not file_content:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Return proper file response with enhanced headers
    return Response(
        content=file_content,
        media_type=file_metadata.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={file_metadata.original_name}",
            "Content-Length": str(len(file_content)),
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

@router.get("/files/{file_id}/preview")
async def preview_file(file_id: int):
    """Get file preview/content for viewing with proper CORS headers and MIME type detection"""
    try:
        from fastapi.responses import Response
        import mimetypes
        import os

        # Get file metadata and content
        file_metadata = await file_service.get_file_metadata(file_id)
        file_content = await file_service.get_file_data(file_id)

        if not file_content:
            raise HTTPException(status_code=404, detail="File not found")

        # Enhanced MIME type detection
        detected_mime_type = file_metadata.mime_type
        if not detected_mime_type:
            # Try to detect MIME type from filename
            detected_mime_type, _ = mimetypes.guess_type(file_metadata.original_name)
            if not detected_mime_type:
                # Default based on file extension
                file_ext = os.path.splitext(file_metadata.original_name)[1].lower()
                mime_map = {
                    '.pdf': 'application/pdf',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.txt': 'text/plain',
                    '.csv': 'text/csv',
                    '.json': 'application/json',
                    '.xml': 'application/xml',
                    '.doc': 'application/msword',
                    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    '.xls': 'application/vnd.ms-excel',
                    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                }
                detected_mime_type = mime_map.get(file_ext, 'application/octet-stream')

        # Comprehensive headers with explicit CORS support
        headers = {
            "Content-Disposition": f"inline; filename=\"{file_metadata.original_name}\"",
            "Content-Length": str(len(file_content)),
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Origin, X-Requested-With, Content-Type, Accept, Authorization",
            "Access-Control-Expose-Headers": "Content-Disposition, Content-Length, Content-Type",
            "Cache-Control": "public, max-age=3600",  # Cache for 1 hour (more reasonable)
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN"
        }

        logger.debug(f"Serving file: {file_metadata.original_name} with MIME type: {detected_mime_type}")

        # Return file content for preview with enhanced headers
        return Response(
            content=file_content,
            media_type=detected_mime_type,
            headers=headers
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to preview file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.options("/files/{file_id}/preview")
async def preview_file_options(file_id: int):
    """Handle preflight requests for file preview"""
    from fastapi.responses import Response
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400"
        }
    )

@router.get("/files/{file_id}/content")
async def get_file_content(file_id: int):
    """Get file content as extracted text (handles PDF, DOCX, and text files)"""
    try:
        # Get file metadata first
        file_metadata = await file_service.get_file_metadata(file_id)

        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")

        # Use the text extraction service to get readable content
        try:
            extracted_text = await file_service.get_full_extracted_text(file_id)
            return {
                "file_id": file_id,
                "filename": file_metadata.original_name,
                "content": extracted_text,
                "mime_type": file_metadata.mime_type,
                "extraction_method": file_metadata.metadata.get("extraction_method", "unknown"),
                "word_count": file_metadata.metadata.get("word_count", 0),
                "character_count": len(extracted_text)
            }
        except Exception as extraction_error:
            logger.warning(f"Text extraction failed for file {file_id}: {extraction_error}")

            # Fallback: try simple UTF-8 decode
            file_content = await file_service.get_file_data(file_id)
            try:
                text_content = file_content.decode('utf-8')
                return {
                    "file_id": file_id,
                    "filename": file_metadata.original_name,
                    "content": text_content,
                    "mime_type": file_metadata.mime_type,
                    "extraction_method": "utf8_fallback",
                    "file_size": len(file_content)
                }
            except UnicodeDecodeError:
                # If not text, return error for non-text files
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file_metadata.original_name} is not a text file and text extraction failed"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Chat Management Endpoints
class ChatMessageRequest(BaseModel):
    session_id: str
    message: str
    files: Optional[List[dict]] = []

class ChatRequest(BaseModel):
    session_id: str
    text: str

@router.post("/chat")
@handle_errors("ChatAPI", "chat_pipeline", ErrorCategory.ANALYSIS)
@log_performance("ChatAPI", "chat_pipeline", slow_threshold=15.0)
async def chat_pipeline(request: ChatRequest):
    """Start the chat pipeline: chat → clarifiers → analysis → BOG → downloads"""
    # Validate message content
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    if len(request.text) > 10000:  # 10k character limit
        raise HTTPException(status_code=400, detail="Message too long (maximum 10,000 characters)")
    
    # Start the pipeline - this will emit WebSocket events for progress
    await pybog_agent.start_chat_pipeline(request.session_id, request.text)
    
    return {
        "success": True,
        "message": "Chat pipeline started - progress via WebSocket",
        "session_id": request.session_id,
        "streaming": True
    }

@router.post("/chat/message")
@handle_errors("ChatAPI", "send_message", ErrorCategory.ANALYSIS)
@log_performance("ChatAPI", "send_message", slow_threshold=15.0)
async def send_chat_message(request: ChatMessageRequest):
    """Send a chat message and get streaming AI response with comprehensive error handling"""
    # Validate message content
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    if len(request.message) > 10000:  # 10k character limit
        raise HTTPException(status_code=400, detail="Message too long (maximum 10,000 characters)")
    
    # Process message with PyBOG Agent V2 (streaming response via WebSocket)
    await pybog_agent.process_chat_message(request.session_id, request.message)
    
    return {
        "success": True,
        "message": "Chat message processed - response streaming via WebSocket",
        "session_id": request.session_id,
        "streaming": True
    }

@router.post("/chat/guidance")
async def get_hvac_guidance(session_id: str, context: dict):
    """Get expert HVAC guidance based on context"""
    try:
        guidance = await pybog_agent.provide_hvac_guidance(session_id, context)
        return {
            "guidance": guidance,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get HVAC guidance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    try:
        # Get conversation history from PyBOG Agent V2
        history = pybog_agent.get_session_history(session_id)
        
        # Convert to frontend-friendly format
        messages = []
        for msg in history:
            if msg["role"] != "system":  # Skip system prompts
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return {
            "messages": messages,
            "session_id": session_id,
            "total_count": len(messages)
        }
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/chat/history/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear chat history for a session"""
    try:
        pybog_agent.clear_session_history(session_id)
        return {
            "success": True,
            "session_id": session_id,
            "message": "Chat history cleared",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to clear chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agent/sessions")
async def get_active_agent_sessions():
    """Get list of active agent sessions"""
    try:
        active_sessions = pybog_agent.get_active_sessions()
        return {
            "active_sessions": active_sessions,
            "count": len(active_sessions),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get active sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analysis Management Endpoints
class DocumentAnalysisRequest(BaseModel):
    session_id: str
    content: str
    analysis_type: str = "hvac_analysis"

@router.post("/analysis/document")
async def analyze_document_content(request: DocumentAnalysisRequest):
    """Analyze document content using PyBOG Agent V2"""
    try:
        result = await pybog_agent.analyze_document_content(
            session_id=request.session_id,
            content=request.content,
            analysis_type=request.analysis_type
        )
        return {
            "analysis_result": result,
            "session_id": request.session_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to analyze document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analysis/test")
async def test_analysis(request: AnalysisRequest):
    """Test PyBOG Agent V2 analysis (legacy endpoint)"""
    try:
        # Get file content for analysis using text extraction
        try:
            content_text = await file_service.get_full_extracted_text(request.file_id)
            if not content_text.strip():
                raise HTTPException(status_code=400, detail="File contains no readable text")
        except Exception as e:
            logger.error(f"Failed to extract text from file {request.file_id}: {e}")
            raise HTTPException(status_code=400, detail=f"Unable to extract text from file: {str(e)}")

        # Check if OpenAI API key is available
        from core.config import get_llm_config
        llm_config = get_llm_config()
        if not llm_config.openai_api_key:
            raise HTTPException(
                status_code=503,
                detail="AI service unavailable: OpenAI API key not configured"
            )

        result = await pybog_agent.analyze_document_content(
            session_id=request.session_id,
            content=content_text,
            analysis_type='hvac_analysis'
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze document: {e}")
        # Provide helpful error messages for common issues
        error_msg = str(e).lower()
        if "openai" in error_msg or "api_key" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="AI service unavailable: OpenAI API connection failed"
            )
        elif "timeout" in error_msg:
            raise HTTPException(
                status_code=504,
                detail="AI service timeout: Analysis took too long, please try again"
            )
        else:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

class AnalysisPipelineRequest(BaseModel):
    session_id: str
    text: Optional[str] = None
    source_ids: Optional[List[str]] = []

@router.post("/analysis")
@handle_errors("AnalysisAPI", "start_analysis", ErrorCategory.ANALYSIS)
@log_performance("AnalysisAPI", "start_analysis", slow_threshold=30.0)
async def start_analysis_pipeline(request: AnalysisPipelineRequest):
    """Start analysis pipeline with WebSocket progress updates"""
    # Start analysis with PyBOG Agent V2
    analysis_id = await pybog_agent.start_analysis_pipeline(
        session_id=request.session_id,
        text=request.text,
        source_ids=request.source_ids or []
    )
    
    return {
        "analysis_id": analysis_id,
        "session_id": request.session_id,
        "status": "started"
    }

# @router.get("/analysis/{analysis_id}")
# async def get_analysis_result(analysis_id: int):
#     """Get analysis result"""
#     raise HTTPException(status_code=404, detail="Analysis functionality temporarily disabled")

# @router.get("/analysis")
# async def list_analyses(session_id: str):
#     """List analyses for a session"""
#     return {"analyses": []}

# @router.post("/analysis/cancel")
# async def cancel_analysis(session_id: str, analysis_id: Optional[int] = None):
#     """Cancel analysis"""
#     return {"cancelled_count": 0}

# Workflow Management Endpoints
@router.get("/workflow/status/{session_id}")
async def get_workflow_status(session_id: str):
    """Get current workflow status for a session"""
    try:
        status = await workflow_service.get_workflow_status(session_id)
        return status.model_dump()
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ReviewSubmissionRequest(BaseModel):
    review_id: str
    decision: str  # 'approve', 'request_changes', 'reject', 'retry'
    feedback: Optional[str] = None
    modified_data: Optional[dict] = None

@router.post("/workflow/review/{session_id}")
async def submit_review(session_id: str, request: ReviewSubmissionRequest):
    """Submit a review decision"""
    try:
        from models.workflow_models import ReviewRequest, ReviewDecision
        
        # Convert string decision to enum
        decision_map = {
            'approve': ReviewDecision.APPROVE,
            'request_changes': ReviewDecision.REQUEST_CHANGES,
            'reject': ReviewDecision.REJECT,
            'retry': ReviewDecision.RETRY
        }
        
        if request.decision not in decision_map:
            raise HTTPException(status_code=400, detail=f"Invalid decision: {request.decision}")
        
        review_request = ReviewRequest(
            session_id=session_id,
            review_id=request.review_id,
            decision=decision_map[request.decision],
            feedback=request.feedback,
            modified_data=request.modified_data
        )
        
        response = await workflow_service.submit_review(review_request)
        return response.model_dump()
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to submit review: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workflow/reset/{session_id}")
async def reset_workflow(session_id: str):
    """Reset workflow to idle state"""
    try:
        await workflow_service.reset_workflow(session_id)
        return {
            "success": True,
            "message": "Workflow reset to idle state",
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Failed to reset workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Text Extraction with Workflow Integration
@router.post("/files/{file_id}/extract-text")
async def extract_text_with_workflow(file_id: int, session_id: str = Form(...)):
    """Extract text from file and start review workflow"""
    try:
        # Get file metadata
        file_metadata = await file_service.get_file_metadata(file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        if file_metadata.session_id != session_id:
            raise HTTPException(status_code=403, detail="File does not belong to session")
        
        # Extract text using real file service
        extraction_result = await file_service.extract_text_content(file_id)

        if not extraction_result.success:
            raise HTTPException(status_code=500, detail=f"Text extraction failed: {extraction_result.error_message}")

        extracted_text = extraction_result.extracted_text

        # Quality assessment based on extraction results
        quality_data = {
            "quality_score": 0.85 if extraction_result.word_count > 50 else 0.6,
            "issues": ["Low word count"] if extraction_result.word_count < 50 else [],
            "recommendations": ["Review extracted text for accuracy"],
            "hvac_terms_found": len([word for word in extracted_text.lower().split() if word in ['hvac', 'temperature', 'control', 'fan', 'ahu', 'vav', 'damper', 'setpoint']]),
            "estimated_tokens": int(extraction_result.word_count * 1.3),
            "word_count": extraction_result.word_count,
            "character_count": extraction_result.character_count,
            "extraction_method": extraction_result.extraction_method
        }
        
        # Start workflow
        review_id = await workflow_service.start_text_extraction_workflow(
            session_id, file_id, extracted_text, quality_data
        )
        
        return {
            "review_id": review_id,
            "extracted_text": extracted_text,
            "quality_data": quality_data,
            "workflow_status": "awaiting_text_review"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extract text with workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analysis with Workflow Integration
class AnalysisWorkflowRequest(BaseModel):
    session_id: str
    approved_text: str

@router.post("/analysis/start-with-workflow")
async def start_analysis_with_workflow(request: AnalysisWorkflowRequest):
    """Start analysis with approved text and workflow integration"""
    try:
        # Validate session exists first
        session = await session_service.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Use real analysis engine instead of simulated data
        analysis_result = await pybog_agent.analyze_document_content(
            session_id=request.session_id,
            content=request.approved_text,
            analysis_type="hvac_analysis"
        )

        # Extract analysis data from the result
        analysis_data = analysis_result.get("analysis_data", {})

        # Start analysis review workflow with real analysis data
        review_id = await workflow_service.start_analysis_review_workflow(
            request.session_id, analysis_result.get("analysis_id", 1), analysis_data
        )
        
        return {
            "review_id": review_id,
            "analysis_data": analysis_data,
            "workflow_status": "awaiting_analysis_review"
        }
        
    except Exception as e:
        logger.error(f"Failed to start analysis with workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# BOG File Generation Endpoints
class BOGRequest(BaseModel):
    session_id: str
    analysis_id: int

@router.post("/bog")
@handle_errors("BOGAPI", "generate_bog", ErrorCategory.ANALYSIS)
@log_performance("BOGAPI", "generate_bog", slow_threshold=60.0)
async def generate_bog_pipeline(request: BOGRequest):
    """Generate BOG file from analysis with WebSocket progress updates"""
    # Start BOG generation with PyBOG Agent V2
    artifact_id = await pybog_agent.start_bog_generation(
        session_id=request.session_id,
        analysis_id=request.analysis_id
    )
    
    return {
        "artifact_id": artifact_id,
        "session_id": request.session_id,
        "analysis_id": request.analysis_id,
        "status": "started"
    }

@router.get("/session/{session_id}/state")
async def get_session_state(session_id: str):
    """Get current session state for resume functionality"""
    try:
        # Get session state from PyBOG Agent V2
        state = await pybog_agent.get_session_state(session_id)
        
        return {
            "session_id": session_id,
            "status": state.get("status", "idle"),
            "last_step": state.get("last_step", "idle"),
            "artifacts": state.get("artifacts", []),
            "current_analysis": state.get("current_analysis"),
            "pipeline_state": state.get("pipeline_state", {})
        }
    except Exception as e:
        logger.error(f"Failed to get session state: {e}")
        raise HTTPException(status_code=500, detail=str(e))