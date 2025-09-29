"""
Workflow Service for PyBOG Backend

Manages review and approval workflow states, transitions, and user interactions.
Integrates with EventBus for real-time updates and coordinates with other services.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from core.events import EventBus, Event
from core.database import get_database
from models.workflow_models import (
    WorkflowState, ReviewType, ReviewDecision, ReviewItem, SessionWorkflow,
    TextExtractionReview, AnalysisReview, ReviewRequest, ReviewResponse,
    WorkflowStatusResponse, WorkflowTransition, is_valid_transition, get_next_actions
)
from models.file_models import ProgressState
from models.analysis_models import AnalysisState

logger = logging.getLogger(__name__)


class WorkflowService:
    """
    Service for managing review and approval workflows.
    
    Handles workflow state transitions, review item management, and coordinates
    with file service and analysis engine for complete workflow orchestration.
    """
    
    def __init__(self, event_bus: EventBus):
        """
        Initialize the workflow service.
        
        Args:
            event_bus: EventBus instance for event emission
        """
        self.event_bus = event_bus
        
        # In-memory workflow state cache for active sessions
        self._workflow_cache: Dict[str, SessionWorkflow] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def get_workflow_status(self, session_id: str) -> WorkflowStatusResponse:
        """
        Get current workflow status for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Current workflow status
        """
        try:
            workflow = await self._get_or_create_workflow(session_id)
            
            # Get current review item if any
            current_review = None
            if workflow.pending_reviews:
                current_review = workflow.pending_reviews[0]  # First pending review
            
            # Calculate progress percentage
            progress_percent = self._calculate_progress(workflow)
            
            return WorkflowStatusResponse(
                session_id=session_id,
                current_state=workflow.current_state,
                pending_reviews_count=len(workflow.pending_reviews),
                completed_reviews_count=len(workflow.completed_reviews),
                next_actions=get_next_actions(workflow.current_state),
                current_review=current_review,
                progress_percent=progress_percent,
                metadata=workflow.metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to get workflow status for session {session_id}: {e}")
            raise
    
    async def start_text_extraction_workflow(self, session_id: str, file_id: int, 
                                           extracted_text: str, quality_data: Dict[str, Any]) -> str:
        """
        Start text extraction review workflow.
        
        Args:
            session_id: Session identifier
            file_id: File ID that was processed
            extracted_text: Extracted text content
            quality_data: Text quality assessment data
            
        Returns:
            Review item ID
        """
        try:
            workflow = await self._get_or_create_workflow(session_id)
            
            # First transition to extracting text state
            await self._transition_workflow(
                workflow, WorkflowState.EXTRACTING_TEXT,
                "text_extraction_started", {"file_id": file_id}
            )

            # Then transition to awaiting text review
            await self._transition_workflow(
                workflow, WorkflowState.AWAITING_TEXT_REVIEW,
                "text_extraction_complete", {"file_id": file_id}
            )
            
            # Create text extraction review item
            review_data = TextExtractionReview(
                file_id=file_id,
                extracted_text=extracted_text,
                quality_score=quality_data.get("quality_score", 0.8),
                quality_issues=quality_data.get("issues", []),
                recommendations=quality_data.get("recommendations", []),
                hvac_terms_found=quality_data.get("hvac_terms_found", 0),
                character_count=len(extracted_text),
                estimated_tokens=quality_data.get("estimated_tokens")
            )
            
            review_id = f"text_review_{uuid.uuid4().hex[:8]}"
            review_item = ReviewItem(
                id=review_id,
                session_id=session_id,
                review_type=ReviewType.TEXT_EXTRACTION,
                state=WorkflowState.AWAITING_TEXT_REVIEW,
                data=review_data
            )
            
            workflow.add_review_item(review_item)
            await self._save_workflow(workflow)
            
            # Emit workflow update event
            await self._emit_workflow_event(
                session_id, "text_review_ready", {
                    "review_id": review_id,
                    "file_id": file_id,
                    "character_count": len(extracted_text),
                    "quality_score": review_data.quality_score,
                    "actions": ["approve_text", "edit_text", "retry_extraction"]
                }
            )
            
            return review_id
            
        except Exception as e:
            logger.error(f"Failed to start text extraction workflow: {e}")
            await self._handle_workflow_error(session_id, f"Text extraction workflow failed: {str(e)}")
            raise
    
    async def start_analysis_review_workflow(self, session_id: str, analysis_id: int,
                                           analysis_data: Dict[str, Any]) -> str:
        """
        Start analysis result review workflow.
        
        Args:
            session_id: Session identifier
            analysis_id: Analysis result ID
            analysis_data: Analysis result data
            
        Returns:
            Review item ID
        """
        try:
            workflow = await self._get_or_create_workflow(session_id)
            
            # Transition to awaiting analysis review
            await self._transition_workflow(
                workflow, WorkflowState.AWAITING_ANALYSIS_REVIEW,
                "analysis_complete", {"analysis_id": analysis_id}
            )
            
            # Create analysis review item
            review_data = AnalysisReview(
                analysis_id=analysis_id,
                quality_score=analysis_data.get("quality_score", 0.0),
                io_points_count=len(analysis_data.get("io_points", [])),
                control_blocks_count=len(analysis_data.get("control_blocks", [])),
                pseudocode_steps_count=len(analysis_data.get("pseudocode", [])),
                issues=analysis_data.get("issues", []),
                recommendations=analysis_data.get("metadata", {}).get("recommendations", []),
                confidence_level=analysis_data.get("metadata", {}).get("confidence", 0.0),
                completeness_score=self._calculate_completeness_score(analysis_data)
            )
            
            review_id = f"analysis_review_{uuid.uuid4().hex[:8]}"
            review_item = ReviewItem(
                id=review_id,
                session_id=session_id,
                review_type=ReviewType.ANALYSIS_RESULT,
                state=WorkflowState.AWAITING_ANALYSIS_REVIEW,
                data=review_data
            )
            
            workflow.add_review_item(review_item)
            await self._save_workflow(workflow)
            
            # Emit workflow update event
            await self._emit_workflow_event(
                session_id, "analysis_review_ready", {
                    "review_id": review_id,
                    "analysis_id": analysis_id,
                    "quality_score": review_data.quality_score,
                    "completeness_score": review_data.completeness_score,
                    "actions": ["approve_analysis", "request_changes", "retry_analysis"]
                }
            )
            
            return review_id
            
        except Exception as e:
            logger.error(f"Failed to start analysis review workflow: {e}")
            await self._handle_workflow_error(session_id, f"Analysis review workflow failed: {str(e)}")
            raise
    
    async def submit_review(self, request: ReviewRequest) -> ReviewResponse:
        """
        Submit a review decision.
        
        Args:
            request: Review submission request
            
        Returns:
            Review response with next steps
        """
        try:
            workflow = await self._get_or_create_workflow(request.session_id)
            
            # Complete the review
            completed_review = workflow.complete_review(
                request.review_id, request.decision, request.feedback
            )
            
            if not completed_review:
                raise ValueError(f"Review {request.review_id} not found in pending reviews")
            
            # Determine next workflow state based on decision
            next_state = await self._determine_next_state(completed_review, request.decision)
            
            # Handle the decision
            response = await self._handle_review_decision(
                workflow, completed_review, request.decision, request.modified_data
            )
            
            # Transition workflow if needed
            if next_state != workflow.current_state:
                await self._transition_workflow(
                    workflow, next_state,
                    f"review_{request.decision.value}",
                    {"review_id": request.review_id, "decision": request.decision.value}
                )
            
            await self._save_workflow(workflow)
            
            # Emit review completion event
            await self._emit_workflow_event(
                request.session_id, "review_completed", {
                    "review_id": request.review_id,
                    "decision": request.decision.value,
                    "next_state": next_state.value,
                    "message": response.message
                }
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to submit review: {e}")
            await self._handle_workflow_error(request.session_id, f"Review submission failed: {str(e)}")
            raise
    
    async def reset_workflow(self, session_id: str) -> None:
        """
        Reset workflow to idle state.
        
        Args:
            session_id: Session identifier
        """
        try:
            workflow = await self._get_or_create_workflow(session_id)
            
            # Clear pending reviews
            workflow.pending_reviews.clear()
            
            # Transition to idle
            await self._transition_workflow(
                workflow, WorkflowState.IDLE,
                "workflow_reset", {}
            )
            
            await self._save_workflow(workflow)
            
            # Emit reset event
            await self._emit_workflow_event(
                session_id, "workflow_reset", {
                    "message": "Workflow reset to idle state"
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to reset workflow: {e}")
            raise
    
    async def _get_or_create_workflow(self, session_id: str) -> SessionWorkflow:
        """Get or create workflow for session."""
        async with self._lock:
            if session_id in self._workflow_cache:
                return self._workflow_cache[session_id]
            
            # Try to load from database
            workflow = await self._load_workflow(session_id)
            if not workflow:
                # Create new workflow
                workflow = SessionWorkflow(session_id=session_id)
                await self._save_workflow(workflow)
            
            self._workflow_cache[session_id] = workflow
            return workflow
    
    async def _load_workflow(self, session_id: str) -> Optional[SessionWorkflow]:
        """Load workflow from database."""
        try:
            db = await get_database()
            
            query = """
                SELECT workflow_data FROM session_workflows 
                WHERE session_id = $1
            """
            record = await db.fetch_one(query, session_id)
            
            if record:
                workflow_data = json.loads(record['workflow_data'])
                return SessionWorkflow(**workflow_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load workflow for session {session_id}: {e}")
            return None
    
    async def _save_workflow(self, workflow: SessionWorkflow) -> None:
        """Save workflow to database."""
        try:
            db = await get_database()
            
            # Update cache
            self._workflow_cache[workflow.session_id] = workflow
            
            # Save to database
            upsert_query = """
                INSERT INTO session_workflows (session_id, workflow_data, updated_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (session_id) 
                DO UPDATE SET 
                    workflow_data = EXCLUDED.workflow_data,
                    updated_at = EXCLUDED.updated_at
            """
            
            await db.execute_query(
                upsert_query,
                workflow.session_id,
                json.dumps(workflow.model_dump(), default=str),
                datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Failed to save workflow: {e}")
            raise
    
    async def _transition_workflow(self, workflow: SessionWorkflow, to_state: WorkflowState,
                                 trigger: str, metadata: Dict[str, Any]) -> None:
        """Transition workflow to new state."""
        if not is_valid_transition(workflow.current_state, to_state):
            raise ValueError(f"Invalid transition from {workflow.current_state} to {to_state}")
        
        workflow.add_transition(to_state, trigger, metadata)
        logger.info(f"Workflow {workflow.session_id} transitioned from {workflow.current_state} to {to_state}")
    
    async def _determine_next_state(self, review: ReviewItem, decision: ReviewDecision) -> WorkflowState:
        """Determine next workflow state based on review decision."""
        if review.review_type == ReviewType.TEXT_EXTRACTION:
            if decision == ReviewDecision.APPROVE:
                return WorkflowState.ANALYZING
            elif decision == ReviewDecision.RETRY:
                return WorkflowState.EXTRACTING_TEXT
            else:
                return WorkflowState.FAILED
        
        elif review.review_type == ReviewType.ANALYSIS_RESULT:
            if decision == ReviewDecision.APPROVE:
                return WorkflowState.GENERATING_BOG
            elif decision == ReviewDecision.RETRY:
                return WorkflowState.ANALYZING
            elif decision == ReviewDecision.REQUEST_CHANGES:
                return WorkflowState.ANALYZING  # Re-analyze with feedback
            else:
                return WorkflowState.FAILED
        
        return WorkflowState.FAILED
    
    async def _handle_review_decision(self, workflow: SessionWorkflow, review: ReviewItem,
                                    decision: ReviewDecision, modified_data: Optional[Dict[str, Any]]) -> ReviewResponse:
        """Handle specific review decision logic."""
        if review.review_type == ReviewType.TEXT_EXTRACTION:
            return await self._handle_text_review_decision(workflow, review, decision, modified_data)
        elif review.review_type == ReviewType.ANALYSIS_RESULT:
            return await self._handle_analysis_review_decision(workflow, review, decision, modified_data)
        else:
            raise ValueError(f"Unknown review type: {review.review_type}")
    
    async def _handle_text_review_decision(self, workflow: SessionWorkflow, review: ReviewItem,
                                         decision: ReviewDecision, modified_data: Optional[Dict[str, Any]]) -> ReviewResponse:
        """Handle text extraction review decision."""
        if decision == ReviewDecision.APPROVE:
            # Start analysis with approved text
            return ReviewResponse(
                review_id=review.id,
                decision=decision,
                next_state=WorkflowState.ANALYZING,
                message="Text approved. Starting analysis...",
                actions_available=["cancel_analysis"],
                metadata={"approved_text": review.data.extracted_text}
            )
        
        elif decision == ReviewDecision.RETRY:
            # Retry text extraction
            return ReviewResponse(
                review_id=review.id,
                decision=decision,
                next_state=WorkflowState.EXTRACTING_TEXT,
                message="Retrying text extraction...",
                actions_available=["cancel_extraction"]
            )
        
        else:
            return ReviewResponse(
                review_id=review.id,
                decision=decision,
                next_state=WorkflowState.FAILED,
                message="Text extraction rejected. Workflow failed.",
                actions_available=["start_new_workflow"]
            )
    
    async def _handle_analysis_review_decision(self, workflow: SessionWorkflow, review: ReviewItem,
                                             decision: ReviewDecision, modified_data: Optional[Dict[str, Any]]) -> ReviewResponse:
        """Handle analysis result review decision."""
        if decision == ReviewDecision.APPROVE:
            # Start BOG generation
            return ReviewResponse(
                review_id=review.id,
                decision=decision,
                next_state=WorkflowState.GENERATING_BOG,
                message="Analysis approved. Generating BOG file...",
                actions_available=["cancel_generation"]
            )
        
        elif decision == ReviewDecision.REQUEST_CHANGES:
            # Re-analyze with user feedback
            return ReviewResponse(
                review_id=review.id,
                decision=decision,
                next_state=WorkflowState.ANALYZING,
                message="Re-analyzing with your feedback...",
                actions_available=["cancel_analysis"],
                metadata={"user_feedback": review.user_feedback}
            )
        
        elif decision == ReviewDecision.RETRY:
            # Retry analysis
            return ReviewResponse(
                review_id=review.id,
                decision=decision,
                next_state=WorkflowState.ANALYZING,
                message="Retrying analysis...",
                actions_available=["cancel_analysis"]
            )
        
        else:
            return ReviewResponse(
                review_id=review.id,
                decision=decision,
                next_state=WorkflowState.FAILED,
                message="Analysis rejected. Workflow failed.",
                actions_available=["start_new_workflow"]
            )
    
    def _calculate_progress(self, workflow: SessionWorkflow) -> Optional[float]:
        """Calculate workflow progress percentage."""
        state_progress = {
            WorkflowState.IDLE: 0.0,
            WorkflowState.EXTRACTING_TEXT: 10.0,
            WorkflowState.AWAITING_TEXT_REVIEW: 25.0,
            WorkflowState.ANALYZING: 50.0,
            WorkflowState.AWAITING_ANALYSIS_REVIEW: 75.0,
            WorkflowState.GENERATING_BOG: 90.0,
            WorkflowState.COMPLETE: 100.0,
            WorkflowState.FAILED: None
        }
        return state_progress.get(workflow.current_state)
    
    def _calculate_completeness_score(self, analysis_data: Dict[str, Any]) -> float:
        """Calculate analysis completeness score."""
        score = 0.0
        
        # Check for IO points
        if analysis_data.get("io_points"):
            score += 0.3
        
        # Check for control blocks
        if analysis_data.get("control_blocks"):
            score += 0.3
        
        # Check for pseudocode
        if analysis_data.get("pseudocode"):
            score += 0.2
        
        # Check for metadata
        if analysis_data.get("metadata", {}).get("recommendations"):
            score += 0.1
        
        # Check quality score
        quality_score = analysis_data.get("quality_score", 0.0)
        score += quality_score * 0.1
        
        return min(1.0, score)
    
    async def _emit_workflow_event(self, session_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """Emit workflow event through EventBus."""
        await self.event_bus.publish(
            session_id,
            Event(
                type=event_type,
                session_id=session_id,
                operation="workflow",
                data=data
            )
        )
    
    async def _handle_workflow_error(self, session_id: str, error_message: str) -> None:
        """Handle workflow error and transition to failed state."""
        try:
            workflow = await self._get_or_create_workflow(session_id)
            
            await self._transition_workflow(
                workflow, WorkflowState.FAILED,
                "error", {"error_message": error_message}
            )
            
            await self._save_workflow(workflow)
            
            # Emit error event
            await self._emit_workflow_event(
                session_id, "workflow_error", {
                    "error_message": error_message,
                    "actions": ["start_new_workflow"]
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to handle workflow error: {e}")