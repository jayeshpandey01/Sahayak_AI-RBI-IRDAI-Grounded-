import json
from uuid import uuid4
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.schemas import (
    DocumentType,
    DocumentOCRResponse,
    DocumentConfirmationRequest,
    ConsentScope,
)
from app.models.db_models import JourneyModel, DocumentModel, UserModel
from app.services.ocr_pipeline import extract_synthetic_fields
from app.services.consent_service import verify_consent_granted
from app.api.dependencies import get_optional_current_user

router = APIRouter(prefix="/api/journeys", tags=["Document Ingestion"])

class DocumentUploadPayload(BaseModel):
    document_type: DocumentType
    simulate_quality_flag: str = "normal"  # "normal", "blur", "crop", "corrupt"
    raw_text: str = ""

@router.post("/{journey_id}/documents/upload", response_model=DocumentOCRResponse)
def upload_document(
    journey_id: str,
    payload: DocumentUploadPayload,
    db: Session = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_optional_current_user)
):
    journey = db.query(JourneyModel).filter(JourneyModel.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    # Data Isolation Check
    if journey.user_id and journey.user_id != "user_sahayak_demo":
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to upload documents for this journey.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if journey.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to upload documents for another user's journey."
            )

    # Consent Check: User must have granted DOCUMENT_OCR_PROCESSING consent
    if not verify_consent_granted(db, journey_id, ConsentScope.DOCUMENT_OCR_PROCESSING):
        raise HTTPException(
            status_code=403,
            detail="Consent Required: Customer must explicitly grant 'document_ocr_processing' consent prior to document ingestion."
        )

    # Perform Preflight & OCR Extraction
    ocr_result = extract_synthetic_fields(
        document_type=payload.document_type,
        raw_text=payload.raw_text,
        simulate_quality_flag=payload.simulate_quality_flag
    )

    if not ocr_result.preflight.is_valid_format or ocr_result.preflight.blur_detected or ocr_result.preflight.cropped_detected:
        raise HTTPException(
            status_code=422,
            detail=f"Preflight Quality Rejection: {ocr_result.preflight.error_message}"
        )

    # Persist document record
    doc_model = DocumentModel(
        document_id=ocr_result.document_id,
        journey_id=journey_id,
        document_type=ocr_result.document_type.value,
        quality_score=ocr_result.overall_confidence,
        fields_json=json.dumps({k: v.model_dump() for k, v in ocr_result.fields.items()}),
        is_confirmed=False
    )
    db.add(doc_model)
    db.commit()

    return ocr_result

@router.post("/{journey_id}/documents/{document_id}/confirm")
def confirm_document_fields(
    journey_id: str,
    document_id: str,
    payload: DocumentConfirmationRequest,
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
                detail="Authentication required to confirm document fields.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if journey.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to confirm documents for another user's journey."
            )

    doc = db.query(DocumentModel).filter(
        DocumentModel.document_id == document_id,
        DocumentModel.journey_id == journey_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    existing_fields = doc.get_fields()
    for key, confirmed_val in payload.confirmed_fields.items():
        if key in existing_fields:
            existing_fields[key]["raw_value"] = confirmed_val
            existing_fields[key]["user_confirmed"] = True

    doc.fields_json = json.dumps(existing_fields)
    doc.is_confirmed = True
    db.commit()

    return {
        "status": "confirmed",
        "document_id": document_id,
        "confirmed_fields": list(payload.confirmed_fields.keys())
    }
