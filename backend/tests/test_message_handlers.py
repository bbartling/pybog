"""
Unit tests for message handlers.
Tests message type handlers for chat, progress, bog_generated, and error events.
"""

import pytest
import asyncio
from datetime import datetime, timezone

from backend.core.events import EventBus, Event
from backend.services.message_handlers import (
    ChatMessageHandler, ProgressMessageHandler,
    BOGGeneratedMessageHandler, ErrorMessageHandler,
    MessageHandlerRegistry
)
from backend.models.websocket_models import ErrorCode
from backend.models.file_models import ProgressState


@pytest.fixture
def event_bus():
    """Create event bus for testing."""
    return EventBus()


@pytest.fixture
def chat_handler(event_bus):
    """Create chat message handler for testing."""
    return ChatMessageHandler(event_bus)


@pytest.fixture
def progress_handler(event_bus):
    """Create progress message handler for testing."""
    return ProgressMessageHandler(event_bus)


@pytest.fixture
def bog_handler(event_bus):
    """Create BOG generated message handler for testing."""
    return BOGGeneratedMessageHandler(event_bus)


@pytest.fixture
def error_handler(event_bus):
    """Create error message handler for testing."""
    return ErrorMessageHandler(event_bus)


@pytest.fixture
def handler_registry(event_bus):
    """Create message handler registry for testing."""
    return MessageHandlerRegistry(event_bus)


class TestChatMessageHandler:
    """Test chat message handler."""
    
    @pytest.mark.asyncio
    async def test_handle_user_message(self, chat_handler, event_bus):
        """Test handling user chat message."""
        session_id = "test-session"
        content = "Hello, how are you?"
        
        # Set up event capture
        received_events = []
        
        async def capture_event(event):
            received_events.append(event)
        
        await event_bus.subscribe(session_id, capture_event)
        
        # Handle user message
        await chat_handler.handle_user_message(session_id, content)
        
        # Check event was published
        assert len(received_events) == 1
        event = received_events[0]
        
        assert event.type == 'chat'
        assert event.session_id == session_id
        assert event.operation == 'user_message'
        assert event.data['content'] == content
        assert event.data['source'] == 'user'
        assert 'timestamp' in event.data
    
    @pytest.mark.asyncio
    async def test_handle_assistant_response(self, chat_handler, event_bus):
        """Test handling assistant response."""
        session_id = "test-session"
        content = "I'm doing well, thank you!"
        message_id = "msg-123"
        
        # Set up event capture
        received_events = []
        
        async def capture_event(event):
            received_events.append(event)
        
        await event_bus.subscribe(session_id, capture_event)
        
        # Handle assistant response
        await chat_handler.handle_assistant_response(
            session_id, content, is_complete=True, message_id=message_id
        )
        
        # Check event was published
        assert len(received_events) == 1
        event = received_events[0]
        
        assert event.type == 'chat'
        assert event.session_id == session_id
        assert event.operation == 'assistant_response'
        assert event.data['content'] == content
        assert event.data['is_complete'] is True
        assert event.data['message_id'] == message_id
        assert event.data['source'] == 'assistant'


