"""
Unit tests for FileService with hybrid storage and EventBus integration.
Tests file upload, storage decision logic, state transitions, and event emission.
"""

import asyncio
import pytest
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from fastapi import UploadFile

from backend.core.events import EventBus, Event
from backend.core.database import DatabaseManager
from backend.models.file_models import FileRecord, FileType, ProgressState, StorageType, FileMetadata
from backend.services.file_service import FileService


class MockUploadFile:
    """Mock UploadFile for testing."""
    
    def __init__(self, filename: str, content: bytes, content_type: str = "text/plain"):
        self.filename = filename
        self.content = content
        self.content_type = content_type
        self._content_read = False
    
    async def read(self) -> bytes:
        if self._content_read:
            return b""  # Simulate file already read
        self._content_read = True
        return self.content


@pytest.fixture
def event_bus():
    """Create EventBus instance for testing."""
    return EventBus()


@pytest.fixture
def mock_db():
    """Create mock database manager."""
    db = AsyncMock(spec=DatabaseManager)
    return db


@pytest.fixture
def file_service(event_bus, mock_db):
    """Create FileService instance with mocked dependencies."""
    with patch('backend.services.file_service.get_file_retention_config') as mock_config:
        # Create a mock config object with the required attributes
        mock_config_obj = MagicMock()
        mock_config_obj.max_file_size_mb = 10
        mock_config_obj.archive_threshold_days = 30
        mock_config_obj.purge_threshold_days = 90
        mock_config.return_value = mock_config_obj
        
        service = FileService(event_bus, mock_db)
        return service


@pytest.fixture
def sample_file_record():
    """Create sample FileRecord for testing."""
    return FileRecord(
        id=1,
        session_id="test-session",
        filename="test-file.txt",
        original_name="original.txt",
        mime_type="text/plain",
        file_type=FileType.UPLOAD,
        file_size=1024,
        state=ProgressState.QUEUED,
        metadata={},
        created_at=datetime.now(timezone.utc)
    )


