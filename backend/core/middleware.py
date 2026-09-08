# backend/core/middleware.py
import uuid
import re
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("mediscanai.middleware")

# Valid incoming request ID: alphanumeric, dash, underscore, 1-64 characters
REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Lightweight correlation / Request ID ASGI middleware.
    - Preserves incoming X-Request-ID if valid and opaque.
    - Generates a fresh random hex identifier if absent or invalid.
    - Attaches request_id to request.state.request_id for logs and downstream error handlers.
    - Exposes X-Request-ID on the outgoing HTTP response header.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        incoming_id = request.headers.get("X-Request-ID")
        if incoming_id and REQUEST_ID_REGEX.match(incoming_id):
            request_id = incoming_id
        else:
            request_id = uuid.uuid4().hex[:16]

        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
