"""
Event Bus System for Service Communication

This module provides an in-memory event bus system that allows services to communicate
through events without direct coupling. Each session has its own event queue and
replay buffer for session resume functionality.
"""

import asyncio
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class Event(BaseModel):
    """Event model with type, session_id, operation, and data fields."""
    
    type: str
    session_id: str
    operation: str
    data: Dict[str, Any]
    timestamp: datetime = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            from datetime import timezone
            data['timestamp'] = datetime.now(timezone.utc)
        super().__init__(**data)


class EventBus:
    """
    In-memory EventBus class with asyncio.Queue per session.
    
    Provides event publishing, subscribing, and replay functionality
    for session-based communication between services.
    """
    
    def __init__(self):
        # Session-specific event queues for real-time event delivery
        self._session_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        
        # Session-specific event replay buffers (last 10 events per session)
        self._session_replay_buffers: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10)
        )
        
        # Session-specific subscribers (callbacks for event handling)
        self._session_subscribers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def publish(self, session_id: str, event: Event) -> None:
        """
        Publish an event to a specific session.
        
        Args:
            session_id: The session identifier
            event: The event to publish
        """
        async with self._lock:
            # Add to replay buffer for session resume
            self._session_replay_buffers[session_id].append(event)
            
            # Add to session queue for real-time delivery
            await self._session_queues[session_id].put(event)
            
            # Notify all subscribers for this session
            for callback in self._session_subscribers[session_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in event callback for session {session_id}: {e}")
    
    async def subscribe(self, session_id: str, callback: Callable) -> None:
        """
        Subscribe to events for a specific session.
        
        Args:
            session_id: The session identifier
            callback: Callback function to handle events (can be sync or async)
        """
        async with self._lock:
            self._session_subscribers[session_id].append(callback)
    
    async def unsubscribe(self, session_id: str, callback: Callable) -> None:
        """
        Unsubscribe from events for a specific session.
        
        Args:
            session_id: The session identifier
            callback: The callback function to remove
        """
        async with self._lock:
            if callback in self._session_subscribers[session_id]:
                self._session_subscribers[session_id].remove(callback)
    
    async def get_next_event(self, session_id: str, timeout: Optional[float] = None) -> Optional[Event]:
        """
        Get the next event for a session (blocking).
        
        Args:
            session_id: The session identifier
            timeout: Optional timeout in seconds
            
        Returns:
            The next event or None if timeout occurred
        """
        try:
            if timeout:
                return await asyncio.wait_for(
                    self._session_queues[session_id].get(), 
                    timeout=timeout
                )
            else:
                return await self._session_queues[session_id].get()
        except asyncio.TimeoutError:
            return None
    
    async def get_replay_events(self, session_id: str) -> List[Event]:
        """
        Get replay events for session resume (last 10 events).
        Filters out chat events to prevent triggering new API calls.

        Args:
            session_id: The session identifier

        Returns:
            List of recent events for the session (excluding chat events)
        """
        async with self._lock:
            all_events = list(self._session_replay_buffers[session_id])
            # Filter out chat events to prevent unintended API calls on reconnect
            filtered_events = [
                event for event in all_events
                if event.type not in ['chat', 'message_sent', 'user_message', 'assistant_message']
            ]
            return filtered_events
    
    async def clear_session(self, session_id: str) -> None:
        """
        Clear all events and subscribers for a session.
        
        Args:
            session_id: The session identifier to clear
        """
        async with self._lock:
            # Clear the queue
            while not self._session_queues[session_id].empty():
                try:
                    self._session_queues[session_id].get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            # Clear replay buffer
            self._session_replay_buffers[session_id].clear()
            
            # Clear subscribers
            self._session_subscribers[session_id].clear()
    
    def get_session_count(self) -> int:
        """Get the number of active sessions."""
        return len(self._session_queues)
    
    def get_queue_size(self, session_id: str) -> int:
        """Get the current queue size for a session."""
        return self._session_queues[session_id].qsize()
    
    def get_replay_buffer_size(self, session_id: str) -> int:
        """Get the current replay buffer size for a session."""
        return len(self._session_replay_buffers[session_id])
    
    def get_subscriber_count(self, session_id: str) -> int:
        """Get the number of subscribers for a session."""
        return len(self._session_subscribers[session_id])