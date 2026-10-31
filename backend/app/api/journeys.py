import json
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.schemas import (
    JourneyStage,
    JourneyCreateRequest,
    JourneyUpdateRequest,
    JourneyStateResponse,
    LenderOffer,
    DocumentOCRResponse,
)
from app.models.db_models import JourneyModel, DocumentModel
from app.services.fsm_engine import validate_state_transition, FSMTransitionError
from app.services.financial_calculator import get_offer_by_id, calculate_kfs_emi
from app.api.dependencies import get_optional_current_user, get_current_user
from app.models.db_models import UserModel

router = APIRouter(prefix="/api/journeys", tags=["Journey Lifecycle"])

def verify_journey_ownership(journey: JourneyModel, current_user: Optional[UserModel]):
    """Enforces strict multi-tenant data isolation on private journeys."""
    if journey.user_id and journey.user_id != "user_sahayak_demo":
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to access or modify this journey.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if journey.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to access or modify another user's journey records."
            )

def build_journey_response(journey: JourneyModel, db: Session) -> JourneyStateResponse:
    # Fetch linked documents
    docs = db.query(DocumentModel).filter(DocumentModel.journey_id == journey.id).all()
    parsed_docs = []
    for d in docs:
        fields = d.get_fields()
        parsed_docs.append(
            DocumentOCRResponse(
                document_id=d.document_id,
                document_type=d.document_type,
                preflight={
                    "is_valid_format": True,
                    "quality_score": d.quality_score,
                    "orientation_correct": True,
                    "blur_detected": False,
                    "cropped_detected": False,
                },
                fields=fields,
                overall_confidence=d.quality_score,
                requires_manual_confirmation=not d.is_confirmed,
            )
        )

    # Missing checklist items based on stage
    missing_items = []
    if journey.stage == JourneyStage.INTENT_CAPTURED.value:
        missing_items = ["Select an approved lender offer", "Review Key Fact Statement (KFS)"]
    elif journey.stage == JourneyStage.OFFERS_REVIEWED.value:
        missing_items = ["Upload Identity & Income documents", "Confirm extracted field values"]
    elif journey.stage == JourneyStage.DOCUMENTS_CONFIRMED.value:
        missing_items = ["Perform final readiness review", "Grant immutable submission consent"]

    selected_offer: Optional[LenderOffer] = None
    calc_summary = None
    if journey.selected_offer_id:
        selected_offer = get_offer_by_id(journey.selected_offer_id, db)
        if selected_offer:
            calc_summary = calculate_kfs_emi(
                principal=Decimal(str(journey.loan_amount)),
                tenure_months=journey.preferred_tenure_months,
                offer=selected_offer,
                maximum_emi=Decimal(str(journey.maximum_emi)) if journey.maximum_emi else None,
            )

    return JourneyStateResponse(
        id=journey.id,
        user_id=journey.user_id,
        stage=JourneyStage(journey.stage),
        language=journey.language,
        loan_amount=Decimal(str(journey.loan_amount)),
        preferred_tenure_months=journey.preferred_tenure_months,
        maximum_emi=Decimal(str(journey.maximum_emi)) if journey.maximum_emi else None,
        purpose=journey.purpose,
        selected_offer=selected_offer,
        calculation_summary=calc_summary,
        documents=parsed_docs,
        missing_items=missing_items,
        customer_confirmed=journey.customer_confirmed,
        ready_for_handoff=journey.ready_for_handoff,
        human_review_required=journey.human_review_required,
        human_review_reason=journey.human_review_reason,
        updated_at=journey.updated_at,
    )

@router.post("", response_model=JourneyStateResponse, status_code=201)
def create_journey(
    payload: JourneyCreateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_optional_current_user),
    x_idempotency_key: Optional[str] = Header(None)
):
    journey_id = f"jrn_{uuid4().hex[:12]}"
    owner_id = current_user.id if current_user else "user_sahayak_demo"
    new_journey = JourneyModel(
        id=journey_id,
        user_id=owner_id,
        stage=JourneyStage.INTENT_CAPTURED.value,
        language=payload.language.value,
        loan_amount=payload.loan_amount,
        preferred_tenure_months=payload.preferred_tenure_months,
        maximum_emi=payload.maximum_emi,
        purpose=payload.purpose,
        customer_confirmed=False,
        ready_for_handoff=False,
        human_review_required=False,
    )
    db.add(new_journey)
    db.commit()
    db.refresh(new_journey)
    return build_journey_response(new_journey, db)


@router.get("", response_model=list[JourneyStateResponse], summary="List authenticated user's loan readiness journeys")
def list_journeys(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """List readiness/handoff records owned by the caller; these are not issued loans."""
    journeys = db.query(JourneyModel).filter(
        JourneyModel.user_id == current_user.id
    ).order_by(JourneyModel.updated_at.desc()).limit(100).all()
    return [build_journey_response(journey, db) for journey in journeys]

@router.get("/{journey_id}", response_model=JourneyStateResponse)
def get_journey(
    journey_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_optional_current_user)
):
    journey = db.query(JourneyModel).filter(JourneyModel.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    verify_journey_ownership(journey, current_user)
    return build_journey_response(journey, db)

@router.patch("/{journey_id}/stage", response_model=JourneyStateResponse)
def update_journey_stage(
    journey_id: str,
    payload: JourneyUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_optional_current_user),
    x_idempotency_key: Optional[str] = Header(None)
):
    journey = db.query(JourneyModel).filter(JourneyModel.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    verify_journey_ownership(journey, current_user)

    current_stage = JourneyStage(journey.stage)
    target_stage = payload.stage

    if payload.selected_offer_id:
        offer = get_offer_by_id(payload.selected_offer_id, db)
        if not offer:
            raise HTTPException(status_code=400, detail="Invalid offer ID")
        journey.selected_offer_id = payload.selected_offer_id

    # Check docs confirmation
    docs = db.query(DocumentModel).filter(DocumentModel.journey_id == journey.id).all()
    docs_confirmed = len(docs) > 0 and all(d.is_confirmed for d in docs)

    try:
        is_valid, reason, human_review = validate_state_transition(
            current_stage=current_stage,
            target_stage=target_stage,
            has_selected_offer=bool(journey.selected_offer_id),
            documents_confirmed=docs_confirmed,
            customer_confirmed=payload.customer_confirmed,
        )
    except FSMTransitionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    journey.stage = target_stage.value
    journey.customer_confirmed = payload.customer_confirmed
    if target_stage == JourneyStage.READY_FOR_HANDOFF:
        journey.ready_for_handoff = True
    if human_review:
        journey.human_review_required = True

    journey.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(journey)
    return build_journey_response(journey, db)

@router.patch("/{journey_id}/revise", response_model=JourneyStateResponse)
def revise_journey_parameters(
    journey_id: str,
    payload: JourneyCreateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_optional_current_user)
):
    """
    Rolls back state machine to INTENT_CAPTURED whenever core loan terms change,
    invalidating stale offer selections and confirmations.
    """
    journey = db.query(JourneyModel).filter(JourneyModel.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    verify_journey_ownership(journey, current_user)

    journey.loan_amount = payload.loan_amount
    journey.preferred_tenure_months = payload.preferred_tenure_months
    journey.maximum_emi = payload.maximum_emi
    journey.purpose = payload.purpose
    journey.language = payload.language.value

    # Invalidate downstream state
    journey.stage = JourneyStage.INTENT_CAPTURED.value
    journey.selected_offer_id = None
    journey.customer_confirmed = False
    journey.ready_for_handoff = False
    journey.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(journey)
    return build_journey_response(journey, db)
