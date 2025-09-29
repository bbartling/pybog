"""
Error handling decorators and utilities for PyBOG Backend

This module provides decorators and utilities for automatic error handling,
retry logic, and error context management across the application.
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Optional, Type, Union, Dict, List
from datetime import datetime, timezone

from core.error_handler import (
    ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity,
    get_error_handler, create_error_context
)

logger = logging.getLogger(__name__)


def handle_errors(
    component: str,
    operation: Optional[str] = None,
    category: ErrorCategory = ErrorCategory.SYSTEM,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    emit_event: bool = True,
    reraise: bool = True,
    fallback_result: Any = None,
    session_id_param: Optional[str] = None
):
    """
    Decorator for automatic error handling with context creation.
    
    Args:
        component: Component name where error occurred
        operation: Operation name (defaults to function name)
        category: Error category for classification
        severity: Error severity level
        emit_event: Whether to emit error events
        reraise: Whether to reraise the exception after handling
        fallback_result: Result to return if not reraising
        session_id_param: Parameter name containing session_id
    
    Example:
        @handle_errors("FileService", "upload_file", ErrorCategory.FILE)
        async def upload_file(self, session_id: str, file: UploadFile):
            # Function implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            error_handler = get_error_handler()
            op_name = operation or func.__name__
            
            # Extract session_id from parameters
            session_id = None
            if session_id_param:
                if session_id_param in kwargs:
                    session_id = kwargs[session_id_param]
                elif len(args) > 0 and hasattr(args[0], session_id_param):
                    session_id = getattr(args[0], session_id_param)
            
            # Try to find session_id in common parameter names
            if not session_id:
                for param_name in ['session_id', 'session', 'sid']:
                    if param_name in kwargs:
                        session_id = kwargs[param_name]
                        break
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Create error context
                context = create_error_context(
                    operation=op_name,
                    component=component,
                    session_id=session_id,
                    additional_data={
                        "function_name": func.__name__,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys())
                    }
                )
                
                # Handle error
                error_response = await error_handler.handle_error(
                    error=e,
                    context=context,
                    emit_event=emit_event
                )
                
                logger.error(f"Error in {component}.{op_name}: {error_response.message}")
                
                if reraise:
                    raise
                else:
                    return fallback_result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions, create a simple wrapper
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {component}.{operation or func.__name__}: {str(e)}")
                if reraise:
                    raise
                else:
                    return fallback_result
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def retry_on_error(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_backoff: bool = True,
    jitter: bool = True,
    retry_on: Optional[List[Type[Exception]]] = None,
    component: str = "Unknown",
    operation: Optional[str] = None
):
    """
    Decorator for automatic retry with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_backoff: Whether to use exponential backoff
        jitter: Whether to add random jitter to delays
        retry_on: List of exception types to retry on (None = all exceptions)
        component: Component name for error context
        operation: Operation name for error context
    
    Example:
        @retry_on_error(max_attempts=3, component="DatabaseService")
        async def connect_to_database(self):
            # Function implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            error_handler = get_error_handler()
            op_name = operation or func.__name__
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    result = await func(*args, **kwargs)
                    
                    # Log success if not first attempt
                    if attempt > 0:
                        logger.info(f"{component}.{op_name} succeeded on attempt {attempt + 1}")
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if we should retry this exception type
                    if retry_on and not any(isinstance(e, exc_type) for exc_type in retry_on):
                        logger.debug(f"Not retrying {type(e).__name__} (not in retry_on list)")
                        raise
                    
                    # Don't retry on last attempt
                    if attempt == max_attempts - 1:
                        break
                    
                    # Calculate delay
                    delay = _calculate_delay(attempt, base_delay, max_delay, exponential_backoff, jitter)
                    
                    logger.warning(
                        f"{component}.{op_name} failed on attempt {attempt + 1}/{max_attempts}, "
                        f"retrying in {delay:.1f}s: {str(e)}"
                    )
                    
                    await asyncio.sleep(delay)
            
            # All retries failed
            if last_exception:
                context = create_error_context(
                    operation=op_name,
                    component=component,
                    additional_data={
                        "max_attempts": max_attempts,
                        "final_attempt": max_attempts
                    }
                )
                
                await error_handler.handle_error(
                    error=last_exception,
                    context=context,
                    custom_message=f"Operation failed after {max_attempts} attempts"
                )
                
                raise last_exception
            
            raise RuntimeError("Retry logic failed unexpectedly")
        
        return wrapper
    
    return decorator


def _calculate_delay(attempt: int, base_delay: float, max_delay: float, 
                    exponential_backoff: bool, jitter: bool) -> float:
    """Calculate retry delay with exponential backoff and jitter."""
    if exponential_backoff:
        delay = base_delay * (2 ** attempt)
    else:
        delay = base_delay
    
    # Apply maximum delay limit
    delay = min(delay, max_delay)
    
    # Add jitter to prevent thundering herd
    if jitter:
        import random
        jitter_factor = random.uniform(0.5, 1.5)
        delay *= jitter_factor
    
    return delay


def validate_session(session_param: str = "session_id"):
    """
    Decorator to validate session existence and accessibility.
    
    Args:
        session_param: Parameter name containing session_id
    
    Example:
        @validate_session("session_id")
        async def get_session_files(self, session_id: str):
            # Function implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract session_id
            session_id = kwargs.get(session_param)
            
            # If not found in kwargs, try to extract from positional args
            if not session_id and len(args) > 1:
                # Try to get from positional args (assuming self is first)
                try:
                    session_id = args[1] if session_param == "session_id" else None
                except IndexError:
                    pass
            
            # If still not found, try to extract from Pydantic request models
            if not session_id:
                for arg in args:
                    if hasattr(arg, session_param):
                        session_id = getattr(arg, session_param)
                        break
            
            if not session_id:
                raise ValueError(f"Missing required parameter: {session_param}")
            
            if not isinstance(session_id, str) or not session_id.strip():
                raise ValueError(f"Invalid {session_param}: must be non-empty string")
            
            # Validate session format (basic validation)
            if len(session_id.strip()) < 3:
                raise ValueError(f"Invalid {session_param}: too short")
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def log_performance(
    component: str,
    operation: Optional[str] = None,
    log_args: bool = False,
    log_result: bool = False,
    slow_threshold: float = 5.0
):
    """
    Decorator to log function performance and detect slow operations.
    
    Args:
        component: Component name for logging
        operation: Operation name (defaults to function name)
        log_args: Whether to log function arguments
        log_result: Whether to log function result
        slow_threshold: Threshold in seconds to log as slow operation
    
    Example:
        @log_performance("FileService", "upload_file", slow_threshold=10.0)
        async def upload_file(self, session_id: str, file: UploadFile):
            # Function implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            start_time = datetime.now(timezone.utc)
            
            # Log start
            log_msg = f"Starting {component}.{op_name}"
            if log_args:
                log_msg += f" with args: {args[1:] if args else []}, kwargs: {kwargs}"
            logger.debug(log_msg)
            
            try:
                result = await func(*args, **kwargs)
                
                # Calculate duration
                end_time = datetime.now(timezone.utc)
                duration = (end_time - start_time).total_seconds()
                
                # Log completion
                log_level = logging.WARNING if duration > slow_threshold else logging.DEBUG
                log_msg = f"Completed {component}.{op_name} in {duration:.2f}s"
                if log_result and result is not None:
                    log_msg += f" -> {type(result).__name__}"
                
                logger.log(log_level, log_msg)
                
                return result
                
            except Exception as e:
                # Calculate duration for failed operation
                end_time = datetime.now(timezone.utc)
                duration = (end_time - start_time).total_seconds()
                
                logger.error(f"Failed {component}.{op_name} after {duration:.2f}s: {str(e)}")
                raise
        
        return wrapper
    
    return decorator


def require_file_access(file_id_param: str = "file_id"):
    """
    Decorator to validate file access permissions.
    
    Args:
        file_id_param: Parameter name containing file_id
    
    Example:
        @require_file_access("file_id")
        async def get_file_content(self, session_id: str, file_id: int):
            # Function implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract file_id
            file_id = kwargs.get(file_id_param)
            if file_id is None:
                # Try to find in positional args
                for i, arg in enumerate(args):
                    if isinstance(arg, int) and i > 0:  # Skip self
                        file_id = arg
                        break
            
            if file_id is None:
                raise ValueError(f"Missing required parameter: {file_id_param}")
            
            if not isinstance(file_id, int) or file_id <= 0:
                raise ValueError(f"Invalid {file_id_param}: must be positive integer")
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