class TestFileServiceUpload:
    """Test file upload functionality."""
    
    @pytest.mark.asyncio
    async def test_upload_small_file_bytea_storage(self, file_service, event_bus):
        """Test uploading a small file that should use BYTEA storage."""
        # Create small file (< 10MB)
        content = b"Small file content for BYTEA storage"
        mock_file = MockUploadFile("small.txt", content, "text/plain")
        
        # Mock database response for upload
        upload_response = {
            'id': 1,
            'session_id': 'test-session',
            'filename': 'small.txt',
            'original_name': 'small.txt',
            'mime_type': 'text/plain',
            'file_type': 'upload',
            'file_size': len(content),
            'state': 'processing',
            'metadata': {},
            'created_at': datetime.now(timezone.utc),
            'archived_at': None
        }
        
        # Mock database response for get_file_metadata (includes storage_type)
        metadata_response = {
            'id': 1,
            'session_id': 'test-session',
            'filename': 'small.txt',
            'original_name': 'small.txt',
            'mime_type': 'text/plain',
            'file_type': 'upload',
            'file_size': len(content),
            'state': 'processing',
            'storage_type': 'bytea',
            'metadata': {},
            'created_at': datetime.now(timezone.utc),
            'archived_at': None
        }
        
        # Set up mock to return different responses for different calls
        file_service.db_manager.fetch_one.side_effect = [upload_response, metadata_response]
        
        # Mock state update
        file_service.db_manager.execute_query.return_value = "UPDATE 1"
        
        # Upload file
        result = await file_service.upload_file("test-session", mock_file)
        
        # Verify result
        assert result.session_id == "test-session"
        assert result.original_name == "small.txt"
        assert result.file_size == len(content)
        assert result.state == ProgressState.COMPLETE
        
        # Verify database was called twice (upload + get_metadata)
        assert file_service.db_manager.fetch_one.call_count == 2
        
        # Check the first call (upload) contained BYTEA data
        first_call_args = file_service.db_manager.fetch_one.call_args_list[0][0]
        assert content in first_call_args  # BYTEA content should be in the upload call
        
        # Verify events were emitted
        events = await event_bus.get_replay_events("test-session")
        assert len(events) >= 3  # queued, processing, complete
        assert any(e.data.get("state") == ProgressState.QUEUED for e in events)
        assert any(e.data.get("state") == ProgressState.COMPLETE for e in events)
    
    @pytest.mark.asyncio
    async def test_upload_large_file_path_storage(self, file_service, event_bus):
        """Test uploading a large file that should use file_path storage."""
        # Create large file (> 10MB)
        content = b"x" * (11 * 1024 * 1024)  # 11MB
        mock_file = MockUploadFile("large.txt", content, "text/plain")
        
        # Mock database response for upload
        upload_response = {
            'id': 2,
            'session_id': 'test-session',
            'filename': 'large.txt',
            'original_name': 'large.txt',
            'mime_type': 'text/plain',
            'file_type': 'upload',
            'file_size': len(content),
            'state': 'processing',
            'metadata': {},
            'created_at': datetime.now(timezone.utc),
            'archived_at': None
        }
        
        # Mock database response for get_file_metadata (includes storage_type)
        metadata_response = {
            'id': 2,
            'session_id': 'test-session',
            'filename': 'large.txt',
            'original_name': 'large.txt',
            'mime_type': 'text/plain',
            'file_type': 'upload',
            'file_size': len(content),
            'state': 'processing',
            'storage_type': 'file_path',
            'metadata': {},
            'created_at': datetime.now(timezone.utc),
            'archived_at': None
        }
        
        # Set up mock to return different responses for different calls
        file_service.db_manager.fetch_one.side_effect = [upload_response, metadata_response]
        
        file_service.db_manager.execute_query.return_value = "UPDATE 1"
        
        # Upload file
        result = await file_service.upload_file("test-session", mock_file)
        
        # Verify result
        assert result.session_id == "test-session"
        assert result.original_name == "large.txt"
        assert result.file_size == len(content)
        assert result.state == ProgressState.COMPLETE
        
        # Verify database was called twice (upload + get_metadata)
        assert file_service.db_manager.fetch_one.call_count == 2
        
        # Check the first call (upload) did NOT contain BYTEA data
        first_call_args = file_service.db_manager.fetch_one.call_args_list[0][0]
        assert content not in first_call_args  # BYTEA content should NOT be in the file_path call
        
        # Verify file was written to disk
        # Note: In real test, we'd check the actual file exists
        
        # Verify events were emitted with storage_type info
        events = await event_bus.get_replay_events("test-session")
        processing_events = [e for e in events if e.data.get("state") == ProgressState.PROCESSING]
        assert len(processing_events) > 0
        assert processing_events[0].data.get("storage_type") == StorageType.FILE_PATH.value
    
    @pytest.mark.asyncio
    async def test_upload_file_too_large_error(self, file_service, event_bus):
        """Test uploading a file that exceeds the maximum size limit."""
        # Create extremely large file (> 50MB)
        content = b"x" * (51 * 1024 * 1024)  # 51MB
        mock_file = MockUploadFile("huge.txt", content, "text/plain")
        
        # Upload should fail
        with pytest.raises(ValueError, match="File too large"):
            await file_service.upload_file("test-session", mock_file)
        
        # Verify error event was emitted
        events = await event_bus.get_replay_events("test-session")
        error_events = [e for e in events if e.type == "error"]
        assert len(error_events) > 0
        assert error_events[0].data.get("error_code") == "FILE"
    
    @pytest.mark.asyncio
    async def test_upload_generates_unique_filename(self, file_service):
        """Test that uploaded files get unique filenames."""
        content = b"Test content"
        mock_file = MockUploadFile("test.txt", content)
        
        # Mock database response for upload
        upload_response = {
            'id': 1,
            'session_id': 'test-session',
            'filename': 'unique-filename.txt',
            'original_name': 'test.txt',
            'mime_type': 'text/plain',
            'file_type': 'upload',
            'file_size': len(content),
            'state': 'processing',
            'metadata': {},
            'created_at': datetime.now(timezone.utc),
            'archived_at': None
        }
        
        # Mock database response for get_file_metadata (includes storage_type)
        metadata_response = {
            'id': 1,
            'session_id': 'test-session',
            'filename': 'unique-filename.txt',
            'original_name': 'test.txt',
            'mime_type': 'text/plain',
            'file_type': 'upload',
            'file_size': len(content),
            'state': 'processing',
            'storage_type': 'bytea',
            'metadata': {},
            'created_at': datetime.now(timezone.utc),
            'archived_at': None
        }
        
        # Set up mock to return different responses for different calls
        file_service.db_manager.fetch_one.side_effect = [upload_response, metadata_response]
        
        file_service.db_manager.execute_query.return_value = "UPDATE 1"
        
        result = await file_service.upload_file("test-session", mock_file)
        
        # Verify original name is preserved but filename is unique
        assert result.original_name == "test.txt"
        assert result.filename != "test.txt"  # Should be unique
        assert result.filename.endswith(".txt")  # Should preserve extension


