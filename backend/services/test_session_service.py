"""
Unit tests for SessionService.

Tests session CRUD operations, data integrity, event emission,
and error handling scenarios.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from backend.services.session_service import SessionService
from backend.models.session_models import (
    Session, 
    SessionCreateRequest, 
    SessionUpdateRequest,
    SessionWithFiles,
    SessionListResponse,
    SessionStatsResponse
)
from backend.core.events import EventBus, Event
from backend.core.database import DatabaseOperationError


class TestSessionService:
    """Test suite for SessionService class."""
    
    @pytest.fixture
    def event_bus(self):
        """Create a mock EventBus for testing."""
        return AsyncMock(spec=EventBus)
    
    @pytest.fixture
    def session_service(self, event_bus):
        """Create SessionService instance with mock EventBus."""
        return SessionService(event_bus)
    
    @pytest.fixture
    def sample_session_data(self):
        """Sample session data for testing."""
        return {
            "session_id": "test-session-123",
            "name": "Test Session",
            "metadata": {"created_by": "test", "purpose": "testing"},
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    
    @pytest.fixture
    def mock_database(self):
        """Create a mock database manager."""
        db_mock = AsyncMock()
        with patch('backend.services.session_service.get_database', return_value=db_mock):
            yield db_mock


class TestCreateSession(TestSessionService):
    """Test session creation functionality."""
    
    async def test_create_session_success(self, session_service, event_bus, mock_database, sample_session_data):
        """Test successful session creation."""
        # Setup
        request = SessionCreateRequest(
            session_id=sample_session_data["session_id"],
            name=sample_session_data["name"],
            metadata=sample_session_data["metadata"]
        )
        
        # Mock database responses
        mock_database.fetch_one.side_effect = [
            None,  # No existing session
            sample_session_data  # Created session data
        ]
        
        # Execute
        result = await session_service.create_session(request)
        
        # Verify
        assert isinstance(result, Session)
        assert result.session_id == sample_session_data["session_id"]
        assert result.name == sample_session_data["name"]
        assert result.metadata == sample_session_data["metadata"]
        
        # Verify database calls
        assert mock_database.fetch_one.call_count == 2
        
        # Verify event emission
        event_bus.publish.assert_called_once()
        call_args = event_bus.publish.call_args
        assert call_args[1]["session_id"] == sample_session_data["session_id"]
        assert call_args[1]["event"].type == "session"
        assert call_args[1]["event"].operation == "created"
    
    async def test_create_session_duplicate_id(self, session_service, mock_database, sample_session_data):
        """Test session creation with duplicate session_id."""
        # Setup
        request = SessionCreateRequest(
            session_id=sample_session_data["session_id"],
            name=sample_session_data["name"],
            metadata=sample_session_data["metadata"]
        )
        
        # Mock existing session
        mock_database.fetch_one.return_value = {"session_id": sample_session_data["session_id"]}
        
        # Execute & Verify
        with pytest.raises(ValueError, match="already exists"):
            await session_service.create_session(request)
    
    async def test_create_session_database_error(self, session_service, mock_database):
        """Test session creation with database error."""
        # Setup
        request = SessionCreateRequest(
            session_id="test-session",
            name="Test Session",
            metadata={}
        )
        
        # Mock database error
        mock_database.fetch_one.side_effect = [None, Exception("Database error")]
        
        # Execute & Verify
        with pytest.raises(DatabaseOperationError):
            await session_service.create_session(request)
    
    async def test_create_session_validation_error(self, session_service):
        """Test session creation with invalid data."""
        # Test empty session_id
        with pytest.raises(ValueError):
            SessionCreateRequest(session_id="", name="Test", metadata={})
        
        # Test empty name
        with pytest.raises(ValueError):
            SessionCreateRequest(session_id="test", name="", metadata={})


class TestGetSession(TestSessionService):
    """Test session retrieval functionality."""
    
    async def test_get_session_success(self, session_service, mock_database, sample_session_data):
        """Test successful session retrieval."""
        # Setup
        mock_database.fetch_one.return_value = sample_session_data
        
        # Execute
        result = await session_service.get_session(sample_session_data["session_id"])
        
        # Verify
        assert isinstance(result, Session)
        assert result.session_id == sample_session_data["session_id"]
        assert result.name == sample_session_data["name"]
        
        # Verify database call
        mock_database.fetch_one.assert_called_once()
    
    async def test_get_session_not_found(self, session_service, mock_database):
        """Test session retrieval when session doesn't exist."""
        # Setup
        mock_database.fetch_one.return_value = None
        
        # Execute
        result = await session_service.get_session("nonexistent-session")
        
        # Verify
        assert result is None
    
    async def test_get_session_database_error(self, session_service, mock_database):
        """Test session retrieval with database error."""
        # Setup
        mock_database.fetch_one.side_effect = Exception("Database error")
        
        # Execute & Verify
        with pytest.raises(DatabaseOperationError):
            await session_service.get_session("test-session")


