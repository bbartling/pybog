"""
Unit tests for the Event Bus system.

Tests cover event publishing, subscribing, replay functionality,
and session management according to requirements 4.1, 4.4, 4.5.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock

from backend.core.events import Event, EventBus


class TestEvent:
    """Test cases for the Event model."""
    
    def test_event_creation_with_timestamp(self):
        """Test that Event creates with automatic timestamp."""
        event = Event(
            type="chat",
            session_id="test-session",
            operation="message",
            data={"content": "Hello"}
        )
        
        assert event.type == "chat"
        assert event.session_id == "test-session"
        assert event.operation == "message"
        assert event.data == {"content": "Hello"}
        assert isinstance(event.timestamp, datetime)
    
    def test_event_creation_with_custom_timestamp(self):
        """Test that Event accepts custom timestamp."""
        custom_time = datetime(2023, 1, 1, 12, 0, 0)
        event = Event(
            type="progress",
            session_id="test-session",
            operation="upload",
            data={"state": "processing"},
            timestamp=custom_time
        )
        
        assert event.timestamp == custom_time
    
    def test_event_serialization(self):
        """Test that Event can be serialized to dict."""
        event = Event(
            type="bog_generated",
            session_id="test-session",
            operation="analyze",
            data={"file_id": 123}
        )
        
        event_dict = event.model_dump()
        assert "type" in event_dict
        assert "session_id" in event_dict
        assert "operation" in event_dict
        assert "data" in event_dict
        assert "timestamp" in event_dict


class TestEventBus:
    """Test cases for the EventBus class."""
    
    @pytest.fixture
    def event_bus(self):
        """Create a fresh EventBus instance for each test."""
        return EventBus()
    
    @pytest.fixture
    def sample_event(self):
        """Create a sample event for testing."""
        return Event(
            type="chat",
            session_id="test-session",
            operation="message",
            data={"content": "Test message"}
        )
    
    @pytest.mark.asyncio
    async def test_publish_and_get_event(self, event_bus, sample_event):
        """Test basic event publishing and retrieval."""
        # Publish event
        await event_bus.publish("test-session", sample_event)
        
        # Get event
        received_event = await event_bus.get_next_event("test-session", timeout=1.0)
        
        assert received_event is not None
        assert received_event.type == sample_event.type
        assert received_event.session_id == sample_event.session_id
        assert received_event.operation == sample_event.operation
        assert received_event.data == sample_event.data
    
    @pytest.mark.asyncio
    async def test_multiple_sessions_isolation(self, event_bus):
        """Test that events are isolated between sessions."""
        event1 = Event(
            type="chat", session_id="session-1", 
            operation="message", data={"content": "Session 1"}
        )
        event2 = Event(
            type="chat", session_id="session-2", 
            operation="message", data={"content": "Session 2"}
        )
        
        # Publish to different sessions
        await event_bus.publish("session-1", event1)
        await event_bus.publish("session-2", event2)
        
        # Each session should only receive its own event
        received1 = await event_bus.get_next_event("session-1", timeout=1.0)
        received2 = await event_bus.get_next_event("session-2", timeout=1.0)
        
        assert received1.data["content"] == "Session 1"
        assert received2.data["content"] == "Session 2"
    
    @pytest.mark.asyncio
    async def test_event_replay_functionality(self, event_bus):
        """Test event replay buffer with maxlen=10."""
        session_id = "replay-session"
        
        # Publish 15 events (more than maxlen=10)
        events = []
        for i in range(15):
            event = Event(
                type="progress",
                session_id=session_id,
                operation="test",
                data={"step": i}
            )
            events.append(event)
            await event_bus.publish(session_id, event)
        
        # Get replay events
        replay_events = await event_bus.get_replay_events(session_id)
        
        # Should only have last 10 events
        assert len(replay_events) == 10
        
        # Should be the last 10 events (steps 5-14)
        for i, replay_event in enumerate(replay_events):
            expected_step = i + 5  # Steps 5-14
            assert replay_event.data["step"] == expected_step
    
    @pytest.mark.asyncio
    async def test_subscriber_callback_sync(self, event_bus, sample_event):
        """Test synchronous callback subscription."""
        received_events = []
        
        def sync_callback(event):
            received_events.append(event)
        
        # Subscribe and publish
        await event_bus.subscribe("test-session", sync_callback)
        await event_bus.publish("test-session", sample_event)
        
        # Give a moment for callback to execute
        await asyncio.sleep(0.1)
        
        assert len(received_events) == 1
        assert received_events[0].type == sample_event.type
    
    @pytest.mark.asyncio
    async def test_subscriber_callback_async(self, event_bus, sample_event):
        """Test asynchronous callback subscription."""
        received_events = []
        
        async def async_callback(event):
            received_events.append(event)
        
        # Subscribe and publish
        await event_bus.subscribe("test-session", async_callback)
        await event_bus.publish("test-session", sample_event)
        
        # Give a moment for callback to execute
        await asyncio.sleep(0.1)
        
        assert len(received_events) == 1
        assert received_events[0].type == sample_event.type
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, event_bus, sample_event):
        """Test multiple subscribers for the same session."""
        callback1_events = []
        callback2_events = []
        
        def callback1(event):
            callback1_events.append(event)
        
        def callback2(event):
            callback2_events.append(event)
        
        # Subscribe both callbacks
        await event_bus.subscribe("test-session", callback1)
        await event_bus.subscribe("test-session", callback2)
        
        # Publish event
        await event_bus.publish("test-session", sample_event)
        
        # Give a moment for callbacks to execute
        await asyncio.sleep(0.1)
        
        # Both callbacks should receive the event
        assert len(callback1_events) == 1
        assert len(callback2_events) == 1
        assert callback1_events[0].type == sample_event.type
        assert callback2_events[0].type == sample_event.type
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, event_bus, sample_event):
        """Test unsubscribing from events."""
        received_events = []
        
        def callback(event):
            received_events.append(event)
        
        # Subscribe, publish, unsubscribe, publish again
        await event_bus.subscribe("test-session", callback)
        await event_bus.publish("test-session", sample_event)
        
        await event_bus.unsubscribe("test-session", callback)
        await event_bus.publish("test-session", sample_event)
        
        # Give a moment for callbacks to execute
        await asyncio.sleep(0.1)
        
        # Should only receive the first event
        assert len(received_events) == 1
    
    @pytest.mark.asyncio
    async def test_get_next_event_timeout(self, event_bus):
        """Test timeout behavior when no events are available."""
        # Try to get event with short timeout
        event = await event_bus.get_next_event("empty-session", timeout=0.1)
        
        assert event is None
    
    @pytest.mark.asyncio
    async def test_clear_session(self, event_bus):
        """Test clearing all session data."""
        session_id = "clear-session"
        
        # Add some events and subscribers
        callback_called = []
        
        def callback(event):
            callback_called.append(True)
        
        await event_bus.subscribe(session_id, callback)
        
        for i in range(5):
            event = Event(
                type="test", session_id=session_id,
                operation="clear", data={"i": i}
            )
            await event_bus.publish(session_id, event)
        
        # Verify data exists
        assert event_bus.get_queue_size(session_id) > 0
        assert event_bus.get_replay_buffer_size(session_id) > 0
        assert event_bus.get_subscriber_count(session_id) > 0
        
        # Clear session
        await event_bus.clear_session(session_id)
        
        # Verify data is cleared
        assert event_bus.get_queue_size(session_id) == 0
        assert event_bus.get_replay_buffer_size(session_id) == 0
        assert event_bus.get_subscriber_count(session_id) == 0
    
    @pytest.mark.asyncio
    async def test_callback_error_handling(self, event_bus, sample_event):
        """Test that callback errors don't break the event bus."""
        good_callback_events = []
        
        def error_callback(event):
            raise Exception("Callback error")
        
        def good_callback(event):
            good_callback_events.append(event)
        
        # Subscribe both callbacks
        await event_bus.subscribe("test-session", error_callback)
        await event_bus.subscribe("test-session", good_callback)
        
        # Publish event
        await event_bus.publish("test-session", sample_event)
        
        # Give a moment for callbacks to execute
        await asyncio.sleep(0.1)
        
        # Good callback should still work despite error in other callback
        assert len(good_callback_events) == 1
    
    def test_session_metrics(self, event_bus):
        """Test session count and metrics methods."""
        # Initially no sessions
        assert event_bus.get_session_count() == 0
        
        # Create some sessions by accessing queues
        event_bus._session_queues["session-1"]
        event_bus._session_queues["session-2"]
        
        assert event_bus.get_session_count() == 2
        
        # Test queue size for empty session
        assert event_bus.get_queue_size("session-1") == 0
        
        # Test replay buffer size for empty session
        assert event_bus.get_replay_buffer_size("session-1") == 0
        
        # Test subscriber count for empty session
        assert event_bus.get_subscriber_count("session-1") == 0