class ErrorContextManager:
    """
    Context manager for error handling with automatic context creation.
    
    Example:
        async with ErrorContextManager("FileService", "upload_file", session_id="123"):
            # Operations that might fail
            result = await some_operation()
    """
    
    def __init__(
        self,
        component: str,
        operation: str,
        session_id: Optional[str] = None,
        emit_event: bool = True,
        reraise: bool = True,
        **context_data
    ):
        self.component = component
        self.operation = operation
        self.session_id = session_id
        self.emit_event = emit_event
        self.reraise = reraise
        self.context_data = context_data
        self.error_handler = get_error_handler()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Create error context
            context = create_error_context(
                operation=self.operation,
                component=self.component,
                session_id=self.session_id,
                additional_data=self.context_data
            )
            
            # Handle error
            await self.error_handler.handle_error(
                error=exc_val,
                context=context,
                emit_event=self.emit_event
            )
            
            # Return False to reraise, True to suppress
            return not self.reraise


def create_service_error_handler(component_name: str):
    """
    Factory function to create error handling decorators for a specific service.
    
    Args:
        component_name: Name of the service component
    
    Returns:
        Dictionary of configured decorators for the service
    
    Example:
        # In FileService
        error_decorators = create_service_error_handler("FileService")
        
        @error_decorators['handle_file_errors']
        async def upload_file(self, session_id: str, file: UploadFile):
            pass
    """
    def create_handle_errors(operation=None, category=ErrorCategory.SYSTEM, severity=ErrorSeverity.MEDIUM):
        return functools.partial(
            handle_errors,
            component=component_name,
            operation=operation,
            category=category,
            severity=severity,
            emit_event=True
        )
    
    return {
        'handle_errors': create_handle_errors(),
        'handle_file_errors': create_handle_errors(category=ErrorCategory.FILE),
        'handle_db_errors': create_handle_errors(category=ErrorCategory.DATABASE, severity=ErrorSeverity.HIGH),
        'handle_analysis_errors': create_handle_errors(category=ErrorCategory.ANALYSIS, severity=ErrorSeverity.HIGH),
        'retry_db_operation': functools.partial(
            retry_on_error,
            max_attempts=3,
            base_delay=2.0,
            component=component_name,
            retry_on=[ConnectionError, TimeoutError]
        ),
        'retry_network_operation': functools.partial(
            retry_on_error,
            max_attempts=5,
            base_delay=1.0,
            max_delay=60.0,
            component=component_name
        ),
        'log_performance': functools.partial(
            log_performance,
            component=component_name
        ),
        'validate_session': validate_session,
        'require_file_access': require_file_access
    }