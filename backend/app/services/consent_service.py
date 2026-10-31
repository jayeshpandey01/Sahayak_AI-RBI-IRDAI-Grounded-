import hashlib
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.schemas import ConsentScope, ConsentRecord
from app.models.db_models import ConsentAuditModel

def compute_consent_tamper_hash(
    consent_id: str,
    journey_id: str,
    user_id: str,
    scope: str,
    purpose: str,
    timestamp: str,
    is_granted: bool
) -> str:
    payload = f"{consent_id}:{journey_id}:{user_id}:{scope}:{purpose}:{timestamp}:{is_granted}:SAHAYAK_SEC_V1"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def record_consent_event(
    db: Session,
    journey_id: str,
    user_id: str,
    scope: ConsentScope,
    purpose: str,
    is_granted: bool,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> ConsentRecord:
    consent_id = f"cst_{uuid4().hex}"
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    tamper_hash = compute_consent_tamper_hash(
        consent_id=consent_id,
        journey_id=journey_id,
        user_id=user_id,
        scope=scope.value,
        purpose=purpose,
        timestamp=now_iso,
        is_granted=is_granted
    )

    db_entry = ConsentAuditModel(
        consent_id=consent_id,
        journey_id=journey_id,
        user_id=user_id,
        scope=scope.value,
        purpose=purpose,
        is_granted=is_granted,
        ip_address=ip_address,
        user_agent=user_agent,
        tamper_hash=tamper_hash,
        timestamp=now
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)

    return ConsentRecord(
        consent_id=consent_id,
        journey_id=journey_id,
        user_id=user_id,
        scope=scope,
        purpose=purpose,
        timestamp=now,
        ip_address=ip_address,
        user_agent=user_agent,
        is_granted=is_granted,
        tamper_hash=tamper_hash
    )

def verify_consent_granted(db: Session, journey_id: str, scope: ConsentScope) -> bool:
    """Verifies that the latest recorded consent for this scope is active and granted."""
    record = (
        db.query(ConsentAuditModel)
        .filter(ConsentAuditModel.journey_id == journey_id, ConsentAuditModel.scope == scope.value)
        .order_by(ConsentAuditModel.timestamp.desc())
        .first()
    )
    if not record:
        return False
    return record.is_granted
