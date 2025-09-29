"""
Unit tests for PyBOG LangChain Agent Service.

Tests agent responses, event emission, document analysis,
and integration with EventBus.
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
from models.agent_models import MessageType, ChatMessage


class TestStreamingCallbackHandler:
    """Test the streaming callback handler."""
    
    @pytest.fixture
    def event_bus(self):
        return EventBus()
    
    @pytest.fixture
    def callback_handler(self, event_bus):
        return StreamingCallbackHandler(event_bus, "test_session", "chat")
    
    @pytest.mark.asyncio
    async def test_on_llm_new_token(self, callback_handler, event_bus):
        """Test token streaming callback."""
        # Subscribe to events
        events = []
        await event_bus.subscribe("test_session", lambda e: events.append(e))
        
        # Simulate token streaming
        await callback_handler.on_llm_new_token("Hello")
        await callback_handler.on_llm_new_token(" world")
        
        # Wait for events to be processed
        await asyncio.sleep(0.1)
        
        # Verify events
        assert len(events) == 2
        
        # First token event
        assert events[0].type == "chat"
        assert events[0].session_id == "test_session"
        assert events[0].operation == "chat"
        assert events[0].data["content"] == "Hello"
        assert events[0].data["is_complete"] is False
        assert events[0].data["buffer_content"] == "Hello"
        
        # Second token event
        assert events[1].data["content"] == " world"
        assert events[1].data["buffer_content"] == "Hello world"
    
    @pytest.mark.asyncio
    async def test_on_llm_end(self, callback_handler, event_bus):
        """Test LLM completion callback."""
        # Subscribe to events
        events = []
        await event_bus.subscribe("test_session", lambda e: events.append(e))
        
        # Add some content to buffer
        callback_handler.content_buffer = "Complete response"
        
        # Simulate LLM completion
        mock_response = MagicMock()
        await callback_handler.on_llm_end(mock_response)
        
        # Wait for events to be processed
        await asyncio.sleep(0.1)
        
        # Verify completion event
        assert len(events) == 1
        assert events[0].type == "chat"
        assert events[0].data["is_complete"] is True
        assert events[0].data["final_content"] == "Complete response"


class TestPyBOGAgent:
    """Test the PyBOG agent service."""
    
    @pytest.fixture
    def event_bus(self):
        return EventBus()
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LangChain LLM."""
        with patch('services.pybog_agent.ChatOpenAI') as mock:
            llm_instance = AsyncMock()
            mock.return_value = llm_instance
            yield llm_instance
    
    @pytest.fixture
    def agent(self, event_bus, mock_llm):
        return PyBOGAgent(event_bus, openai_api_key="test_key")
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.event_bus is not None
        assert agent.llm is not None
        assert agent._session_history == {}
        assert "PyBOG" in agent.system_prompt
    
    @pytest.mark.asyncio
    async def test_process_chat_message_success(self, agent, event_bus, mock_llm):
        """Test successful chat message processing."""
        # Mock LLM response
        mock_generation = MagicMock()
        mock_generation.text = "This is a helpful response about HVAC systems."
        mock_result = MagicMock()
        mock_result.generations = [[mock_generation]]
        mock_llm.agenerate.return_value = mock_result
        
        # Subscribe to events
        events = []
        await event_bus.subscribe("test_session", lambda e: events.append(e))
        
        # Process chat message
        await agent.process_chat_message("test_session", "Tell me about HVAC control sequences")
        
        # Wait for events to be processed
        await asyncio.sleep(0.1)
        
        # Verify events were emitted
        assert len(events) >= 2  # At least progress start and end
        
        # Check progress events
        progress_events = [e for e in events if e.type == "progress"]
        assert len(progress_events) >= 2
        
        # Check start progress
        start_event = progress_events[0]
        assert start_event.data["state"] == "processing"
        assert start_event.data["operation"] == "chat"
        
        # Check end progress
        end_event = progress_events[-1]
        assert end_event.data["state"] == "complete"
        
        # Verify session history was updated
        history = agent.get_session_history("test_session")
        assert len(history) == 3  # System + User + Assistant
        assert history[1].content == "Tell me about HVAC control sequences"
        assert history[2].content == "This is a helpful response about HVAC systems."
    
    @pytest.mark.asyncio
    async def test_process_chat_message_error(self, agent, event_bus, mock_llm):
        """Test chat message processing with error."""
        # Mock LLM to raise exception
        mock_llm.agenerate.side_effect = Exception("LLM API error")
        
        # Subscribe to events
        events = []
        await event_bus.subscribe("test_session", lambda e: events.append(e))
        
        # Process chat message
        await agent.process_chat_message("test_session", "Test message")
        
        # Wait for events to be processed
        await asyncio.sleep(0.1)
        
        # Verify error event was emitted
        error_events = [e for e in events if e.type == "error"]
        assert len(error_events) == 1
        
        error_event = error_events[0]
        assert error_event.data["error_code"] == "CHAT_PROCESSING"
        assert "LLM API error" in error_event.data["message"]
    
    @pytest.mark.asyncio
    async def test_analyze_document_content_success(self, agent, event_bus, mock_llm):
        """Test successful document analysis."""
        # Mock LLM response with valid JSON
        analysis_json = {
            "io_points": [
                {
                    "name": "supply_air_temp",
                    "type": "input",
                    "data_type": "numeric",
                    "units": "°F",
                    "description": "Supply air temperature sensor"
                }
            ],
            "control_blocks": [
                {
                    "name": "temperature_control",
                    "type": "PID",
                    "description": "Temperature control loop",
                    "logic": ["Read sensor", "Calculate error", "Apply PID"],
                    "complexity": 5
                }
            ],
            "pseudocode": [
                {
                    "step": 1,
                    "description": "Read temperature",
                    "code": "temp = read_sensor(supply_air_temp)"
                }
            ],
            "quality_score": 0.85,
            "issues": [],
            "metadata": {
                "document_type": "sequence",
                "confidence": 0.9,
                "recommendations": ["Add fault detection"]
            }
        }
        
        mock_generation = MagicMock()
        mock_generation.text = f"Here's the analysis:\n```json\n{json.dumps(analysis_json)}\n```"
        mock_result = MagicMock()
        mock_result.generations = [[mock_generation]]
        mock_llm.agenerate.return_value = mock_result
        
        # Subscribe to events
        events = []
        await event_bus.subscribe("test_session", lambda e: events.append(e))
        
        # Analyze document
        result = await agent.analyze_document_content(
            "test_session", 
            "HVAC sequence document content"
        )
        
        # Wait for events to be processed
        await asyncio.sleep(0.1)
        
        # Verify result structure
        assert "io_points" in result
        assert "control_blocks" in result
        assert "pseudocode" in result
        assert "quality_score" in result
        assert "issues" in result
        assert "metadata" in result
        
        # Verify IO points
        assert len(result["io_points"]) == 1
        assert result["io_points"][0]["name"] == "supply_air_temp"
        assert result["io_points"][0]["type"] == "input"
        
        # Verify control blocks
        assert len(result["control_blocks"]) == 1
        assert result["control_blocks"][0]["name"] == "temperature_control"
        
        # Verify progress events
        progress_events = [e for e in events if e.type == "progress"]
        assert len(progress_events) >= 2
        assert progress_events[0].data["state"] == "processing"
        assert progress_events[-1].data["state"] == "complete"
    
    @pytest.mark.asyncio
    async def test_analyze_document_content_invalid_json(self, agent, event_bus, mock_llm):
        """Test document analysis with invalid JSON response."""
        # Mock LLM response with invalid JSON
        mock_generation = MagicMock()
        mock_generation.text = "This is not valid JSON response"
        mock_result = MagicMock()
        mock_result.generations = [[mock_generation]]
        mock_llm.agenerate.return_value = mock_result
        
        # Analyze document
        result = await agent.analyze_document_content(
            "test_session", 
            "Document content"
        )
        
        # Verify fallback result
        assert result["quality_score"] == 0.0
        assert len(result["issues"]) > 0
        assert "Failed to parse" in result["issues"][0]
        assert result["metadata"]["document_type"] == "unknown"
    
    @pytest.mark.asyncio
    async def test_analyze_document_content_error(self, agent, event_bus, mock_llm):
        """Test document analysis with LLM error."""
        # Mock LLM to raise exception
        mock_llm.agenerate.side_effect = Exception("Analysis failed")
        
        # Subscribe to events
        events = []
        await event_bus.subscribe("test_session", lambda e: events.append(e))
        
        # Analyze document
        result = await agent.analyze_document_content(
            "test_session", 
            "Document content"
        )
        
        # Wait for events to be processed
        await asyncio.sleep(0.1)
        
        # Verify error result
        assert result["quality_score"] == 0.0
        assert "Analysis failed" in result["issues"][0]
        
        # Verify error event was emitted
        error_events = [e for e in events if e.type == "error"]
        assert len(error_events) == 1
        assert error_events[0].data["error_code"] == "DOCUMENT_ANALYSIS"
    
    def test_validate_analysis_data(self, agent):
        """Test analysis data validation."""
        # Test valid data
        valid_data = {
            "io_points": [
                {
                    "name": "temp_sensor",
                    "type": "input",
                    "data_type": "numeric",
                    "description": "Temperature sensor"
                }
            ],
            "control_blocks": [
                {
                    "name": "pid_control",
                    "type": "PID",
                    "description": "PID controller",
                    "logic": ["read", "calculate", "output"],
                    "complexity": 5
                }
            ],
            "pseudocode": [],
            "quality_score": 0.8,
            "issues": [],
            "metadata": {}
        }
        
        result = agent._validate_analysis_data(valid_data)
        
        # Verify structure
        assert len(result["io_points"]) == 1
        assert len(result["control_blocks"]) == 1
        assert result["quality_score"] == 0.8
        
        # Test invalid data cleanup
        invalid_data = {
            "io_points": [
                {"name": "invalid"},  # Missing required fields
                {
                    "name": "valid_point",
                    "type": "input",
                    "data_type": "numeric",
                    "description": "Valid point"
                }
            ],
            "control_blocks": [
                {"name": "invalid"},  # Missing required fields
            ],
            "quality_score": 1.5,  # Out of range
        }
        
        result = agent._validate_analysis_data(invalid_data)
        
        # Verify cleanup
        assert len(result["io_points"]) == 1  # Only valid point kept
        assert len(result["control_blocks"]) == 0  # Invalid block removed
        assert result["quality_score"] == 1.0  # Clamped to valid range
    
    def test_session_management(self, agent):
        """Test session history management."""
        # Initially no sessions
        assert agent.get_active_sessions() == []
        
        # Add session history
        agent._session_history["session1"] = ["message1", "message2"]
        agent._session_history["session2"] = ["message3"]
        
        # Verify active sessions
        sessions = agent.get_active_sessions()
        assert len(sessions) == 2
        assert "session1" in sessions
        assert "session2" in sessions
        
        # Verify session history retrieval
        history = agent.get_session_history("session1")
        assert history == ["message1", "message2"]
        
        # Test non-existent session
        history = agent.get_session_history("nonexistent")
        assert history == []
        
        # Clear session history
        agent.clear_session_history("session1")
        assert "session1" not in agent._session_history
        assert len(agent.get_active_sessions()) == 1