class TestUpdateSession(TestSessionService):
    """Test session update functionality."""
    
    async def test_update_session_name_only(self, session_service, event_bus, mock_database, sample_session_data):
        """Test updating session name only."""
        # Setup
        request = SessionUpdateRequest(name="Updated Name")
        updated_data = {**sample_session_data, "name": "Updated Name"}
        
        mock_database.fetch_one.return_value = updated_data
        
        # Execute
        result = await session_service.update_session(sample_session_data["session_id"], request)
        
        # Verify
        assert isinstance(result, Session)
        assert result.name == "Updated Name"
        assert result.session_id == sample_session_data["session_id"]
        
        # Verify event emission
        event_bus.publish.assert_called_once()
        call_args = event_bus.publish.call_args
        assert call_args[1]["event"].operation == "updated"
    
    async def test_update_session_metadata_only(self, session_service, event_bus, mock_database, sample_session_data):
        """Test updating session metadata only."""
        # Setup
        new_metadata = {"updated": True, "version": 2}
        request = SessionUpdateRequest(metadata=new_metadata)
        updated_data = {**sample_session_data, "metadata": new_metadata}
        
        mock_database.fetch_one.return_value = updated_data
        
        # Execute
        result = await session_service.update_session(sample_session_data["session_id"], request)
        
        # Verify
        assert isinstance(result, Session)
        assert result.metadata == new_metadata
        assert result.session_id == sample_session_data["session_id"]
    
    async def test_update_session_both_fields(self, session_service, event_bus, mock_database, sample_session_data):
        """Test updating both name and metadata."""
        # Setup
        new_metadata = {"updated": True}
        request = SessionUpdateRequest(name="New Name", metadata=new_metadata)
        updated_data = {**sample_session_data, "name": "New Name", "metadata": new_metadata}
        
        mock_database.fetch_one.return_value = updated_data
        
        # Execute
        result = await session_service.update_session(sample_session_data["session_id"], request)
        
        # Verify
        assert result.name == "New Name"
        assert result.metadata == new_metadata
    
    async def test_update_session_no_fields(self, session_service, mock_database, sample_session_data):
        """Test update with no fields specified."""
        # Setup
        request = SessionUpdateRequest()
        
        with patch.object(session_service, 'get_session', return_value=Session(**sample_session_data)):
            # Execute
            result = await session_service.update_session(sample_session_data["session_id"], request)
            
            # Verify - should return current session without database update
            assert isinstance(result, Session)
            assert result.session_id == sample_session_data["session_id"]
    
    async def test_update_session_not_found(self, session_service, mock_database):
        """Test updating non-existent session."""
        # Setup
        request = SessionUpdateRequest(name="New Name")
        mock_database.fetch_one.return_value = None
        
        # Execute
        result = await session_service.update_session("nonexistent", request)
        
        # Verify
        assert result is None
    
    async def test_update_session_database_error(self, session_service, mock_database):
        """Test session update with database error."""
        # Setup
        request = SessionUpdateRequest(name="New Name")
        mock_database.fetch_one.side_effect = Exception("Database error")
        
        # Execute & Verify
        with pytest.raises(DatabaseOperationError):
            await session_service.update_session("test-session", request)


class TestDeleteSession(TestSessionService):
    """Test session deletion functionality."""
    
    async def test_delete_session_success(self, session_service, event_bus, mock_database):
        """Test successful session deletion."""
        # Setup
        session_id = "test-session-123"
        mock_database.execute_query.return_value = "DELETE 1"
        
        # Execute
        result = await session_service.delete_session(session_id)
        
        # Verify
        assert result is True
        
        # Verify database call
        mock_database.execute_query.assert_called_once()
        
        # Verify event emission
        event_bus.publish.assert_called_once()
        call_args = event_bus.publish.call_args
        assert call_args[1]["event"].operation == "deleted"
        
        # Verify session cleared from event bus
        event_bus.clear_session.assert_called_once_with(session_id)
    
    async def test_delete_session_not_found(self, session_service, mock_database):
        """Test deleting non-existent session."""
        # Setup
        mock_database.execute_query.return_value = "DELETE 0"
        
        # Execute
        result = await session_service.delete_session("nonexistent")
        
        # Verify
        assert result is False
    
    async def test_delete_session_database_error(self, session_service, mock_database):
        """Test session deletion with database error."""
        # Setup
        mock_database.execute_query.side_effect = Exception("Database error")
        
        # Execute & Verify
        with pytest.raises(DatabaseOperationError):
            await session_service.delete_session("test-session")


