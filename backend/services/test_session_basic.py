"""
Basic tests for SessionService to verify functionality.
"""

import pytest
from backend.models.session_models import Session, SessionCreateRequest, SessionUpdateRequest


def test_session_model_creation():
    """Test basic Session model creation."""
    session = Session(
        session_id="test-123",
        name="Test Session",
        metadata={"key": "value"}
    )
    assert session.session_id == "test-123"
    assert session.name == "Test Session"
    assert session.metadata == {"key": "value"}


def test_session_model_validation():
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


def test_create_request_validation():
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


def test_update_request_validation():
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


def test_session_service_import():
    """Test that SessionService can be imported."""
    from backend.services.session_service import SessionService
    from backend.core.events import EventBus
    
    # Create EventBus and SessionService
    event_bus = EventBus()
    service = SessionService(event_bus)
    
    # Verify service was created
    assert service is not None
    assert service.event_bus is event_bus