class TestProgressMessageHandler:
    """Test progress message handler."""
    
    @pytest.mark.asyncio
    async def test_handle_progress_update(self, progress_handler, event_bus):
        """Test handling progress update."""
        session_id = "test-session"
        state = ProgressState.PROCESSING
        message = "Processing file..."
        operation = "file_upload"
        file_id = 123
        progress_percent = 45.5
        
        # Set up event capture
        received_events = []
        
        async def capture_event(event):
            received_events.append(event)
        
        await event_bus.subscribe(session_id, capture_event)
        
        # Handle progress update
        await progress_handler.handle_progress_update(
            session_id, state, message, operation, file_id, progress_percent
        )
        
        # Check event was published
        assert len(received_events) == 1
        event = received_events[0]
        
        assert event.type == 'progress'
        assert event.session_id == session_id
        assert event.operation == operation
        assert event.data['state'] == state.value
        assert event.data['message'] == message
        assert event.data['file_id'] == file_id
        assert event.data['progress_percent'] == progress_percent
    
    @pytest.mark.asyncio
    async def test_handle_file_upload_progress(self, progress_handler, event_bus):
        """Test handling file upload progress."""
        session_id = "test-session"
        file_id = 123
        progress_percent = 75.0
        
        # Set up event capture
        received_events = []
        
        async def capture_event(event):
            received_events.append(event)
        
        await event_bus.subscribe(session_id, capture_event)
        
        # Handle file upload progress
        await progress_handler.handle_file_upload_progress(
            session_id, file_id, progress_percent
        )
        
        # Check event was published
        assert len(received_events) == 1
        event = received_events[0]
        
        assert event.type == 'progress'
        assert event.operation == 'file_upload'
        assert event.data['state'] == ProgressState.PROCESSING.value
        assert event.data['file_id'] == file_id
        assert event.data['progress_percent'] == progress_percent
        assert "75.0%" in event.data['message']
    
    @pytest.mark.asyncio
    async def test_handle_analysis_progress(self, progress_handler, event_bus):
        """Test handling analysis progress."""
        session_id = "test-session"
        file_id = 123
        state = ProgressState.FINALIZING
        message = "Generating BOG file..."
        
        # Set up event capture
        received_events = []
        
        async def capture_event(event):
            received_events.append(event)
        
        await event_bus.subscribe(session_id, capture_event)
        
        # Handle analysis progress
        await progress_handler.handle_analysis_progress(
            session_id, file_id, state, message
        )
        
        # Check event was published
        assert len(received_events) == 1
        event = received_events[0]
        
        assert event.type == 'progress'
        assert event.operation == 'analysis'
        assert event.data['state'] == state.value
        assert event.data['message'] == message
        assert event.data['file_id'] == file_id


class TestBOGGeneratedMessageHandler:
    """Test BOG generated message handler."""
    
    @pytest.mark.asyncio
    async def test_handle_bog_generated(self, bog_handler, event_bus):
        """Test handling BOG file generation."""
        session_id = "test-session"
        file_id = 123
        filename = "test.bog"
        analysis = {
            "io_points": [{"name": "temp", "type": "input"}],
            "control_blocks": [{"name": "pid", "type": "controller"}]
        }
        download_url = "http://example.com/download/123"
        
        # Set up event capture
        received_events = []
        
        async def capture_event(event):
            received_events.append(event)
        
        await event_bus.subscribe(session_id, capture_event)
        
        # Handle BOG generated
        await bog_handler.handle_bog_generated(
            session_id, file_id, filename, analysis, download_url
        )
        
        # Check event was published
        assert len(received_events) == 1
        event = received_events[0]
        
        assert event.type == 'bog_generated'
        assert event.session_id == session_id
        assert event.operation == 'bog_generation'
        assert event.data['file_id'] == file_id
        assert event.data['filename'] == filename
        assert event.data['analysis'] == analysis
        assert event.data['download_url'] == download_url


