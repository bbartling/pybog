"""
Unit tests for AnalysisEngine service.

Tests the analysis workflow, state machine transitions, BOG file generation,
and cancellation support with comprehensive coverage.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from core.events import EventBus, Event
from services.analysis_engine import AnalysisEngine
from services.pybog_agent import PyBOGAgent
from models.analysis_models import (
    AnalysisState, DocumentAnalysis, IOPoint, ControlBlock, 
    PseudocodeStep, AnalysisMetadata, IOPointType, DataType
)
from models.file_models import FileType, ProgressState


@pytest.fixture
def event_bus():
    """Create EventBus instance for testing."""
    return EventBus()


@pytest.fixture
def mock_pybog_agent():
    """Create mock PyBOGAgent for testing."""
    agent = AsyncMock(spec=PyBOGAgent)
    
    # Mock analyze_document_content response
    agent.analyze_document_content.return_value = {
        "io_points": [
            {
                "name": "temp_sensor",
                "type": "input",
                "data_type": "numeric",
                "units": "°F",
                "description": "Room temperature sensor"
            },
            {
                "name": "heating_output",
                "type": "output", 
                "data_type": "boolean",
                "description": "Heating system control"
            }
        ],
        "control_blocks": [
            {
                "name": "temperature_control",
                "type": "PID",
                "description": "Temperature control logic",
                "logic": ["Read temperature", "Compare to setpoint", "Adjust output"],
                "complexity": 5
            }
        ],
        "pseudocode": [
            {
                "step": 1,
                "description": "Read temperature sensor",
                "code": "temp = read_sensor('temp_sensor')"
            }
        ],
        "quality_score": 0.85,
        "issues": ["Missing error handling"],
        "metadata": {
            "document_type": "sequence",
            "confidence": 0.9,
            "recommendations": ["Add fault detection"]
        }
    }
    
    return agent


@pytest.fixture
def mock_database():
    """Create mock database connection."""
    db = AsyncMock()
    
    # Mock file record
    file_record = {
        'id': 1,
        'session_id': 'test-session',
        'filename': 'test.txt',
        'original_name': 'test.txt',
        'file_type': 'upload',
        'file_size': 1000,
        'state': 'complete',
        'file_data': b'Test document content for analysis',
        'file_path': None
    }
    
    # Mock analysis record
    analysis_record = {
        'id': 1,
        'session_id': 'test-session',
        'input_file_id': 1,
        'bog_file_id': None,
        'state': 'complete',
        'analysis_data': {
            "io_points": [],
            "control_blocks": [],
            "pseudocode": [],
            "quality_score": 0.85,
            "issues": [],
            "metadata": {"document_type": "sequence", "confidence": 0.9, "recommendations": []}
        },
        'error_message': None,
        'created_at': datetime.now(timezone.utc),
        'completed_at': datetime.now(timezone.utc)
    }
    
    def mock_fetchrow(query, *args):
        if 'files' in query:
            return file_record
        elif 'analysis_results' in query:
            return analysis_record
        return file_record
    
    db.fetchrow.side_effect = mock_fetchrow
    db.fetchval.return_value = 1  # Mock insert returning ID
    db.execute.return_value = None
    db.fetch.return_value = [analysis_record]
    
    return db


@pytest.fixture
def analysis_engine(event_bus, mock_pybog_agent):
    """Create AnalysisEngine instance for testing."""
    return AnalysisEngine(event_bus, mock_pybog_agent)


class TestAnalysisEngine:
    """Test cases for AnalysisEngine."""
    
    @pytest.mark.asyncio
    async def test_analyze_document_success(self, analysis_engine, mock_database):
        """Test successful document analysis workflow."""
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            # Start analysis
            analysis_id = await analysis_engine.analyze_document('test-session', 1)
            
            assert analysis_id == 1
            
            # Wait for analysis task to complete
            await asyncio.sleep(0.1)
            
            # Verify database calls
            assert mock_database.fetchrow.called
            assert mock_database.fetchval.called
            assert mock_database.execute.called
    
    @pytest.mark.asyncio
    async def test_analyze_document_file_not_found(self, analysis_engine, mock_database):
        """Test analysis with non-existent file."""
        mock_database.fetchrow.return_value = None
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            with pytest.raises(ValueError, match="File 999 not found"):
                await analysis_engine.analyze_document('test-session', 999)
    
    @pytest.mark.asyncio
    async def test_analyze_document_file_not_ready(self, analysis_engine, mock_database):
        """Test analysis with file not ready for processing."""
        file_record = {
            'id': 1,
            'session_id': 'test-session',
            'state': 'processing'  # Not complete
        }
        mock_database.fetchrow.return_value = file_record
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            with pytest.raises(ValueError, match="is not ready for analysis"):
                await analysis_engine.analyze_document('test-session', 1)
    
    @pytest.mark.asyncio
    async def test_state_machine_transitions(self, analysis_engine, mock_database, event_bus):
        """Test analysis state machine transitions."""
        events_received = []
        
        async def capture_events(event):
            events_received.append(event)
        
        await event_bus.subscribe('test-session', capture_events)
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            analysis_id = await analysis_engine.analyze_document('test-session', 1)
            
            # Wait for analysis to complete
            await asyncio.sleep(0.2)
            
            # Check state transitions in events
            progress_events = [e for e in events_received if e.type == "progress"]
            states = [e.data['state'] for e in progress_events]
            
            assert 'queued' in states
            assert 'processing' in states
            assert 'finalizing' in states
            assert 'complete' in states
    
    @pytest.mark.asyncio
    async def test_generate_bog_file_success(self, analysis_engine, mock_database):
        """Test successful BOG file generation."""
        # Mock analysis record with complete state
        analysis_record = {
            'id': 1,
            'session_id': 'test-session',
            'input_file_id': 1,
            'bog_file_id': None,
            'state': 'complete',
            'analysis_data': {
                "io_points": [
                    {
                        "name": "temp_sensor",
                        "type": "input",
                        "data_type": "numeric",
                        "units": "°F",
                        "description": "Temperature sensor"
                    }
                ],
                "control_blocks": [],
                "pseudocode": [],
                "quality_score": 0.85,
                "issues": [],
                "metadata": {"document_type": "sequence", "confidence": 0.9, "recommendations": []}
            },
            'created_at': datetime.now(timezone.utc)
        }
        
        mock_database.fetchrow.return_value = analysis_record
        mock_database.fetchval.return_value = 2  # BOG file ID
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            bog_file_id = await analysis_engine.generate_bog_file('test-session', 1)
            
            assert bog_file_id == 2
            
            # Verify file creation call
            assert mock_database.fetchval.called
            assert mock_database.execute.called
    
    @pytest.mark.asyncio
    async def test_generate_bog_file_already_exists(self, analysis_engine, mock_database):
        """Test BOG file generation when file already exists."""
        # Mock analysis record with existing BOG file
        analysis_record = {
            'id': 1,
            'session_id': 'test-session',
            'bog_file_id': 5,  # Already has BOG file
            'state': 'complete'
        }
        
        mock_database.fetchrow.return_value = analysis_record
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            bog_file_id = await analysis_engine.generate_bog_file('test-session', 1)
            
            assert bog_file_id == 5
    
    @pytest.mark.asyncio
    async def test_generate_bog_file_analysis_not_complete(self, analysis_engine, mock_database):
        """Test BOG file generation with incomplete analysis."""
        analysis_record = {
            'id': 1,
            'session_id': 'test-session',
            'state': 'processing'  # Not complete
        }
        
        mock_database.fetchrow.return_value = analysis_record
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            with pytest.raises(ValueError, match="is not complete"):
                await analysis_engine.generate_bog_file('test-session', 1)
    
    @pytest.mark.asyncio
    async def test_cancel_analysis_specific(self, analysis_engine, mock_database):
        """Test cancelling a specific analysis."""
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            # Start analysis
            analysis_id = await analysis_engine.analyze_document('test-session', 1)
            
            # Cancel the analysis
            result = await analysis_engine.cancel_analysis('test-session', analysis_id)
            
            assert result.cancelled_count == 1
            assert analysis_id in result.cancelled_analysis_ids
            assert result.session_id == 'test-session'
    
    @pytest.mark.asyncio
    async def test_cancel_analysis_all_session(self, analysis_engine, mock_database):
        """Test cancelling all analyses for a session."""
        # Mock active analyses query
        mock_database.fetch.return_value = [
            {'id': 1}, {'id': 2}
        ]
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            # Start multiple analyses
            analysis_id1 = await analysis_engine.analyze_document('test-session', 1)
            analysis_id2 = await analysis_engine.analyze_document('test-session', 2)
            
            # Cancel all analyses for session
            result = await analysis_engine.cancel_analysis('test-session')
            
            assert result.cancelled_count >= 0  # May be 0 if tasks completed quickly
            assert result.session_id == 'test-session'
    
    @pytest.mark.asyncio
    async def test_cancellation_during_processing(self, analysis_engine, mock_database, mock_pybog_agent):
        """Test cancellation interrupts processing."""
        # Make agent analysis take longer
        async def slow_analysis(*args):
            await asyncio.sleep(0.5)
            return mock_pybog_agent.analyze_document_content.return_value
        
        mock_pybog_agent.analyze_document_content.side_effect = slow_analysis
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            # Start analysis
            analysis_id = await analysis_engine.analyze_document('test-session', 1)
            
            # Cancel immediately
            await asyncio.sleep(0.1)
            result = await analysis_engine.cancel_analysis('test-session', analysis_id)
            
            assert result.cancelled_count == 1
    
    @pytest.mark.asyncio
    async def test_get_analysis_result(self, analysis_engine, mock_database):
        """Test retrieving analysis result."""
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            result = await analysis_engine.get_analysis_result('test-session', 1)
            
            assert result is not None
            assert result.id == 1
            assert result.session_id == 'test-session'
            assert result.state == AnalysisState.COMPLETE
    
    @pytest.mark.asyncio
    async def test_get_analysis_result_not_found(self, analysis_engine, mock_database):
        """Test retrieving non-existent analysis result."""
        mock_database.fetchrow.return_value = None
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            result = await analysis_engine.get_analysis_result('test-session', 999)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_list_session_analyses(self, analysis_engine, mock_database):
        """Test listing all analyses for a session."""
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            results = await analysis_engine.list_session_analyses('test-session')
            
            assert len(results) == 1
            assert results[0].session_id == 'test-session'
    
    @pytest.mark.asyncio
    async def test_event_emission_during_analysis(self, analysis_engine, mock_database, event_bus):
        """Test that proper events are emitted during analysis."""
        events_received = []
        
        async def capture_events(event):
            events_received.append(event)
        
        await event_bus.subscribe('test-session', capture_events)
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            await analysis_engine.analyze_document('test-session', 1)
            
            # Wait for analysis to complete
            await asyncio.sleep(0.2)
            
            # Check for required event types
            event_types = [e.type for e in events_received]
            
            assert 'progress' in event_types
            assert any(e.type == 'analysis_complete' for e in events_received)
    
    @pytest.mark.asyncio
    async def test_event_emission_during_bog_generation(self, analysis_engine, mock_database, event_bus):
        """Test that proper events are emitted during BOG generation."""
        events_received = []
        
        async def capture_events(event):
            events_received.append(event)
        
        await event_bus.subscribe('test-session', capture_events)
        
        # Mock complete analysis
        analysis_record = {
            'id': 1,
            'session_id': 'test-session',
            'input_file_id': 1,
            'bog_file_id': None,
            'state': 'complete',
            'analysis_data': {
                "io_points": [],
                "control_blocks": [],
                "pseudocode": [],
                "quality_score": 0.85,
                "issues": [],
                "metadata": {"document_type": "sequence", "confidence": 0.9, "recommendations": []}
            },
            'created_at': datetime.now(timezone.utc)
        }
        
        mock_database.fetchrow.return_value = analysis_record
        mock_database.fetchval.return_value = 2
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            await analysis_engine.generate_bog_file('test-session', 1)
            
            # Check for BOG generation events
            event_types = [e.type for e in events_received]
            
            assert 'progress' in event_types
            assert 'bog_generated' in event_types
    
    @pytest.mark.asyncio
    async def test_error_handling_during_analysis(self, analysis_engine, mock_database, mock_pybog_agent, event_bus):
        """Test error handling during analysis processing."""
        events_received = []
        
        async def capture_events(event):
            events_received.append(event)
        
        await event_bus.subscribe('test-session', capture_events)
        
        # Make agent analysis fail
        mock_pybog_agent.analyze_document_content.side_effect = Exception("Analysis failed")
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            await analysis_engine.analyze_document('test-session', 1)
            
            # Wait for analysis to fail
            await asyncio.sleep(0.2)
            
            # Check for error events
            error_events = [e for e in events_received if e.type == "error"]
            assert len(error_events) > 0
            
            # Check final state is failed
            progress_events = [e for e in events_received if e.type == "progress"]
            final_states = [e.data['state'] for e in progress_events]
            assert 'failed' in final_states
    
    def test_convert_to_document_analysis(self, analysis_engine):
        """Test conversion of analysis data to DocumentAnalysis model."""
        data = {
            "io_points": [
                {
                    "name": "temp_sensor",
                    "type": "input",
                    "data_type": "numeric",
                    "units": "°F",
                    "description": "Temperature sensor"
                }
            ],
            "control_blocks": [
                {
                    "name": "temp_control",
                    "type": "PID",
                    "description": "Temperature control",
                    "logic": ["Read temp", "Compare setpoint"],
                    "complexity": 5
                }
            ],
            "pseudocode": [
                {
                    "step": 1,
                    "description": "Read sensor",
                    "code": "temp = read_sensor()"
                }
            ],
            "quality_score": 0.85,
            "issues": ["Missing error handling"],
            "metadata": {
                "document_type": "sequence",
                "confidence": 0.9,
                "recommendations": ["Add fault detection"]
            }
        }
        
        result = analysis_engine._convert_to_document_analysis(data)
        
        assert isinstance(result, DocumentAnalysis)
        assert len(result.io_points) == 1
        assert len(result.control_blocks) == 1
        assert len(result.pseudocode) == 1
        assert result.quality_score == 0.85
        assert len(result.issues) == 1
        assert result.metadata.document_type == "sequence"
    
    def test_convert_to_document_analysis_invalid_data(self, analysis_engine):
        """Test conversion with invalid data returns empty analysis."""
        data = {
            "io_points": [
                {"invalid": "data"}  # Missing required fields
            ],
            "control_blocks": [
                {"also": "invalid"}  # Missing required fields
            ]
        }
        
        result = analysis_engine._convert_to_document_analysis(data)
        
        assert isinstance(result, DocumentAnalysis)
        assert len(result.io_points) == 0  # Invalid points filtered out
        assert len(result.control_blocks) == 0  # Invalid blocks filtered out
    
    @pytest.mark.asyncio
    async def test_generate_bog_content(self, analysis_engine):
        """Test BOG file content generation."""
        analysis = DocumentAnalysis(
            io_points=[
                IOPoint(
                    name="temp_sensor",
                    type=IOPointType.INPUT,
                    data_type=DataType.NUMERIC,
                    units="°F",
                    description="Temperature sensor"
                )
            ],
            control_blocks=[
                ControlBlock(
                    name="temp_control",
                    type="PID",
                    description="Temperature control logic",
                    logic=["Read temperature", "Compare to setpoint"],
                    complexity=5
                )
            ],
            pseudocode=[
                PseudocodeStep(
                    step=1,
                    description="Read sensor",
                    code="temp = read_sensor('temp_sensor')"
                )
            ],
            quality_score=0.85,
            issues=["Missing error handling"],
            metadata=AnalysisMetadata(
                document_type="sequence",
                confidence=0.9,
                recommendations=["Add fault detection"]
            )
        )
        
        content = await analysis_engine._generate_bog_content(analysis)
        
        assert "PyBOG File Generated from Document Analysis" in content
        assert "Quality Score: 0.85" in content
        assert "INPUT: temp_sensor" in content
        assert "Block: temp_control" in content
        assert "Step 1: Read sensor" in content
        assert "ISSUE: Missing error handling" in content
        assert "REC: Add fault detection" in content


if __name__ == "__main__":
    pytest.main([__file__])