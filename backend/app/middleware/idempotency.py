import hashlib
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.database import SessionLocal
from app.models.db_models import IdempotencyModel

class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if (
            request.method not in ("POST", "PATCH", "PUT")
            or request.url.path in ("/health", "/docs", "/openapi.json")
            or request.url.path.startswith("/api/auth/")
            # Chat responses and voice payloads must not enter the durable
            # idempotency response cache. These endpoints are transient by contract.
            or request.url.path == "/api/chat"
            or request.url.path.startswith("/api/chat/")
            or "/webhooks/" in request.url.path
        ):
            return await call_next(request)

        idempotency_key = request.headers.get("X-Idempotency-Key")
        if not idempotency_key:
            # For non-state-critical requests or if missing, proceed
            return await call_next(request)

        body_bytes = await request.body()
        request_hash = hashlib.sha256(body_bytes).hexdigest()

        # 1. Check existing record in DB using a short-lived scoped session
        cached_record = None
        db = SessionLocal()
        try:
            cached_record = db.query(IdempotencyModel).filter(IdempotencyModel.idempotency_key == idempotency_key).first()
            if cached_record:
                if cached_record.request_hash != request_hash:
                    return JSONResponse(
                        status_code=409,
                        content={"detail": "Idempotency key reused with different request payload"},
                        headers={"X-Cache-Lookup": "IDEMPOTENCY_CONFLICT"}
                    )
                # Replay cached response
                cached_body = json.loads(cached_record.response_body)
                return JSONResponse(
                    status_code=cached_record.response_status,
                    content=cached_body,
                    headers={"X-Cache-Lookup": "IDEMPOTENCY_HIT", "X-Idempotency-Key": idempotency_key}
                )
        finally:
            db.close()

        # 2. Process request downstream WITHOUT holding an open database session
        response = await call_next(request)

        # 3. Only cache 2xx responses using a separate short-lived session
        if 200 <= response.status_code < 300:
            response_body_bytes = [section async for section in response.body_iterator]
            full_body = b"".join(response_body_bytes)
            try:
                parsed_json = json.loads(full_body.decode("utf-8"))
                write_db = SessionLocal()
                try:
                    new_record = IdempotencyModel(
                        idempotency_key=idempotency_key,
                        endpoint=request.url.path,
                        request_hash=request_hash,
                        response_status=response.status_code,
                        response_body=json.dumps(parsed_json)
                    )
                    write_db.add(new_record)
                    write_db.commit()
                finally:
                    write_db.close()
            except Exception:
                pass

            return Response(
                content=full_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )

        return response