class TestPyBOGAgentIntegration:
    """Integration tests for PyBOG agent with EventBus."""
    
    @pytest.fixture
    def event_bus(self):
        return EventBus()
    
    @pytest.mark.asyncio
    async def test_event_bus_integration(self, event_bus):
        """Test that agent properly integrates with EventBus."""
        # Create agent with mocked LLM
        with patch('services.pybog_agent.ChatOpenAI') as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm_class.return_value = mock_llm
            
            # Mock successful response
            mock_generation = MagicMock()
            mock_generation.text = "Test response"
            mock_result = MagicMock()
            mock_result.generations = [[mock_generation]]
            mock_llm.agenerate.return_value = mock_result
            
            agent = PyBOGAgent(event_bus, openai_api_key="test_key")
            
            # Subscribe to all events for session
            all_events = []
            await event_bus.subscribe("test_session", lambda e: all_events.append(e))
            
            # Process chat message
            await agent.process_chat_message("test_session", "Test message")
            
            # Wait for all events to be processed
            await asyncio.sleep(0.1)
            
            # Verify events were emitted to EventBus
            assert len(all_events) > 0
            
            # Verify event types
            event_types = [e.type for e in all_events]
            assert "progress" in event_types
            
            # Verify all events have correct session_id
            for event in all_events:
                assert event.session_id == "test_session"
                assert hasattr(event, 'timestamp')
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, event_bus):
        """Test agent handling multiple concurrent sessions."""
        with patch('services.pybog_agent.ChatOpenAI') as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm_class.return_value = mock_llm
            
            # Mock responses
            mock_generation = MagicMock()
            mock_generation.text = "Response"
            mock_result = MagicMock()
            mock_result.generations = [[mock_generation]]
            mock_llm.agenerate.return_value = mock_result
            
            agent = PyBOGAgent(event_bus, openai_api_key="test_key")
            
            # Subscribe to events for different sessions
            session1_events = []
            session2_events = []
            
            await event_bus.subscribe("session1", lambda e: session1_events.append(e))
            await event_bus.subscribe("session2", lambda e: session2_events.append(e))
            
            # Process messages concurrently
            await asyncio.gather(
                agent.process_chat_message("session1", "Message 1"),
                agent.process_chat_message("session2", "Message 2")
            )
            
            # Wait for events
            await asyncio.sleep(0.1)
            
            # Verify session isolation
            assert len(session1_events) > 0
            assert len(session2_events) > 0
            
            # Verify no cross-session events
            for event in session1_events:
                assert event.session_id == "session1"
            
            for event in session2_events:
                assert event.session_id == "session2"
            
            # Verify separate session histories
            assert len(agent.get_active_sessions()) == 2
            assert agent.get_session_history("session1") != agent.get_session_history("session2")


if __name__ == "__main__":
    pytest.main([__file__])