@pytest.mark.asyncio
async def test_concurrent_publishing():
    """Test concurrent event publishing from multiple tasks."""
    event_bus = EventBus()
    session_id = "concurrent-session"
    num_tasks = 10
    events_per_task = 5
    
    async def publish_events(task_id):
        for i in range(events_per_task):
            event = Event(
                type="concurrent",
                session_id=session_id,
                operation="test",
                data={"task_id": task_id, "event_id": i}
            )
            await event_bus.publish(session_id, event)
    
    # Run concurrent publishing tasks
    tasks = [publish_events(i) for i in range(num_tasks)]
    await asyncio.gather(*tasks)
    
    # Verify all events were published
    total_expected = num_tasks * events_per_task
    assert event_bus.get_queue_size(session_id) == total_expected
    
    # Verify replay buffer has correct size (max 10)
    replay_events = await event_bus.get_replay_events(session_id)
    assert len(replay_events) == min(10, total_expected)


@pytest.mark.asyncio
async def test_session_resume_scenario():
    """Test a realistic session resume scenario."""
    event_bus = EventBus()
    session_id = "resume-session"
    
    # Simulate a session with various events
    events = [
        Event(type="chat", session_id=session_id, operation="message", 
              data={"content": "Hello"}),
        Event(type="progress", session_id=session_id, operation="upload", 
              data={"state": "processing", "file_id": 1}),
        Event(type="progress", session_id=session_id, operation="upload", 
              data={"state": "complete", "file_id": 1}),
        Event(type="progress", session_id=session_id, operation="analyze", 
              data={"state": "processing", "file_id": 1}),
        Event(type="bog_generated", session_id=session_id, operation="analyze", 
              data={"file_id": 2, "analysis": {"quality": 0.85}})
    ]
    
    # Publish all events
    for event in events:
        await event_bus.publish(session_id, event)
    
    # Simulate session resume - get replay events
    replay_events = await event_bus.get_replay_events(session_id)
    
    # Should have all 5 events in replay buffer
    assert len(replay_events) == 5
    
    # Events should be in order
    assert replay_events[0].data["content"] == "Hello"
    assert replay_events[-1].data["file_id"] == 2
    
    # New subscriber should be able to get replay events
    received_new_events = []
    
    def new_session_callback(event):
        received_new_events.append(event)
    
    await event_bus.subscribe(session_id, new_session_callback)
    
    # Publish a new event after resume
    new_event = Event(
        type="chat", session_id=session_id, 
        operation="message", data={"content": "Resumed"}
    )
    await event_bus.publish(session_id, new_event)
    
    await asyncio.sleep(0.1)
    
    # New subscriber should receive the new event
    assert len(received_new_events) == 1
    assert received_new_events[0].data["content"] == "Resumed"