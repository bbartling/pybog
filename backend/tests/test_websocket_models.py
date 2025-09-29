"""
Unit tests for WebSocket message models.
Tests message envelope format, validation, and helper functions.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from backend.models.websocket_models import (
    WebSocketMessage, MessageType, ErrorCode,
    ChatMessageData, ProgressMessageData, BOGGeneratedMessageData,
    ErrorMessageData, WebSocketConnectionInfo, SessionResumeInfo,
    create_chat_message, create_progress_message,
    create_bog_generated_message, create_error_message
)
from backend.models.file_models import ProgressState


class TestWebSocketMessage:
    """Test WebSocket message envelope."""
    
    def test_create_valid_message(self):
        """Test creating a valid WebSocket message."""
        message = WebSocketMessage(
            type=MessageType.CHAT,
            session_id="test-session",
            data={"content": "Hello", "is_complete": True}
        )
        
        assert message.type == MessageType.CHAT
        assert message.session_id == "test-session"
        assert message.data["content"] == "Hello"
        assert isinstance(message.timestamp, datetime)
    
    def test_empty_session_id_validation(self):
        """Test validation of empty session ID."""
        with pytest.raises(ValidationError) as exc_info:
            WebSocketMessage(
                type=MessageType.CHAT,
                session_id="",
                data={"content": "Hello"}
            )
        
        assert "Session ID cannot be empty" in str(exc_info.value)
    
    def test_whitespace_session_id_validation(self):
        """Test validation of whitespace-only session ID."""
        with pytest.raises(ValidationError) as exc_info:
            WebSocketMessage(
                type=MessageType.CHAT,
                session_id="   ",
                data={"content": "Hello"}
            )
        
        assert "Session ID cannot be empty" in str(exc_info.value)
    
    def test_json_serialization(self):
        """Test JSON serialization of WebSocket message."""
        message = WebSocketMessage(
            type=MessageType.CHAT,
            session_id="test-session",
            data={"content": "Hello", "is_complete": True}
        )
        
        json_str = message.model_dump_json()
        assert "test-session" in json_str
        assert "Hello" in json_str
        assert "chat" in json_str


class TestChatMessageData:
    """Test chat message data structure."""
    
    def test_create_valid_chat_data(self):
        """Test creating valid chat message data."""
        data = ChatMessageData(
            content="Hello world",
            is_complete=True,
            message_id="msg-123"
        )
        
        assert data.content == "Hello world"
        assert data.is_complete is True
        assert data.message_id == "msg-123"
    
    def test_default_values(self):
        """Test default values for chat message data."""
        data = ChatMessageData(content="Hello")
        
        assert data.content == "Hello"
        assert data.is_complete is False
        assert data.message_id is None
    
    def test_none_content_validation(self):
        """Test validation of None content."""
        with pytest.raises(ValidationError) as exc_info:
            ChatMessageData(content=None)
        
        # Pydantic v2 gives different error message for None string
        assert "string" in str(exc_info.value).lower()


class TestProgressMessageData:
    """Test progress message data structure."""
    
    def test_create_valid_progress_data(self):
        """Test creating valid progress message data."""
        data = ProgressMessageData(
            state=ProgressState.PROCESSING,
            message="Processing file...",
            operation="file_upload",
            file_id=123,
            progress_percent=45.5
        )
        
        assert data.state == ProgressState.PROCESSING
        assert data.message == "Processing file..."
        assert data.operation == "file_upload"
        assert data.file_id == 123
        assert data.progress_percent == 45.5
    
    def test_progress_percent_validation(self):
        """Test validation of progress percentage."""
        # Valid percentage
        data = ProgressMessageData(
            state=ProgressState.PROCESSING,
            message="Processing...",
            operation="test",
            progress_percent=50.0
        )
        assert data.progress_percent == 50.0
        
        # Invalid percentage - too low
        with pytest.raises(ValidationError) as exc_info:
            ProgressMessageData(
                state=ProgressState.PROCESSING,
                message="Processing...",
                operation="test",
                progress_percent=-10.0
            )
        assert "Progress percent must be between 0 and 100" in str(exc_info.value)
        
        # Invalid percentage - too high
        with pytest.raises(ValidationError) as exc_info:
            ProgressMessageData(
                state=ProgressState.PROCESSING,
                message="Processing...",
                operation="test",
                progress_percent=150.0
            )
        assert "Progress percent must be between 0 and 100" in str(exc_info.value)


class TestBOGGeneratedMessageData:
    """Test BOG generated message data structure."""
    
    def test_create_valid_bog_data(self):
        """Test creating valid BOG generated message data."""
        analysis = {"io_points": [], "control_blocks": []}
        data = BOGGeneratedMessageData(
            file_id=123,
            filename="test.bog",
            analysis=analysis,
            download_url="http://example.com/download/123"
        )
        
        assert data.file_id == 123
        assert data.filename == "test.bog"
        assert data.analysis == analysis
        assert data.download_url == "http://example.com/download/123"
    
    def test_file_id_validation(self):
        """Test validation of file ID."""
        with pytest.raises(ValidationError) as exc_info:
            BOGGeneratedMessageData(
                file_id=0,
                filename="test.bog",
                analysis={}
            )
        
        assert "File ID must be positive" in str(exc_info.value)
    
    def test_filename_validation(self):
        """Test validation of filename."""
        # Empty filename
        with pytest.raises(ValidationError) as exc_info:
            BOGGeneratedMessageData(
                file_id=123,
                filename="",
                analysis={}
            )
        assert "Filename cannot be empty" in str(exc_info.value)
        
        # Whitespace filename
        with pytest.raises(ValidationError) as exc_info:
            BOGGeneratedMessageData(
                file_id=123,
                filename="   ",
                analysis={}
            )
        assert "Filename cannot be empty" in str(exc_info.value)


class TestErrorMessageData:
    """Test error message data structure."""
    
    def test_create_valid_error_data(self):
        """Test creating valid error message data."""
        data = ErrorMessageData(
            error_code=ErrorCode.FILE,
            message="File upload failed",
            operation="file_upload",
            details={"file_size": 1000000},
            retry_possible=True
        )
        
        assert data.error_code == ErrorCode.FILE
        assert data.message == "File upload failed"
        assert data.operation == "file_upload"
        assert data.details == {"file_size": 1000000}
        assert data.retry_possible is True
    
    def test_message_validation(self):
        """Test validation of error message."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorMessageData(
                error_code=ErrorCode.FILE,
                message="",
                operation="test"
            )
        
        assert "Error message cannot be empty" in str(exc_info.value)
    
    def test_operation_validation(self):
        """Test validation of operation."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorMessageData(
                error_code=ErrorCode.FILE,
                message="Test error",
                operation=""
            )
        
        assert "Operation cannot be empty" in str(exc_info.value)


class TestWebSocketConnectionInfo:
    """Test WebSocket connection info."""
    
    def test_create_connection_info(self):
        """Test creating connection info."""
        info = WebSocketConnectionInfo(session_id="test-session")
        
        assert info.session_id == "test-session"
        assert isinstance(info.connected_at, datetime)
        assert isinstance(info.last_activity, datetime)
        assert info.message_count == 0
    
    def test_update_activity(self):
        """Test updating activity."""
        import time
        info = WebSocketConnectionInfo(session_id="test-session")
        original_activity = info.last_activity
        original_count = info.message_count
        
        # Sleep a tiny bit to ensure timestamp difference
        time.sleep(0.001)
        info.update_activity()
        
        assert info.last_activity >= original_activity
        assert info.message_count == original_count + 1


class TestHelperFunctions:
    """Test helper functions for creating messages."""
    
    def test_create_chat_message(self):
        """Test creating chat message."""
        message = create_chat_message(
            session_id="test-session",
            content="Hello world",
            is_complete=True,
            message_id="msg-123"
        )
        
        assert message.type == MessageType.CHAT
        assert message.session_id == "test-session"
        assert message.data["content"] == "Hello world"
        assert message.data["is_complete"] is True
        assert message.data["message_id"] == "msg-123"
    
    def test_create_progress_message(self):
        """Test creating progress message."""
        message = create_progress_message(
            session_id="test-session",
            state=ProgressState.PROCESSING,
            message="Processing...",
            operation="file_upload",
            file_id=123,
            progress_percent=50.0
        )
        
        assert message.type == MessageType.PROGRESS
        assert message.session_id == "test-session"
        assert message.data["state"] == ProgressState.PROCESSING
        assert message.data["message"] == "Processing..."
        assert message.data["operation"] == "file_upload"
        assert message.data["file_id"] == 123
        assert message.data["progress_percent"] == 50.0
    
    def test_create_bog_generated_message(self):
        """Test creating BOG generated message."""
        analysis = {"io_points": [], "control_blocks": []}
        message = create_bog_generated_message(
            session_id="test-session",
            file_id=123,
            filename="test.bog",
            analysis=analysis,
            download_url="http://example.com/download/123"
        )
        
        assert message.type == MessageType.BOG_GENERATED
        assert message.session_id == "test-session"
        assert message.data["file_id"] == 123
        assert message.data["filename"] == "test.bog"
        assert message.data["analysis"] == analysis
        assert message.data["download_url"] == "http://example.com/download/123"
    
    def test_create_error_message(self):
        """Test creating error message."""
        details = {"file_id": 123}
        message = create_error_message(
            session_id="test-session",
            error_code=ErrorCode.FILE,
            message="File upload failed",
            operation="file_upload",
            details=details,
            retry_possible=True
        )
        
        assert message.type == MessageType.ERROR
        assert message.session_id == "test-session"
        assert message.data["error_code"] == ErrorCode.FILE
        assert message.data["message"] == "File upload failed"
        assert message.data["operation"] == "file_upload"
        assert message.data["details"] == details
        assert message.data["retry_possible"] is True