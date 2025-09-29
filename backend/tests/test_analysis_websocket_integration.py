"""
Integration tests for AnalysisEngine WebSocket streaming.

Tests that analysis state machine transitions stream correctly via WebSocket
and that the complete workflow integrates properly with the event system.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from core.events import EventBus, Event
from services.analysis_engine import AnalysisEngine
from services.pybog_agent import PyBOGAgent
# from services.websocket_manager import WebSocketManager
from models.analysis_models import AnalysisState
# from models.websocket_models import WebSocketMessage


@pytest.fixture
def event_bus():
    """Create EventBus instance for testing."""
    return EventBus()


@pytest.fixture
def mock_pybog_agent():
    """Create mock PyBOGAgent for testing."""
    agent = AsyncMock(spec=PyBOGAgent)
    
    # Mock analyze_document_content with realistic response
    agent.analyze_document_content.return_value = {
        "io_points": [
            {
                "name": "zone_temp",
                "type": "input",
                "data_type": "numeric",
                "units": "°F",
                "description": "Zone temperature sensor"
            },
            {
                "name": "damper_position",
                "type": "output",
                "data_type": "numeric",
                "units": "%",
                "description": "VAV damper position"
            }
        ],
        "control_blocks": [
            {
                "name": "vav_control",
                "type": "PID",
                "description": "VAV box temperature control",
                "logic": [
                    "Read zone temperature",
                    "Compare to setpoint",
                    "Calculate PID output",
                    "Modulate damper position"
                ],
                "complexity": 6
            }
        ],
        "pseudocode": [
            {
                "step": 1,
                "description": "Initialize control loop",
                "code": "setpoint = get_zone_setpoint()"
            },
            {
                "step": 2,
                "description": "Read current temperature",
                "code": "current_temp = read_sensor('zone_temp')"
            }
        ],
        "quality_score": 0.92,
        "issues": [],
        "metadata": {
            "document_type": "sequence",
            "confidence": 0.95,
            "recommendations": ["Consider adding occupancy override"]
        }
    }
    
    return agent


@pytest.fixture
def mock_database():
    """Create mock database connection."""
    db = AsyncMock()
    
    # Mock file record for HVAC document
    file_record = {
        'id': 1,
        'session_id': 'hvac-session-1',
        'filename': 'vav_sequence.pdf',
        'original_name': 'VAV Control Sequence.pdf',
        'file_type': 'upload',
        'file_size': 2500,
        'state': 'complete',
        'file_data': b'VAV Box Control Sequence\n\nThe VAV box shall maintain zone temperature by modulating the damper position...',
        'file_path': None
    }
    
    # Mock analysis record
    analysis_record = {
        'id': 1,
        'session_id': 'hvac-session-1',
        'input_file_id': 1,
        'bog_file_id': None,
        'state': 'complete',
        'analysis_data': {
            "io_points": [],
            "control_blocks": [],
            "pseudocode": [],
            "quality_score": 0.92,
            "issues": [],
            "metadata": {"document_type": "sequence", "confidence": 0.95, "recommendations": []}
        },
        'created_at': datetime.now(timezone.utc)
    }
    
    db.fetchrow.side_effect = lambda query, *args: {
        'SELECT id, session_id, filename': file_record,
        'SELECT id, session_id, input_file_id': analysis_record
    }.get(query.split('FROM')[0].strip(), file_record)
    
    db.fetchval.return_value = 1  # Mock insert returning ID
    db.execute.return_value = None
    db.fetch.return_value = [analysis_record]
    
    return db


# @pytest.fixture
# def websocket_manager(event_bus):
#     """Create WebSocketManager for testing."""
#     return WebSocketManager(event_bus)


@pytest.fixture
def analysis_engine(event_bus, mock_pybog_agent):
    """Create AnalysisEngine instance for testing."""
    return AnalysisEngine(event_bus, mock_pybog_agent)


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.messages_sent = []
        self.closed = False
    
    async def send_text(self, message: str):
        """Mock send_text method."""
        if not self.closed:
            self.messages_sent.append(message)
    
    async def close(self):
        """Mock close method."""
        self.closed = True


class WebSocketMessage:
    """Mock WebSocket message for testing."""
    
    def __init__(self, type: str, session_id: str, data: dict, timestamp: datetime):
        self.type = type
        self.session_id = session_id
        self.data = data
        self.timestamp = timestamp
    
    def model_dump_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps({
            'type': self.type,
            'session_id': self.session_id,
            'data': self.data,
            'timestamp': self.timestamp.isoformat()
        })


class TestAnalysisWebSocketIntegration:
    """Integration tests for analysis engine WebSocket streaming."""
    
    @pytest.mark.asyncio
    async def test_complete_analysis_workflow_streaming(self, analysis_engine, 
                                                       event_bus, mock_database):
        """Test complete analysis workflow with WebSocket streaming."""
        # Create mock WebSocket
        mock_websocket = MockWebSocket()
        
        # Track all WebSocket messages
        websocket_messages = []
        
        # Mock WebSocket manager to capture messages
        async def mock_handle_session_events(event):
            # Convert event to WebSocket message format
            if event.type == "progress":
                message = WebSocketMessage(
                    type="progress",
                    session_id=event.session_id,
                    data=event.data,
                    timestamp=datetime.now(timezone.utc)
                )
            elif event.type == "analysis_complete":
                message = WebSocketMessage(
                    type="analysis_complete",
                    session_id=event.session_id,
                    data=event.data,
                    timestamp=datetime.now(timezone.utc)
                )
            elif event.type == "error":
                message = WebSocketMessage(
                    type="error",
                    session_id=event.session_id,
                    data=event.data,
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                return
            
            websocket_messages.append(message)
            await mock_websocket.send_text(message.model_dump_json())
        
        # Subscribe WebSocket manager to events
        await event_bus.subscribe('hvac-session-1', mock_handle_session_events)
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            # Start analysis
            analysis_id = await analysis_engine.analyze_document('hvac-session-1', 1)
            
            # Wait for analysis to complete
            await asyncio.sleep(0.3)
            
            # Verify WebSocket messages were sent
            assert len(mock_websocket.messages_sent) > 0
            
            # Parse and verify message sequence
            messages = [json.loads(msg) for msg in mock_websocket.messages_sent]
            
            # Check for state transitions in messages
            progress_messages = [msg for msg in messages if msg['type'] == 'progress']
            states_received = [msg['data']['state'] for msg in progress_messages]
            
            # Verify state machine progression
            assert 'queued' in states_received
            assert 'processing' in states_received
            assert 'finalizing' in states_received
            assert 'complete' in states_received
            
            # Verify state transitions are in correct order
            queued_idx = states_received.index('queued')
            processing_idx = states_received.index('processing')
            finalizing_idx = states_received.index('finalizing')
            complete_idx = states_received.index('complete')
            
            assert queued_idx < processing_idx < finalizing_idx < complete_idx
            
            # Check for analysis complete message
            complete_messages = [msg for msg in messages if msg['type'] == 'analysis_complete']
            assert len(complete_messages) == 1
            
            complete_data = complete_messages[0]['data']
            assert complete_data['analysis_id'] == analysis_id
            assert complete_data['file_id'] == 1
            assert 'quality_score' in complete_data
    
    @pytest.mark.asyncio
    async def test_analysis_progress_percentages(self, analysis_engine, event_bus, mock_database):
        """Test that progress percentages are properly streamed."""
        progress_updates = []
        
        async def capture_progress(event):
            if event.type == "progress":
                progress_updates.append(event.data)
        
        await event_bus.subscribe('hvac-session-1', capture_progress)
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            await analysis_engine.analyze_document('hvac-session-1', 1)
            
            # Wait for analysis to complete
            await asyncio.sleep(0.3)
            
            # Check progress percentages
            progress_with_percent = [
                update for update in progress_updates 
                if update.get('progress_percent') is not None
            ]
            
            assert len(progress_with_percent) > 0
            
            # Verify progress increases over time
            percentages = [update['progress_percent'] for update in progress_with_percent]
            assert percentages[0] <= percentages[-1]  # Should increase or stay same
    
    @pytest.mark.asyncio
    async def test_bog_generation_streaming(self, analysis_engine, event_bus, mock_database):
        """Test BOG file generation streaming via WebSocket."""
        bog_events = []
        
        async def capture_bog_events(event):
            if event.type in ["progress", "bog_generated"]:
                bog_events.append(event)
        
        await event_bus.subscribe('hvac-session-1', capture_bog_events)
        
        # Mock complete analysis for BOG generation
        analysis_record = {
            'id': 1,
            'session_id': 'hvac-session-1',
            'input_file_id': 1,
            'bog_file_id': None,
            'state': 'complete',
            'analysis_data': {
                "io_points": [
                    {
                        "name": "zone_temp",
                        "type": "input",
                        "data_type": "numeric",
                        "units": "°F",
                        "description": "Zone temperature"
                    }
                ],
                "control_blocks": [],
                "pseudocode": [],
                "quality_score": 0.92,
                "issues": [],
                "metadata": {"document_type": "sequence", "confidence": 0.95, "recommendations": []}
            },
            'created_at': datetime.now(timezone.utc)
        }
        
        mock_database.fetchrow.return_value = analysis_record
        mock_database.fetchval.return_value = 2  # BOG file ID
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            bog_file_id = await analysis_engine.generate_bog_file('hvac-session-1', 1)
            
            # Check for BOG generation events
            progress_events = [e for e in bog_events if e.type == "progress"]
            bog_generated_events = [e for e in bog_events if e.type == "bog_generated"]
            
            assert len(progress_events) > 0
            assert len(bog_generated_events) == 1
            
            # Verify BOG generated event data
            bog_event = bog_generated_events[0]
            assert bog_event.data['file_id'] == bog_file_id
            assert bog_event.data['analysis_id'] == 1
            assert 'filename' in bog_event.data
            assert 'analysis' in bog_event.data
    
    @pytest.mark.asyncio
    async def test_cancellation_streaming(self, analysis_engine, event_bus, mock_database, mock_pybog_agent):
        """Test analysis cancellation streaming via WebSocket."""
        cancellation_events = []
        
        async def capture_cancellation_events(event):
            if event.type in ["progress", "cancellation_complete"]:
                cancellation_events.append(event)
        
        await event_bus.subscribe('hvac-session-1', capture_cancellation_events)
        
        # Make analysis take longer to allow cancellation
        async def slow_analysis(*args):
            await asyncio.sleep(0.5)
            return mock_pybog_agent.analyze_document_content.return_value
        
        mock_pybog_agent.analyze_document_content.side_effect = slow_analysis
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            # Start analysis
            analysis_id = await analysis_engine.analyze_document('hvac-session-1', 1)
            
            # Cancel after short delay
            await asyncio.sleep(0.1)
            result = await analysis_engine.cancel_analysis('hvac-session-1', analysis_id)
            
            # Wait for cancellation to complete
            await asyncio.sleep(0.2)
            
            # Check for cancellation events
            progress_events = [e for e in cancellation_events if e.type == "progress"]
            cancellation_complete_events = [e for e in cancellation_events if e.type == "cancellation_complete"]
            
            # Should have progress events showing failed state
            failed_progress = [e for e in progress_events if e.data.get('state') == 'failed']
            assert len(failed_progress) > 0
            
            # Should have cancellation complete event
            assert len(cancellation_complete_events) == 1
            
            cancellation_data = cancellation_complete_events[0].data
            assert cancellation_data['cancelled_count'] >= 1
            assert analysis_id in cancellation_data['cancelled_analysis_ids']
    
    @pytest.mark.asyncio
    async def test_error_handling_streaming(self, analysis_engine, event_bus, mock_database, mock_pybog_agent):
        """Test error handling streaming via WebSocket."""
        error_events = []
        
        async def capture_error_events(event):
            if event.type in ["progress", "error"]:
                error_events.append(event)
        
        await event_bus.subscribe('hvac-session-1', capture_error_events)
        
        # Make analysis fail
        mock_pybog_agent.analyze_document_content.side_effect = Exception("AI service unavailable")
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            await analysis_engine.analyze_document('hvac-session-1', 1)
            
            # Wait for analysis to fail
            await asyncio.sleep(0.3)
            
            # Check for error events
            progress_events = [e for e in error_events if e.type == "progress"]
            error_events_list = [e for e in error_events if e.type == "error"]
            
            # Should have progress events showing failed state
            failed_progress = [e for e in progress_events if e.data.get('state') == 'failed']
            assert len(failed_progress) > 0
            
            # Should have error event
            assert len(error_events_list) > 0
            
            error_data = error_events_list[0].data
            assert error_data['error_code'] == 'ANALYSIS'
            assert 'AI service unavailable' in error_data['message']
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_analyses(self, analysis_engine, event_bus, mock_database):
        """Test multiple concurrent analyses don't interfere with each other."""
        session1_events = []
        session2_events = []
        
        async def capture_session1_events(event):
            if event.session_id == 'session-1':
                session1_events.append(event)
        
        async def capture_session2_events(event):
            if event.session_id == 'session-2':
                session2_events.append(event)
        
        await event_bus.subscribe('session-1', capture_session1_events)
        await event_bus.subscribe('session-2', capture_session2_events)
        
        # Mock different file records for each session
        def mock_fetchrow(query, *args):
            session_id = args[1] if len(args) > 1 else args[0]
            return {
                'id': 1 if session_id == 'session-1' else 2,
                'session_id': session_id,
                'filename': f'test_{session_id}.txt',
                'original_name': f'test_{session_id}.txt',
                'file_type': 'upload',
                'file_size': 1000,
                'state': 'complete',
                'file_data': f'Test content for {session_id}'.encode(),
                'file_path': None
            }
        
        mock_database.fetchrow.side_effect = mock_fetchrow
        
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            # Start analyses for both sessions
            analysis_id1 = await analysis_engine.analyze_document('session-1', 1)
            analysis_id2 = await analysis_engine.analyze_document('session-2', 2)
            
            # Wait for both to complete
            await asyncio.sleep(0.4)
            
            # Verify both sessions received events
            assert len(session1_events) > 0
            assert len(session2_events) > 0
            
            # Verify events are properly isolated
            session1_progress = [e for e in session1_events if e.type == "progress"]
            session2_progress = [e for e in session2_events if e.type == "progress"]
            
            assert len(session1_progress) > 0
            assert len(session2_progress) > 0
            
            # Verify analysis IDs are different
            session1_analysis_ids = {e.data.get('analysis_id') for e in session1_progress if 'analysis_id' in e.data}
            session2_analysis_ids = {e.data.get('analysis_id') for e in session2_progress if 'analysis_id' in e.data}
            
            assert analysis_id1 in session1_analysis_ids
            assert analysis_id2 in session2_analysis_ids
            assert session1_analysis_ids.isdisjoint(session2_analysis_ids)
    
    @pytest.mark.asyncio
    async def test_websocket_reconnection_replay(self, analysis_engine, event_bus, mock_database):
        """Test that WebSocket reconnection can replay recent events."""
        # Start analysis
        with patch('services.analysis_engine.get_database', return_value=mock_database):
            analysis_id = await analysis_engine.analyze_document('hvac-session-1', 1)
            
            # Wait for some progress
            await asyncio.sleep(0.2)
            
            # Get replay events (simulating reconnection)
            replay_events = await event_bus.get_replay_events('hvac-session-1')
            
            # Should have recent events available for replay
            assert len(replay_events) > 0
            
            # Should include progress events
            progress_events = [e for e in replay_events if e.type == "progress"]
            assert len(progress_events) > 0
            
            # Events should be properly formatted
            for event in replay_events:
                assert hasattr(event, 'type')
                assert hasattr(event, 'session_id')
                assert hasattr(event, 'data')
                assert event.session_id == 'hvac-session-1'


if __name__ == "__main__":
    pytest.main([__file__])