"""
Workflow API Routes
Handles all n8n workflow interactions through clean REST endpoints
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks, Form, Request
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import logging
import json

from ..database import get_session as get_db, get_raw_connection
from ..services.workflow_service import workflow_service
from ..models import Session as SessionModel
import asyncpg
import os
import httpx
from pathlib import Path

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
    action: str  # allow any string; n8n waits expect approve_text, approve_analysis, confirm, regenerate, cancel, etc.
    feedback: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None
    approvedText: Optional[str] = None
    extractedText: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    userAction: Optional[str] = None


class ChatMessageRequest(BaseModel):
    sessionId: str
    message: str
    includeContext: bool = True


# ==================== Document Ingestion ====================

@router.post("/ingest/documents")
async def ingest_documents(
    session_id: str = Form(...),
    files: List[UploadFile] = File(...),
    message: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Upload and process documents through n8n workflow (Analysis - Workflow)
    Files are streamed to n8n; if a Wait node responds with resumeUrl, we normalize the payload.
    """
    try:
        # Validate session exists
        result_check = await db.get(SessionModel, session_id)
        if result_check is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Trigger workflow via service (with DB context for persistence)
        result = await workflow_service.trigger_document_ingestion(
            session_id=session_id,
            files=files,
            message=message,
            db=db
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        data = result.get('data') or {}
        resume_url = result.get('resumeUrl') or data.get('resumeUrl')

        # Return normalized payload for frontend approval handling
        payload = {
            "success": True,
            "sessionId": data.get('sessionId') or session_id,
            "status": data.get('status') or ("text_extracted" if resume_url and (data.get('extractedText') or data.get('fullText')) else data.get('status')),
            "step": data.get('step') or ("text_review" if resume_url and (data.get('extractedText') or data.get('fullText')) else data.get('step')),
            "message": data.get('message') or f"Processing {len(files)} document(s)",
            "resumeUrl": resume_url,
            "extractedText": data.get('extractedText'),
            "textQuality": data.get('textQuality'),
            "qualityScore": data.get('qualityScore'),
            "qualityIssues": data.get('qualityIssues'),
            "recommendations": data.get('recommendations'),
            "hvacTermsFound": data.get('hvacTermsFound'),
            "analysis": data.get('analysis'),
            "summary": data.get('summary'),
        }
        
        return JSONResponse(content=payload)
        
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
            approved_text=request.approvedText or request.extractedText,
            analysis=request.analysis,
            user_action=request.userAction,
            db=db
        )
        
        if not result.get('success'):
            raise HTTPException(
                status_code=400 if 'No resume URL' in result.get('error', '') else 500,
                detail=result.get('error')
            )
        
        # Normalize downstream body from n8n resume response if present
        body = result.get('body') or {}
        payload = {
            "success": True,
            "action": request.action,
            "message": body.get('message') or f"Workflow {request.action}ed successfully",
        }
        # Surface useful fields back to frontend for chaining
        for key in ("resumeUrl", "status", "step", "downloadUrl", "bogFilePath", "analysis", "summary"):
            if key in body:
                payload[key] = body[key]
        return JSONResponse(content=payload)
        
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

class ReplayFilesRequest(BaseModel):
    session_id: str
    source_message_id: Optional[str] = None
    message: Optional[str] = None

