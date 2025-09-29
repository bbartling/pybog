"""
Unit tests for WebSocket manager.
Tests WebSocket connection handling, message broadcasting, and session resume functionality.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from backend.core.events import EventBus, Event
from backend.services.websocket_manager import WebSocketManager
from backend.models.websocket_models import (
    WebSocketMessage, MessageType, ErrorCode,
    create_chat_message, create_error_message
)
from backend.models.file_models import ProgressState


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.sent_messages = []
        self.closed = False
    
    async def accept(self):
        """Mock accept method."""
        pass
    
    async def send_text(self, data: str):
        """Mock send_text method."""
        if self.closed:
            raise Exception("WebSocket connection closed")
        self.sent_messages.append(data)
    
    async def close(self):
        """Mock close method."""
        self.closed = True


@pytest.fixture
def event_bus():
    """Create event bus for testing."""
    return EventBus()


@pytest.fixture
def websocket_manager(event_bus):
    """Create WebSocket manager for testing."""
    return WebSocketManager(event_bus)


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket for testing."""
    return MockWebSocket()


class TestWebSocketManager:
    """Test WebSocket manager functionality."""
    
    @pytest.mark.asyncio
    async def test_connect_websocket(self, websocket_manager, mock_websocket):
        """Test WebSocket connection."""
        session_id = "test-session"
        
        await websocket_manager.connect(mock_websocket, session_id)
        
        # Check connection is stored
        assert websocket_manager.is_session_connected(session_id)
        assert session_id in websocket_manager.get_connected_sessions()
        assert websocket_manager.get_connection_count() == 1
        
        # Check connection info
        info = websocket_manager.get_connection_info(session_id)
        assert info is not None
        assert info.session_id == session_id
        assert isinstance(info.connected_at, datetime)
    
    @pytest.mark.asyncio
    async def test_disconnect_websocket(self, websocket_manager, mock_websocket):
        """Test WebSocket disconnection."""
        session_id = "test-session"
        
        # Connect first
        await websocket_manager.connect(mock_websocket, session_id)
        assert websocket_manager.is_session_connected(session_id)
        
        # Disconnect
        await websocket_manager.disconnect(session_id)
        
        # Check connection is removed
        assert not websocket_manager.is_session_connected(session_id)
        assert session_id not in websocket_manager.get_connected_sessions()
        assert websocket_manager.get_connection_count() == 0
        assert websocket_manager.get_connection_info(session_id) is None
    
    @pytest.mark.asyncio
    async def test_send_message(self, websocket_manager, mock_websocket):
        """Test sending message to WebSocket."""
        session_id = "test-session"
        
        # Connect WebSocket
        await websocket_manager.connect(mock_websocket, session_id)
        
        # Create and send message
        message = create_chat_message(
            session_id=session_id,
            content="Hello world",
            is_complete=True
        )
        
        result = await websocket_manager.send_message(session_id, message)
        
        # Check message was sent
        assert result is True
        assert len(mock_websocket.sent_messages) >= 1  # May include resume message
        
        # Check message content (last message should be our chat message)
        sent_data = json.loads(mock_websocket.sent_messages[-1])
        assert sent_data["type"] == "chat"
        assert sent_data["session_id"] == session_id
        assert sent_data["data"]["content"] == "Hello world"
    
    @pytest.mark.asyncio
    async def test_send_message_no_connection(self, websocket_manager):
        """Test sending message when no WebSocket connection exists."""
        session_id = "test-session"
        
        message = create_chat_message(
            session_id=session_id,
            content="Hello world"
        )
        
        result = await websocket_manager.send_message(session_id, message)
        
        # Should return False when no connection
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_message_broken_connection(self, websocket_manager, mock_websocket):
        """Test sending message to broken WebSocket connection."""
        session_id = "test-session"
        
        # Connect WebSocket
        await websocket_manager.connect(mock_websocket, session_id)
        
        # Break the connection
        mock_websocket.closed = True
        
        # Try to send message
        message = create_chat_message(
            session_id=session_id,
            content="Hello world"
        )
        
        result = await websocket_manager.send_message(session_id, message)
        
        # Should return False and clean up connection
        assert result is False
        assert not websocket_manager.is_session_connected(session_id)
    
    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, websocket_manager):
        """Test broadcasting message to all connected sessions."""
        # Connect multiple WebSockets
        sessions = ["session-1", "session-2", "session-3"]
        websockets = []
        
        for session_id in sessions:
            ws = MockWebSocket()
            websockets.append(ws)
            await websocket_manager.connect(ws, session_id)
        
        # Broadcast message
        message = create_chat_message(
            session_id="broadcast",  # Will be overridden per session
            content="Broadcast message"
        )
        
        sent_count = await websocket_manager.broadcast_to_all(message)
        
        # Check all sessions received the message
        assert sent_count == 3
        
        for i, ws in enumerate(websockets):
            # Each WebSocket should have received resume message + broadcast message
            assert len(ws.sent_messages) >= 1
            
            # Check the broadcast message (last message)
            sent_data = json.loads(ws.sent_messages[-1])
            assert sent_data["type"] == "chat"
            assert sent_data["session_id"] == sessions[i]
            assert sent_data["data"]["content"] == "Broadcast message"
    
    @pytest.mark.asyncio
    async def test_handle_session_events(self, websocket_manager, mock_websocket, event_bus):
        """Test handling events for a session."""
        session_id = "test-session"
        
        # Connect WebSocket
        await websocket_manager.connect(mock_websocket, session_id)
        
        # Create and publish event
        event = Event(
            type='chat',
            session_id=session_id,
            operation='assistant_response',
            data={
                'content': 'Hello from assistant',
                'is_complete': True,
                'source': 'assistant'
            }
        )
        
        await websocket_manager.handle_session_events(session_id, event)
        
        # Check message was sent to WebSocket
        assert len(mock_websocket.sent_messages) >= 1
        
        # Find the chat message (not the resume message)
        chat_message = None
        for msg_str in mock_websocket.sent_messages:
            msg_data = json.loads(msg_str)
            if msg_data.get("data", {}).get("content") == "Hello from assistant":
                chat_message = msg_data
                break
        
        assert chat_message is not None
        assert chat_message["type"] == "chat"
        assert chat_message["session_id"] == session_id
    
    @pytest.mark.asyncio
    async def test_resume_session(self, websocket_manager, mock_websocket, event_bus):
        """Test session resume functionality."""
        session_id = "test-session"
        
        # Add some events to replay buffer first
        events = [
            Event(
                type='chat',
                session_id=session_id,
                operation='user_message',
                data={'content': 'Hello', 'source': 'user'}
            ),
            Event(
                type='progress',
                session_id=session_id,
                operation='file_upload',
                data={'state': 'processing', 'message': 'Uploading...'}
            )
        ]
        
        for event in events:
            await event_bus.publish(session_id, event)
        
        # Now connect and resume
        await websocket_manager.connect(mock_websocket, session_id)
        
        # Check that replay events were sent
        assert len(mock_websocket.sent_messages) >= len(events)
        
        # Verify replay events are in the messages
        sent_messages = [json.loads(msg) for msg in mock_websocket.sent_messages]
        
        # Should have resume info message plus replay events
        chat_messages = [msg for msg in sent_messages if msg["type"] == "chat"]
        progress_messages = [msg for msg in sent_messages if msg["type"] == "progress"]
        
        assert len(chat_messages) >= 1  # At least the user message
        assert len(progress_messages) >= 1  # The progress message
    
    @pytest.mark.asyncio
    async def test_handle_incoming_chat_message(self, websocket_manager, event_bus):
        """Test handling incoming chat message from client."""
        session_id = "test-session"
        
        # Set up event capture
        received_events = []
        
        async def capture_event(event):
            received_events.append(event)
        
        await event_bus.subscribe(session_id, capture_event)
        
        # Handle incoming message
        message_text = json.dumps({
            "type": "chat",
            "content": "Hello from user"
        })
        
        await websocket_manager.handle_incoming_message(session_id, message_text)
        
        # Check event was published
        assert len(received_events) == 1
        event = received_events[0]
        assert event.type == 'chat'
        assert event.session_id == session_id
        assert event.operation == 'user_message'
        assert event.data['content'] == "Hello from user"
        assert event.data['source'] == 'user'
    
    @pytest.mark.asyncio
    async def test_handle_incoming_ping_message(self, websocket_manager, mock_websocket):
        """Test handling incoming ping message from client."""
        session_id = "test-session"
        
        # Connect WebSocket
        await websocket_manager.connect(mock_websocket, session_id)
        
        # Handle ping message
        message_text = json.dumps({"type": "ping"})
        
        await websocket_manager.handle_incoming_message(session_id, message_text)
        
        # Check pong response was sent
        sent_messages = [json.loads(msg) for msg in mock_websocket.sent_messages]
        pong_messages = [msg for msg in sent_messages 
                        if msg.get("data", {}).get("content") == "pong"]
        
        assert len(pong_messages) == 1
        assert pong_messages[0]["type"] == "chat"
    
    @pytest.mark.asyncio
    async def test_handle_invalid_json_message(self, websocket_manager, mock_websocket):
        """Test handling invalid JSON message from client."""
        session_id = "test-session"
        
        # Connect WebSocket
        await websocket_manager.connect(mock_websocket, session_id)
        
        # Handle invalid JSON
        await websocket_manager.handle_incoming_message(session_id, "invalid json")
        
        # Check error message was sent
        sent_messages = [json.loads(msg) for msg in mock_websocket.sent_messages]
        error_messages = [msg for msg in sent_messages if msg["type"] == "error"]
        
        assert len(error_messages) == 1
        error_msg = error_messages[0]
        assert error_msg["data"]["error_code"] == "STREAM"
        assert "Invalid JSON format" in error_msg["data"]["message"]
    
    @pytest.mark.asyncio
    async def test_convert_event_to_message(self, websocket_manager):
        """Test converting events to WebSocket messages."""
        # Test chat event
        chat_event = Event(
            type='chat',
            session_id='test-session',
            operation='assistant_response',
            data={
                'content': 'Hello',
                'is_complete': True,
                'message_id': 'msg-123'
            }
        )
        
        message = await websocket_manager._convert_event_to_message(chat_event)
        assert message is not None
        assert message.type == MessageType.CHAT
        assert message.data['content'] == 'Hello'
        assert message.data['is_complete'] is True
        
        # Test progress event
        progress_event = Event(
            type='progress',
            session_id='test-session',
            operation='file_upload',
            data={
                'state': 'processing',
                'message': 'Uploading...',
                'file_id': 123,
                'progress_percent': 50.0
            }
        )
        
        message = await websocket_manager._convert_event_to_message(progress_event)
        assert message is not None
        assert message.type == MessageType.PROGRESS
        assert message.data['state'] == 'processing'
        assert message.data['file_id'] == 123
        
        # Test unknown event type
        unknown_event = Event(
            type='unknown',
            session_id='test-session',
            operation='test',
            data={}
        )
        
        message = await websocket_manager._convert_event_to_message(unknown_event)
        assert message is None