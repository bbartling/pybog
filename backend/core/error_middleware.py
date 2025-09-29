"""
Error handling middleware for FastAPI application

This middleware provides global error handling, request/response logging,
and standardized error responses for all API endpoints.
"""

import json
import logging
import time
import traceback
from typing import Callable, Dict, Any
from datetime import datetime, timezone

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.error_handler import get_error_handler, create_error_context, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive error handling middleware for FastAPI.
    
    Features:
    - Global exception handling with standardized responses
    - Request/response logging with performance metrics
    - Error context creation and tracking
    - Rate limiting and abuse detection
    - Security headers and CORS handling
    """
    
    def __init__(self, app: ASGIApp, enable_request_logging: bool = True):
        super().__init__(app)
        self.enable_request_logging = enable_request_logging
        self.error_handler = get_error_handler()
        
        # Track request patterns for abuse detection
        self._request_counts: Dict[str, Dict[str, int]] = {}
        self._error_counts: Dict[str, int] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with comprehensive error handling and logging."""
        start_time = time.time()
        request_id = self._generate_request_id()
        client_ip = self._get_client_ip(request)
        
        # Add request ID to request state for downstream use
        request.state.request_id = request_id
        request.state.start_time = start_time
        
        try:
            # Log incoming request
            if self.enable_request_logging:
                await self._log_request(request, request_id, client_ip)
            
            # Check for rate limiting (basic implementation)
            if await self._check_rate_limit(client_ip, request.url.path):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": "Too many requests. Please try again later.",
                        "retry_after": 60
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Add response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Processing-Time"] = f"{processing_time:.3f}s"
            
            # Log successful response
            if self.enable_request_logging:
                await self._log_response(request, response, request_id, processing_time)
            
            return response
            
        except HTTPException as e:
            # Handle FastAPI HTTP exceptions
            processing_time = time.time() - start_time
            
            error_response = await self._handle_http_exception(
                e, request, request_id, client_ip, processing_time
            )
            
            return error_response
            
        except Exception as e:
            # Handle unexpected exceptions
            processing_time = time.time() - start_time
            
            error_response = await self._handle_unexpected_exception(
                e, request, request_id, client_ip, processing_time
            )
            
            return error_response
    
    def _generate_request_id(self) -> str:
        """Generate unique request identifier."""
        import uuid
        return f"req_{uuid.uuid4().hex[:12]}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first (for load balancers/proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if hasattr(request.client, 'host'):
            return request.client.host
        
        return "unknown"
    
    async def _log_request(self, request: Request, request_id: str, client_ip: str) -> None:
        """Log incoming request details."""
        try:
            # Get request body for POST/PUT requests (with size limit)
            body_content = ""
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.body()
                    if len(body) < 1024:  # Only log small bodies
                        body_content = body.decode('utf-8', errors='ignore')[:500]
                except Exception:
                    body_content = "[body read error]"
            
            logger.info(
                f"[{request_id}] {request.method} {request.url.path} - "
                f"Client: {client_ip} - "
                f"User-Agent: {request.headers.get('User-Agent', 'unknown')[:100]} - "
                f"Body: {body_content[:100] if body_content else 'none'}"
            )
            
        except Exception as e:
            logger.warning(f"Failed to log request: {e}")
    
    async def _log_response(
        self, 
        request: Request, 
        response: Response, 
        request_id: str, 
        processing_time: float
    ) -> None:
        """Log response details and performance metrics."""
        try:
            # Determine log level based on status code and processing time
            status_code = response.status_code
            if status_code >= 500:
                log_level = logging.ERROR
            elif status_code >= 400:
                log_level = logging.WARNING
            elif processing_time > 5.0:  # Slow request
                log_level = logging.WARNING
            else:
                log_level = logging.INFO
            
            logger.log(
                log_level,
                f"[{request_id}] {request.method} {request.url.path} - "
                f"Status: {status_code} - "
                f"Time: {processing_time:.3f}s"
            )
            
        except Exception as e:
            logger.warning(f"Failed to log response: {e}")
    
    async def _check_rate_limit(self, client_ip: str, path: str) -> bool:
        """Basic rate limiting check."""
        try:
            current_minute = int(time.time() // 60)
            
            # Initialize tracking for this IP
            if client_ip not in self._request_counts:
                self._request_counts[client_ip] = {}
            
            # Clean old entries (keep only current minute)
            self._request_counts[client_ip] = {
                minute: count for minute, count in self._request_counts[client_ip].items()
                if minute >= current_minute - 1
            }
            
            # Count requests in current minute
            current_count = self._request_counts[client_ip].get(current_minute, 0)
            
            # Rate limits by endpoint type
            rate_limits = {
                "/api/files/upload": 50,      # 50 uploads per minute (increased for testing)
                "/api/chat/message": 100,     # 100 chat messages per minute (increased for testing)
                "/api/analysis/": 20,         # 20 analysis requests per minute (increased for testing)
            }
            
            # Find applicable rate limit
            limit = 100  # Default limit
            for endpoint_prefix, endpoint_limit in rate_limits.items():
                if path.startswith(endpoint_prefix):
                    limit = endpoint_limit
                    break
            
            # Check if limit exceeded
            if current_count >= limit:
                logger.warning(f"Rate limit exceeded for {client_ip} on {path}: {current_count}/{limit}")
                return True
            
            # Update count
            self._request_counts[client_ip][current_minute] = current_count + 1
            return False
            
        except Exception as e:
            logger.error(f"Rate limiting check failed: {e}")
            return False  # Allow request if rate limiting fails
    
    async def _handle_http_exception(
        self,
        exc: HTTPException,
        request: Request,
        request_id: str,
        client_ip: str,
        processing_time: float
    ) -> JSONResponse:
        """Handle FastAPI HTTP exceptions with standardized response."""
        try:
            # Create error context
            context = create_error_context(
                operation=f"{request.method} {request.url.path}",
                component="HTTPMiddleware",
                additional_data={
                    "request_id": request_id,
                    "client_ip": client_ip,
                    "processing_time": processing_time,
                    "status_code": exc.status_code,
                    "user_agent": request.headers.get("User-Agent", "unknown")
                }
            )
            
            # Determine error category based on status code
            if exc.status_code == 404:
                category = ErrorCategory.VALIDATION
            elif exc.status_code == 403:
                category = ErrorCategory.AUTHENTICATION
            elif exc.status_code == 400:
                category = ErrorCategory.VALIDATION
            elif exc.status_code >= 500:
                category = ErrorCategory.SYSTEM
            else:
                category = ErrorCategory.SYSTEM
            
            # Handle error (but don't emit event for HTTP exceptions)
            error_response = await self.error_handler.handle_error(
                error=exc,
                context=context,
                emit_event=False  # Don't emit events for HTTP exceptions
            )
            
            # Create standardized response
            response_content = {
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "error_id": error_response.error_id,
                    "category": category.value,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "request_id": request_id,
                "processing_time": f"{processing_time:.3f}s"
            }
            
            # Add recovery suggestions for client errors
            if 400 <= exc.status_code < 500:
                response_content["error"]["suggestions"] = self._get_client_error_suggestions(exc.status_code)
            
            return JSONResponse(
                status_code=exc.status_code,
                content=response_content,
                headers={
                    "X-Request-ID": request_id,
                    "X-Processing-Time": f"{processing_time:.3f}s"
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to handle HTTP exception: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": 500,
                        "message": "Internal server error in error handling",
                        "request_id": request_id
                    }
                }
            )
    
    async def _handle_unexpected_exception(
        self,
        exc: Exception,
        request: Request,
        request_id: str,
        client_ip: str,
        processing_time: float
    ) -> JSONResponse:
        """Handle unexpected exceptions with comprehensive error processing."""
        try:
            # Create error context
            context = create_error_context(
                operation=f"{request.method} {request.url.path}",
                component="HTTPMiddleware",
                additional_data={
                    "request_id": request_id,
                    "client_ip": client_ip,
                    "processing_time": processing_time,
                    "exception_type": type(exc).__name__,
                    "user_agent": request.headers.get("User-Agent", "unknown")
                }
            )
            
            # Handle error with comprehensive system
            error_response = await self.error_handler.handle_error(
                error=exc,
                context=context,
                emit_event=True  # Emit events for unexpected exceptions
            )
            
            # Track error frequency
            self._error_counts[type(exc).__name__] = self._error_counts.get(type(exc).__name__, 0) + 1
            
            # Log detailed error information
            logger.error(
                f"[{request_id}] Unexpected exception in {request.method} {request.url.path}: "
                f"{type(exc).__name__}: {str(exc)}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            
            # Create standardized error response
            response_content = {
                "error": {
                    "code": 500,
                    "message": "An unexpected error occurred. Please try again later.",
                    "error_id": error_response.error_id,
                    "category": error_response.category.value,
                    "severity": error_response.severity.value,
                    "timestamp": error_response.timestamp.isoformat(),
                    "retry_possible": error_response.retry_possible
                },
                "request_id": request_id,
                "processing_time": f"{processing_time:.3f}s"
            }
            
            # Add recovery suggestions
            if error_response.recovery_suggestions:
                response_content["error"]["suggestions"] = error_response.recovery_suggestions
            
            # Add support reference
            if error_response.support_reference:
                response_content["error"]["support_reference"] = error_response.support_reference
            
            return JSONResponse(
                status_code=500,
                content=response_content,
                headers={
                    "X-Request-ID": request_id,
                    "X-Processing-Time": f"{processing_time:.3f}s",
                    "X-Error-ID": error_response.error_id
                }
            )
            
        except Exception as handler_error:
            # Fallback error handling if error handler itself fails
            logger.critical(f"Error handler middleware failed: {handler_error}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": 500,
                        "message": "Critical system error",
                        "request_id": request_id
                    }
                }
            )
    
    def _get_client_error_suggestions(self, status_code: int) -> list:
        """Get recovery suggestions for client errors."""
        suggestions = {
            400: [
                "Check your request format and parameters",
                "Ensure all required fields are provided",
                "Verify data types match the expected format"
            ],
            401: [
                "Check your authentication credentials",
                "Ensure your session is still valid",
                "Try logging in again"
            ],
            403: [
                "Verify you have permission to access this resource",
                "Check if your account has the required privileges",
                "Contact support if you believe this is an error"
            ],
            404: [
                "Check the URL for typos",
                "Verify the resource exists",
                "Try refreshing the page"
            ],
            413: [
                "Reduce the size of your request",
                "Compress files before uploading",
                "Split large requests into smaller chunks"
            ],
            429: [
                "Wait a moment before trying again",
                "Reduce the frequency of your requests",
                "Contact support if you need higher rate limits"
            ]
        }
        
        return suggestions.get(status_code, ["Try again later", "Contact support if the problem persists"])
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        return {
            "error_counts": dict(self._error_counts),
            "total_errors": sum(self._error_counts.values()),
            "unique_error_types": len(self._error_counts),
            "request_tracking_ips": len(self._request_counts)
        }


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Request validation middleware for security and data integrity.
    
    Features:
    - Request size limits
    - Content type validation
    - Security headers
    - Basic input sanitization
    """
    
    def __init__(self, app: ASGIApp, max_request_size: int = 50 * 1024 * 1024):  # 50MB
        super().__init__(app)
        self.max_request_size = max_request_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate request before processing."""
        try:
            # Check request size
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_request_size:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": 413,
                            "message": f"Request too large (maximum {self.max_request_size // (1024*1024)}MB)",
                            "category": "VALIDATION"
                        }
                    }
                )
            
            # Validate content type for POST/PUT requests
            if request.method in ["POST", "PUT", "PATCH"]:
                content_type = request.headers.get("content-type", "")
                
                # Allow common content types
                allowed_types = [
                    "application/json",
                    "multipart/form-data",
                    "application/x-www-form-urlencoded",
                    "text/plain"
                ]
                
                if not any(allowed_type in content_type for allowed_type in allowed_types):
                    return JSONResponse(
                        status_code=415,
                        content={
                            "error": {
                                "code": 415,
                                "message": f"Unsupported content type: {content_type}",
                                "category": "VALIDATION",
                                "supported_types": allowed_types
                            }
                        }
                    )
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            
            return response
            
        except Exception as e:
            logger.error(f"Request validation middleware error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": 500,
                        "message": "Request validation failed",
                        "category": "SYSTEM"
                    }
                }
            )