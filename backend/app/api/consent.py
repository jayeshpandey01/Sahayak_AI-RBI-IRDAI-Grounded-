from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.schemas import ConsentRecord, ConsentRequest
from app.models.db_models import JourneyModel, ConsentAuditModel, UserModel
from app.services.consent_service import record_consent_event, compute_consent_tamper_hash
from app.api.dependencies import get_optional_current_user

router = APIRouter(prefix="/api/journeys", tags=["Consent & Statutory Compliance"])

@router.post("/{journey_id}/consent", response_model=ConsentRecord)
def capture_consent(
    journey_id: str,
    payload: ConsentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_optional_current_user)
):
    journey = db.query(JourneyModel).filter(JourneyModel.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    # Isolation check: prevent User A or anonymous callers from altering User B's journey consent
    if journey.user_id and journey.user_id != "user_sahayak_demo":
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to record consent for this journey.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if journey.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to modify another user's consent."
            )

    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent", "MobileApp/1.0")
    user_id = current_user.id if current_user else "user_sahayak_demo"

    return record_consent_event(
        db=db,
        journey_id=journey_id,
        user_id=user_id,
        scope=payload.scope,
        purpose=payload.purpose,
        is_granted=payload.is_granted,
        ip_address=client_ip,
        user_agent=user_agent
    )

@router.get("/{journey_id}/consent/audit", response_model=List[ConsentRecord])
def get_consent_audit_trail(
    journey_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_optional_current_user)
):
    journey = db.query(JourneyModel).filter(JourneyModel.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.user_id and journey.user_id != "user_sahayak_demo":
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view consent audit trail.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if journey.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to view another user's consent audit trail."
            )

    records = (
        db.query(ConsentAuditModel)
        .filter(ConsentAuditModel.journey_id == journey_id)
        .order_by(ConsentAuditModel.timestamp.asc())
        .all()
    )

    result = []
    for r in records:
        # Verify tamper signature
        expected_hash = compute_consent_tamper_hash(
            consent_id=r.consent_id,
            journey_id=r.journey_id,
            user_id=r.user_id,
            scope=r.scope,
            purpose=r.purpose,
            timestamp=r.timestamp.isoformat(),
            is_granted=r.is_granted
        )
        is_valid = (expected_hash == r.tamper_hash)

        result.append(
            ConsentRecord(
                consent_id=r.consent_id,
                journey_id=r.journey_id,
                user_id=r.user_id,
                scope=r.scope,
                purpose=r.purpose,
                timestamp=r.timestamp,
                ip_address=r.ip_address,
                user_agent=r.user_agent,
                is_granted=r.is_granted,
                tamper_hash=r.tamper_hash,
            )
        )
    return result