@router.post("/replay-files")
async def replay_files(request: ReplayFilesRequest):
    """
    Re-stream persisted files for a session into the Analysis workflow.
    This is used when retrying after a refresh where browser File objects are gone.
    """
    try:
        # Idempotency lock to prevent duplicate n8n executions per session (short TTL)
        try:
            redis = await workflow_service.get_redis()
            lock_key = f"pybog:session:{request.session_id}:replay_lock"
            # SET NX EX 20 (20s window)
            locked = await redis.set(lock_key, "1", ex=20, nx=True)
            if not locked:
                return JSONResponse(status_code=202, content={
                    "success": True,
                    "message": "Replay already in progress for this session",
                })
        except Exception:
            pass

        # Fetch files for the session from legacy session_files table
        # (We choose session_files because upload writes here reliably.)
        DB_URL = os.getenv('DATABASE_URL', 'postgresql://pybog:pybog123@postgres:5432/pybog')
        conn = await asyncpg.connect(DB_URL)
        try:
            rows = await conn.fetch(
                """
                SELECT filename, mime_type, path
                FROM session_files
                WHERE session_id = $1
                ORDER BY uploaded_at ASC
                """,
                request.session_id,
            )
        finally:
            await conn.close()

        if not rows:
            # Fallback to unified ORM-backed files table
            DB_URL = os.getenv('DATABASE_URL', 'postgresql://pybog:pybog123@postgres:5432/pybog')
            conn2 = await asyncpg.connect(DB_URL)
            try:
                rows2 = await conn2.fetch(
                    """
                    SELECT filename, file_type AS mime_type, storage_path AS path
                    FROM files
                    WHERE session_id = $1
                    ORDER BY upload_time ASC
                    """,
                    request.session_id,
                )
            finally:
                await conn2.close()
            rows = rows2

        if not rows:
            raise HTTPException(status_code=404, detail="No stored files for this session")

        # Prepare multipart files for n8n webhook (use repeated 'files' field to satisfy binaryPropertyName="files")
        files_list = []
        for r in rows:
            fpath = Path(r['path']) if r.get('path') else None
            if not fpath or not fpath.exists():
                # fallback path
                fpath = Path(os.getcwd()) / 'data' / 'uploads' / request.session_id / r['filename']
            if not fpath.exists():
                continue
            content = fpath.read_bytes()
            files_list.append(('files', (r['filename'], content, r.get('mime_type') or 'application/octet-stream')))

        if not files_list:
            raise HTTPException(status_code=404, detail="Stored files not found on disk")

        # Mirror workflow_service.trigger_document_ingestion behavior
        n8n_url = os.getenv('N8N_URL', 'http://localhost:5678')
        analyze_path = os.getenv('N8N_ANALYZE_WEBHOOK_PATH', '/webhook/pybog-analyze').lstrip('/')
        webhook_url = f"{n8n_url.rstrip('/')}/{analyze_path}"
        data = {
            'sessionId': request.session_id,
            'message': (request.message or f"Replaying {len(files_list)} document(s)"),
            'metadata': json.dumps({
                'fileCount': len(files_list),
                'replay': True,
            })
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(webhook_url, files=files_list, data=data)
            if not (200 <= resp.status_code < 300):
                raise HTTPException(status_code=502, detail=f"Replay failed: {resp.status_code} {resp.text}")
            raw = resp.json()

        # Normalize response similar to ingest_documents
        first_json = None
        if isinstance(raw, list) and raw:
            try:
                first_json = raw[0].get('json') if isinstance(raw[0], dict) else None
            except Exception:
                first_json = None
        if not first_json and isinstance(raw, dict):
            first_json = raw.get('data') or raw

        resume_url = first_json.get('resumeUrl') if isinstance(first_json, dict) else None
        has_text = False
        if isinstance(first_json, dict):
            has_text = bool(first_json.get('extractedText') or first_json.get('fullText'))
        computed_status = None
        computed_step = None
        if resume_url and has_text:
            computed_status = 'text_extracted'
            computed_step = 'text_review'
        
        payload = {
            "success": True,
            "sessionId": request.session_id,
            "status": computed_status or (first_json.get('status') if isinstance(first_json, dict) else None),
            "step": computed_step or (first_json.get('step') if isinstance(first_json, dict) else None),
            "message": (first_json.get('message') if isinstance(first_json, dict) else None) or f"Replayed {len(files_list)} document(s)",
            "resumeUrl": resume_url,
            "requiresApproval": bool(resume_url),
            "extractedText": first_json.get('extractedText') if isinstance(first_json, dict) else None,
            "fullText": first_json.get('fullText') if isinstance(first_json, dict) else None,
            "textQuality": first_json.get('quality') if isinstance(first_json, dict) else None,
            "qualityScore": first_json.get('confidence') if isinstance(first_json, dict) else None,
            "qualityIssues": first_json.get('issues') if isinstance(first_json, dict) else None,
            "recommendations": first_json.get('recommendations') if isinstance(first_json, dict) else None,
            "hvacTermsFound": first_json.get('hvacTermsFound') if isinstance(first_json, dict) else None,
            "analysis": first_json.get('analysis') if isinstance(first_json, dict) else None,
            "summary": first_json.get('summary') if isinstance(first_json, dict) else None,
        }

        # Persist resume URL for UI approval if present
        if resume_url:
            try:
                from ..n8n_resume import store_resume_url
                await store_resume_url(request.session_id, resume_url)
            except Exception:
                pass

        return JSONResponse(content=payload)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Replay files failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

# Ingress for external workflow events (e.g., from n8n HTTP Request nodes)
class WorkflowEventIn(BaseModel):
    sessionId: str
    type: str
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    downloadUrl: Optional[str] = None

@router.post("/event")
async def ingest_workflow_event(event: WorkflowEventIn):
    try:
        await workflow_service._stream_workflow_event(event.sessionId, {
            'type': event.type,
            'message': event.message,
            'data': event.data,
            'downloadUrl': event.downloadUrl
        })
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to ingest workflow event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.api_route("/webhook/{webhook_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_webhook(
    webhook_path: str,
    request: Request,
):
    """
    Reverse proxy for n8n webhooks.
    - Preserves method, query string, and body (including multipart uploads)
    - Forwards most headers except hop-by-hop ones
    - Streams response back to the client
    """
    try:
        n8n_base = os.getenv("N8N_URL", "http://localhost:5678").rstrip("/")
        # Ensure we forward to /webhook/<path>, without double "webhook"
        normalized_path = webhook_path.lstrip("/")
        if not normalized_path.startswith("webhook/"):
            normalized_path = f"webhook/{normalized_path}"
        target_url = f"{n8n_base}/{normalized_path}"
        if request.url.query:
            target_url = f"{target_url}?{request.url.query}"

        # Prepare headers: drop hop-by-hop and auto-calculated ones
        excluded_headers = {
            "host", "content-length", "transfer-encoding", "connection", "accept-encoding", "keep-alive"
        }
        forward_headers = {k: v for k, v in request.headers.items() if k.lower() not in excluded_headers}

        body = await request.body()

        timeout = httpx.Timeout(120.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream_resp = await client.request(
                request.method,
                target_url,
                headers=forward_headers,
                content=body if body else None,
            )

        # Build downstream response (read into memory to avoid StreamConsumed errors)
        excluded_resp_headers = {"transfer-encoding", "connection", "content-length"}
        resp_headers = {
            k: v for k, v in upstream_resp.headers.items() if k.lower() not in excluded_resp_headers
        }

        logger.info(
            f"[WebhookProxy] {request.method} /api/workflow/webhook/{webhook_path} -> {upstream_resp.status_code}"
        )

        # Ensure content is fully read once, then return a stable Response body
        content_type = upstream_resp.headers.get("content-type")
        try:
            await upstream_resp.aread()
        except Exception:
            pass
        content_bytes = upstream_resp.content or b""

        from fastapi import Response
        return Response(
            content=content_bytes,
            status_code=upstream_resp.status_code,
            headers=resp_headers,
            media_type=content_type
        )

    except httpx.RequestError as e:
        logger.error(f"Webhook proxy upstream error: {e}")
        raise HTTPException(status_code=502, detail="Failed to reach n8n webhook endpoint")
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
