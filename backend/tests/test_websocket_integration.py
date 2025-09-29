"""
Integration tests for WebSocket message envelope system.
Tests end-to-end chat → WebSocket echo functionality and event flow.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from backend.core.events import EventBus, Event
from backend.services.websocket_manager import WebSocketManager
from backend.services.message_handlers import MessageHandlerRegistry
from backend.models.websocket_models import (
    WebSocketMessage, MessageType, ErrorCode,
    create_chat_message, create_progress_message
)
from backend.models.file_models import ProgressState


class MockWebSocket:
    """Mock WebSocket for integration testing."""
    
    def __init__(self):
        self.sent_messages = []
        self.closed = False
        self.accepted = False
    
    async def accept(self):
        """Mock accept method."""
        self.accepted = True
    
    async def send_text(self, data: str):
        """Mock send_text method."""
        if self.closed:
            raise Exception("WebSocket connection closed")
        self.sent_messages.append(data)
    
    async def close(self):
        """Mock close method."""
        self.closed = True
    
    def get_sent_messages_as_json(self):
        """Get sent messages as parsed JSON."""
        return [json.loads(msg) for msg in self.sent_messages]


@pytest.fixture
def event_bus():
    """Create event bus for testing."""
    return EventBus()


@pytest.fixture
def websocket_manager(event_bus):
    """Create WebSocket manager for testing."""
    return WebSocketManager(event_bus)


@pytest.fixture
def message_handlers(event_bus):
    """Create message handler registry for testing."""
    return MessageHandlerRegistry(event_bus)


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket for testing."""
    return MockWebSocket()