class TestListSessions(TestSessionService):
    """Test session listing functionality."""
    
    async def test_list_sessions_success(self, session_service, mock_database):
        """Test successful session listing."""
        # Setup
        session_data = [
            {
                "session_id": "session-1",
                "name": "Session 1",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "metadata": {},
                "message_count": 5,
                "file_count": 2,
                "upload_count": 1,
                "bog_count": 1,
                "analysis_count": 1,
                "completed_analysis_count": 1,
                "active_analysis_count": 0
            },
            {
                "session_id": "session-2",
                "name": "Session 2",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "metadata": {},
                "message_count": 3,
                "file_count": 1,
                "upload_count": 1,
                "bog_count": 0,
                "analysis_count": 0,
                "completed_analysis_count": 0,
                "active_analysis_count": 0
            }
        ]
        
        mock_database.fetch_all.return_value = session_data
        mock_database.fetch_val.return_value = 2
        
        # Execute
        result = await session_service.list_sessions(limit=10, offset=0)
        
        # Verify
        assert isinstance(result, SessionListResponse)
        assert len(result.sessions) == 2
        assert result.total_count == 2
        assert all(isinstance(s, SessionWithFiles) for s in result.sessions)
        
        # Verify database calls
        mock_database.fetch_all.assert_called_once()
        mock_database.fetch_val.assert_called_once()
    
    async def test_list_sessions_empty(self, session_service, mock_database):
        """Test listing when no sessions exist."""
        # Setup
        mock_database.fetch_all.return_value = []
        mock_database.fetch_val.return_value = 0
        
        # Execute
        result = await session_service.list_sessions()
        
        # Verify
        assert isinstance(result, SessionListResponse)
        assert len(result.sessions) == 0
        assert result.total_count == 0
    
    async def test_list_sessions_with_pagination(self, session_service, mock_database):
        """Test session listing with pagination parameters."""
        # Setup
        mock_database.fetch_all.return_value = []
        mock_database.fetch_val.return_value = 100
        
        # Execute
        await session_service.list_sessions(limit=20, offset=40)
        
        # Verify pagination parameters were passed
        call_args = mock_database.fetch_all.call_args
        assert call_args[0][1] == 20  # limit
        assert call_args[0][2] == 40  # offset
    
    async def test_list_sessions_database_error(self, session_service, mock_database):
        """Test session listing with database error."""
        # Setup
        mock_database.fetch_all.side_effect = Exception("Database error")
        
        # Execute & Verify
        with pytest.raises(DatabaseOperationError):
            await session_service.list_sessions()


class TestSessionStats(TestSessionService):
    """Test session statistics functionality."""
    
    async def test_get_session_stats_success(self, session_service, mock_database):
        """Test successful session stats retrieval."""
        # Setup
        stats_data = {
            "total_sessions": 10,
            "active_sessions": 3,
            "total_messages": 50,
            "total_files": 25,
            "total_analyses": 15
        }
        
        mock_database.fetch_one.return_value = stats_data
        
        # Execute
        result = await session_service.get_session_stats()
        
        # Verify
        assert isinstance(result, SessionStatsResponse)
        assert result.total_sessions == 10
        assert result.active_sessions == 3
        assert result.total_messages == 50
        assert result.total_files == 25
        assert result.total_analyses == 15
    
    async def test_get_session_stats_database_error(self, session_service, mock_database):
        """Test session stats with database error."""
        # Setup
        mock_database.fetch_one.side_effect = Exception("Database error")
        
        # Execute & Verify
        with pytest.raises(DatabaseOperationError):
            await session_service.get_session_stats()


