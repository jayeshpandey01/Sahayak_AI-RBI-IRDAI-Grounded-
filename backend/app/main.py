from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db, init_db
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.pii_masking import PIIMaskingMiddleware
from app.api.financial import router as financial_router
from app.api.journeys import router as journeys_router
from app.api.documents import router as documents_router
from app.api.consent import router as consent_router
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from app.api.voice import router as voice_router
from app.api.payment_orders import router as payment_orders_router
from app.api.demo_wallet import router as demo_wallet_router
from app.api.loan_audit import router as loan_audit_router
from app.api.bills import router as bills_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite/PostgreSQL schemas
    init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sahayak AI — High-Reliability Financial Journey Copilot",
    lifespan=lifespan,
)

# Security Middlewares
if settings.ENVIRONMENT != "production":
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r".*",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Idempotency-Key", "X-Cache-Lookup", "X-Request-ID"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Idempotency-Key", "X-Cache-Lookup", "X-Request-ID"],
    )
app.add_middleware(RequestIDMiddleware)
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(PIIMaskingMiddleware)

# Standardized Error Handlers (FastAPI & API Design Principles)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    headers = getattr(exc, "headers", None)
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "path": request.url.path,
                "request_id": req_id,
            },
        },
        headers=headers,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []))
        errors.append({"field": field, "issue": err.get("msg", "")})

    req_id = getattr(request.state, "request_id", None)
    content = {
        "detail": jsonable_encoder(exc.errors()),
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Input validation failed on one or more fields",
            "details": errors,
            "path": request.url.path,
            "request_id": req_id,
        },
    }
    return JSONResponse(status_code=422, content=content)

# API Routers
app.include_router(auth_router)
app.include_router(financial_router)
app.include_router(journeys_router)
app.include_router(documents_router)
app.include_router(consent_router)
app.include_router(chat_router)
app.include_router(voice_router)
app.include_router(payment_orders_router)
app.include_router(demo_wallet_router)
app.include_router(loan_audit_router)
app.include_router(bills_router)

# Direct root aliases for decoupled frontend clients
@app.get("/api/offers", tags=["Financial Services"])
def direct_offers(db: Session = Depends(get_db)):
    from app.api.financial import list_offers
    return {"items": list_offers(db=db), "notice": "Synthetic demo catalogue. Terms are illustrative and are not lender offers."}

@app.post("/api/emi", tags=["Financial Services"])
def direct_emi(payload: dict, db: Session = Depends(get_db)):
    from app.api.financial import calculate_emi_endpoint
    from app.models.schemas import EMICalculationRequest
    from pydantic import ValidationError
    from fastapi import HTTPException
    try:
        req = EMICalculationRequest(**payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())
    return calculate_emi_endpoint(req, db)

@app.get("/health", tags=["System"])
def health_check():
    from app.database import check_all_dbs
    db_status = check_all_dbs()
    is_healthy = db_status.get("primary_db", {}).get("status") == "connected"
    return {
        "status": "healthy" if is_healthy else "degraded",
        "service": "sahayak-ai-api",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status.get("primary_db", {}).get("status"),
        "datastores": db_status,
        "rbi_kfs_compliance": "ACTIVE",
    }
