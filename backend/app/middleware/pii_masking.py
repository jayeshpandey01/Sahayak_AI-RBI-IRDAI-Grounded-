import re
import time
import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

logger = logging.getLogger("sahayak.audit")

PAN_REGEX = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b")
AADHAAR_REGEX = re.compile(r"\b[2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b")
PHONE_REGEX = re.compile(r"\b(?:\+91|91)?[6-9]\d{9}\b")

def scrub_pii(text: str) -> str:
    """Masks PAN, Aadhaar, and phone numbers from logs and error strings."""
    if not isinstance(text, str):
        return text
    scrubbed = PAN_REGEX.sub("[MASKED_PAN]", text)
    scrubbed = AADHAAR_REGEX.sub("[MASKED_AADHAAR]", scrubbed)
    scrubbed = PHONE_REGEX.sub("[MASKED_PHONE]", scrubbed)
    return scrubbed

class PIIMaskingMiddleware(BaseHTTPMiddleware):
    """
    Milestone 1 Structured Logging & PII Masking Middleware:
    Logs HTTP requests in structured JSON with timing and masks sensitive PII.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = getattr(request.state, "request_id", "unknown")

        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Do not log health checks to reduce log noise
        if request.url.path != "/health":
            safe_path = scrub_pii(request.url.path)
            log_payload = {
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": safe_path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": (
                    "redacted"
                    if request.url.path == "/api/chat" or request.url.path.startswith("/api/chat/")
                    else request.client.host if request.client else "unknown"
                )
            }
            logger.info(json.dumps(log_payload))

        return response
