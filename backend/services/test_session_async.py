"""
Async tests for SessionService functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from backend.services.session_service import SessionService
from backend.models.session_models import Session, SessionCreateRequest, SessionUpdateRequest
from backend.core.events import EventBus
from backend.core.database import DatabaseOperationError


@pytest.mark.asyncio
async def test_create_session_success():
    """Test successful session creation."""
    # Setup
    event_bus = AsyncMock(spec=EventBus)
    service = SessionService(event_bus)
    
    sample_data = {
        "session_id": "test-session-123",
        "name": "Test Session",
        "metadata": {"created_by": "test"},
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    request = SessionCreateRequest(
        session_id=sample_data["session_id"],
        name=sample_data["name"],
        metadata=sample_data["metadata"]
    )
    
    # Mock database
    mock_db = AsyncMock()
    mock_db.fetch_one.side_effect = [
        None,  # No existing session
        sample_data  # Created session data
    ]
    
    with patch('backend.services.session_service.get_database', return_value=mock_db):
        # Execute
        result = await service.create_session(request)
        
        # Verify
        assert isinstance(result, Session)
        assert result.session_id == sample_data["session_id"]
        assert result.name == sample_data["name"]
        assert result.metadata == sample_data["metadata"]
        
        # Verify database calls
        assert mock_db.fetch_one.call_count == 2
        
        # Verify event emission
        event_bus.publish.assert_called_once()


@pytest.mark.asyncio
async def test_create_session_duplicate_id():
    """Test session creation with duplicate session_id."""
    # Setup
    event_bus = AsyncMock(spec=EventBus)
    service = SessionService(event_bus)
    
    request = SessionCreateRequest(
        session_id="existing-session",
        name="Test Session",
        metadata={}
    )
    
    # Mock database - existing session
    mock_db = AsyncMock()
    mock_db.fetch_one.return_value = {"session_id": "existing-session"}
    
    with patch('backend.services.session_service.get_database', return_value=mock_db):
        # Execute & Verify
        with pytest.raises(ValueError, match="already exists"):
            await service.create_session(request)


@pytest.mark.asyncio
async def test_get_session_success():
    """Test successful session retrieval."""
    # Setup
    event_bus = AsyncMock(spec=EventBus)
    service = SessionService(event_bus)
    
    sample_data = {
        "session_id": "test-session-123",
        "name": "Test Session",
        "metadata": {"key": "value"},
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    # Mock database
    mock_db = AsyncMock()
    mock_db.fetch_one.return_value = sample_data
    
    with patch('backend.services.session_service.get_database', return_value=mock_db):
        # Execute
        result = await service.get_session(sample_data["session_id"])
        
        # Verify
        assert isinstance(result, Session)
        assert result.session_id == sample_data["session_id"]
        assert result.name == sample_data["name"]


@pytest.mark.asyncio
async def test_get_session_not_found():
    """Test session retrieval when session doesn't exist."""
    # Setup
    event_bus = AsyncMock(spec=EventBus)
    service = SessionService(event_bus)
    
    # Mock database - no session found
    mock_db = AsyncMock()
    mock_db.fetch_one.return_value = None
    
    with patch('backend.services.session_service.get_database', return_value=mock_db):
        # Execute
        result = await service.get_session("nonexistent-session")
        
        # Verify
        assert result is None


@pytest.mark.asyncio
async def test_update_session_success():
    """Test successful session update."""
    # Setup
    event_bus = AsyncMock(spec=EventBus)
    service = SessionService(event_bus)
    
    session_id = "test-session-123"
    request = SessionUpdateRequest(name="Updated Name")
    
    updated_data = {
        "session_id": session_id,
        "name": "Updated Name",
        "metadata": {"key": "value"},
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    # Mock database
    mock_db = AsyncMock()
    mock_db.fetch_one.return_value = updated_data
    
    with patch('backend.services.session_service.get_database', return_value=mock_db):
        # Execute
        result = await service.update_session(session_id, request)
        
        # Verify
        assert isinstance(result, Session)
        assert result.name == "Updated Name"
        assert result.session_id == session_id
        
        # Verify event emission
        event_bus.publish.assert_called_once()


@pytest.mark.asyncio
async def test_delete_session_success():
    """Test successful session deletion."""
    # Setup
    event_bus = AsyncMock(spec=EventBus)
    service = SessionService(event_bus)
    
    session_id = "test-session-123"
    
    # Mock database
    mock_db = AsyncMock()
    mock_db.execute_query.return_value = "DELETE 1"
    
    with patch('backend.services.session_service.get_database', return_value=mock_db):
        # Execute
        result = await service.delete_session(session_id)
        
        # Verify
        assert result is True
        
        # Verify database call
        mock_db.execute_query.assert_called_once()
        
        # Verify event emission
        event_bus.publish.assert_called_once()
        
        # Verify session cleared from event bus
        event_bus.clear_session.assert_called_once_with(session_id)


@pytest.mark.asyncio
async def test_session_exists():
    """Test session existence check."""
    # Setup
    event_bus = AsyncMock(spec=EventBus)
    service = SessionService(event_bus)
    
    # Mock database
    mock_db = AsyncMock()
    mock_db.fetch_val.return_value = 1  # Session exists
    
    with patch('backend.services.session_service.get_database', return_value=mock_db):
        # Execute
        result = await service.session_exists("test-session")
        
        # Verify
        assert result is True


@pytest.mark.asyncio
async def test_generate_session_id():
    """Test session ID generation."""
    # Setup
    event_bus = AsyncMock(spec=EventBus)
    service = SessionService(event_bus)
    
    # Mock session_exists to return False (no conflicts)
    with patch.object(service, 'session_exists', return_value=False):
        # Execute
        session_id = await service.generate_session_id()
        
        # Verify
        assert session_id.startswith("session-")
        assert len(session_id) == 16  # "session-" + 8 hex chars


@pytest.mark.asyncio
async def test_database_error_handling():
    """Test database error handling."""
    # Setup
    event_bus = AsyncMock(spec=EventBus)
    service = SessionService(event_bus)
    
    request = SessionCreateRequest(
        session_id="test-session",
        name="Test Session",
        metadata={}
    )
    
    # Mock database error
    mock_db = AsyncMock()
    mock_db.fetch_one.side_effect = Exception("Database connection failed")
    
    with patch('backend.services.session_service.get_database', return_value=mock_db):
        # Execute & Verify
        with pytest.raises(DatabaseOperationError):
            await service.create_session(request)