class TestFileServiceRetrieval:
    """Test file data retrieval functionality."""
    
    @pytest.mark.asyncio
    async def test_get_file_data_bytea_storage(self, file_service):
        """Test retrieving file data from BYTEA storage."""
        content = b"BYTEA stored content"
        
        # Mock database response with BYTEA data
        file_service.db_manager.fetch_one.return_value = {
            'id': 1,
            'session_id': 'test-session',
            'filename': 'test.txt',
            'file_data': content,
            'file_path': None,
            'file_size': len(content),
            'state': 'complete'
        }
        
        result = await file_service.get_file_data(1)
        
        assert result == content
        file_service.db_manager.fetch_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_file_data_file_path_storage(self, file_service):
        """Test retrieving file data from file_path storage."""
        content = b"File path stored content"
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Mock database response with file_path
            file_service.db_manager.fetch_one.return_value = {
                'id': 2,
                'session_id': 'test-session',
                'filename': 'test.txt',
                'file_data': None,
                'file_path': temp_path,
                'file_size': len(content),
                'state': 'complete'
            }
            
            result = await file_service.get_file_data(2)
            
            assert result == content
            file_service.db_manager.fetch_one.assert_called_once()
        
        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_get_file_data_not_found(self, file_service):
        """Test retrieving data for non-existent file."""
        file_service.db_manager.fetch_one.return_value = None
        
        with pytest.raises(FileNotFoundError):
            await file_service.get_file_data(999)
    
    @pytest.mark.asyncio
    async def test_get_file_data_no_storage(self, file_service):
        """Test retrieving data for file with no storage."""
        # Mock file with neither BYTEA nor file_path
        file_service.db_manager.fetch_one.return_value = {
            'id': 3,
            'session_id': 'test-session',
            'filename': 'test.txt',
            'file_data': None,
            'file_path': None,
            'file_size': 0,
            'state': 'failed'
        }
        
        with pytest.raises(ValueError, match="has no data"):
            await file_service.get_file_data(3)


