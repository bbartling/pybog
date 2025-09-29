"""
Analysis Engine Service for PyBOG Backend

This service handles document analysis and BOG file generation with state machine
transitions and event emission. Integrates with the EventBus for real-time progress
updates and supports cancellation of mid-workflow operations.
"""

import asyncio
import json
import logging
import tempfile
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path

from core.events import EventBus, Event
from core.database import get_database
from models.analysis_models import (
    AnalysisResult, AnalysisState, DocumentAnalysis, AnalysisRequest,
    BOGGenerationRequest, AnalysisStateUpdate, AnalysisProgress,
    CancellationRequest, CancellationResult, IOPoint, ControlBlock,
    PseudocodeStep, AnalysisMetadata
)
from models.file_models import FileRecord, FileType, ProgressState
from services.pybog_agent_v2 import PyBOGAgentV2

logger = logging.getLogger(__name__)


class AnalysisEngine:
    """
    Analysis engine for document processing and BOG file generation.
    
    Handles the complete analysis workflow with state machine transitions:
    queued → processing → finalizing → complete/failed
    
    Emits events to EventBus for real-time progress updates and integrates
    with PyBOGAgent for intelligent document analysis.
    """
    
    def __init__(self, event_bus: EventBus, pybog_agent: PyBOGAgentV2):
        """
        Initialize the analysis engine.
        
        Args:
            event_bus: EventBus instance for event emission
            pybog_agent: PyBOGAgent instance for document analysis
        """
        self.event_bus = event_bus
        self.pybog_agent = pybog_agent
        
        # Track active analysis operations for cancellation support
        self._active_analyses: Dict[int, asyncio.Task] = {}
        self._cancellation_flags: Dict[int, bool] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def analyze_document(self, session_id: str, file_id: int, 
                             options: Optional[Dict[str, Any]] = None) -> int:
        """
        Analyze a document and create analysis result with state transitions.
        
        Args:
            session_id: Session identifier
            file_id: File ID to analyze
            options: Optional analysis options
            
        Returns:
            Analysis result ID
            
        Raises:
            ValueError: If file not found or invalid
            RuntimeError: If analysis fails
        """
        options = options or {}
        
        try:
            # Get database connection
            db = await get_database()
            
            # Verify file exists and get metadata
            file_query = """
                SELECT id, session_id, filename, original_name, file_type, 
                       file_size, state, file_data, file_path
                FROM files 
                WHERE id = $1 AND session_id = $2
            """
            file_record = await db.fetch_one(file_query, file_id, session_id)
            
            if not file_record:
                raise ValueError(f"File {file_id} not found in session {session_id}")
            
            if file_record['state'] != 'complete':
                raise ValueError(f"File {file_id} is not ready for analysis (state: {file_record['state']})")
            
            # Create analysis result record
            analysis_data = DocumentAnalysis()  # Empty initial analysis
            
            insert_query = """
                INSERT INTO analysis_results (session_id, input_file_id, state, analysis_data)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """
            analysis_id = await db.fetch_val(
                insert_query, 
                session_id, 
                file_id, 
                AnalysisState.QUEUED.value,
                json.dumps(analysis_data.model_dump())
            )
            
            # Emit queued event
            await self._emit_progress_event(
                session_id, analysis_id, "analyze", AnalysisState.QUEUED,
                "Analysis queued for processing", 0.0
            )
            
            # Start analysis task
            task = asyncio.create_task(
                self._process_analysis(session_id, analysis_id, file_record, options)
            )
            
            async with self._lock:
                self._active_analyses[analysis_id] = task
                self._cancellation_flags[analysis_id] = False
            
            return analysis_id
            
        except Exception as e:
            logger.error(f"Failed to start analysis for file {file_id}: {e}")
            
            # Emit error event
            await self.event_bus.publish(
                session_id,
                Event(
                    type="error",
                    session_id=session_id,
                    operation="analyze",
                    data={
                        "error_code": "ANALYSIS",
                        "message": f"Failed to start analysis: {str(e)}",
                        "operation": "analyze",
                        "session_id": session_id,
                        "file_id": file_id
                    }
                )
            )
            raise
    
    async def _process_analysis(self, session_id: str, analysis_id: int, 
                              file_record: dict, options: Dict[str, Any]) -> None:
        """
        Process document analysis with state transitions.
        
        Args:
            session_id: Session identifier
            analysis_id: Analysis result ID
            file_record: File record from database
            options: Analysis options
        """
        try:
            # Check for cancellation
            if await self._check_cancellation(analysis_id):
                return
            
            # Update state to processing
            await self._update_analysis_state(
                analysis_id, AnalysisState.PROCESSING
            )
            
            await self._emit_progress_event(
                session_id, analysis_id, "analyze", AnalysisState.PROCESSING,
                "Starting document analysis...", 10.0
            )
            
            # Get file content
            file_content = await self._get_file_content(file_record)
            
            if await self._check_cancellation(analysis_id):
                return
            
            await self._emit_progress_event(
                session_id, analysis_id, "analyze", AnalysisState.PROCESSING,
                "Analyzing document content with AI...", 30.0
            )
            
            # Analyze document with PyBOG agent
            analysis_data_dict = await self.pybog_agent.analyze_document_content(
                session_id, file_content
            )
            
            if await self._check_cancellation(analysis_id):
                return
            
            await self._emit_progress_event(
                session_id, analysis_id, "analyze", AnalysisState.PROCESSING,
                "Processing analysis results...", 70.0
            )
            
            # Convert to structured analysis
            analysis_data = self._convert_to_document_analysis(analysis_data_dict)
            
            if await self._check_cancellation(analysis_id):
                return
            
            # Update state to finalizing
            await self._update_analysis_state(
                analysis_id, AnalysisState.FINALIZING, analysis_data=analysis_data
            )
            
            await self._emit_progress_event(
                session_id, analysis_id, "analyze", AnalysisState.FINALIZING,
                "Finalizing analysis results...", 90.0
            )
            
            # Small delay to simulate finalization
            await asyncio.sleep(0.5)
            
            if await self._check_cancellation(analysis_id):
                return
            
            # Update state to complete
            await self._update_analysis_state(
                analysis_id, AnalysisState.COMPLETE, 
                analysis_data=analysis_data, completed_at=datetime.now(timezone.utc)
            )
            
            await self._emit_progress_event(
                session_id, analysis_id, "analyze", AnalysisState.COMPLETE,
                "Document analysis completed successfully", 100.0
            )
            
            # Emit analysis complete event
            await self.event_bus.publish(
                session_id,
                Event(
                    type="analysis_complete",
                    session_id=session_id,
                    operation="analyze",
                    data={
                        "analysis_id": analysis_id,
                        "file_id": file_record['id'],
                        "quality_score": analysis_data.quality_score,
                        "io_points_count": len(analysis_data.io_points),
                        "control_blocks_count": len(analysis_data.control_blocks),
                        "issues_count": len(analysis_data.issues)
                    }
                )
            )
            
        except Exception as e:
            logger.error(f"Analysis failed for analysis {analysis_id}: {e}")
            
            # Update state to failed
            await self._update_analysis_state(
                analysis_id, AnalysisState.FAILED, error_message=str(e)
            )
            
            await self._emit_progress_event(
                session_id, analysis_id, "analyze", AnalysisState.FAILED,
                f"Analysis failed: {str(e)}", None
            )
            
            # Emit error event
            await self.event_bus.publish(
                session_id,
                Event(
                    type="error",
                    session_id=session_id,
                    operation="analyze",
                    data={
                        "error_code": "ANALYSIS",
                        "message": f"Analysis failed: {str(e)}",
                        "operation": "analyze",
                        "session_id": session_id,
                        "analysis_id": analysis_id
                    }
                )
            )
        
        finally:
            # Clean up active analysis tracking
            async with self._lock:
                self._active_analyses.pop(analysis_id, None)
                self._cancellation_flags.pop(analysis_id, None)
    
    async def generate_bog_file(self, session_id: str, analysis_id: int,
                              filename: Optional[str] = None) -> int:
        """
        Generate a PyBOG file from analysis results and emit completion events.
        
        Args:
            session_id: Session identifier
            analysis_id: Analysis result ID
            filename: Optional custom filename
            
        Returns:
            BOG file ID
            
        Raises:
            ValueError: If analysis not found or not complete
            RuntimeError: If BOG generation fails
        """
        try:
            # Get database connection
            db = await get_database()
            
            # Get analysis result
            analysis_query = """
                SELECT id, session_id, input_file_id, bog_file_id, state, 
                       analysis_data, created_at
                FROM analysis_results 
                WHERE id = $1 AND session_id = $2
            """
            analysis_record = await db.fetch_one(analysis_query, analysis_id, session_id)
            
            if not analysis_record:
                raise ValueError(f"Analysis {analysis_id} not found in session {session_id}")
            
            if analysis_record['state'] != AnalysisState.COMPLETE.value:
                raise ValueError(f"Analysis {analysis_id} is not complete (state: {analysis_record['state']})")
            
            if analysis_record['bog_file_id']:
                # BOG file already exists, return existing file ID
                logger.info(f"BOG file already exists for analysis {analysis_id}")
                return analysis_record['bog_file_id']
            
            # Emit progress event
            await self._emit_progress_event(
                session_id, analysis_id, "generate_bog", AnalysisState.PROCESSING,
                "Generating PyBOG file...", 0.0
            )
            
            # Parse analysis data
            # Parse JSON analysis data
            analysis_data_dict = json.loads(analysis_record['analysis_data']) if isinstance(analysis_record['analysis_data'], str) else analysis_record['analysis_data']
            analysis_data = DocumentAnalysis(**analysis_data_dict)
            
            # Generate BOG file content
            bog_content = await self._generate_bog_content(analysis_data)
            
            await self._emit_progress_event(
                session_id, analysis_id, "generate_bog", AnalysisState.PROCESSING,
                "Creating BOG file...", 50.0
            )
            
            # Create filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"analysis_{analysis_id}_{timestamp}.bog"
            
            # Create file record
            file_insert_query = """
                INSERT INTO files (session_id, filename, original_name, mime_type, 
                                 file_type, file_data, file_size, state)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """
            
            bog_bytes = bog_content.encode('utf-8')
            bog_file_id = await db.fetch_val(
                file_insert_query,
                session_id,
                filename,
                filename,
                "application/x-pybog",
                FileType.BOG.value,
                bog_bytes,
                len(bog_bytes),
                ProgressState.COMPLETE.value
            )
            
            # Update analysis result with BOG file ID
            update_query = """
                UPDATE analysis_results 
                SET bog_file_id = $1 
                WHERE id = $2
            """
            await db.execute_query(update_query, bog_file_id, analysis_id)
            
            await self._emit_progress_event(
                session_id, analysis_id, "generate_bog", AnalysisState.COMPLETE,
                "PyBOG file generated successfully", 100.0
            )
            
            # Emit BOG generated event
            await self.event_bus.publish(
                session_id,
                Event(
                    type="bog_generated",
                    session_id=session_id,
                    operation="generate_bog",
                    data={
                        "file_id": bog_file_id,
                        "filename": filename,
                        "analysis_id": analysis_id,
                        "file_size": len(bog_bytes),
                        "analysis": analysis_data.model_dump()
                    }
                )
            )
            
            return bog_file_id
            
        except Exception as e:
            logger.error(f"Failed to generate BOG file for analysis {analysis_id}: {e}")
            
            # Emit error event
            await self.event_bus.publish(
                session_id,
                Event(
                    type="error",
                    session_id=session_id,
                    operation="generate_bog",
                    data={
                        "error_code": "ANALYSIS",
                        "message": f"Failed to generate BOG file: {str(e)}",
                        "operation": "generate_bog",
                        "session_id": session_id,
                        "analysis_id": analysis_id
                    }
                )
            )
            raise
    
    async def cancel_analysis(self, session_id: str, analysis_id: Optional[int] = None) -> CancellationResult:
        """
        Cancel analysis operations for mid-workflow interruption.
        
        Args:
            session_id: Session identifier
            analysis_id: Specific analysis ID to cancel (None for all active)
            
        Returns:
            Cancellation result with count and IDs
        """
        cancelled_ids = []
        
        try:
            async with self._lock:
                if analysis_id:
                    # Cancel specific analysis
                    if analysis_id in self._active_analyses:
                        self._cancellation_flags[analysis_id] = True
                        task = self._active_analyses[analysis_id]
                        task.cancel()
                        cancelled_ids.append(analysis_id)
                else:
                    # Cancel all active analyses for session
                    db = await get_database()
                    
                    # Get active analyses for session
                    active_query = """
                        SELECT id FROM analysis_results 
                        WHERE session_id = $1 AND state IN ('queued', 'processing', 'finalizing')
                    """
                    active_records = await db.fetch_all(active_query, session_id)
                    
                    for record in active_records:
                        aid = record['id']
                        if aid in self._active_analyses:
                            self._cancellation_flags[aid] = True
                            task = self._active_analyses[aid]
                            task.cancel()
                            cancelled_ids.append(aid)
            
            # Update database state for cancelled analyses
            if cancelled_ids:
                db = await get_database()
                
                for aid in cancelled_ids:
                    await self._update_analysis_state(
                        aid, AnalysisState.FAILED, 
                        error_message="Analysis cancelled by user"
                    )
                    
                    # Emit cancellation event
                    await self._emit_progress_event(
                        session_id, aid, "cancel", AnalysisState.FAILED,
                        "Analysis cancelled by user", None
                    )
            
            result = CancellationResult(
                cancelled_count=len(cancelled_ids),
                cancelled_analysis_ids=cancelled_ids,
                session_id=session_id,
                message=f"Cancelled {len(cancelled_ids)} analysis operations"
            )
            
            # Emit cancellation complete event
            await self.event_bus.publish(
                session_id,
                Event(
                    type="cancellation_complete",
                    session_id=session_id,
                    operation="cancel",
                    data=result.model_dump()
                )
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to cancel analysis for session {session_id}: {e}")
            
            # Emit error event
            await self.event_bus.publish(
                session_id,
                Event(
                    type="error",
                    session_id=session_id,
                    operation="cancel",
                    data={
                        "error_code": "ANALYSIS",
                        "message": f"Failed to cancel analysis: {str(e)}",
                        "operation": "cancel",
                        "session_id": session_id
                    }
                )
            )
            raise
    
    async def get_analysis_result(self, session_id: str, analysis_id: int) -> Optional[AnalysisResult]:
        """
        Get analysis result by ID.
        
        Args:
            session_id: Session identifier
            analysis_id: Analysis result ID
            
        Returns:
            Analysis result or None if not found
        """
        try:
            db = await get_database()
            
            query = """
                SELECT id, session_id, input_file_id, bog_file_id, state, 
                       analysis_data, error_message, created_at, completed_at
                FROM analysis_results 
                WHERE id = $1 AND session_id = $2
            """
            record = await db.fetch_one(query, analysis_id, session_id)
            
            if not record:
                return None
            
            # Parse JSON analysis data
            analysis_data_dict = json.loads(record['analysis_data']) if isinstance(record['analysis_data'], str) else record['analysis_data']
            
            return AnalysisResult(
                id=record['id'],
                session_id=record['session_id'],
                input_file_id=record['input_file_id'],
                bog_file_id=record['bog_file_id'],
                state=AnalysisState(record['state']),
                analysis_data=DocumentAnalysis(**analysis_data_dict),
                error_message=record['error_message'],
                created_at=record['created_at'],
                completed_at=record['completed_at']
            )
            
        except Exception as e:
            logger.error(f"Failed to get analysis result {analysis_id}: {e}")
            return None
    
    async def list_session_analyses(self, session_id: str) -> List[AnalysisResult]:
        """
        List all analysis results for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of analysis results
        """
        try:
            db = await get_database()
            
            query = """
                SELECT id, session_id, input_file_id, bog_file_id, state, 
                       analysis_data, error_message, created_at, completed_at
                FROM analysis_results 
                WHERE session_id = $1
                ORDER BY created_at DESC
            """
            records = await db.fetch_all(query, session_id)
            
            results = []
            for record in records:
                # Parse JSON analysis data
                analysis_data_dict = json.loads(record['analysis_data']) if isinstance(record['analysis_data'], str) else record['analysis_data']
                
                results.append(AnalysisResult(
                    id=record['id'],
                    session_id=record['session_id'],
                    input_file_id=record['input_file_id'],
                    bog_file_id=record['bog_file_id'],
                    state=AnalysisState(record['state']),
                    analysis_data=DocumentAnalysis(**analysis_data_dict),
                    error_message=record['error_message'],
                    created_at=record['created_at'],
                    completed_at=record['completed_at']
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to list analyses for session {session_id}: {e}")
            return []
    
    async def validate_analysis_requirements(self, analysis: DocumentAnalysis, 
                                           requirements: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate analysis results against specific requirements.
        
        Args:
            analysis: Analysis result to validate
            requirements: Optional requirements to validate against
            
        Returns:
            Validation result with compliance status and recommendations
        """
        try:
            validation_result = {
                "is_valid": True,
                "compliance_score": 1.0,
                "validation_issues": [],
                "recommendations": [],
                "requirements_met": [],
                "requirements_failed": []
            }
            
            # Default HVAC analysis requirements if none provided
            if not requirements:
                requirements = {
                    "min_io_points": 3,
                    "min_control_blocks": 1,
                    "min_quality_score": 0.6,
                    "required_point_types": ["input", "output"],
                    "required_data_types": ["numeric"],
                    "max_issues": 5
                }
            
            compliance_factors = []
            
            # Check minimum IO points
            if "min_io_points" in requirements:
                min_points = requirements["min_io_points"]
                actual_points = len(analysis.io_points)
                
                if actual_points >= min_points:
                    validation_result["requirements_met"].append(f"IO points: {actual_points} >= {min_points}")
                    compliance_factors.append(1.0)
                else:
                    validation_result["requirements_failed"].append(f"IO points: {actual_points} < {min_points}")
                    validation_result["validation_issues"].append(f"Insufficient IO points: need at least {min_points}, found {actual_points}")
                    validation_result["recommendations"].append(f"Identify additional sensors and actuators to reach minimum {min_points} IO points")
                    compliance_factors.append(actual_points / min_points)
            
            # Check minimum control blocks
            if "min_control_blocks" in requirements:
                min_blocks = requirements["min_control_blocks"]
                actual_blocks = len(analysis.control_blocks)
                
                if actual_blocks >= min_blocks:
                    validation_result["requirements_met"].append(f"Control blocks: {actual_blocks} >= {min_blocks}")
                    compliance_factors.append(1.0)
                else:
                    validation_result["requirements_failed"].append(f"Control blocks: {actual_blocks} < {min_blocks}")
                    validation_result["validation_issues"].append(f"Insufficient control blocks: need at least {min_blocks}, found {actual_blocks}")
                    validation_result["recommendations"].append(f"Define additional control logic blocks to reach minimum {min_blocks}")
                    compliance_factors.append(actual_blocks / min_blocks if min_blocks > 0 else 0.0)
            
            # Check quality score
            if "min_quality_score" in requirements:
                min_quality = requirements["min_quality_score"]
                actual_quality = analysis.quality_score
                
                if actual_quality >= min_quality:
                    validation_result["requirements_met"].append(f"Quality score: {actual_quality:.2f} >= {min_quality:.2f}")
                    compliance_factors.append(1.0)
                else:
                    validation_result["requirements_failed"].append(f"Quality score: {actual_quality:.2f} < {min_quality:.2f}")
                    validation_result["validation_issues"].append(f"Quality score too low: {actual_quality:.2f} < {min_quality:.2f}")
                    validation_result["recommendations"].append("Improve analysis quality by adding more detailed control information")
                    compliance_factors.append(actual_quality / min_quality)
            
            # Check required point types
            if "required_point_types" in requirements:
                required_types = set(requirements["required_point_types"])
                actual_types = set(point.type.value for point in analysis.io_points)
                missing_types = required_types - actual_types
                
                if not missing_types:
                    validation_result["requirements_met"].append(f"Point types: {list(actual_types)} includes all required {list(required_types)}")
                    compliance_factors.append(1.0)
                else:
                    validation_result["requirements_failed"].append(f"Missing point types: {list(missing_types)}")
                    validation_result["validation_issues"].append(f"Missing required point types: {list(missing_types)}")
                    validation_result["recommendations"].append(f"Add {list(missing_types)} points to complete control system")
                    compliance_factors.append(len(actual_types & required_types) / len(required_types))
            
            # Check maximum issues
            if "max_issues" in requirements:
                max_issues = requirements["max_issues"]
                actual_issues = len(analysis.issues)
                
                if actual_issues <= max_issues:
                    validation_result["requirements_met"].append(f"Issues count: {actual_issues} <= {max_issues}")
                    compliance_factors.append(1.0)
                else:
                    validation_result["requirements_failed"].append(f"Issues count: {actual_issues} > {max_issues}")
                    validation_result["validation_issues"].append(f"Too many analysis issues: {actual_issues} > {max_issues}")
                    validation_result["recommendations"].append("Resolve analysis issues to improve quality")
                    compliance_factors.append(max_issues / actual_issues if actual_issues > 0 else 1.0)
            
            # Calculate overall compliance score
            if compliance_factors:
                validation_result["compliance_score"] = sum(compliance_factors) / len(compliance_factors)
            
            # Determine overall validity
            validation_result["is_valid"] = (
                validation_result["compliance_score"] >= 0.8 and 
                len(validation_result["requirements_failed"]) == 0
            )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Failed to validate analysis requirements: {e}")
            return {
                "is_valid": False,
                "compliance_score": 0.0,
                "validation_issues": [f"Validation failed: {str(e)}"],
                "recommendations": ["Manual review required"],
                "requirements_met": [],
                "requirements_failed": ["Validation process failed"]
            }
    
    async def get_analysis_statistics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get analysis statistics for monitoring and reporting.
        
        Args:
            session_id: Optional session ID to filter statistics
            
        Returns:
            Dictionary with analysis statistics
        """
        try:
            db = await get_database()
            
            # Base query
            base_query = """
                SELECT 
                    COUNT(*) as total_analyses,
                    COUNT(CASE WHEN state = 'complete' THEN 1 END) as completed_analyses,
                    COUNT(CASE WHEN state = 'failed' THEN 1 END) as failed_analyses,
                    COUNT(CASE WHEN state IN ('queued', 'processing', 'finalizing') THEN 1 END) as active_analyses,
                    COUNT(CASE WHEN bog_file_id IS NOT NULL THEN 1 END) as bog_files_generated,
                    AVG(CASE WHEN state = 'complete' THEN 
                        CAST((analysis_data->>'quality_score')::text AS FLOAT) 
                    END) as avg_quality_score
                FROM analysis_results
            """
            
            if session_id:
                query = base_query + " WHERE session_id = $1"
                stats = await db.fetch_one(query, session_id)
            else:
                stats = await db.fetch_one(base_query)
            
            # Get recent analysis trends
            trend_query = """
                SELECT 
                    DATE(created_at) as analysis_date,
                    COUNT(*) as daily_count,
                    AVG(CASE WHEN state = 'complete' THEN 
                        CAST((analysis_data->>'quality_score')::text AS FLOAT) 
                    END) as daily_avg_quality
                FROM analysis_results
                WHERE created_at >= NOW() - INTERVAL '7 days'
            """
            
            if session_id:
                trend_query += " AND session_id = $1"
                trend_data = await db.fetch_all(trend_query, session_id)
            else:
                trend_data = await db.fetch_all(trend_query)
            
            trend_query += " GROUP BY DATE(created_at) ORDER BY analysis_date DESC"
            
            return {
                "total_analyses": stats["total_analyses"] or 0,
                "completed_analyses": stats["completed_analyses"] or 0,
                "failed_analyses": stats["failed_analyses"] or 0,
                "active_analyses": stats["active_analyses"] or 0,
                "bog_files_generated": stats["bog_files_generated"] or 0,
                "success_rate": (stats["completed_analyses"] or 0) / max(1, stats["total_analyses"] or 1),
                "avg_quality_score": float(stats["avg_quality_score"] or 0.0),
                "session_id": session_id,
                "daily_trends": [
                    {
                        "date": str(row["analysis_date"]),
                        "count": row["daily_count"],
                        "avg_quality": float(row["daily_avg_quality"] or 0.0)
                    }
                    for row in trend_data
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get analysis statistics: {e}")
            return {
                "total_analyses": 0,
                "completed_analyses": 0,
                "failed_analyses": 0,
                "active_analyses": 0,
                "bog_files_generated": 0,
                "success_rate": 0.0,
                "avg_quality_score": 0.0,
                "session_id": session_id,
                "daily_trends": [],
                "error": str(e)
            }
    
    # Helper methods
    
    async def _check_cancellation(self, analysis_id: int) -> bool:
        """Check if analysis has been cancelled."""
        async with self._lock:
            if self._cancellation_flags.get(analysis_id, False):
                await self._update_analysis_state(
                    analysis_id, AnalysisState.FAILED,
                    error_message="Analysis cancelled by user"
                )
                return True
        return False
    
    async def _update_analysis_state(self, analysis_id: int, state: AnalysisState,
                                   analysis_data: Optional[DocumentAnalysis] = None,
                                   error_message: Optional[str] = None,
                                   completed_at: Optional[datetime] = None) -> None:
        """Update analysis state in database."""
        try:
            db = await get_database()
            
            if analysis_data:
                query = """
                    UPDATE analysis_results 
                    SET state = $1, analysis_data = $2, error_message = $3, completed_at = $4
                    WHERE id = $5
                """
                await db.execute_query(
                    query, state.value, json.dumps(analysis_data.model_dump()), 
                    error_message, completed_at, analysis_id
                )
            else:
                query = """
                    UPDATE analysis_results 
                    SET state = $1, error_message = $2, completed_at = $3
                    WHERE id = $4
                """
                await db.execute_query(query, state.value, error_message, completed_at, analysis_id)
                
        except Exception as e:
            logger.error(f"Failed to update analysis state for {analysis_id}: {e}")
    
    async def _emit_progress_event(self, session_id: str, analysis_id: int, 
                                 operation: str, state: AnalysisState,
                                 message: str, progress_percent: Optional[float]) -> None:
        """Emit progress event to EventBus."""
        await self.event_bus.publish(
            session_id,
            Event(
                type="progress",
                session_id=session_id,
                operation=operation,
                data={
                    "analysis_id": analysis_id,
                    "state": state.value,
                    "message": message,
                    "operation": operation,
                    "progress_percent": progress_percent
                }
            )
        )
    
    async def _get_file_content(self, file_record: dict) -> str:
        """Get file content from database or filesystem."""
        try:
            if file_record['file_data']:
                # File stored as BYTEA
                return file_record['file_data'].decode('utf-8')
            elif file_record['file_path']:
                # File stored on filesystem
                with open(file_record['file_path'], 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                raise ValueError("File has no content data or path")
                
        except Exception as e:
            logger.error(f"Failed to get file content for file {file_record['id']}: {e}")
            raise
    
    def _convert_to_document_analysis(self, data: Dict[str, Any]) -> DocumentAnalysis:
        """Convert analysis data dictionary to DocumentAnalysis model with quality assessment."""
        try:
            # Convert IO points
            io_points = []
            for point_data in data.get('io_points', []):
                io_points.append(IOPoint(**point_data))
            
            # Convert control blocks
            control_blocks = []
            for block_data in data.get('control_blocks', []):
                control_blocks.append(ControlBlock(**block_data))
            
            # Convert pseudocode
            pseudocode = []
            for i, step_data in enumerate(data.get('pseudocode', []), 1):
                if isinstance(step_data, dict):
                    pseudocode.append(PseudocodeStep(
                        step=step_data.get('step', i),
                        description=step_data.get('description', ''),
                        code=step_data.get('code', '')
                    ))
            
            # Convert metadata
            metadata_data = data.get('metadata', {})
            metadata = AnalysisMetadata(
                document_type=metadata_data.get('document_type', 'unknown'),
                confidence=metadata_data.get('confidence', 0.0),
                recommendations=metadata_data.get('recommendations', [])
            )
            
            # Create initial analysis
            analysis = DocumentAnalysis(
                io_points=io_points,
                control_blocks=control_blocks,
                pseudocode=pseudocode,
                quality_score=data.get('quality_score', 0.0),
                issues=data.get('issues', []),
                metadata=metadata
            )
            
            # Perform quality assessment and validation
            return self._assess_analysis_quality(analysis)
            
        except Exception as e:
            logger.error(f"Failed to convert analysis data: {e}")
            # Return empty analysis on conversion failure
            return DocumentAnalysis()
    
    def _assess_analysis_quality(self, analysis: DocumentAnalysis) -> DocumentAnalysis:
        """Assess and validate analysis quality, updating quality score and issues."""
        try:
            quality_factors = []
            issues = list(analysis.issues)  # Copy existing issues
            recommendations = list(analysis.metadata.recommendations)  # Copy existing recommendations
            
            # Factor 1: IO Points completeness (0-30 points)
            io_score = 0
            if len(analysis.io_points) > 0:
                io_score = min(30, len(analysis.io_points) * 5)  # 5 points per IO point, max 30
                
                # Check for balanced input/output ratio
                inputs = [p for p in analysis.io_points if p.type.value == "input"]
                outputs = [p for p in analysis.io_points if p.type.value == "output"]
                
                if len(inputs) == 0:
                    issues.append("No input points identified - control system needs sensor inputs")
                    io_score *= 0.7
                elif len(outputs) == 0:
                    issues.append("No output points identified - control system needs actuator outputs")
                    io_score *= 0.7
                elif abs(len(inputs) - len(outputs)) > len(analysis.io_points) * 0.7:
                    issues.append("Unbalanced input/output ratio - verify point classifications")
                    io_score *= 0.9
                
                # Check for units and descriptions
                points_with_units = [p for p in analysis.io_points if p.units]
                points_with_descriptions = [p for p in analysis.io_points if p.description and len(p.description) > 10]
                
                if len(points_with_units) < len(analysis.io_points) * 0.5:
                    issues.append("Many IO points missing units - specify measurement units")
                    recommendations.append("Add units to IO points (°F, CFM, %RH, etc.)")
                
                if len(points_with_descriptions) < len(analysis.io_points) * 0.8:
                    issues.append("IO points need more detailed descriptions")
                    recommendations.append("Provide clear, descriptive names for all IO points")
            else:
                issues.append("No IO points identified - document may not contain control information")
                recommendations.append("Verify document contains HVAC control sequences with sensors and actuators")
            
            quality_factors.append(("IO Points", io_score))
            
            # Factor 2: Control Blocks completeness (0-25 points)
            control_score = 0
            if len(analysis.control_blocks) > 0:
                control_score = min(25, len(analysis.control_blocks) * 8)  # 8 points per block, max 25
                
                # Check control block complexity and logic
                total_complexity = sum(block.complexity for block in analysis.control_blocks)
                avg_complexity = total_complexity / len(analysis.control_blocks)
                
                if avg_complexity < 3:
                    issues.append("Control blocks appear overly simple - verify control logic detail")
                    recommendations.append("Add more detailed control logic and operational steps")
                elif avg_complexity > 8:
                    issues.append("Control blocks are very complex - consider breaking into smaller blocks")
                    recommendations.append("Simplify complex control blocks for better maintainability")
                
                # Check for logic steps
                blocks_with_logic = [b for b in analysis.control_blocks if b.logic and len(b.logic) > 2]
                if len(blocks_with_logic) < len(analysis.control_blocks) * 0.7:
                    issues.append("Control blocks need more detailed logic steps")
                    recommendations.append("Provide step-by-step control logic for each block")
                    control_score *= 0.8
            else:
                issues.append("No control blocks identified - document should contain control logic")
                recommendations.append("Identify and document control blocks (PID, Logic, Schedule, etc.)")
            
            quality_factors.append(("Control Blocks", control_score))
            
            # Factor 3: Pseudocode implementation (0-20 points)
            pseudocode_score = 0
            if len(analysis.pseudocode) > 0:
                pseudocode_score = min(20, len(analysis.pseudocode) * 3)  # 3 points per step, max 20
                
                # Check for implementation detail
                detailed_steps = [s for s in analysis.pseudocode if s.code and len(s.code) > 20]
                if len(detailed_steps) < len(analysis.pseudocode) * 0.6:
                    issues.append("Pseudocode steps need more implementation detail")
                    recommendations.append("Provide detailed pseudocode with conditions and actions")
                    pseudocode_score *= 0.8
            else:
                issues.append("No pseudocode generated - implementation steps missing")
                recommendations.append("Generate step-by-step pseudocode for control implementation")
            
            quality_factors.append(("Pseudocode", pseudocode_score))
            
            # Factor 4: Document type and confidence (0-15 points)
            metadata_score = 0
            if analysis.metadata.document_type != "unknown":
                metadata_score += 5
            
            if analysis.metadata.confidence > 0.7:
                metadata_score += 10
            elif analysis.metadata.confidence > 0.5:
                metadata_score += 7
            elif analysis.metadata.confidence > 0.3:
                metadata_score += 4
            
            quality_factors.append(("Metadata", metadata_score))
            
            # Factor 5: Issues and completeness (0-10 points)
            issues_score = 10
            if len(issues) > 5:
                issues_score = 5
            elif len(issues) > 2:
                issues_score = 7
            
            quality_factors.append(("Issues", issues_score))
            
            # Calculate final quality score (0-100 scale, then normalize to 0-1)
            total_score = sum(score for _, score in quality_factors)
            quality_score = min(1.0, total_score / 100.0)
            
            # Log quality assessment
            logger.info(f"Quality assessment: {quality_factors}, Final: {quality_score:.2f}")
            
            # Update analysis with quality assessment
            analysis.quality_score = quality_score
            analysis.issues = issues
            analysis.metadata.recommendations = recommendations
            
            # Add quality breakdown to metadata
            analysis.metadata.processing_time_seconds = None  # Will be set by caller if needed
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to assess analysis quality: {e}")
            # Return original analysis if assessment fails
            return analysis
    
    async def _generate_bog_content(self, analysis: DocumentAnalysis) -> str:
        """Generate PyBOG file content from analysis using the integrated PyBOG builder."""
        try:
            from bog_builder import BogFolderBuilder
            
            # Create BOG builder with analysis-based folder name
            folder_name = f"Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            builder = BogFolderBuilder(folder_name, debug=False)
            
            # Add input points as writables
            for point in analysis.io_points:
                if point.type.value == "input":
                    if point.data_type.value == "boolean":
                        builder.add_boolean_writable(
                            name=self._sanitize_component_name(point.name),
                            default_value=False
                        )
                    elif point.data_type.value == "numeric":
                        builder.add_numeric_writable(
                            name=self._sanitize_component_name(point.name),
                            default_value=0.0,
                            precision=2
                        )
            
            # Add control blocks as components
            for block in analysis.control_blocks:
                block_name = self._sanitize_component_name(block.name)
                
                if block.type.lower() == "pid":
                    # Add PID control components
                    builder.add_loop_point(
                        name=f"{block_name}_PID",
                        properties={
                            "proportionalConstant": 1.0,
                            "integralConstant": 0.1,
                            "derivativeConstant": 0.0
                        }
                    )
                elif block.type.lower() == "logic":
                    # Add logic components based on complexity
                    if block.complexity <= 3:
                        builder.add_boolean_switch(name=f"{block_name}_Switch")
                    else:
                        builder.add_numeric_select(name=f"{block_name}_Select")
                elif block.type.lower() == "schedule":
                    # Add schedule component
                    builder.add_boolean_schedule(
                        name=f"{block_name}_Schedule",
                        properties={"defaultValue": "false"}
                    )
                else:
                    # Default to numeric writable for unknown types
                    builder.add_numeric_writable(
                        name=f"{block_name}_Control",
                        default_value=0.0
                    )
            
            # Add output points as constants or writables
            for point in analysis.io_points:
                if point.type.value == "output":
                    if point.data_type.value == "boolean":
                        builder.add_boolean_writable(
                            name=self._sanitize_component_name(f"{point.name}_Output"),
                            default_value=False
                        )
                    elif point.data_type.value == "numeric":
                        builder.add_numeric_writable(
                            name=self._sanitize_component_name(f"{point.name}_Output"),
                            default_value=0.0,
                            precision=2
                        )
            
            # Add basic linking for simple control loops
            self._add_basic_control_links(builder, analysis)
            
            # Generate BOG file content to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.bog', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                builder.save(temp_path)
                
                # Read the generated BOG file
                with open(temp_path, 'rb') as bog_file:
                    bog_content = bog_file.read()
                
                # Clean up temporary file
                os.unlink(temp_path)
                
                # Return as string (BOG files are binary but we'll store as base64 or handle as bytes)
                return bog_content.decode('utf-8', errors='replace')
                
            except Exception as e:
                # Clean up on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise e
            
        except Exception as e:
            logger.error(f"Failed to generate BOG content with PyBOG builder: {e}")
            
            # Fallback to simple text-based BOG content
            return self._generate_fallback_bog_content(analysis)
    
    def _sanitize_component_name(self, name: str) -> str:
        """Sanitize component name for PyBOG builder compatibility."""
        import re
        # Replace invalid characters with underscores
        sanitized = re.sub(r'[^A-Za-z0-9_]', '_', name)
        # Ensure it starts with a letter or underscore
        if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
            sanitized = f"Comp_{sanitized}"
        # Ensure it's not empty
        if not sanitized:
            sanitized = "Component"
        return sanitized
    
    def _add_basic_control_links(self, builder: 'BogFolderBuilder', analysis: DocumentAnalysis) -> None:
        """Add basic control links between components."""
        try:
            # Simple linking strategy: connect inputs to control blocks to outputs
            input_points = [p for p in analysis.io_points if p.type.value == "input"]
            output_points = [p for p in analysis.io_points if p.type.value == "output"]
            
            # For each control block, try to link appropriate inputs and outputs
            for i, block in enumerate(analysis.control_blocks):
                block_name = self._sanitize_component_name(block.name)
                
                # Link first available input to control block
                if i < len(input_points) and input_points[i]:
                    input_name = self._sanitize_component_name(input_points[i].name)
                    try:
                        if block.type.lower() == "pid":
                            builder.add_link(
                                source_comp_name=input_name,
                                source_slot="out",
                                target_comp_name=f"{block_name}_PID",
                                target_slot="controlledVariable"
                            )
                        else:
                            # Generic linking for other block types
                            target_comp = f"{block_name}_Control"
                            if block.type.lower() == "logic":
                                target_comp = f"{block_name}_Switch"
                                builder.add_link(
                                    source_comp_name=input_name,
                                    source_slot="out",
                                    target_comp_name=target_comp,
                                    target_slot="inSwitch"
                                )
                    except Exception as link_error:
                        logger.warning(f"Failed to add link for {block_name}: {link_error}")
                        
        except Exception as e:
            logger.warning(f"Failed to add control links: {e}")
    
    def _generate_fallback_bog_content(self, analysis: DocumentAnalysis) -> str:
        """Generate fallback BOG content as text when PyBOG builder fails."""
        bog_lines = [
            "# PyBOG File Generated from Document Analysis",
            f"# Generated at: {datetime.now().isoformat()}",
            f"# Quality Score: {analysis.quality_score:.2f}",
            "",
            "# Input/Output Points",
        ]
        
        for point in analysis.io_points:
            units_str = f" ({point.units})" if point.units else ""
            bog_lines.append(
                f"# {point.type.value.upper()}: {point.name} [{point.data_type.value}]{units_str} - {point.description}"
            )
        
        bog_lines.extend([
            "",
            "# Control Blocks",
        ])
        
        for block in analysis.control_blocks:
            bog_lines.append(f"# Block: {block.name} (Type: {block.type}, Complexity: {block.complexity})")
            bog_lines.append(f"# Description: {block.description}")
            bog_lines.append("# Logic Steps:")
            for step in block.logic:
                bog_lines.append(f"#   - {step}")
            bog_lines.append("")
        
        bog_lines.extend([
            "",
            "# Pseudocode Implementation",
        ])
        
        for step in analysis.pseudocode:
            bog_lines.append(f"# Step {step.step}: {step.description}")
            bog_lines.append(f"# Code: {step.code}")
            bog_lines.append("")
        
        if analysis.issues:
            bog_lines.extend([
                "",
                "# Analysis Issues",
            ])
            for issue in analysis.issues:
                bog_lines.append(f"# ISSUE: {issue}")
        
        bog_lines.extend([
            "",
            f"# Analysis Metadata",
            f"# Document Type: {analysis.metadata.document_type}",
            f"# Confidence: {analysis.metadata.confidence:.2f}",
            "",
            "# Recommendations:",
        ])
        
        for rec in analysis.metadata.recommendations:
            bog_lines.append(f"# - {rec}")
        
        return "\n".join(bog_lines)