class TestErrorMessageHandler:
    """Test error message handler."""
    
    @pytest.mark.asyncio
    async def test_handle_error(self, error_handler, event_bus):
        """Test handling error event."""
        session_id = "test-session"
        error_code = ErrorCode.FILE
        message = "File upload failed"
        operation = "file_upload"
        details = {"file_size": 1000000}
        retry_possible = True
        
        # Set up event capture
        received_events = []
        
        async def capture_event(event):
            received_events.append(event)
        
        await event_bus.subscribe(session_id, capture_event)
        
        # Handle error
        await error_handler.handle_error(
            session_id, error_code, message, operation, details, retry_possible
        )
        
        # Check event was published
        assert len(received_events) == 1
        event = received_events[0]
        
        assert event.type == 'error'
        assert event.session_id == session_id
        assert event.operation == operation
        assert event.data['error_code'] == error_code.value
        assert event.data['message'] == message
        assert event.data['details'] == details
        assert event.data['retry_possible'] == retry_possible
    
    @pytest.mark.asyncio
    async def test_handle_file_error(self, error_handler, event_bus):
        """Test handling file-specific error."""
        session_id = "test-session"
        message = "File too large"
        file_id = 123
        
        # Set up event capture
        received_events = []
        
        async def capture_event(event):
            received_events.append(event)
        
        await event_bus.subscribe(session_id, capture_event)
        
        # Handle file error
        await error_handler.handle_file_error(session_id, message, file_id)
        
        # Check event was published
        assert len(received_events) == 1
        event = received_events[0]
        
        assert event.type == 'error'
        assert event.operation == 'file_operation'
        assert event.data['error_code'] == ErrorCode.FILE.value
        assert event.data['message'] == message
        assert event.data['details']['file_id'] == file_id
        assert event.data['retry_possible'] is True
    
    @pytest.mark.asyncio
    async def test_handle_analysis_error(self, error_handler, event_bus):
        """Test handling analysis-specific error."""
        session_id = "test-session"
        message = "Analysis failed"
        file_id = 123
        
        # Set up event capture
        received_events = []
        
        async def capture_event(event):
            received_events.append(event)
        
        await event_bus.subscribe(session_id, capture_event)
        
        # Handle analysis error
        await error_handler.handle_analysis_error(session_id, message, file_id)
        
        # Check event was published
        assert len(received_events) == 1
        event = received_events[0]
        
        assert event.type == 'error'
        assert event.operation == 'analysis'
        assert event.data['error_code'] == ErrorCode.ANALYSIS.value
        assert event.data['message'] == message
        assert event.data['details']['file_id'] == file_id
    
    @pytest.mark.asyncio
    async def test_handle_database_error(self, error_handler, event_bus):
        """Test handling database-specific error."""
        session_id = "test-session"
        message = "Connection failed"
        operation = "session_create"
        
        # Set up event capture
        received_events = []
        
        async def capture_event(event):
            received_events.append(event)
        
        await event_bus.subscribe(session_id, capture_event)
        
        # Handle database error
        await error_handler.handle_database_error(session_id, message, operation)
        
        # Check event was published
        assert len(received_events) == 1
        event = received_events[0]
        
        assert event.type == 'error'
        assert event.operation == operation
        assert event.data['error_code'] == ErrorCode.DB.value
        assert event.data['message'] == message
        assert event.data['retry_possible'] is False
    
    @pytest.mark.asyncio
    async def test_handle_stream_error(self, error_handler, event_bus):
        """Test handling stream-specific error."""
        session_id = "test-session"
        message = "WebSocket disconnected"
        operation = "websocket_send"
        
        # Set up event capture
        received_events = []
        
        async def capture_event(event):
            received_events.append(event)
        
        await event_bus.subscribe(session_id, capture_event)
        
        # Handle stream error
        await error_handler.handle_stream_error(session_id, message, operation)
        
        # Check event was published
        assert len(received_events) == 1
        event = received_events[0]
        
        assert event.type == 'error'
        assert event.operation == operation
        assert event.data['error_code'] == ErrorCode.STREAM.value
        assert event.data['message'] == message
        assert event.data['retry_possible'] is True


class TestMessageHandlerRegistry:
    """Test message handler registry."""
    
    def test_registry_initialization(self, handler_registry):
        """Test registry initialization."""
        assert handler_registry.get_chat_handler() is not None
        assert handler_registry.get_progress_handler() is not None
        assert handler_registry.get_bog_handler() is not None
        assert handler_registry.get_error_handler() is not None
    
    def test_handler_types(self, handler_registry):
        """Test handler types."""
        assert isinstance(handler_registry.get_chat_handler(), ChatMessageHandler)
        assert isinstance(handler_registry.get_progress_handler(), ProgressMessageHandler)
        assert isinstance(handler_registry.get_bog_handler(), BOGGeneratedMessageHandler)
        assert isinstance(handler_registry.get_error_handler(), ErrorMessageHandler)