class TestFileServiceStateManagement:
    """Test file state management and transitions."""
    
    @pytest.mark.asyncio
    async def test_valid_state_transitions(self, file_service, event_bus):
        """Test valid state transitions."""
        # Mock current file state
        file_service.db_manager.fetch_one.return_value = {
            'id': 1,
            'session_id': 'test-session',
            'filename': 'test.txt',
            'original_name': 'test.txt',
            'mime_type': 'text/plain',
            'file_type': 'upload',
            'file_size': 1024,
            'state': 'queued',
            'storage_type': 'bytea',
            'metadata': {},
            'created_at': datetime.now(timezone.utc),
            'archived_at': None
        }
        
        file_service.db_manager.execute_query.return_value = "UPDATE 1"
        
        # Test QUEUED -> PROCESSING
        result = await file_service.update_file_state(1, ProgressState.PROCESSING)
        assert result is True
        
        # Verify event was emitted
        events = await event_bus.get_replay_events("test-session")
        assert len(events) > 0
        assert events[-1].data.get("state") == ProgressState.PROCESSING.value
    
    @pytest.mark.asyncio
    async def test_invalid_state_transition(self, file_service):
        """Test invalid state transitions raise errors."""
        # Mock current file in COMPLETE state
        file_service.db_manager.fetch_one.return_value = {
            'id': 1,
            'session_id': 'test-session',
            'filename': 'test.txt',
            'original_name': 'test.txt',
            'mime_type': 'text/plain',
            'file_type': 'upload',
            'file_size': 1024,
            'state': 'complete',  # Terminal state
            'storage_type': 'bytea',
            'metadata': {},
            'created_at': datetime.now(timezone.utc),
            'archived_at': None
        }
        
        # Try to transition from COMPLETE to PROCESSING (invalid)
        with pytest.raises(ValueError, match="Invalid state transition"):
            await file_service.update_file_state(1, ProgressState.PROCESSING)
    
    @pytest.mark.asyncio
    async def test_failed_state_with_error_message(self, file_service, event_bus):
        """Test updating to FAILED state with error message."""
        # Mock current file state
        file_service.db_manager.fetch_one.return_value = {
            'id': 1,
            'session_id': 'test-session',
            'filename': 'test.txt',
            'original_name': 'test.txt',
            'mime_type': 'text/plain',
            'file_type': 'upload',
            'file_size': 1024,
            'state': 'processing',
            'storage_type': 'bytea',
            'metadata': {},
            'created_at': datetime.now(timezone.utc),
            'archived_at': None
        }
        
        file_service.db_manager.execute_query.return_value = "UPDATE 1"
        
        # Update to FAILED with error message
        error_msg = "Processing failed due to corruption"
        result = await file_service.update_file_state(
            1, ProgressState.FAILED, error_message=error_msg
        )
        
        assert result is True
        
        # Verify event includes error message
        events = await event_bus.get_replay_events("test-session")
        assert len(events) > 0
        assert events[-1].data.get("state") == ProgressState.FAILED.value
        assert events[-1].data.get("error_message") == error_msg
    
    def test_state_transition_validation_logic(self, file_service):
        """Test the state transition validation logic."""
        # Valid transitions
        file_service._validate_state_transition(ProgressState.QUEUED, ProgressState.PROCESSING)
        file_service._validate_state_transition(ProgressState.PROCESSING, ProgressState.FINALIZING)
        file_service._validate_state_transition(ProgressState.FINALIZING, ProgressState.COMPLETE)
        file_service._validate_state_transition(ProgressState.FAILED, ProgressState.QUEUED)  # Retry
        
        # Invalid transitions should raise ValueError
        with pytest.raises(ValueError):
            file_service._validate_state_transition(ProgressState.COMPLETE, ProgressState.PROCESSING)
        
        with pytest.raises(ValueError):
            file_service._validate_state_transition(ProgressState.QUEUED, ProgressState.COMPLETE)


class TestFileServiceListing:
    """Test file listing functionality."""
    
    @pytest.mark.asyncio
    async def test_list_session_files(self, file_service):
        """Test listing all files for a session."""
        # Mock database response
        file_service.db_manager.fetch_all.return_value = [
            {
                'id': 1,
                'session_id': 'test-session',
                'filename': 'file1.txt',
                'original_name': 'file1.txt',
                'mime_type': 'text/plain',
                'file_type': 'upload',
                'file_size': 1024,
                'state': 'complete',
                'storage_type': 'bytea',
                'metadata': {},
                'created_at': datetime.now(timezone.utc),
                'archived_at': None
            },
            {
                'id': 2,
                'session_id': 'test-session',
                'filename': 'file2.pdf',
                'original_name': 'file2.pdf',
                'mime_type': 'application/pdf',
                'file_type': 'document',
                'file_size': 2048,
                'state': 'processing',
                'storage_type': 'file_path',
                'metadata': {},
                'created_at': datetime.now(timezone.utc),
                'archived_at': None
            }
        ]
        
        result = await file_service.list_session_files("test-session")
        
        assert result.session_id == "test-session"
        assert result.total_count == 2
        assert len(result.files) == 2
        
        # Verify file details
        assert result.files[0].filename == "file1.txt"
        assert result.files[0].storage_type == StorageType.BYTEA
        assert result.files[1].filename == "file2.pdf"
        assert result.files[1].storage_type == StorageType.FILE_PATH
    
    @pytest.mark.asyncio
    async def test_list_session_files_with_type_filter(self, file_service):
        """Test listing files with file type filter."""
        file_service.db_manager.fetch_all.return_value = [
            {
                'id': 1,
                'session_id': 'test-session',
                'filename': 'upload.txt',
                'original_name': 'upload.txt',
                'mime_type': 'text/plain',
                'file_type': 'upload',
                'file_size': 1024,
                'state': 'complete',
                'storage_type': 'bytea',
                'metadata': {},
                'created_at': datetime.now(timezone.utc),
                'archived_at': None
            }
        ]
        
        result = await file_service.list_session_files("test-session", FileType.UPLOAD)
        
        assert result.total_count == 1
        assert result.files[0].file_type == FileType.UPLOAD
        
        # Verify query included file type filter
        file_service.db_manager.fetch_all.assert_called_once()
        call_args = file_service.db_manager.fetch_all.call_args[0]
        assert "file_type = $2" in call_args[0]
        assert "upload" in call_args


