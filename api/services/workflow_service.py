"""
Comprehensive Workflow Service for N8N Integration
Handles webhooks, wait nodes, SSE streaming, and data persistence
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import httpx
from redis import asyncio as aioredis
import os

from ..models import Session, Message, File, AnalysisResult, BOGFile
from ..n8n_resume import (
    store_resume_url, 
    get_resume_url, 
    append_message,
    resume_workflow as resume_n8n_workflow
)

logger = logging.getLogger(__name__)


class WorkflowService:
    """
    Unified service for managing n8n workflow interactions
    """
    
    def __init__(self, n8n_url: str = None, redis_url: str = "redis://redis:6379/0"):
        # Allow N8N_URL env override; default to localhost for dev
        self.n8n_url = (n8n_url or os.getenv("N8N_URL", "http://localhost:5678")).rstrip("/")
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None
        
    async def get_redis(self) -> aioredis.Redis:
        """Get or create Redis connection"""
        if not self._redis:
            self._redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        return self._redis
        
    # ==================== Workflow Triggering ====================
    
    async def trigger_document_ingestion(
        self, 
        session_id: str,
        files: List[UploadFile],
        message: str = "",
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Trigger document ingestion workflow with proper file streaming
        """
        try:
            # Prepare multipart form data
            form_files = []
            for _, file in enumerate(files):
                file_content = await file.read()
                await file.seek(0)  # Reset for potential reuse
                # Use repeated 'files' field so n8n Webhook binaryPropertyName="files" receives them
                form_files.append(
                    ('files', (file.filename, file_content, file.content_type or 'application/octet-stream'))
                )
            
            # Prepare session context
            session_context = await self._get_session_context(session_id, db)
            
            data = {
                'sessionId': session_id,
                'message': message or f"Processing {len(files)} document(s)",
                'conversationHistory': json.dumps(session_context.get('messages', [])),
                'metadata': json.dumps({
                    'fileCount': len(files),
                    'timestamp': datetime.utcnow().isoformat(),
                    'sessionState': session_context.get('state', 'processing')
                })
            }
            
            # Call n8n webhook (align with active Analysis workflow)
            analyze_path = os.getenv('N8N_ANALYZE_WEBHOOK_PATH', '/webhook/pybog-analyze').lstrip('/')
            analyze_full = os.getenv('N8N_ANALYZE_WEBHOOK')
            webhook_url = analyze_full or f"{self.n8n_url}/{analyze_path}"
            logger.info(f"Triggering analyze webhook: {webhook_url}")
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    webhook_url,
                    files=form_files,
                    data=data
                )
                
                if response.status_code >= 200 and response.status_code < 300:
                    try:
                        raw_result = response.json()
                    except Exception:
                        # Fallback: wrap plain text into JSON structure
                        text_body = response.text or ''
                        raw_result = { 'data': { 'message': text_body, 'status': 'chat_ready' if text_body else 'ok' } }

                    # Respond to Webhook may return "allIncomingItems" (array of items)
                    # Normalize to a single JSON object for the frontend
                    first_json = None
                    if isinstance(raw_result, list) and raw_result:
                        try:
                            first_json = raw_result[0].get('json') if isinstance(raw_result[0], dict) else None
                        except Exception:
                            first_json = None
                    if not first_json and isinstance(raw_result, dict):
                        first_json = raw_result.get('data') or raw_result

                    normalized = {
                        'sessionId': session_id,
                        'status': first_json.get('status') if isinstance(first_json, dict) else None,
                        'step': first_json.get('step') if isinstance(first_json, dict) else None,
                        'message': (first_json.get('message') if isinstance(first_json, dict) else None) or 'Document received',
                        'resumeUrl': first_json.get('resumeUrl') if isinstance(first_json, dict) else None,
                        'extractedText': first_json.get('extractedText') if isinstance(first_json, dict) else None,
                        'fullText': first_json.get('fullText') if isinstance(first_json, dict) else None,
                        'textQuality': first_json.get('quality') if isinstance(first_json, dict) else None,
                        'qualityScore': first_json.get('confidence') if isinstance(first_json, dict) else None,
                        'qualityIssues': first_json.get('issues') if isinstance(first_json, dict) else None,
                        'recommendations': first_json.get('recommendations') if isinstance(first_json, dict) else None,
                        'hvacTermsFound': first_json.get('hvacTermsFound') if isinstance(first_json, dict) else None,
                        'analysis': first_json.get('analysis') if isinstance(first_json, dict) else None,
                        'summary': first_json.get('summary') if isinstance(first_json, dict) else None,
                    }
                    
                    # Store workflow execution info (best-effort; raw_result might not include ids)
                    try:
                        await self._store_workflow_execution(session_id, raw_result if isinstance(raw_result, dict) else {})
                    except Exception:
                        pass
                    
                    # Stream initial event
                    await self._stream_workflow_event(session_id, {
                        'type': 'workflow_started',
                        'workflow': 'analysis_document',
                        'files': [f.filename for f in files]
                    })
                    
                    # If we have a resume URL, persist it and stream an approval message
                    resume_url = normalized.get('resumeUrl')
                    if resume_url:
                        try:
                            await store_resume_url(session_id, resume_url)
                        except Exception:
                            pass
                        # Reuse wait node handler to create a proper approval message for the UI
                        try:
                            await self.handle_wait_node_response(
                                session_id,
                                normalized.get('executionId') or '',
                                {
                                    'resumeUrl': resume_url,
                                    'nodeName': 'Text Review',
                                    'waitType': 'approval',
                                    'data': {
                                        'extractedText': normalized.get('extractedText'),
                                        'textQuality': normalized.get('textQuality'),
                                        'qualityScore': normalized.get('qualityScore'),
                                        'qualityIssues': normalized.get('qualityIssues'),
                                        'recommendations': normalized.get('recommendations'),
                                    }
                                }
                            )
                        except Exception:
                            pass
                    
                    # Save files to database if provided
                    if db:
                        await self._save_uploaded_files(session_id, files, db)
                    
                    return {
                        'success': True,
                        'data': normalized,
                        'resumeUrl': normalized.get('resumeUrl')
                    }
                else:
                    error_msg = f"Workflow error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    await self._stream_workflow_event(session_id, {
                        'type': 'workflow_error',
                        'error': error_msg
                    })
                    return {'success': False, 'error': error_msg}
                    
        except Exception as e:
            logger.error(f"Failed to trigger document ingestion: {e}")
            await self._stream_workflow_event(session_id, {
                'type': 'workflow_error',
                'error': str(e)
            })
            return {'success': False, 'error': str(e)}
    
    async def trigger_chat_conversation(
        self,
        session_id: str,
        message: str,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Trigger conversational chat workflow
        """
        try:
            # Get session context including embeddings and history
            session_context = await self._get_session_context(session_id, db)
            
            payload = {
                'sessionId': session_id,
                'message': message,
                'conversationHistory': session_context.get('messages', []),
                'sessionContext': {
                    'hasDocuments': session_context.get('hasDocuments', False),
                    'hasAnalysis': session_context.get('hasAnalysis', False),
                    'currentState': session_context.get('state', 'idle')
                }
            }
            
            chat_path = os.getenv('N8N_CHAT_WEBHOOK_PATH', '/webhook/pybog-chat').lstrip('/')
            chat_full = os.getenv('N8N_CHAT_WEBHOOK')
            webhook_url = chat_full or f"{self.n8n_url}/{chat_path}"
            logger.info(f"Triggering chat webhook: {webhook_url}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(webhook_url, json=payload)
                
                if response.status_code >= 200 and response.status_code < 300:
                    result = response.json()
                    
                    # Store execution info
                    await self._store_workflow_execution(session_id, result)
                    
                    # Stream event
                    await self._stream_workflow_event(session_id, {
                        'type': 'workflow_started',
                        'workflow': 'chat_conversation',
                        'executionId': result.get('executionId')
                    })
                    
                    # Save message to database
                    if db:
                        await self._save_message(session_id, 'user', message, db)
                    
                    return {
                        'success': True,
                        'executionId': result.get('executionId'),
                        'resumeUrl': result.get('resumeUrl'),
                        'data': result
                    }
                else:
                    return {'success': False, 'error': f"Chat workflow error: {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Failed to trigger chat workflow: {e}")
            return {'success': False, 'error': str(e)}
    
    # ==================== Wait Node Handling ====================
    
    async def handle_wait_node_response(
        self,
        session_id: str,
        execution_id: str,
        wait_data: Dict[str, Any]
    ) -> None:
        """
        Process wait node data and prepare for frontend display
        """
        try:
            # Extract wait node information
            resume_url = wait_data.get('resumeUrl')
            node_name = wait_data.get('nodeName', 'Approval Required')
            wait_type = wait_data.get('waitType', 'approval')
            display_data = wait_data.get('data', {})
            
            # Store resume URL for later use
            if resume_url:
                await store_resume_url(session_id, resume_url)
            
            # Create approval message for frontend
            approval_message = {
                'messageId': str(uuid.uuid4()),
                'sessionId': session_id,
                'type': 'system',
                'messageType': 'approval',
                'content': self._format_wait_node_content(node_name, display_data),
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': {
                    'executionId': execution_id,
                    'requiresAction': True,
                    'actionType': wait_type
                },
                'waitNode': {
                    'nodeId': wait_data.get('nodeId'),
                    'nodeName': node_name,
                    'executionId': execution_id,
                    'resumeUrl': resume_url,
                    'waitType': wait_type,
                    'displayData': {
                        'title': node_name,
                        'description': wait_data.get('description'),
                        'data': display_data,
                        'actions': self._generate_wait_actions(wait_type, display_data)
                    }
                }
            }
            
            # Stream to frontend
            await self._stream_message(session_id, approval_message)
            
            # Store in Redis for persistence
            await append_message(session_id, approval_message)
            
            # Update session state
            await self._update_session_state(session_id, 'waiting_approval')
            
        except Exception as e:
            logger.error(f"Failed to handle wait node: {e}")
            raise
    
    async def resume_workflow_with_approval(
        self,
        session_id: str,
        action: str,
        feedback: Optional[str] = None,
        modifications: Optional[Dict[str, Any]] = None,
        approved_text: Optional[str] = None,
        analysis: Optional[Dict[str, Any]] = None,
        user_action: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Resume a waiting workflow with user approval/rejection
        """
        try:
            # Build payload based on action
            # Build 'body' object as expected by n8n Wait nodes
            body = {
                'action': action,
                'sessionId': session_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            if feedback:
                body['feedback'] = feedback
            if modifications:
                body['modifications'] = modifications
            if approved_text:
                # For text approval
                body['approvedText'] = approved_text
                body['extractedText'] = approved_text
            if analysis:
                body['analysis'] = analysis
            if user_action:
                body['userAction'] = user_action

            # Convenience flags for legacy actions
            if action == 'approve':
                body['approved'] = True
            elif action in ('reject', 'modify'):
                body['approved'] = False

            payload = { 'body': body }
            
            # Resume the workflow
            result = await resume_n8n_workflow(session_id, payload)
            
            if result.get('success'):
                # Stream success event
                await self._stream_workflow_event(session_id, {
                    'type': 'workflow_resumed',
                    'action': action,
                    'executionId': result.get('executionId')
                })
                
                # Update session state
                new_state = 'processing' if action in ('approve', 'approve_text', 'approve_analysis', 'confirm') else 'idle'
                await self._update_session_state(session_id, new_state)
                
                # Save approval message
                if db:
                    await self._save_message(
                        session_id, 
                        'user',
                        f"Action: {action}. {feedback or ''}",
                        db,
                        message_type='approval'
                    )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to resume workflow: {e}")
            return {'success': False, 'error': str(e)}
    
    # ==================== SSE Streaming ====================
    
    async def create_event_stream(self, session_id: str) -> AsyncGenerator[str, None]:
        """
        Create SSE event stream for real-time updates
        """
        redis = await self.get_redis()
        pubsub = redis.pubsub()
        channel = f"pybog:session:{session_id}:events"
        
        await pubsub.subscribe(channel)
        
        # Send initial connection event
        yield self._format_sse_event('connected', {'sessionId': session_id})
        
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
                
                if message and message.get('type') == 'message':
                    try:
                        data = json.loads(message['data'])
                        yield self._format_sse_event(data.get('type', 'message'), data)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in Redis message: {message['data']}")
                else:
                    # Send keepalive
                    yield ":keepalive\\n\\n"
                    
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for session {session_id}")
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
    
    def _format_sse_event(self, event_type: str, data: Any) -> str:
        """Format data as SSE event"""
        return f"event: {event_type}\\ndata: {json.dumps(data)}\\n\\n"
    
    async def _stream_workflow_event(self, session_id: str, event: Dict[str, Any]):
        """Stream workflow event to connected clients"""
        redis = await self.get_redis()
        channel = f"pybog:session:{session_id}:events"
        event['timestamp'] = datetime.utcnow().isoformat()
        await redis.publish(channel, json.dumps(event))
    
    async def _stream_message(self, session_id: str, message: Dict[str, Any]):
        """Stream message to connected clients"""
        event = {
            'type': 'message',
            'message': message
        }
        await self._stream_workflow_event(session_id, event)
    
    # ==================== Database Operations ====================
    
    async def _get_session_context(self, session_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Get comprehensive session context"""
        context = {
            'messages': [],
            'hasDocuments': False,
            'hasAnalysis': False,
            'state': 'idle'
        }
        
        if not db:
            return context
            
        try:
            # Get session
            session = await db.execute(
                select(Session).where(Session.session_id == session_id)
            )
            session_obj = session.scalar_one_or_none()
            
            if session_obj:
                context['state'] = session_obj.state
                
                # Get recent messages
                messages = await db.execute(
                    select(Message)
                    .where(Message.session_id == session_id)
                    .order_by(Message.timestamp.desc())
                    .limit(20)
                )
                
                for msg in messages.scalars():
                    context['messages'].append({
                        'role': msg.type,
                        'content': msg.content,
                        'timestamp': msg.timestamp.isoformat()
                    })
                
                context['messages'].reverse()  # Chronological order
                
                # Check for documents
                files = await db.execute(
                    select(File).where(File.session_id == session_id).limit(1)
                )
                context['hasDocuments'] = files.scalar_one_or_none() is not None
                
                # Check for analysis
                analysis = await db.execute(
                    select(AnalysisResult).where(AnalysisResult.session_id == session_id).limit(1)
                )
                context['hasAnalysis'] = analysis.scalar_one_or_none() is not None
                
        except Exception as e:
            logger.error(f"Error getting session context: {e}")
            
        return context
    
    async def _save_uploaded_files(self, session_id: str, files: List[UploadFile], db: AsyncSession):
        """Save uploaded file records to database"""
        try:
            for file in files:
                file_id = str(uuid.uuid4())
                file_record = File(
                    file_id=file_id,
                    session_id=session_id,
                    filename=file.filename,
                    file_type=file.content_type,
                    file_size=file.size if hasattr(file, 'size') else 0,
                    meta={'uploaded_via': 'workflow'}
                )
                db.add(file_record)
            
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save file records: {e}")
            await db.rollback()
    
    async def _save_message(
        self, 
        session_id: str, 
        msg_type: str, 
        content: str, 
        db: AsyncSession,
        message_type: Optional[str] = None
    ):
        """Save message to database"""
        try:
            message = Message(
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                type=msg_type,
                message_type=message_type,
                content=content,
                meta={'source': 'workflow'}
            )
            db.add(message)
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            await db.rollback()
    
    async def _update_session_state(self, session_id: str, new_state: str):
        """Update session state in database and Redis"""
        redis = await self.get_redis()
        
        # Update in Redis
        await redis.hset(f"pybog:session:{session_id}:state", "current", new_state)
        
        # Stream state change event
        await self._stream_workflow_event(session_id, {
            'type': 'state_change',
            'oldState': await redis.hget(f"pybog:session:{session_id}:state", "previous") or 'unknown',
            'newState': new_state
        })
        
        await redis.hset(f"pybog:session:{session_id}:state", "previous", new_state)
    
    async def _store_workflow_execution(self, session_id: str, execution_data: Dict[str, Any]):
        """Store workflow execution details"""
        redis = await self.get_redis()
        
        execution_key = f"pybog:session:{session_id}:execution"
        await redis.hset(execution_key, mapping={
            'executionId': execution_data.get('executionId', ''),
            'workflowId': execution_data.get('workflowId', ''),
            'startedAt': datetime.utcnow().isoformat(),
            'status': 'running'
        })
        
        # Set expiry (24 hours)
        await redis.expire(execution_key, 86400)
    
    # ==================== Helper Methods ====================
    
    def _format_wait_node_content(self, node_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format wait node data for display"""
        content = {
            'text': f"**{node_name}**\\n\\nPlease review the following:",
            'components': []
        }
        
        # Add data display components
        if 'extractedText' in data:
            content['components'].append({
                'type': 'card',
                'props': {
                    'title': 'Extracted Text',
                    'content': data['extractedText'][:500] + '...' if len(data.get('extractedText', '')) > 500 else data.get('extractedText'),
                    'expandable': True
                }
            })
        
        if 'analysis' in data:
            content['components'].append({
                'type': 'card',
                'props': {
                    'title': 'Analysis Results',
                    'content': data['analysis']
                }
            })
        
        if 'recommendations' in data:
            content['components'].append({
                'type': 'alert',
                'props': {
                    'type': 'info',
                    'title': 'Recommendations',
                    'messages': data['recommendations']
                }
            })
        
        return content
    
    def _generate_wait_actions(self, wait_type: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate action buttons for wait node"""
        actions = []
        
        if wait_type == 'approval':
            actions = [
                {
                    'id': 'approve',
                    'label': 'Approve',
                    'type': 'primary',
                    'payload': {'action': 'approve'}
                },
                {
                    'id': 'reject',
                    'label': 'Reject',
                    'type': 'danger',
                    'payload': {'action': 'reject'},
                    'requiresInput': True,
                    'inputFields': [
                        {
                            'name': 'feedback',
                            'type': 'textarea',
                            'label': 'Reason for rejection',
                            'required': True
                        }
                    ]
                },
                {
                    'id': 'modify',
                    'label': 'Request Changes',
                    'type': 'secondary',
                    'payload': {'action': 'modify'},
                    'requiresInput': True,
                    'inputFields': [
                        {
                            'name': 'feedback',
                            'type': 'textarea',
                            'label': 'Changes needed',
                            'required': True
                        }
                    ]
                }
            ]
        elif wait_type == 'input':
            # Generate input fields based on data requirements
            pass
        elif wait_type == 'confirmation':
            actions = [
                {
                    'id': 'confirm',
                    'label': 'Confirm',
                    'type': 'primary',
                    'payload': {'action': 'confirm'}
                },
                {
                    'id': 'cancel',
                    'label': 'Cancel',
                    'type': 'secondary',
                    'payload': {'action': 'cancel'}
                }
            ]
        
        return actions


# Singleton instance
workflow_service = WorkflowService()
