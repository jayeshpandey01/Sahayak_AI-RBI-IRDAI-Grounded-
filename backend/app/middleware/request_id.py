import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Milestone 1 Correlation Tracking:
    Extracts incoming X-Request-ID or generates a unique UUIDv4.
    Attaches request_id to request.state and propagates in response headers.
    """
    async def dispatch(self, request: Request, call_next):
        incoming_id = request.headers.get("X-Request-ID")
        request_id = incoming_id if incoming_id else f"req-{uuid.uuid4().hex[:12]}"
        
        # Attach to request state for access in exception handlers and logs
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