class TestFileServiceCleanup:
    """Test file cleanup functionality."""
    
    @pytest.mark.asyncio
    async def test_cleanup_old_files(self, file_service, event_bus):
        """Test file cleanup operations."""
        # Mock database cleanup functions
        file_service.db_manager.fetch_val.side_effect = [5, 3]  # archived, purged
        
        result = await file_service.cleanup_old_files()
        
        assert result.archived_count == 5
        assert result.purged_count == 3
        
        # Verify database functions were called
        assert file_service.db_manager.fetch_val.call_count == 2
        
        # Verify cleanup event was emitted
        events = await event_bus.get_replay_events("system")
        assert len(events) > 0
        cleanup_events = [e for e in events if e.operation == "file_cleanup"]
        assert len(cleanup_events) > 0
        assert cleanup_events[0].data.get("archived_count") == 5
        assert cleanup_events[0].data.get("purged_count") == 3


class TestFileServiceEventEmission:
    """Test event emission functionality."""
    
    @pytest.mark.asyncio
    async def test_event_emission_during_upload(self, file_service, event_bus):
        """Test that events are properly emitted during file upload."""
        content = b"Test content"
        mock_file = MockUploadFile("test.txt", content)
        
        # Mock database response for upload
        upload_response = {
            'id': 1,
            'session_id': 'test-session',
            'filename': 'test.txt',
            'original_name': 'test.txt',
            'mime_type': 'text/plain',
            'file_type': 'upload',
            'file_size': len(content),
            'state': 'processing',
            'metadata': {},
            'created_at': datetime.now(timezone.utc),
            'archived_at': None
        }
        
        # Mock database response for get_file_metadata (includes storage_type)
        metadata_response = {
            'id': 1,
            'session_id': 'test-session',
            'filename': 'test.txt',
            'original_name': 'test.txt',
            'mime_type': 'text/plain',
            'file_type': 'upload',
            'file_size': len(content),
            'state': 'processing',
            'storage_type': 'bytea',
            'metadata': {},
            'created_at': datetime.now(timezone.utc),
            'archived_at': None
        }
        
        # Set up mock to return different responses for different calls
        file_service.db_manager.fetch_one.side_effect = [upload_response, metadata_response]
        
        file_service.db_manager.execute_query.return_value = "UPDATE 1"
        
        await file_service.upload_file("test-session", mock_file)
        
        # Verify events were emitted in correct order
        events = await event_bus.get_replay_events("test-session")
        
        # Should have: queued, processing, complete events
        assert len(events) >= 3
        
        # Check event types and order
        event_states = [e.data.get("state") for e in events if "state" in e.data]
        assert ProgressState.QUEUED in event_states
        assert ProgressState.PROCESSING in event_states
        assert ProgressState.COMPLETE in event_states
        
        # Verify all events have correct session_id
        for event in events:
            assert event.session_id == "test-session"
    
    @pytest.mark.asyncio
    async def test_error_event_emission(self, file_service, event_bus):
        """Test that error events are properly emitted."""
        # Create file that will trigger size error
        content = b"x" * (51 * 1024 * 1024)  # 51MB
        mock_file = MockUploadFile("huge.txt", content)
        
        try:
            await file_service.upload_file("test-session", mock_file)
        except ValueError:
            pass  # Expected
        
        # Verify error event was emitted
        events = await event_bus.get_replay_events("test-session")
        error_events = [e for e in events if e.type == "error"]
        
        assert len(error_events) > 0
        assert error_events[0].data.get("error_code") == "FILE"
        assert "File too large" in error_events[0].data.get("message", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])