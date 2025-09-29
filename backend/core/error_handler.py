"""
Comprehensive Error Handling System for PyBOG Backend

This module provides centralized error handling with standardized error codes,
user-friendly messages, recovery suggestions, and retry mechanisms.
"""

import asyncio
import logging
import traceback
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Union
from pydantic import BaseModel, Field

from core.events import EventBus, Event
from models.websocket_models import ErrorCode, create_error_message

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels for categorization and handling."""
    LOW = "low"           # Minor issues, system continues normally
    MEDIUM = "medium"     # Significant issues, some functionality affected
    HIGH = "high"         # Major issues, core functionality affected
    CRITICAL = "critical" # System-threatening issues, immediate attention required


class ErrorCategory(str, Enum):
    """Error categories for classification and handling."""
    FILE = "FILE"                 # File operations, upload, storage, retrieval
    ANALYSIS = "ANALYSIS"         # Document analysis, LLM processing, BOG generation
    DATABASE = "DATABASE"         # Database connections, queries, transactions
    WEBSOCKET = "WEBSOCKET"       # WebSocket connections, messaging, streaming
    AUTHENTICATION = "AUTH"       # Authentication, authorization, permissions
    VALIDATION = "VALIDATION"     # Input validation, data format, constraints
    NETWORK = "NETWORK"          # External API calls, network connectivity
    SYSTEM = "SYSTEM"            # System resources, memory, disk, configuration
    BUSINESS = "BUSINESS"        # Business logic, workflow, state transitions


class RecoveryAction(BaseModel):
    """Recovery action suggestion for error resolution."""
    action_type: str = Field(description="Type of recovery action")
    description: str = Field(description="Human-readable description")
    automated: bool = Field(default=False, description="Whether action can be automated")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")


class ErrorContext(BaseModel):
    """Context information for error occurrence."""
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    operation: str = Field(description="Operation being performed when error occurred")
    component: str = Field(description="System component where error occurred")
    request_id: Optional[str] = None
    file_id: Optional[int] = None
    analysis_id: Optional[int] = None
    additional_data: Dict[str, Any] = Field(default_factory=dict)


class ErrorDetails(BaseModel):
    """Detailed error information for logging and debugging."""
    error_id: str = Field(description="Unique error identifier")
    category: ErrorCategory = Field(description="Error category")
    severity: ErrorSeverity = Field(description="Error severity level")
    code: str = Field(description="Specific error code")
    message: str = Field(description="User-friendly error message")
    technical_message: str = Field(description="Technical error details")
    context: ErrorContext = Field(description="Error context information")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    stack_trace: Optional[str] = None
    recovery_actions: List[RecoveryAction] = Field(default_factory=list)
    retry_possible: bool = Field(default=False)
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)


class ErrorResponse(BaseModel):
    """Standardized error response format."""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    code: str
    message: str
    timestamp: datetime
    context: Dict[str, Any] = Field(default_factory=dict)
    recovery_suggestions: List[str] = Field(default_factory=list)
    retry_possible: bool = False
    support_reference: Optional[str] = None


class RetryConfig(BaseModel):
    """Configuration for retry mechanisms."""
    max_attempts: int = Field(default=3, ge=1, le=10)
    base_delay: float = Field(default=1.0, ge=0.1, le=60.0)
    max_delay: float = Field(default=30.0, ge=1.0, le=300.0)
    exponential_backoff: bool = Field(default=True)
    jitter: bool = Field(default=True)


class ErrorHandler:
    """
    Centralized error handling system with comprehensive error management.
    
    Features:
    - Standardized error categorization and severity levels
    - User-friendly error messages with technical details
    - Recovery action suggestions and automated retry mechanisms
    - Event emission for real-time error communication
    - Error tracking and analytics for system monitoring
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize the error handler.
        
        Args:
            event_bus: Optional EventBus for error event emission
        """
        self.event_bus = event_bus
        self._error_registry: Dict[str, ErrorDetails] = {}
        self._error_patterns: Dict[str, Dict[str, Any]] = {}
        self._retry_configs: Dict[str, RetryConfig] = {}
        self._setup_default_patterns()
        self._setup_default_retry_configs()
    
    def _setup_default_patterns(self) -> None:
        """Set up default error patterns and recovery actions."""
        self._error_patterns = {
            # File operation errors
            "file_not_found": {
                "category": ErrorCategory.FILE,
                "severity": ErrorSeverity.MEDIUM,
                "message_template": "File '{filename}' not found",
                "recovery_actions": [
                    RecoveryAction(
                        action_type="verify_file",
                        description="Verify the file exists and is accessible",
                        automated=False
                    ),
                    RecoveryAction(
                        action_type="re_upload",
                        description="Re-upload the file if it was deleted",
                        automated=False
                    )
                ]
            },
            "file_too_large": {
                "category": ErrorCategory.FILE,
                "severity": ErrorSeverity.MEDIUM,
                "message_template": "File size ({size} MB) exceeds maximum limit ({limit} MB)",
                "recovery_actions": [
                    RecoveryAction(
                        action_type="compress_file",
                        description="Compress the file to reduce its size",
                        automated=False
                    ),
                    RecoveryAction(
                        action_type="split_file",
                        description="Split large file into smaller chunks",
                        automated=False
                    )
                ]
            },
            "file_corrupt": {
                "category": ErrorCategory.FILE,
                "severity": ErrorSeverity.HIGH,
                "message_template": "File '{filename}' appears to be corrupted or unreadable",
                "recovery_actions": [
                    RecoveryAction(
                        action_type="re_upload",
                        description="Re-upload the file from the original source",
                        automated=False
                    ),
                    RecoveryAction(
                        action_type="file_repair",
                        description="Attempt to repair the corrupted file",
                        automated=False
                    )
                ]
            },
            
            # Database errors
            "db_connection_failed": {
                "category": ErrorCategory.DATABASE,
                "severity": ErrorSeverity.CRITICAL,
                "message_template": "Database connection failed",
                "recovery_actions": [
                    RecoveryAction(
                        action_type="retry_connection",
                        description="Retry database connection",
                        automated=True,
                        parameters={"max_retries": 3, "delay": 5}
                    ),
                    RecoveryAction(
                        action_type="check_db_status",
                        description="Check database server status",
                        automated=False
                    )
                ]
            },
            "db_constraint_violation": {
                "category": ErrorCategory.DATABASE,
                "severity": ErrorSeverity.MEDIUM,
                "message_template": "Data validation failed: {constraint}",
                "recovery_actions": [
                    RecoveryAction(
                        action_type="validate_input",
                        description="Validate input data before submission",
                        automated=False
                    ),
                    RecoveryAction(
                        action_type="fix_data",
                        description="Correct the data to meet requirements",
                        automated=False
                    )
                ]
            },
            
            # Analysis errors
            "analysis_llm_failed": {
                "category": ErrorCategory.ANALYSIS,
                "severity": ErrorSeverity.HIGH,
                "message_template": "AI analysis failed: {reason}",
                "recovery_actions": [
                    RecoveryAction(
                        action_type="retry_analysis",
                        description="Retry the analysis with different parameters",
                        automated=True,
                        parameters={"max_retries": 2, "delay": 10}
                    ),
                    RecoveryAction(
                        action_type="manual_review",
                        description="Review document manually for analysis",
                        automated=False
                    )
                ]
            },
            "analysis_insufficient_content": {
                "category": ErrorCategory.ANALYSIS,
                "severity": ErrorSeverity.MEDIUM,
                "message_template": "Document contains insufficient content for analysis",
                "recovery_actions": [
                    RecoveryAction(
                        action_type="upload_complete_document",
                        description="Upload a more complete document with detailed information",
                        automated=False
                    ),
                    RecoveryAction(
                        action_type="manual_input",
                        description="Provide additional information manually",
                        automated=False
                    )
                ]
            },
            
            # WebSocket errors
            "websocket_connection_lost": {
                "category": ErrorCategory.WEBSOCKET,
                "severity": ErrorSeverity.MEDIUM,
                "message_template": "Real-time connection lost",
                "recovery_actions": [
                    RecoveryAction(
                        action_type="reconnect",
                        description="Automatically reconnect to restore real-time updates",
                        automated=True,
                        parameters={"max_retries": 5, "delay": 2}
                    ),
                    RecoveryAction(
                        action_type="refresh_page",
                        description="Refresh the page to restore connection",
                        automated=False
                    )
                ]
            },
            
            # Validation errors
            "invalid_session_id": {
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.MEDIUM,
                "message_template": "Invalid session identifier",
                "recovery_actions": [
                    RecoveryAction(
                        action_type="create_new_session",
                        description="Create a new session to continue",
                        automated=False
                    ),
                    RecoveryAction(
                        action_type="restore_session",
                        description="Restore from a previous valid session",
                        automated=False
                    )
                ]
            }
        }
    
    def _setup_default_retry_configs(self) -> None:
        """Set up default retry configurations for different error types."""
        self._retry_configs = {
            ErrorCategory.DATABASE.value: RetryConfig(
                max_attempts=3,
                base_delay=2.0,
                max_delay=30.0,
                exponential_backoff=True,
                jitter=True
            ),
            ErrorCategory.NETWORK.value: RetryConfig(
                max_attempts=5,
                base_delay=1.0,
                max_delay=60.0,
                exponential_backoff=True,
                jitter=True
            ),
            ErrorCategory.ANALYSIS.value: RetryConfig(
                max_attempts=2,
                base_delay=5.0,
                max_delay=30.0,
                exponential_backoff=False,
                jitter=False
            ),
            ErrorCategory.WEBSOCKET.value: RetryConfig(
                max_attempts=5,
                base_delay=1.0,
                max_delay=10.0,
                exponential_backoff=True,
                jitter=True
            )
        }
    
    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        error_code: Optional[str] = None,
        custom_message: Optional[str] = None,
        emit_event: bool = True
    ) -> ErrorResponse:
        """
        Handle an error with comprehensive processing and response generation.
        
        Args:
            error: The exception that occurred
            context: Context information about the error
            error_code: Optional specific error code
            custom_message: Optional custom user message
            emit_event: Whether to emit error event via EventBus
            
        Returns:
            Standardized error response
        """
        try:
            # Generate unique error ID
            error_id = self._generate_error_id()
            
            # Determine error pattern and details
            error_pattern = self._identify_error_pattern(error, error_code)
            
            # Create error details
            error_details = ErrorDetails(
                error_id=error_id,
                category=error_pattern.get("category", ErrorCategory.SYSTEM),
                severity=error_pattern.get("severity", ErrorSeverity.MEDIUM),
                code=error_code or error_pattern.get("code", "UNKNOWN"),
                message=custom_message or self._generate_user_message(error, error_pattern, context),
                technical_message=str(error),
                context=context,
                stack_trace=traceback.format_exc(),
                recovery_actions=error_pattern.get("recovery_actions", []),
                retry_possible=self._is_retry_possible(error, error_pattern)
            )
            
            # Store error details for tracking
            self._error_registry[error_id] = error_details
            
            # Log error with appropriate level
            self._log_error(error_details)
            
            # Emit error event if requested and EventBus available
            if emit_event and self.event_bus and context.session_id:
                await self._emit_error_event(error_details)
            
            # Generate response
            response = ErrorResponse(
                error_id=error_id,
                category=error_details.category,
                severity=error_details.severity,
                code=error_details.code,
                message=error_details.message,
                timestamp=error_details.timestamp,
                context={
                    "operation": context.operation,
                    "component": context.component,
                    "session_id": context.session_id,
                    "file_id": context.file_id,
                    "analysis_id": context.analysis_id
                },
                recovery_suggestions=[action.description for action in error_details.recovery_actions],
                retry_possible=error_details.retry_possible,
                support_reference=error_id
            )
            
            return response
            
        except Exception as handler_error:
            # Fallback error handling if error handler itself fails
            logger.critical(f"Error handler failed: {handler_error}")
            return ErrorResponse(
                error_id="HANDLER_FAILED",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                code="HANDLER_ERROR",
                message="An unexpected error occurred in the error handling system",
                timestamp=datetime.now(timezone.utc),
                retry_possible=False
            )
    
    def _generate_error_id(self) -> str:
        """Generate a unique error identifier."""
        import uuid
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"ERR_{timestamp}_{unique_id}"
    
    def _identify_error_pattern(self, error: Exception, error_code: Optional[str]) -> Dict[str, Any]:
        """Identify error pattern based on exception type and error code."""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Check for specific error codes first
        if error_code and error_code.lower() in self._error_patterns:
            return self._error_patterns[error_code.lower()]
        
        # Pattern matching based on exception type and message
        if "file not found" in error_message or isinstance(error, FileNotFoundError):
            return self._error_patterns["file_not_found"]
        elif "too large" in error_message or "size limit" in error_message:
            return self._error_patterns["file_too_large"]
        elif "corrupt" in error_message or "invalid format" in error_message:
            return self._error_patterns["file_corrupt"]
        elif "connection" in error_message and "database" in error_message:
            return self._error_patterns["db_connection_failed"]
        elif "constraint" in error_message or "violation" in error_message:
            return self._error_patterns["db_constraint_violation"]
        elif "websocket" in error_message or "connection lost" in error_message:
            return self._error_patterns["websocket_connection_lost"]
        elif "session" in error_message and "invalid" in error_message:
            return self._error_patterns["invalid_session_id"]
        
        # Default pattern for unknown errors
        return {
            "category": ErrorCategory.SYSTEM,
            "severity": ErrorSeverity.MEDIUM,
            "message_template": "An unexpected error occurred: {error}",
            "recovery_actions": [
                RecoveryAction(
                    action_type="retry",
                    description="Try the operation again",
                    automated=False
                ),
                RecoveryAction(
                    action_type="contact_support",
                    description="Contact support if the problem persists",
                    automated=False
                )
            ]
        }
    
    def _generate_user_message(self, error: Exception, pattern: Dict[str, Any], context: ErrorContext) -> str:
        """Generate user-friendly error message from pattern template."""
        template = pattern.get("message_template", "An error occurred: {error}")
        
        # Prepare template variables
        template_vars = {
            "error": str(error),
            "operation": context.operation,
            "component": context.component,
            "filename": context.additional_data.get("filename", "unknown"),
            "size": context.additional_data.get("file_size_mb", "unknown"),
            "limit": context.additional_data.get("size_limit_mb", "unknown"),
            "reason": context.additional_data.get("reason", "unknown"),
            "constraint": context.additional_data.get("constraint", "data constraint")
        }
        
        try:
            return template.format(**template_vars)
        except KeyError:
            # Fallback if template variables are missing
            return f"An error occurred during {context.operation}: {str(error)}"
    
    def _is_retry_possible(self, error: Exception, pattern: Dict[str, Any]) -> bool:
        """Determine if the error is retryable."""
        # Check if any recovery actions are automated (indicating retry possibility)
        automated_actions = [action for action in pattern.get("recovery_actions", []) if action.automated]
        if automated_actions:
            return True
        
        # Check error category for retry possibility
        retryable_categories = [
            ErrorCategory.NETWORK,
            ErrorCategory.DATABASE,
            ErrorCategory.WEBSOCKET,
            ErrorCategory.ANALYSIS
        ]
        
        return pattern.get("category") in retryable_categories
    
    def _log_error(self, error_details: ErrorDetails) -> None:
        """Log error with appropriate level based on severity."""
        log_message = (
            f"[{error_details.error_id}] {error_details.category.value} Error in "
            f"{error_details.context.component}.{error_details.context.operation}: "
            f"{error_details.message}"
        )
        
        if error_details.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra={"error_details": error_details.model_dump()})
        elif error_details.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra={"error_details": error_details.model_dump()})
        elif error_details.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra={"error_details": error_details.model_dump()})
        else:
            logger.info(log_message, extra={"error_details": error_details.model_dump()})
    
    async def _emit_error_event(self, error_details: ErrorDetails) -> None:
        """Emit error event via EventBus for real-time communication."""
        try:
            if not self.event_bus or not error_details.context.session_id:
                return
            
            # Create WebSocket error message
            error_message = create_error_message(
                session_id=error_details.context.session_id,
                error_code=ErrorCode(error_details.category.value),
                message=error_details.message,
                operation=error_details.context.operation,
                details={
                    "error_id": error_details.error_id,
                    "severity": error_details.severity.value,
                    "component": error_details.context.component,
                    "recovery_actions": [action.description for action in error_details.recovery_actions]
                },
                retry_possible=error_details.retry_possible
            )
            
            # Publish error event
            await self.event_bus.publish(
                error_details.context.session_id,
                Event(
                    type="error",
                    session_id=error_details.context.session_id,
                    operation=error_details.context.operation,
                    data=error_message.data
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to emit error event: {e}")
    
    async def retry_with_backoff(
        self,
        operation: Callable,
        context: ErrorContext,
        retry_config: Optional[RetryConfig] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute operation with retry logic and exponential backoff.
        
        Args:
            operation: Async function to execute
            context: Error context for tracking
            retry_config: Optional retry configuration
            *args: Arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Operation result
            
        Raises:
            Last exception if all retries fail
        """
        # Get retry config for error category
        if not retry_config:
            category_key = context.additional_data.get("error_category", ErrorCategory.SYSTEM.value)
            retry_config = self._retry_configs.get(category_key, RetryConfig())
        
        last_exception = None
        
        for attempt in range(retry_config.max_attempts):
            try:
                # Execute operation
                result = await operation(*args, **kwargs)
                
                # Success - log retry success if not first attempt
                if attempt > 0:
                    logger.info(f"Operation succeeded on attempt {attempt + 1}/{retry_config.max_attempts}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Don't retry on last attempt
                if attempt == retry_config.max_attempts - 1:
                    break
                
                # Calculate delay
                delay = self._calculate_retry_delay(attempt, retry_config)
                
                logger.warning(
                    f"Operation failed on attempt {attempt + 1}/{retry_config.max_attempts}, "
                    f"retrying in {delay:.1f}s: {str(e)}"
                )
                
                # Wait before retry
                await asyncio.sleep(delay)
        
        # All retries failed - handle final error
        if last_exception:
            error_response = await self.handle_error(
                last_exception,
                context,
                custom_message=f"Operation failed after {retry_config.max_attempts} attempts"
            )
            raise last_exception
        
        # Should not reach here
        raise RuntimeError("Retry logic failed unexpectedly")
    
    def _calculate_retry_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate retry delay with exponential backoff and jitter."""
        if config.exponential_backoff:
            delay = config.base_delay * (2 ** attempt)
        else:
            delay = config.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, config.max_delay)
        
        # Add jitter to prevent thundering herd
        if config.jitter:
            import random
            jitter_factor = random.uniform(0.5, 1.5)
            delay *= jitter_factor
        
        return delay
    
    def get_error_details(self, error_id: str) -> Optional[ErrorDetails]:
        """Get detailed error information by error ID."""
        return self._error_registry.get(error_id)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring and analysis."""
        if not self._error_registry:
            return {"total_errors": 0}
        
        errors = list(self._error_registry.values())
        
        # Count by category
        category_counts = {}
        for error in errors:
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Count by severity
        severity_counts = {}
        for error in errors:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Recent errors (last hour)
        recent_cutoff = datetime.now(timezone.utc).timestamp() - 3600
        recent_errors = [
            error for error in errors 
            if error.timestamp.timestamp() > recent_cutoff
        ]
        
        return {
            "total_errors": len(errors),
            "recent_errors": len(recent_errors),
            "category_breakdown": category_counts,
            "severity_breakdown": severity_counts,
            "retry_success_rate": self._calculate_retry_success_rate(errors)
        }
    
    def _calculate_retry_success_rate(self, errors: List[ErrorDetails]) -> float:
        """Calculate retry success rate from error history."""
        retryable_errors = [error for error in errors if error.retry_possible]
        if not retryable_errors:
            return 0.0
        
        # This is a simplified calculation - in production, you'd track actual retry outcomes
        successful_retries = len([error for error in retryable_errors if error.retry_count > 0])
        return successful_retries / len(retryable_errors) if retryable_errors else 0.0


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler(event_bus: Optional[EventBus] = None) -> ErrorHandler:
    """Get or create global error handler instance."""
    global _global_error_handler
    
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler(event_bus)
    elif event_bus and not _global_error_handler.event_bus:
        _global_error_handler.event_bus = event_bus
    
    return _global_error_handler


def create_error_context(
    operation: str,
    component: str,
    session_id: Optional[str] = None,
    **kwargs
) -> ErrorContext:
    """Helper function to create error context."""
    return ErrorContext(
        operation=operation,
        component=component,
        session_id=session_id,
        **kwargs
    )