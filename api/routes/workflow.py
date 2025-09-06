"""
Workflow API Routes
Handles all n8n workflow interactions through clean REST endpoints
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import logging

from ..database import get_db
from ..services.workflow_service import workflow_service
from ..models import Session as SessionModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow", tags=["workflow"])


# ==================== Request Models ====================

class TriggerWorkflowRequest(BaseModel):
    sessionId: str
    workflowType: str = Field(..., description="Type of workflow: document_ingestion, chat, analysis")
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ApprovalRequest(BaseModel):
    sessionId: str
    action: str = Field(..., pattern="^(approve|reject|modify)$")
    feedback: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None


class ChatMessageRequest(BaseModel):
    sessionId: str
    message: str
    includeContext: bool = True


# ==================== Document Ingestion ====================

@router.post("/ingest/documents")
async def ingest_documents(
    session_id: str,
    files: List[UploadFile] = File(...),
    message: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Upload and process documents through n8n workflow
    Files are streamed directly to n8n without local storage
    """
    try:
        # Validate session exists
        session = await db.get(SessionModel, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Trigger workflow
        result = await workflow_service.trigger_document_ingestion(
            session_id=session_id,
            files=files,
            message=message,
            db=db
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        # Handle wait node if present
        if result.get('resumeUrl'):
            background_tasks.add_task(
                workflow_service.handle_wait_node_response,
                session_id,
                result.get('executionId'),
                {
                    'resumeUrl': result.get('resumeUrl'),
                    'nodeName': 'Document Processing',
                    'waitType': 'approval',
                    'data': result.get('data', {})
                }
            )
        
        return JSONResponse(content={
            "success": True,
            "executionId": result.get('executionId'),
            "message": f"Processing {len(files)} document(s)",
            "hasWaitNode": bool(result.get('resumeUrl'))
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Chat Conversation ====================

@router.post("/chat/message")
async def send_chat_message(
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Send message to chat workflow for AI processing
    """
    try:
        result = await workflow_service.trigger_chat_conversation(
            session_id=request.sessionId,
            message=request.message,
            db=db if request.includeContext else None
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        # Handle wait node if present
        if result.get('resumeUrl'):
            background_tasks.add_task(
                workflow_service.handle_wait_node_response,
                request.sessionId,
                result.get('executionId'),
                {
                    'resumeUrl': result.get('resumeUrl'),
                    'nodeName': 'AI Response Review',
                    'waitType': 'approval',
                    'data': result.get('data', {})
                }
            )
        
        return JSONResponse(content={
            "success": True,
            "executionId": result.get('executionId'),
            "hasWaitNode": bool(result.get('resumeUrl'))
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat message failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Approval Handling ====================

@router.post("/approve")
async def handle_approval(
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle approval/rejection/modification of waiting workflows
    """
    try:
        result = await workflow_service.resume_workflow_with_approval(
            session_id=request.sessionId,
            action=request.action,
            feedback=request.feedback,
            modifications=request.modifications,
            db=db
        )
        
        if not result.get('success'):
            raise HTTPException(
                status_code=400 if 'No resume URL' in result.get('error', '') else 500,
                detail=result.get('error')
            )
        
        return JSONResponse(content={
            "success": True,
            "action": request.action,
            "message": f"Workflow {request.action}ed successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Approval handling failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SSE Event Stream ====================

@router.get("/events/{session_id}")
async def workflow_events(session_id: str):
    """
    Server-Sent Events stream for real-time workflow updates
    """
    try:
        return StreamingResponse(
            workflow_service.create_event_stream(session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
    except Exception as e:
        logger.error(f"Failed to create event stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Workflow Status ====================

@router.get("/status/{session_id}")
async def get_workflow_status(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current workflow status and pending actions
    """
    try:
        redis = await workflow_service.get_redis()
        
        # Get execution info
        execution_key = f"pybog:session:{session_id}:execution"
        execution_info = await redis.hgetall(execution_key)
        
        # Get session state
        state_key = f"pybog:session:{session_id}:state"
        current_state = await redis.hget(state_key, "current") or "idle"
        
        # Check for resume URL
        from ..n8n_resume import get_resume_url
        resume_url = await get_resume_url(session_id)
        
        return JSONResponse(content={
            "sessionId": session_id,
            "state": current_state,
            "hasActiveWorkflow": bool(execution_info),
            "executionId": execution_info.get('executionId'),
            "workflowId": execution_info.get('workflowId'),
            "startedAt": execution_info.get('startedAt'),
            "requiresAction": bool(resume_url),
            "canResume": bool(resume_url)
        })
        
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Webhook Proxy ====================

@router.post("/webhook/{webhook_path:path}")
async def proxy_webhook(
    webhook_path: str,
    background_tasks: BackgroundTasks
):
    """
    Proxy webhook calls to n8n with proper handling
    This allows frontend to call n8n webhooks through our API
    """
    try:
        # This would be expanded to handle specific webhook types
        # For now, it's a placeholder for future webhook proxying
        return JSONResponse(content={
            "success": True,
            "message": f"Webhook {webhook_path} received"
        })
    except Exception as e:
        logger.error(f"Webhook proxy failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Analysis Workflow ====================

@router.post("/analyze")
async def trigger_analysis(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Trigger comprehensive analysis workflow for session
    """
    try:
        # Get session context
        session = await db.get(SessionModel, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Trigger analysis workflow (would be expanded)
        result = await workflow_service.trigger_chat_conversation(
            session_id=session_id,
            message="Please analyze the uploaded documents and provide HVAC component extraction",
            db=db
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        return JSONResponse(content={
            "success": True,
            "executionId": result.get('executionId'),
            "message": "Analysis workflow started"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== BOG Generation ====================

@router.post("/generate-bog")
async def generate_bog(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger BOG generation after analysis approval
    """
    try:
        # This would connect to the BOG generation workflow
        # For now, approve the current workflow to proceed
        result = await workflow_service.resume_workflow_with_approval(
            session_id=session_id,
            action="approve",
            feedback="Generate BOG file",
            db=db
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        return JSONResponse(content={
            "success": True,
            "message": "BOG generation initiated"
        })
        
    except Exception as e:
        logger.error(f"BOG generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
