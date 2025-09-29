"""
Integration tests for PyBOG LangChain Agent with EventBus.

Specifically tests that LangChain emits events to EventBus correctly
as required by the task specification.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import sys
from pathlib import Path

# Add backend directory to Python path for testing
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.events import EventBus, Event
from services.pybog_agent import PyBOGAgent, StreamingCallbackHandler


class TestLangChainEventBusIntegration:
    """Integration tests for LangChain -> EventBus event emission."""
    
    @pytest.fixture
    def event_bus(self):
        """Create EventBus instance for testing."""
        return EventBus()
    
    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI streaming response."""
        mock_generation = MagicMock()
        mock_generation.text = "This is a complete response about HVAC control sequences."
        mock_result = MagicMock()
        mock_result.generations = [[mock_generation]]
        return mock_result
    
    @pytest.mark.asyncio
    async def test_langchain_emits_chat_events_correctly(self, event_bus, mock_openai_response):
        """
        **Integration Test**: Verify LangChain emits events to EventBus correctly.
        
        This test verifies the core requirement that the LangChain agent
        properly emits events through the EventBus system.
        """
        # Track all events emitted to EventBus
        emitted_events = []
        
        async def event_collector(event: Event):
            emitted_events.append(event)
        
        # Subscribe to session events
        session_id = "integration_test_session"
        await event_bus.subscribe(session_id, event_collector)
        
        # Create agent with mocked LLM
        with patch('services.pybog_agent.ChatOpenAI') as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm_class.return_value = mock_llm
            mock_llm.agenerate.return_value = mock_openai_response
            
            agent = PyBOGAgent(event_bus, openai_api_key="test_key")
            
            # Process a chat message
            await agent.process_chat_message(session_id, "Explain HVAC control sequences")
            
            # Allow time for all events to be processed
            await asyncio.sleep(0.2)
        
        # Verify events were emitted
        assert len(emitted_events) > 0, "No events were emitted to EventBus"
        
        # Verify event structure and types
        event_types = [event.type for event in emitted_events]
        
        # Should have progress events
        assert "progress" in event_types, "Missing progress events"
        
        # Find progress events
        progress_events = [e for e in emitted_events if e.type == "progress"]
        assert len(progress_events) >= 2, "Should have at least start and end progress events"
        
        # Verify progress event structure
        start_progress = progress_events[0]
        assert start_progress.session_id == session_id
        assert start_progress.operation == "chat"
        assert start_progress.data["state"] == "processing"
        assert "message" in start_progress.data
        
        end_progress = progress_events[-1]
        assert end_progress.session_id == session_id
        assert end_progress.operation == "chat"
        assert end_progress.data["state"] == "complete"
        
        # Verify all events have required fields
        for event in emitted_events:
            assert hasattr(event, 'type'), "Event missing type field"
            assert hasattr(event, 'session_id'), "Event missing session_id field"
            assert hasattr(event, 'operation'), "Event missing operation field"
            assert hasattr(event, 'data'), "Event missing data field"
            assert hasattr(event, 'timestamp'), "Event missing timestamp field"
            assert event.session_id == session_id, "Event has wrong session_id"
    
    @pytest.mark.asyncio
    async def test_langchain_streaming_events_emission(self, event_bus):
        """
        Test that LangChain streaming callbacks emit events correctly.
        
        Verifies the streaming token events are properly emitted through EventBus.
        """
        session_id = "streaming_test_session"
        emitted_events = []
        
        async def event_collector(event: Event):
            emitted_events.append(event)
        
        await event_bus.subscribe(session_id, event_collector)
        
        # Create streaming callback handler
        callback_handler = StreamingCallbackHandler(event_bus, session_id, "chat")
        
        # Simulate streaming tokens
        await callback_handler.on_llm_new_token("Hello")
        await callback_handler.on_llm_new_token(" there")
        await callback_handler.on_llm_new_token("!")
        
        # Simulate completion
        mock_result = MagicMock()
        await callback_handler.on_llm_end(mock_result)
        
        # Allow events to be processed
        await asyncio.sleep(0.1)
        
        # Verify streaming events
        assert len(emitted_events) == 4, "Should have 3 token events + 1 completion event"
        
        # Verify token events
        token_events = emitted_events[:3]
        for i, event in enumerate(token_events):
            assert event.type == "chat"
            assert event.session_id == session_id
            assert event.operation == "chat"
            assert event.data["is_complete"] is False
            assert "content" in event.data
            assert "buffer_content" in event.data
        
        # Verify token content
        assert token_events[0].data["content"] == "Hello"
        assert token_events[1].data["content"] == " there"
        assert token_events[2].data["content"] == "!"
        
        # Verify buffer accumulation
        assert token_events[0].data["buffer_content"] == "Hello"
        assert token_events[1].data["buffer_content"] == "Hello there"
        assert token_events[2].data["buffer_content"] == "Hello there!"
        
        # Verify completion event
        completion_event = emitted_events[3]
        assert completion_event.type == "chat"
        assert completion_event.data["is_complete"] is True
        assert completion_event.data["final_content"] == "Hello there!"
    
    @pytest.mark.asyncio
    async def test_document_analysis_events_emission(self, event_bus):
        """
        Test that document analysis emits events correctly to EventBus.
        """
        session_id = "analysis_test_session"
        emitted_events = []
        
        async def event_collector(event: Event):
            emitted_events.append(event)
        
        await event_bus.subscribe(session_id, event_collector)
        
        # Mock LLM response with valid analysis JSON
        analysis_data = {
            "io_points": [
                {
                    "name": "supply_temp",
                    "type": "input",
                    "data_type": "numeric",
                    "units": "°F",
                    "description": "Supply air temperature"
                }
            ],
            "control_blocks": [
                {
                    "name": "temp_control",
                    "type": "PID",
                    "description": "Temperature control loop",
                    "logic": ["Read sensor", "Calculate PID", "Output signal"],
                    "complexity": 6
                }
            ],
            "pseudocode": [
                {
                    "step": 1,
                    "description": "Read temperature sensor",
                    "code": "temp = read_sensor('supply_temp')"
                }
            ],
            "quality_score": 0.85,
            "issues": [],
            "metadata": {
                "document_type": "sequence",
                "confidence": 0.9,
                "recommendations": ["Add error handling"]
            }
        }
        
        with patch('services.pybog_agent.ChatOpenAI') as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm_class.return_value = mock_llm
            
            # Mock LLM response
            mock_generation = MagicMock()
            mock_generation.text = f"Analysis result:\n{json.dumps(analysis_data)}"
            mock_result = MagicMock()
            mock_result.generations = [[mock_generation]]
            mock_llm.agenerate.return_value = mock_result
            
            agent = PyBOGAgent(event_bus, openai_api_key="test_key")
            
            # Perform document analysis
            result = await agent.analyze_document_content(
                session_id, 
                "HVAC control sequence document content"
            )
            
            # Allow events to be processed
            await asyncio.sleep(0.1)
        
        # Verify events were emitted
        assert len(emitted_events) > 0, "No events emitted for document analysis"
        
        # Verify progress events for analysis
        progress_events = [e for e in emitted_events if e.type == "progress"]
        assert len(progress_events) >= 2, "Should have start and end progress events"
        
        # Verify analysis start event
        start_event = progress_events[0]
        assert start_event.operation == "document_analysis"
        assert start_event.data["state"] == "processing"
        assert "Analyzing document" in start_event.data["message"]
        
        # Verify analysis completion event
        end_event = progress_events[-1]
        assert end_event.operation == "document_analysis"
        assert end_event.data["state"] == "complete"
        
        # Verify analysis result structure
        assert "io_points" in result
        assert "control_blocks" in result
        assert len(result["io_points"]) == 1
        assert len(result["control_blocks"]) == 1
        assert result["quality_score"] == 0.85
    
    @pytest.mark.asyncio
    async def test_error_events_emission(self, event_bus):
        """
        Test that errors are properly emitted as events to EventBus.
        """
        session_id = "error_test_session"
        emitted_events = []
        
        async def event_collector(event: Event):
            emitted_events.append(event)
        
        await event_bus.subscribe(session_id, event_collector)
        
        # Create agent with LLM that will fail
        with patch('services.pybog_agent.ChatOpenAI') as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm_class.return_value = mock_llm
            mock_llm.agenerate.side_effect = Exception("Simulated LLM failure")
            
            agent = PyBOGAgent(event_bus, openai_api_key="test_key")
            
            # Attempt chat that will fail
            await agent.process_chat_message(session_id, "This will fail")
            
            # Allow events to be processed
            await asyncio.sleep(0.1)
        
        # Verify error event was emitted
        error_events = [e for e in emitted_events if e.type == "error"]
        assert len(error_events) > 0, "No error events emitted"
        
        # Verify error event structure
        error_event = error_events[0]
        assert error_event.session_id == session_id
        assert error_event.operation == "chat"
        assert error_event.data["error_code"] == "CHAT_PROCESSING"
        assert "Simulated LLM failure" in error_event.data["message"]
        assert error_event.data["session_id"] == session_id
    
    @pytest.mark.asyncio
    async def test_multiple_sessions_event_isolation(self, event_bus):
        """
        Test that events from different sessions are properly isolated.
        """
        session1_events = []
        session2_events = []
        
        async def session1_collector(event: Event):
            session1_events.append(event)
        
        async def session2_collector(event: Event):
            session2_events.append(event)
        
        await event_bus.subscribe("session1", session1_collector)
        await event_bus.subscribe("session2", session2_collector)
        
        with patch('services.pybog_agent.ChatOpenAI') as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm_class.return_value = mock_llm
            
            # Mock successful responses
            mock_generation = MagicMock()
            mock_generation.text = "Response"
            mock_result = MagicMock()
            mock_result.generations = [[mock_generation]]
            mock_llm.agenerate.return_value = mock_result
            
            agent = PyBOGAgent(event_bus, openai_api_key="test_key")
            
            # Process messages for both sessions concurrently
            await asyncio.gather(
                agent.process_chat_message("session1", "Message for session 1"),
                agent.process_chat_message("session2", "Message for session 2")
            )
            
            # Allow events to be processed
            await asyncio.sleep(0.2)
        
        # Verify both sessions received events
        assert len(session1_events) > 0, "Session 1 received no events"
        assert len(session2_events) > 0, "Session 2 received no events"
        
        # Verify event isolation - no cross-session events
        for event in session1_events:
            assert event.session_id == "session1", f"Session 1 received event for {event.session_id}"
        
        for event in session2_events:
            assert event.session_id == "session2", f"Session 2 received event for {event.session_id}"
    
    @pytest.mark.asyncio
    async def test_event_replay_functionality(self, event_bus):
        """
        Test that EventBus replay functionality works with agent events.
        """
        session_id = "replay_test_session"
        
        with patch('services.pybog_agent.ChatOpenAI') as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm_class.return_value = mock_llm
            
            mock_generation = MagicMock()
            mock_generation.text = "Test response"
            mock_result = MagicMock()
            mock_result.generations = [[mock_generation]]
            mock_llm.agenerate.return_value = mock_result
            
            agent = PyBOGAgent(event_bus, openai_api_key="test_key")
            
            # Process a message to generate events
            await agent.process_chat_message(session_id, "Test message")
            
            # Allow events to be processed
            await asyncio.sleep(0.1)
        
        # Get replay events from EventBus
        replay_events = await event_bus.get_replay_events(session_id)
        
        # Verify replay events exist
        assert len(replay_events) > 0, "No replay events available"
        
        # Verify replay events have correct structure
        for event in replay_events:
            assert hasattr(event, 'type')
            assert hasattr(event, 'session_id')
            assert hasattr(event, 'operation')
            assert hasattr(event, 'data')
            assert hasattr(event, 'timestamp')
            assert event.session_id == session_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])