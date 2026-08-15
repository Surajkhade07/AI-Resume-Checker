"""
Advanced middleware for the ATS Resume Analyzer API.
Provides rate limiting, request logging, timing, and security headers.
"""
import logging
import time
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint

logger = logging.getLogger('ats_resume_scorer')


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all incoming requests with method, path, status, and duration.
    Helps with debugging, monitoring, and usage tracking.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.time()
        
        # Log incoming request
        logger.info(f"-> {request.method} {request.url.path}")
        
        # Process the request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response with status and duration
        logger.info(
            f"<- {request.method} {request.url.path} -> {response.status_code} "
            f"({duration:.3f}s)"
        )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.
    Protects against common web vulnerabilities.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    Limits requests per IP address within a time window.
    Note: For production, use Redis-based rate limiting instead.
    """
    
    def __init__(self, app: FastAPI, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict = {}  # IP -> list of timestamps

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip rate limiting for health and readiness checks
        if request.url.path in ("/health", "/ready", "/api/v1/health", "/api/v1/ready"):
            return await call_next(request)
        
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        
        # Clean old entries
        if client_ip in self._requests:
            self._requests[client_ip] = [
                t for t in self._requests[client_ip]
                if now - t < self.window_seconds
            ]
        else:
            self._requests[client_ip] = []
        
        # Check rate limit
        if len(self._requests[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after_seconds": self.window_seconds,
                },
            )
        
        # Record this request
        self._requests[client_ip].append(now)
        
        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    """
    Register all middleware in the correct order.
    Order matters: first registered = outermost (runs first on request, last on response).
    
    Args:
        app: FastAPI application instance
    """
    # Security headers (innermost - runs closest to the app)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Request logging
    app.add_middleware(RequestLoggingMiddleware)
    
    # Rate limiting (outermost - runs first)
    app.add_middleware(RateLimitMiddleware, max_requests=60, window_seconds=60)
    
    logger.info("All middleware registered successfully")