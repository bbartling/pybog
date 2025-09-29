"""
WebSocket Manager for handling session events and broadcasting.

This module provides the WebSocketManager class that handles WebSocket connections,
message broadcasting, session resume functionality, and event replay.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.events import EventBus, Event
from models.websocket_models import (
    WebSocketMessage, MessageType, ErrorCode, WebSocketConnectionInfo,
    SessionResumeInfo, create_error_message, create_chat_message
)

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    WebSocket manager for handling session events and broadcasting.
    
    Manages WebSocket connections, handles event broadcasting, and provides
    session resume functionality with event replay from memory/DB.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        
        # Active WebSocket connections by session_id
        self._connections: Dict[str, WebSocket] = {}
        
        # Connection information tracking
        self._connection_info: Dict[str, WebSocketConnectionInfo] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """
        Accept a WebSocket connection and set up session handling.
        
        Args:
            websocket: The WebSocket connection
            session_id: The session identifier
        """
        await websocket.accept()
        
        async with self._lock:
            # Store connection
            self._connections[session_id] = websocket
            self._connection_info[session_id] = WebSocketConnectionInfo(session_id=session_id)
            
            # Subscribe to events for this session
            await self.event_bus.subscribe(session_id, self._handle_event)
        
        logger.info(f"WebSocket connected for session: {session_id}")
        
        # Resume session with event replay
        await self.resume_session(session_id, websocket)
    
    async def disconnect(self, session_id: str) -> None:
        """
        Handle WebSocket disconnection cleanup.
        
        Args:
            session_id: The session identifier
        """
        async with self._lock:
            # Remove connection
            if session_id in self._connections:
                del self._connections[session_id]
            
            # Remove connection info
            if session_id in self._connection_info:
                del self._connection_info[session_id]
            
            # Note: We don't clear the event bus session here to preserve
            # replay buffer for potential reconnection
        
        logger.info(f"WebSocket disconnected for session: {session_id}")
    
    async def send_message(self, session_id: str, message: WebSocketMessage) -> bool:
        """
        Send a message to a specific session.
        
        Args:
            session_id: The session identifier
            message: The WebSocket message to send
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        async with self._lock:
            websocket = self._connections.get(session_id)
            if not websocket:
                logger.warning(f"No WebSocket connection for session: {session_id}")
                return False
            
            try:
                # Update connection activity
                if session_id in self._connection_info:
                    self._connection_info[session_id].update_activity()
                
                # Send message
                await websocket.send_text(message.model_dump_json())
                logger.debug(f"Sent {message.type} message to session: {session_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error sending message to session {session_id}: {e}")
                # Clean up broken connection
                await self.disconnect(session_id)
                return False
    
    async def broadcast_to_all(self, message: WebSocketMessage) -> int:
        """
        Broadcast a message to all connected sessions.
        
        Args:
            message: The WebSocket message to broadcast
            
        Returns:
            Number of sessions that received the message
        """
        sent_count = 0
        session_ids = list(self._connections.keys())
        
        for session_id in session_ids:
            # Update message with correct session_id
            session_message = WebSocketMessage(
                type=message.type,
                session_id=session_id,
                data=message.data,
                timestamp=message.timestamp
            )
            
            if await self.send_message(session_id, session_message):
                sent_count += 1
        
        return sent_count
    
    async def handle_session_events(self, session_id: str, event: Event) -> None:
        """
        Handle events for a specific session and convert to WebSocket messages.
        
        Args:
            session_id: The session identifier
            event: The event to handle
        """
        try:
            # Convert event to WebSocket message based on event type
            message = await self._convert_event_to_message(event)
            if message:
                await self.send_message(session_id, message)
        
        except Exception as e:
            logger.error(f"Error handling event for session {session_id}: {e}")
            # Send error message to client
            error_message = create_error_message(
                session_id=session_id,
                error_code=ErrorCode.STREAM,
                message=f"Error processing event: {str(e)}",
                operation=event.operation
            )
            await self.send_message(session_id, error_message)
    
    async def resume_session(self, session_id: str, websocket: WebSocket) -> None:
        """
        Resume a session with event replay from memory/DB.
        
        Args:
            session_id: The session identifier
            websocket: The WebSocket connection
        """
        try:
            # Get replay events from event bus
            replay_events = await self.event_bus.get_replay_events(session_id)
            
            # Send resume info message first
            resume_message = create_chat_message(
                session_id=session_id,
                content=f"Session resumed with {len(replay_events)} recent events",
                is_complete=True
            )
            await websocket.send_text(resume_message.model_dump_json())
            
            # Convert events to WebSocket messages and send
            for event in replay_events:
                message = await self._convert_event_to_message(event)
                if message:
                    await websocket.send_text(message.model_dump_json())
            
            logger.info(f"Resumed session {session_id} with {len(replay_events)} replay events")
            
        except Exception as e:
            logger.error(f"Error resuming session {session_id}: {e}")
            # Send error message
            error_message = create_error_message(
                session_id=session_id,
                error_code=ErrorCode.STREAM,
                message=f"Error resuming session: {str(e)}",
                operation="session_resume"
            )
            await websocket.send_text(error_message.model_dump_json())
    
    async def handle_incoming_message(self, session_id: str, message_text: str) -> None:
        """
        Handle incoming WebSocket message from client with comprehensive error handling.
        
        Args:
            session_id: The session identifier
            message_text: The raw message text from client
        """
        from core.error_handler import get_error_handler, create_error_context, ErrorCategory
        
        error_handler = get_error_handler()
        
        try:
            # Validate message size
            if len(message_text) > 100000:  # 100KB limit
                raise ValueError("Message too large (maximum 100KB)")
            
            # Parse incoming message
            message_data = json.loads(message_text)
            
            # Validate message structure
            if not isinstance(message_data, dict):
                raise ValueError("Message must be a JSON object")
            
            # Handle different message types from client
            message_type = message_data.get('type')
            
            if not message_type:
                raise ValueError("Message must include 'type' field")
            
            if message_type == 'chat':
                await self._handle_chat_message(session_id, message_data)
            elif message_type == 'ping':
                await self._handle_ping_message(session_id, message_data)
            elif message_type == 'file_approval':
                await self._handle_file_approval(session_id, message_data)
            elif message_type == 'analysis_approval':
                await self._handle_analysis_approval(session_id, message_data)
            else:
                logger.warning(f"Unknown message type from client: {message_type}")
                # Send error for unknown message type
                error_message = create_error_message(
                    session_id=session_id,
                    error_code=ErrorCode.STREAM,
                    message=f"Unknown message type: {message_type}",
                    operation="message_parse",
                    retry_possible=False
                )
                await self.send_message(session_id, error_message)
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from client in session {session_id}: {e}")
            
            # Create error context
            context = create_error_context(
                operation="websocket_message_parse",
                component="WebSocketManager",
                session_id=session_id,
                additional_data={
                    "message_length": len(message_text),
                    "parse_error": str(e)
                }
            )
            
            # Handle error
            await error_handler.handle_error(
                error=e,
                context=context,
                emit_event=True
            )
            
            error_message = create_error_message(
                session_id=session_id,
                error_code=ErrorCode.STREAM,
                message="Invalid message format. Please send valid JSON.",
                operation="message_parse",
                retry_possible=True
            )
            await self.send_message(session_id, error_message)
        
        except ValueError as e:
            logger.error(f"Message validation error for session {session_id}: {e}")
            
            # Create error context
            context = create_error_context(
                operation="websocket_message_validate",
                component="WebSocketManager",
                session_id=session_id,
                additional_data={
                    "message_length": len(message_text),
                    "validation_error": str(e)
                }
            )
            
            # Handle error
            await error_handler.handle_error(
                error=e,
                context=context,
                emit_event=True
            )
            
            error_message = create_error_message(
                session_id=session_id,
                error_code=ErrorCode.STREAM,
                message=str(e),
                operation="message_validate",
                retry_possible=True
            )
            await self.send_message(session_id, error_message)
        
        except Exception as e:
            logger.error(f"Error handling incoming message for session {session_id}: {e}")
            
            # Create error context
            context = create_error_context(
                operation="websocket_message_handle",
                component="WebSocketManager",
                session_id=session_id,
                additional_data={
                    "message_length": len(message_text),
                    "error_type": type(e).__name__
                }
            )
            
            # Handle error
            await error_handler.handle_error(
                error=e,
                context=context,
                emit_event=True
            )
            
            error_message = create_error_message(
                session_id=session_id,
                error_code=ErrorCode.STREAM,
                message="An error occurred while processing your message. Please try again.",
                operation="message_handle",
                retry_possible=True
            )
            await self.send_message(session_id, error_message)
    
    async def _handle_chat_message(self, session_id: str, message_data: dict) -> None:
        """Handle chat message with error handling."""
        content = message_data.get('content', '')
        
        # Validate content
        if not content or not content.strip():
            raise ValueError("Chat message cannot be empty")
        
        if len(content) > 10000:  # 10k character limit
            raise ValueError("Chat message too long (maximum 10,000 characters)")
        
        # Import and use PyBOG Agent V2 for chat processing
        try:
            from .pybog_agent_v2 import PyBOGAgentV2
            
            # Create agent instance if not exists (in production, this would be injected)
            if not hasattr(self, '_pybog_agent'):
                from core.config import get_llm_config
                llm_config = get_llm_config()
                self._pybog_agent = PyBOGAgentV2(self.event_bus, openai_api_key=llm_config.openai_api_key)
            
            # Process chat message through agent (will stream response via events)
            await self._pybog_agent.process_chat_message(session_id, content)
            
        except Exception as e:
            logger.error(f"Error processing chat message through agent: {e}")
            
            # Fallback to basic event publishing
            chat_event = Event(
                type='chat',
                session_id=session_id,
                operation='user_message',
                data={
                    'content': content, 
                    'source': 'user',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
            await self.event_bus.publish(session_id, chat_event)
            
            # Send error message with recovery suggestions
            error_message = create_error_message(
                session_id=session_id,
                error_code=ErrorCode.ANALYSIS,
                message="Chat processing temporarily unavailable. Your message has been saved.",
                operation="chat_processing",
                retry_possible=True
            )
            await self.send_message(session_id, error_message)
    
    async def _handle_ping_message(self, session_id: str, message_data: dict) -> None:
        """Handle ping message."""
        pong_message = create_chat_message(
            session_id=session_id,
            content='pong',
            is_complete=True
        )
        await self.send_message(session_id, pong_message)
    
    async def _handle_file_approval(self, session_id: str, message_data: dict) -> None:
        """Handle file approval message."""
        file_id = message_data.get('file_id')
        approved = message_data.get('approved', False)
        
        # Validate file_id
        if not file_id or not isinstance(file_id, int):
            raise ValueError("file_id must be a valid integer")
        
        approval_event = Event(
            type='file_approval',
            session_id=session_id,
            operation='file_approval',
            data={
                'file_id': file_id,
                'approved': approved,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )
        await self.event_bus.publish(session_id, approval_event)
    
    async def _handle_analysis_approval(self, session_id: str, message_data: dict) -> None:
        """Handle analysis approval message."""
        analysis_id = message_data.get('analysis_id')
        approved = message_data.get('approved', False)
        feedback = message_data.get('feedback', '')
        
        # Validate analysis_id
        if not analysis_id or not isinstance(analysis_id, int):
            raise ValueError("analysis_id must be a valid integer")
        
        approval_event = Event(
            type='analysis_approval',
            session_id=session_id,
            operation='analysis_approval',
            data={
                'analysis_id': analysis_id,
                'approved': approved,
                'feedback': feedback,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )
        await self.event_bus.publish(session_id, approval_event)
    
    async def _handle_event(self, event: Event) -> None:
        """
        Internal event handler for event bus subscription.
        
        Args:
            event: The event to handle
        """
        await self.handle_session_events(event.session_id, event)
    
    async def _convert_event_to_message(self, event: Event) -> Optional[WebSocketMessage]:
        """
        Convert an event to a WebSocket message.
        
        Args:
            event: The event to convert
            
        Returns:
            WebSocket message or None if conversion not possible
        """
        try:
            # Determine message type based on event
            if event.type == 'chat':
                return WebSocketMessage(
                    type=MessageType.CHAT,
                    session_id=event.session_id,
                    data={
                        'content': event.data.get('content', ''),
                        'is_complete': event.data.get('is_complete', False),
                        'message_id': event.data.get('message_id'),
                        'buffer_content': event.data.get('buffer_content'),
                        'final_content': event.data.get('final_content'),
                        'message_type': event.data.get('message_type')
                    }
                )
            
            elif event.type == 'progress':
                return WebSocketMessage(
                    type=MessageType.PROGRESS,
                    session_id=event.session_id,
                    data={
                        'state': event.data.get('state'),
                        'message': event.data.get('message', ''),
                        'operation': event.operation,
                        'file_id': event.data.get('file_id'),
                        'progress_percent': event.data.get('progress_percent')
                    }
                )
            
            elif event.type == 'bog_generated':
                return WebSocketMessage(
                    type=MessageType.BOG_GENERATED,
                    session_id=event.session_id,
                    data={
                        'file_id': event.data.get('file_id'),
                        'filename': event.data.get('filename'),
                        'analysis': event.data.get('analysis', {}),
                        'download_url': event.data.get('download_url')
                    }
                )
            
            elif event.type == 'error':
                return WebSocketMessage(
                    type=MessageType.ERROR,
                    session_id=event.session_id,
                    data={
                        'error_code': event.data.get('error_code', 'STREAM'),
                        'message': event.data.get('message', ''),
                        'operation': event.operation,
                        'details': event.data.get('details'),
                        'retry_possible': event.data.get('retry_possible', False)
                    }
                )
            
            elif event.type == 'system':
                # Handle system events as chat messages for now
                return WebSocketMessage(
                    type=MessageType.CHAT,
                    session_id=event.session_id,
                    data={
                        'content': event.data.get('message', f"System: {event.operation}"),
                        'is_complete': True,
                        'message_id': f"system_{event.operation}"
                    }
                )
            
            else:
                logger.warning(f"Unknown event type for conversion: {event.type}")
                return None
        
        except Exception as e:
            logger.error(f"Error converting event to message: {e}")
            return None
    

    
    def get_connection_count(self) -> int:
        """Get the number of active WebSocket connections."""
        return len(self._connections)
    
    def get_connected_sessions(self) -> List[str]:
        """Get list of connected session IDs."""
        return list(self._connections.keys())
    
    def is_session_connected(self, session_id: str) -> bool:
        """Check if a session has an active WebSocket connection."""
        return session_id in self._connections
    
    def get_connection_info(self, session_id: str) -> Optional[WebSocketConnectionInfo]:
        """Get connection information for a session."""
        return self._connection_info.get(session_id)