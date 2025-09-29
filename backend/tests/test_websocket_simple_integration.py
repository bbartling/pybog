"""
Simple integration test for WebSocket message envelope system.
Tests basic event flow without complex WebSocket mocking.
"""

import pytest
import asyncio
import json

from backend.core.events import EventBus, Event
from backend.services.websocket_manager import WebSocketManager
from backend.services.message_handlers import MessageHandlerRegistry
from backend.models.websocket_models import (
    WebSocketMessage, MessageType, ErrorCode,
    create_chat_message, create_progress_message
)
from backend.models.file_models import ProgressState


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


class TestSimpleWebSocketIntegration:
    """Simple integration tests for WebSocket message envelope system."""
    
    @pytest.mark.asyncio
    async def test_event_to_message_conversion(self, websocket_manager):
        """Test converting events to WebSocket messages."""
        # Test chat event conversion
        chat_event = Event(
            type='chat',
            session_id='test-session',
            operation='assistant_response',
            data={
                'content': 'Hello from assistant',
                'is_complete': True,
                'source': 'assistant'
            }
        )
        
        message = await websocket_manager._convert_event_to_message(chat_event)
        assert message is not None
        assert message.type == MessageType.CHAT
        assert message.session_id == 'test-session'
        assert message.data['content'] == 'Hello from assistant'
        assert message.data['is_complete'] is True
        
        # Test progress event conversion
        progress_event = Event(
            type='progress',
            session_id='test-session',
            operation='file_upload',
            data={
                'state': 'processing',
                'message': 'Uploading file...',
                'file_id': 123,
                'progress_percent': 50.0
            }
        )
        
        message = await websocket_manager._convert_event_to_message(progress_event)
        assert message is not None
        assert message.type == MessageType.PROGRESS
        assert message.session_id == 'test-session'
        assert message.data['state'] == 'processing'
        assert message.data['file_id'] == 123
        assert message.data['progress_percent'] == 50.0
    
    @pytest.mark.asyncio
    async def test_message_handler_event_publishing(self, event_bus, message_handlers):
        """Test that message handlers properly publish events to event bus."""
        session_id = "test-session"
        
        # Set up event capture
        received_events = []
        
        async def capture_event(event):
            received_events.append(event)
        
        await event_bus.subscribe(session_id, capture_event)
        
        # Test chat handler
        chat_handler = message_handlers.get_chat_handler()
        await chat_handler.handle_user_message(session_id, "Test message")
        
        # Test progress handler
        progress_handler = message_handlers.get_progress_handler()
        await progress_handler.handle_progress_update(
            session_id, ProgressState.PROCESSING, "Processing...", "test_operation"
        )
        
        # Test error handler
        error_handler = message_handlers.get_error_handler()
        await error_handler.handle_file_error(session_id, "Test error", file_id=123)
        
        # Test BOG handler
        bog_handler = message_handlers.get_bog_handler()
        await bog_handler.handle_bog_generated(
            session_id, 456, "test.bog", {"analysis": "data"}
        )
        
        # Wait for async processing
        await asyncio.sleep(0.1)
        
        # Verify events were published
        assert len(received_events) == 4
        
        # Check event types
        event_types = [event.type for event in received_events]
        assert 'chat' in event_types
        assert 'progress' in event_types
        assert 'error' in event_types
        assert 'bog_generated' in event_types
    
    @pytest.mark.asyncio
    async def test_event_replay_functionality(self, event_bus):
        """Test event replay functionality for session resume."""
        session_id = "test-session"
        
        # Publish some events
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
            ),
            Event(
                type='bog_generated',
                session_id=session_id,
                operation='bog_generation',
                data={'file_id': 123, 'filename': 'test.bog', 'analysis': {}}
            )
        ]
        
        for event in events:
            await event_bus.publish(session_id, event)
        
        # Get replay events
        replay_events = await event_bus.get_replay_events(session_id)
        
        # Verify replay events
        assert len(replay_events) == 3
        assert replay_events[0].type == 'chat'
        assert replay_events[1].type == 'progress'
        assert replay_events[2].type == 'bog_generated'
    
    @pytest.mark.asyncio
    async def test_websocket_message_creation_helpers(self):
        """Test WebSocket message creation helper functions."""
        session_id = "test-session"
        
        # Test chat message creation
        chat_msg = create_chat_message(
            session_id=session_id,
            content="Hello world",
            is_complete=True,
            message_id="msg-123"
        )
        
        assert chat_msg.type == MessageType.CHAT
        assert chat_msg.session_id == session_id
        assert chat_msg.data["content"] == "Hello world"
        assert chat_msg.data["is_complete"] is True
        assert chat_msg.data["message_id"] == "msg-123"
        
        # Test progress message creation
        progress_msg = create_progress_message(
            session_id=session_id,
            state=ProgressState.PROCESSING,
            message="Processing file...",
            operation="file_upload",
            file_id=123,
            progress_percent=75.0
        )
        
        assert progress_msg.type == MessageType.PROGRESS
        assert progress_msg.session_id == session_id
        assert progress_msg.data["state"] == ProgressState.PROCESSING
        assert progress_msg.data["file_id"] == 123
        assert progress_msg.data["progress_percent"] == 75.0
    
    @pytest.mark.asyncio
    async def test_websocket_manager_basic_functionality(self, websocket_manager):
        """Test basic WebSocket manager functionality without actual WebSocket."""
        # Test connection tracking
        assert websocket_manager.get_connection_count() == 0
        assert len(websocket_manager.get_connected_sessions()) == 0
        assert not websocket_manager.is_session_connected("test-session")
        
        # Test message sending to non-existent connection
        message = create_chat_message("test-session", "Hello")
        result = await websocket_manager.send_message("test-session", message)
        assert result is False  # Should fail when no connection exists
    
    def test_message_serialization(self):
        """Test that WebSocket messages can be properly serialized to JSON."""
        message = create_chat_message(
            session_id="test-session",
            content="Hello world",
            is_complete=True
        )
        
        # Test JSON serialization
        json_str = message.model_dump_json()
        parsed = json.loads(json_str)
        
        assert parsed["type"] == "chat"
        assert parsed["session_id"] == "test-session"
        assert parsed["data"]["content"] == "Hello world"
        assert parsed["data"]["is_complete"] is True
        assert "timestamp" in parsed
    
    @pytest.mark.asyncio
    async def test_end_to_end_message_flow_without_websocket(self, event_bus, websocket_manager, message_handlers):
        """
        Test end-to-end message flow without actual WebSocket connection.
        
        This verifies the complete flow:
        1. Message handler publishes event
        2. Event can be converted to WebSocket message
        3. Message is properly formatted
        """
        session_id = "test-session"
        
        # Use chat handler to publish event
        chat_handler = message_handlers.get_chat_handler()
        await chat_handler.handle_assistant_response(
            session_id=session_id,
            content="This is a test response",
            is_complete=True,
            message_id="test-msg-123"
        )
        
        # Get the event from the event bus
        event = await event_bus.get_next_event(session_id, timeout=1.0)
        assert event is not None
        assert event.type == 'chat'
        assert event.data['content'] == "This is a test response"
        
        # Convert event to WebSocket message
        ws_message = await websocket_manager._convert_event_to_message(event)
        assert ws_message is not None
        assert ws_message.type == MessageType.CHAT
        assert ws_message.session_id == session_id
        assert ws_message.data['content'] == "This is a test response"
        assert ws_message.data['is_complete'] is True
        
        # Verify message can be serialized
        json_str = ws_message.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed['type'] == 'chat'
        assert parsed['data']['content'] == "This is a test response"