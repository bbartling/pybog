"""
Message type handlers for WebSocket communication.

This module provides specialized handlers for different WebSocket message types
including chat, progress, bog_generated, and error events.
"""

import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime, timezone

from ..core.events import EventBus, Event
from ..models.websocket_models import (
    WebSocketMessage, MessageType, ErrorCode, ProgressState,
    create_chat_message, create_progress_message, 
    create_bog_generated_message, create_error_message
)

logger = logging.getLogger(__name__)


class MessageHandler:
    """Base class for message handlers."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
    
    async def handle(self, session_id: str, data: Dict[str, Any]) -> Optional[WebSocketMessage]:
        """
        Handle a message and return a WebSocket message if needed.
        
        Args:
            session_id: The session identifier
            data: The message data
            
        Returns:
            WebSocket message or None
        """
        raise NotImplementedError


class ChatMessageHandler(MessageHandler):
    """Handler for chat message events."""
    
    async def handle_user_message(self, session_id: str, content: str) -> None:
        """
        Handle incoming user chat message.
        
        Args:
            session_id: The session identifier
            content: The chat message content
        """
        try:
            # Publish user message event
            await self.event_bus.publish(
                session_id,
                Event(
                    type='chat',
                    session_id=session_id,
                    operation='user_message',
                    data={
                        'content': content,
                        'source': 'user',
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                )
            )
            
            logger.debug(f"Handled user message for session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error handling user message for session {session_id}: {e}")
            # Publish error event
            await self.event_bus.publish(
                session_id,
                Event(
                    type='error',
                    session_id=session_id,
                    operation='chat_handle',
                    data={
                        'error_code': ErrorCode.STREAM,
                        'message': f"Error processing chat message: {str(e)}",
                        'retry_possible': True
                    }
                )
            )
    
    async def handle_assistant_response(self, session_id: str, content: str, 
                                      is_complete: bool = False, 
                                      message_id: Optional[str] = None) -> None:
        """
        Handle assistant response for streaming chat.
        
        Args:
            session_id: The session identifier
            content: The response content
            is_complete: Whether this is the final chunk
            message_id: Optional message identifier
        """
        try:
            # Publish assistant response event
            await self.event_bus.publish(
                session_id,
                Event(
                    type='chat',
                    session_id=session_id,
                    operation='assistant_response',
                    data={
                        'content': content,
                        'is_complete': is_complete,
                        'message_id': message_id,
                        'source': 'assistant',
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                )
            )
            
            logger.debug(f"Handled assistant response for session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error handling assistant response for session {session_id}: {e}")


class ProgressMessageHandler(MessageHandler):
    """Handler for progress update events."""
    
    async def handle_progress_update(self, session_id: str, state: ProgressState, 
                                   message: str, operation: str,
                                   file_id: Optional[int] = None,
                                   progress_percent: Optional[float] = None) -> None:
        """
        Handle progress update event.
        
        Args:
            session_id: The session identifier
            state: The progress state
            message: Progress message
            operation: The operation being performed
            file_id: Optional file ID
            progress_percent: Optional progress percentage
        """
        try:
            # Publish progress event
            await self.event_bus.publish(
                session_id,
                Event(
                    type='progress',
                    session_id=session_id,
                    operation=operation,
                    data={
                        'state': state.value,
                        'message': message,
                        'file_id': file_id,
                        'progress_percent': progress_percent,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                )
            )
            
            logger.debug(f"Handled progress update for session: {session_id}, state: {state}")
            
        except Exception as e:
            logger.error(f"Error handling progress update for session {session_id}: {e}")
    
    async def handle_file_upload_progress(self, session_id: str, file_id: int, 
                                        progress_percent: float) -> None:
        """
        Handle file upload progress.
        
        Args:
            session_id: The session identifier
            file_id: The file ID
            progress_percent: Upload progress percentage
        """
        await self.handle_progress_update(
            session_id=session_id,
            state=ProgressState.PROCESSING,
            message=f"Uploading file... {progress_percent:.1f}%",
            operation="file_upload",
            file_id=file_id,
            progress_percent=progress_percent
        )
    
    async def handle_analysis_progress(self, session_id: str, file_id: int, 
                                     state: ProgressState, message: str) -> None:
        """
        Handle analysis progress.
        
        Args:
            session_id: The session identifier
            file_id: The file ID being analyzed
            state: The analysis state
            message: Progress message
        """
        await self.handle_progress_update(
            session_id=session_id,
            state=state,
            message=message,
            operation="analysis",
            file_id=file_id
        )


class BOGGeneratedMessageHandler(MessageHandler):
    """Handler for BOG file generation events."""
    
    async def handle_bog_generated(self, session_id: str, file_id: int, 
                                 filename: str, analysis: Dict[str, Any],
                                 download_url: Optional[str] = None) -> None:
        """
        Handle BOG file generation completion.
        
        Args:
            session_id: The session identifier
            file_id: The generated BOG file ID
            filename: The BOG filename
            analysis: The analysis results
            download_url: Optional download URL
        """
        try:
            # Publish BOG generated event
            await self.event_bus.publish(
                session_id,
                Event(
                    type='bog_generated',
                    session_id=session_id,
                    operation='bog_generation',
                    data={
                        'file_id': file_id,
                        'filename': filename,
                        'analysis': analysis,
                        'download_url': download_url,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                )
            )
            
            logger.info(f"BOG file generated for session: {session_id}, file_id: {file_id}")
            
        except Exception as e:
            logger.error(f"Error handling BOG generation for session {session_id}: {e}")


class ErrorMessageHandler(MessageHandler):
    """Handler for error events."""
    
    async def handle_error(self, session_id: str, error_code: ErrorCode, 
                         message: str, operation: str,
                         details: Optional[Dict[str, Any]] = None,
                         retry_possible: bool = False) -> None:
        """
        Handle error event.
        
        Args:
            session_id: The session identifier
            error_code: The error code
            message: Error message
            operation: The operation that failed
            details: Optional error details
            retry_possible: Whether retry is possible
        """
        try:
            # Publish error event
            await self.event_bus.publish(
                session_id,
                Event(
                    type='error',
                    session_id=session_id,
                    operation=operation,
                    data={
                        'error_code': error_code.value,
                        'message': message,
                        'details': details,
                        'retry_possible': retry_possible,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                )
            )
            
            logger.error(f"Error event for session {session_id}: {error_code} - {message}")
            
        except Exception as e:
            logger.error(f"Error handling error event for session {session_id}: {e}")
    
    async def handle_file_error(self, session_id: str, message: str, 
                              file_id: Optional[int] = None,
                              retry_possible: bool = True) -> None:
        """
        Handle file-related error.
        
        Args:
            session_id: The session identifier
            message: Error message
            file_id: Optional file ID
            retry_possible: Whether retry is possible
        """
        await self.handle_error(
            session_id=session_id,
            error_code=ErrorCode.FILE,
            message=message,
            operation="file_operation",
            details={'file_id': file_id} if file_id else None,
            retry_possible=retry_possible
        )
    
    async def handle_analysis_error(self, session_id: str, message: str,
                                  file_id: Optional[int] = None,
                                  retry_possible: bool = True) -> None:
        """
        Handle analysis-related error.
        
        Args:
            session_id: The session identifier
            message: Error message
            file_id: Optional file ID
            retry_possible: Whether retry is possible
        """
        await self.handle_error(
            session_id=session_id,
            error_code=ErrorCode.ANALYSIS,
            message=message,
            operation="analysis",
            details={'file_id': file_id} if file_id else None,
            retry_possible=retry_possible
        )
    
    async def handle_database_error(self, session_id: str, message: str,
                                  operation: str = "database_operation",
                                  retry_possible: bool = False) -> None:
        """
        Handle database-related error.
        
        Args:
            session_id: The session identifier
            message: Error message
            operation: The database operation that failed
            retry_possible: Whether retry is possible
        """
        await self.handle_error(
            session_id=session_id,
            error_code=ErrorCode.DB,
            message=message,
            operation=operation,
            retry_possible=retry_possible
        )
    
    async def handle_stream_error(self, session_id: str, message: str,
                                operation: str = "websocket_operation",
                                retry_possible: bool = True) -> None:
        """
        Handle WebSocket/streaming-related error.
        
        Args:
            session_id: The session identifier
            message: Error message
            operation: The streaming operation that failed
            retry_possible: Whether retry is possible
        """
        await self.handle_error(
            session_id=session_id,
            error_code=ErrorCode.STREAM,
            message=message,
            operation=operation,
            retry_possible=retry_possible
        )


class MessageHandlerRegistry:
    """Registry for message handlers."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        
        # Initialize handlers
        self.chat_handler = ChatMessageHandler(event_bus)
        self.progress_handler = ProgressMessageHandler(event_bus)
        self.bog_handler = BOGGeneratedMessageHandler(event_bus)
        self.error_handler = ErrorMessageHandler(event_bus)
    
    def get_chat_handler(self) -> ChatMessageHandler:
        """Get the chat message handler."""
        return self.chat_handler
    
    def get_progress_handler(self) -> ProgressMessageHandler:
        """Get the progress message handler."""
        return self.progress_handler
    
    def get_bog_handler(self) -> BOGGeneratedMessageHandler:
        """Get the BOG generated message handler."""
        return self.bog_handler
    
    def get_error_handler(self) -> ErrorMessageHandler:
        """Get the error message handler."""
        return self.error_handler