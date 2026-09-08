# backend/core/errors.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging

import uuid

logger = logging.getLogger("mediscanai.backend")


class DatabaseConnectionError(Exception):
    """Raised when database connection or ping fails."""
    pass


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all exception handler that logs the error server-side tagged with a unique
    error_id and request_id, and returns a sanitized client response without leaking traceback details.
    """
    error_id = uuid.uuid4().hex[:10]
    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
    
    log_prefix = f"[Request ID: {request_id}] [Error ID: {error_id}]" if request_id else f"[Error ID: {error_id}]"
    logger.error(f"{log_prefix} Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    
    content = {
        "detail": "An internal server error occurred. Please try again later.",
        "error_id": error_id
    }
    if request_id:
        content["request_id"] = request_id

    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=content
    )
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response