class TestSessionUtilities(TestSessionService):
    """Test utility functions."""
    
    async def test_session_exists_true(self, session_service, mock_database):
        """Test session existence check when session exists."""
        # Setup
        mock_database.fetch_val.return_value = 1
        
        # Execute
        result = await session_service.session_exists("test-session")
        
        # Verify
        assert result is True
    
    async def test_session_exists_false(self, session_service, mock_database):
        """Test session existence check when session doesn't exist."""
        # Setup
        mock_database.fetch_val.return_value = None
        
        # Execute
        result = await session_service.session_exists("nonexistent")
        
        # Verify
        assert result is False
    
    async def test_session_exists_database_error(self, session_service, mock_database):
        """Test session existence check with database error."""
        # Setup
        mock_database.fetch_val.side_effect = Exception("Database error")
        
        # Execute & Verify
        with pytest.raises(DatabaseOperationError):
            await session_service.session_exists("test-session")
    
    async def test_generate_session_id_unique(self, session_service):
        """Test session ID generation produces unique IDs."""
        # Mock session_exists to always return False (no conflicts)
        with patch.object(session_service, 'session_exists', return_value=False):
            # Execute
            session_id = await session_service.generate_session_id()
            
            # Verify
            assert session_id.startswith("session-")
            assert len(session_id) == 16  # "session-" + 8 hex chars
    
    async def test_generate_session_id_with_collision(self, session_service):
        """Test session ID generation handles collisions."""
        # Mock session_exists to return True first time, False second time
        with patch.object(session_service, 'session_exists', side_effect=[True, False]):
            # Execute
            session_id = await session_service.generate_session_id()
            
            # Verify
            assert session_id.startswith("session-")
            assert len(session_id) == 16


class TestDataIntegrity(TestSessionService):
    """Test data integrity and consistency."""
    
    async def test_session_model_validation(self):
        """Test Session model validation."""
        # Valid session
        session = Session(
            session_id="test-123",
            name="Test Session",
            metadata={"key": "value"}
        )
        assert session.session_id == "test-123"
        assert session.name == "Test Session"
        
        # Invalid session - empty session_id
        with pytest.raises(ValueError):
            Session(session_id="", name="Test", metadata={})
        
        # Invalid session - empty name
        with pytest.raises(ValueError):
            Session(session_id="test", name="", metadata={})
    
    async def test_create_request_validation(self):
        """Test SessionCreateRequest validation."""
        # Valid request
        request = SessionCreateRequest(
            session_id="test-123",
            name="Test Session",
            metadata={"key": "value"}
        )
        assert request.session_id == "test-123"
        
        # Invalid - whitespace handling
        request = SessionCreateRequest(
            session_id="  test-123  ",
            name="  Test Session  ",
            metadata={}
        )
        assert request.session_id == "test-123"
        assert request.name == "Test Session"
    
    async def test_update_request_validation(self):
        """Test SessionUpdateRequest validation."""
        # Valid request with name
        request = SessionUpdateRequest(name="New Name")
        assert request.name == "New Name"
        
        # Valid request with metadata
        request = SessionUpdateRequest(metadata={"updated": True})
        assert request.metadata == {"updated": True}
        
        # Valid request with both
        request = SessionUpdateRequest(name="New Name", metadata={"key": "value"})
        assert request.name == "New Name"
        assert request.metadata == {"key": "value"}
        
        # Invalid - empty name
        with pytest.raises(ValueError):
            SessionUpdateRequest(name="")


# Integration test fixtures and helpers
@pytest.fixture
def real_event_bus():
    """Create a real EventBus for integration testing."""
    return EventBus()


@pytest.mark.integration
class TestSessionServiceIntegration:
    """Integration tests with real EventBus."""
    
    @pytest.fixture
    def mock_database_integration(self):
        """Create a mock database manager for integration tests."""
        db_mock = AsyncMock()
        with patch('backend.services.session_service.get_database', return_value=db_mock):
            yield db_mock
    
    async def test_event_emission_integration(self, real_event_bus, mock_database_integration, sample_session_data):
        """Test that events are properly emitted to EventBus."""
        # Setup
        service = SessionService(real_event_bus)
        request = SessionCreateRequest(
            session_id=sample_session_data["session_id"],
            name=sample_session_data["name"],
            metadata=sample_session_data["metadata"]
        )
        
        # Mock database
        mock_database_integration.fetch_one.side_effect = [None, sample_session_data]
        
        # Setup event listener
        received_events = []
        
        async def event_listener(event):
            received_events.append(event)
        
        await real_event_bus.subscribe(sample_session_data["session_id"], event_listener)
        
        # Execute
        await service.create_session(request)
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Verify event was received
        assert len(received_events) == 1
        event = received_events[0]
        assert event.type == "session"
        assert event.operation == "created"
        assert event.session_id == sample_session_data["session_id"]