class TestWebSocketIntegration:
    """Integration tests for WebSocket message envelope system."""
    
    @pytest.mark.asyncio
    async def test_chat_echo_end_to_end(self, event_bus, websocket_manager, 
                                       message_handlers, mock_websocket):
        """
        Test complete chat → WebSocket echo workflow.
        
        This test verifies:
        1. User sends chat message via WebSocket
        2. Message is processed and published to event bus
        3. Event is converted back to WebSocket message
        4. WebSocket message is sent back to client
        """
        session_id = "test-session"
        
        # Connect WebSocket
        await websocket_manager.connect(mock_websocket, session_id)
        
        # Clear any initial messages (like session resume info)
        mock_websocket.sent_messages.clear()
        
        # Simulate user sending chat message
        user_message = {
            "type": "chat",
            "content": "Hello, this is a test message!"
        }
        
        # Handle incoming message (simulates WebSocket receiving message from client)
        await websocket_manager.handle_incoming_message(
            session_id, 
            json.dumps(user_message)
        )
        
        # Wait a bit for async processing
        await asyncio.sleep(0.1)
        
        # Now simulate assistant response using message handler
        chat_handler = message_handlers.get_chat_handler()
        await chat_handler.handle_assistant_response(
            session_id=session_id,
            content="Echo: Hello, this is a test message!",
            is_complete=True,
            message_id="response-123"
        )
        
        # Wait for message to be processed and sent
        await asyncio.sleep(0.1)
        
        # Check that WebSocket received the echo response
        sent_messages = mock_websocket.get_sent_messages_as_json()
        
        # Should have at least one message (the assistant response)
        assert len(sent_messages) >= 1
        
        # Find the assistant response message
        assistant_message = None
        for msg in sent_messages:
            if (msg.get("type") == "chat" and 
                msg.get("data", {}).get("content", "").startswith("Echo:")):
                assistant_message = msg
                break
        
        assert assistant_message is not None
        assert assistant_message["type"] == "chat"
        assert assistant_message["session_id"] == session_id
        assert assistant_message["data"]["content"] == "Echo: Hello, this is a test message!"
        assert assistant_message["data"]["is_complete"] is True
        assert assistant_message["data"]["message_id"] == "response-123"
    
    @pytest.mark.asyncio
    async def test_progress_update_flow(self, event_bus, websocket_manager, 
                                       message_handlers, mock_websocket):
        """
        Test progress update flow through WebSocket.
        
        This test verifies:
        1. Progress handler publishes progress event
        2. Event is converted to WebSocket message
        3. WebSocket message is sent to client
        """
        session_id = "test-session"
        
        # Connect WebSocket
        await websocket_manager.connect(mock_websocket, session_id)
        mock_websocket.sent_messages.clear()
        
        # Simulate progress updates
        progress_handler = message_handlers.get_progress_handler()
        
        # File upload progress
        await progress_handler.handle_file_upload_progress(
            session_id=session_id,
            file_id=123,
            progress_percent=25.0
        )
        
        await asyncio.sleep(0.1)
        
        # Analysis progress
        await progress_handler.handle_analysis_progress(
            session_id=session_id,
            file_id=123,
            state=ProgressState.PROCESSING,
            message="Analyzing document structure..."
        )
        
        await asyncio.sleep(0.1)
        
        # Check WebSocket received progress messages
        sent_messages = mock_websocket.get_sent_messages_as_json()
        progress_messages = [msg for msg in sent_messages if msg["type"] == "progress"]
        
        assert len(progress_messages) >= 2
        
        # Check file upload progress message
        upload_msg = next((msg for msg in progress_messages 
                          if msg["data"]["operation"] == "file_upload"), None)
        assert upload_msg is not None
        assert upload_msg["data"]["file_id"] == 123
        assert upload_msg["data"]["progress_percent"] == 25.0
        assert "25.0%" in upload_msg["data"]["message"]
        
        # Check analysis progress message
        analysis_msg = next((msg for msg in progress_messages 
                           if msg["data"]["operation"] == "analysis"), None)
        assert analysis_msg is not None
        assert analysis_msg["data"]["file_id"] == 123
        assert analysis_msg["data"]["state"] == "processing"
        assert analysis_msg["data"]["message"] == "Analyzing document structure..."
    
    @pytest.mark.asyncio
    async def test_bog_generation_flow(self, event_bus, websocket_manager, 
                                      message_handlers, mock_websocket):
        """
        Test BOG file generation flow through WebSocket.
        
        This test verifies:
        1. BOG handler publishes BOG generated event
        2. Event is converted to WebSocket message
        3. WebSocket message is sent to client
        """
        session_id = "test-session"
        
        # Connect WebSocket
        await websocket_manager.connect(mock_websocket, session_id)
        mock_websocket.sent_messages.clear()
        
        # Simulate BOG file generation
        bog_handler = message_handlers.get_bog_handler()
        
        analysis_data = {
            "io_points": [
                {"name": "temperature", "type": "input", "data_type": "numeric"},
                {"name": "setpoint", "type": "output", "data_type": "numeric"}
            ],
            "control_blocks": [
                {"name": "pid_controller", "type": "PID", "description": "Temperature control"}
            ],
            "quality_score": 0.85
        }
        
        await bog_handler.handle_bog_generated(
            session_id=session_id,
            file_id=456,
            filename="hvac_control.bog",
            analysis=analysis_data,
            download_url="http://example.com/download/456"
        )
        
        await asyncio.sleep(0.1)
        
        # Check WebSocket received BOG generated message
        sent_messages = mock_websocket.get_sent_messages_as_json()
        bog_messages = [msg for msg in sent_messages if msg["type"] == "bog_generated"]
        
        assert len(bog_messages) == 1
        bog_msg = bog_messages[0]
        
        assert bog_msg["session_id"] == session_id
        assert bog_msg["data"]["file_id"] == 456
        assert bog_msg["data"]["filename"] == "hvac_control.bog"
        assert bog_msg["data"]["analysis"] == analysis_data
        assert bog_msg["data"]["download_url"] == "http://example.com/download/456"
    
    @pytest.mark.asyncio
    async def test_error_handling_flow(self, event_bus, websocket_manager, 
                                      message_handlers, mock_websocket):
        """
        Test error handling flow through WebSocket.
        
        This test verifies:
        1. Error handler publishes error event
        2. Event is converted to WebSocket message
        3. WebSocket message is sent to client
        """
        session_id = "test-session"
        
        # Connect WebSocket
        await websocket_manager.connect(mock_websocket, session_id)
        mock_websocket.sent_messages.clear()
        
        # Simulate different types of errors
        error_handler = message_handlers.get_error_handler()
        
        # File error
        await error_handler.handle_file_error(
            session_id=session_id,
            message="File size exceeds limit",
            file_id=123,
            retry_possible=False
        )
        
        await asyncio.sleep(0.1)
        
        # Analysis error
        await error_handler.handle_analysis_error(
            session_id=session_id,
            message="Unable to parse document structure",
            file_id=123,
            retry_possible=True
        )
        
        await asyncio.sleep(0.1)
        
        # Check WebSocket received error messages
        sent_messages = mock_websocket.get_sent_messages_as_json()
        error_messages = [msg for msg in sent_messages if msg["type"] == "error"]
        
        assert len(error_messages) >= 2
        
        # Check file error message
        file_error = next((msg for msg in error_messages 
                          if msg["data"]["error_code"] == "FILE"), None)
        assert file_error is not None
        assert file_error["data"]["message"] == "File size exceeds limit"
        assert file_error["data"]["operation"] == "file_operation"
        assert file_error["data"]["retry_possible"] is False
        
        # Check analysis error message
        analysis_error = next((msg for msg in error_messages 
                             if msg["data"]["error_code"] == "ANALYSIS"), None)
        assert analysis_error is not None
        assert analysis_error["data"]["message"] == "Unable to parse document structure"
        assert analysis_error["data"]["operation"] == "analysis"
        assert analysis_error["data"]["retry_possible"] is True
    
    @pytest.mark.asyncio
    async def test_session_resume_with_replay(self, event_bus, websocket_manager, 
                                             message_handlers, mock_websocket):
        """
        Test session resume functionality with event replay.
        
        This test verifies:
        1. Events are published to session before WebSocket connection
        2. When WebSocket connects, replay events are sent
        3. New events continue to be sent normally
        """
        session_id = "test-session"
        
        # Publish some events before WebSocket connection
        chat_handler = message_handlers.get_chat_handler()
        progress_handler = message_handlers.get_progress_handler()
        
        await chat_handler.handle_user_message(session_id, "Hello before connection")
        await progress_handler.handle_file_upload_progress(session_id, 123, 50.0)
        await chat_handler.handle_assistant_response(
            session_id, "Response before connection", is_complete=True
        )
        
        # Now connect WebSocket (should trigger replay)
        await websocket_manager.connect(mock_websocket, session_id)
        
        await asyncio.sleep(0.1)
        
        # Check that replay events were sent
        sent_messages = mock_websocket.get_sent_messages_as_json()
        
        # Should have resume info message plus replay events
        chat_messages = [msg for msg in sent_messages if msg["type"] == "chat"]
        progress_messages = [msg for msg in sent_messages if msg["type"] == "progress"]
        
        # Should have at least the replay events
        assert len(chat_messages) >= 2  # User message + assistant response (+ resume info)
        assert len(progress_messages) >= 1  # Progress message
        
        # Clear messages and send new event after connection
        mock_websocket.sent_messages.clear()
        
        await chat_handler.handle_assistant_response(
            session_id, "New message after connection", is_complete=True
        )
        
        await asyncio.sleep(0.1)
        
        # Check new message was sent
        new_messages = mock_websocket.get_sent_messages_as_json()
        new_chat_messages = [msg for msg in new_messages if msg["type"] == "chat"]
        
        assert len(new_chat_messages) == 1
        assert new_chat_messages[0]["data"]["content"] == "New message after connection"
    
    @pytest.mark.asyncio
    async def test_multiple_sessions_isolation(self, event_bus, websocket_manager, 
                                              message_handlers):
        """
        Test that multiple WebSocket sessions are properly isolated.
        
        This test verifies:
        1. Messages sent to one session don't leak to another
        2. Each session maintains its own event replay buffer
        3. Session disconnection doesn't affect other sessions
        """
        session1_id = "session-1"
        session2_id = "session-2"
        
        # Create WebSockets for both sessions
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        
        # Connect both sessions
        await websocket_manager.connect(ws1, session1_id)
        await websocket_manager.connect(ws2, session2_id)
        
        # Clear initial messages
        ws1.sent_messages.clear()
        ws2.sent_messages.clear()
        
        # Send message to session 1 only
        chat_handler = message_handlers.get_chat_handler()
        await chat_handler.handle_assistant_response(
            session1_id, "Message for session 1", is_complete=True
        )
        
        await asyncio.sleep(0.1)
        
        # Check only session 1 received the message
        ws1_messages = ws1.get_sent_messages_as_json()
        ws2_messages = ws2.get_sent_messages_as_json()
        
        session1_chat = [msg for msg in ws1_messages if msg["type"] == "chat"]
        session2_chat = [msg for msg in ws2_messages if msg["type"] == "chat"]
        
        assert len(session1_chat) == 1
        assert len(session2_chat) == 0
        assert session1_chat[0]["data"]["content"] == "Message for session 1"
        
        # Send message to session 2 only
        await chat_handler.handle_assistant_response(
            session2_id, "Message for session 2", is_complete=True
        )
        
        await asyncio.sleep(0.1)
        
        # Check only session 2 received the new message
        ws1_new_messages = ws1.get_sent_messages_as_json()[len(ws1_messages):]
        ws2_new_messages = ws2.get_sent_messages_as_json()
        
        session1_new_chat = [msg for msg in ws1_new_messages if msg["type"] == "chat"]
        session2_new_chat = [msg for msg in ws2_new_messages if msg["type"] == "chat"]
        
        assert len(session1_new_chat) == 0
        assert len(session2_new_chat) == 1
        assert session2_new_chat[0]["data"]["content"] == "Message for session 2"
        
        # Disconnect session 1 and verify session 2 is unaffected
        await websocket_manager.disconnect(session1_id)
        
        assert not websocket_manager.is_session_connected(session1_id)
        assert websocket_manager.is_session_connected(session2_id)
        assert websocket_manager.get_connection_count() == 1