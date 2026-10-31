import re
from uuid import uuid4
from typing import Dict, Any, Tuple
from app.models.schemas import (
    DocumentType,
    DocumentPreflightResult,
    ExtractedField,
    DocumentOCRResponse,
)

INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
    re.compile(r"approve\s+(this\s+)?loan\s+without", re.IGNORECASE),
    re.compile(r"override\s+underwriting", re.IGNORECASE),
]

def mask_pii_string(key: str, value: str) -> str:
    """Masks sensitive numbers like PAN, Aadhaar, Phone."""
    val = value.strip()
    if key in ("pan_number", "pan") and len(val) == 10:
        return f"{val[:2]}XXXXXX{val[-2:]}"
    if key in ("aadhaar_number", "aadhaar") and len(val) >= 12:
        return f"XXXXXXXX{val[-4:]}"
    if key in ("phone", "mobile") and len(val) >= 10:
        return f"XXXXXX{val[-4:]}"
    if key in ("account_number", "bank_account") and len(val) >= 4:
        return f"******{val[-4:]}"
    return val

def sanitize_document_text(text: str) -> Tuple[str, bool]:
    """Sanitizes raw document text, neutralizing prompt injection attempts."""
    flagged = False
    sanitized = text
    for pattern in INJECTION_PATTERNS:
        if pattern.search(sanitized):
            flagged = True
            sanitized = pattern.sub("[REDACTED_PROMPT_INJECTION_ATTEMPT]", sanitized)
    return sanitized, flagged

def analyze_document_preflight(
    filename: str,
    content_bytes: bytes,
    document_type: DocumentType,
    simulate_quality_flag: str = "normal"
) -> DocumentPreflightResult:
    """
    Evaluates document image quality, cropping, orientation, and format.
    Supports synthetic simulation flags for automated chaos testing:
    'blur', 'crop', 'corrupt', 'normal'.
    """
    if len(content_bytes) < 100 or simulate_quality_flag == "corrupt":
        return DocumentPreflightResult(
            is_valid_format=False,
            quality_score=0.1,
            orientation_correct=False,
            blur_detected=True,
            cropped_detected=True,
            error_message="Document file corrupted or unreadable."
        )

    if simulate_quality_flag == "blur":
        return DocumentPreflightResult(
            is_valid_format=True,
            quality_score=0.35,
            orientation_correct=True,
            blur_detected=True,
            cropped_detected=False,
            error_message="Image is excessively blurry. Please re-capture in good lighting."
        )

    if simulate_quality_flag == "crop":
        return DocumentPreflightResult(
            is_valid_format=True,
            quality_score=0.45,
            orientation_correct=True,
            blur_detected=False,
            cropped_detected=True,
            error_message="Document edges are cropped. Ensure all four corners are within frame."
        )

    return DocumentPreflightResult(
        is_valid_format=True,
        quality_score=0.96,
        orientation_correct=True,
        blur_detected=False,
        cropped_detected=False,
        error_message=None
    )

def extract_synthetic_fields(
    document_type: DocumentType,
    raw_text: str = "",
    simulate_quality_flag: str = "normal"
) -> DocumentOCRResponse:
    doc_id = f"doc_{uuid4().hex[:12]}"
    preflight = analyze_document_preflight(
        filename=f"{doc_id}.jpg",
        content_bytes=b"dummy_bytes_for_synthetic_ocr" * 20,
        document_type=document_type,
        simulate_quality_flag=simulate_quality_flag
    )

    if not preflight.is_valid_format or preflight.blur_detected or preflight.cropped_detected:
        return DocumentOCRResponse(
            document_id=doc_id,
            document_type=document_type,
            preflight=preflight,
            fields={},
            overall_confidence=preflight.quality_score,
            requires_manual_confirmation=True,
        )

    clean_text, injection_detected = sanitize_document_text(raw_text)

    fields: Dict[str, ExtractedField] = {}
    if document_type == DocumentType.PAN_CARD:
        fields = {
            "pan_number": ExtractedField(
                field_key="pan_number",
                raw_value="ABCDE1234F",
                masked_value=mask_pii_string("pan_number", "ABCDE1234F"),
                confidence=0.98,
                user_confirmed=False
            ),
            "full_name": ExtractedField(
                field_key="full_name",
                raw_value="Rajesh Kumar Verma",
                masked_value="Rajesh Kumar Verma",
                confidence=0.95,
                user_confirmed=False
            ),
            "dob": ExtractedField(
                field_key="dob",
                raw_value="15/08/1990",
                masked_value="15/08/1990",
                confidence=0.94,
                user_confirmed=False
            ),
        }
    elif document_type == DocumentType.SALARY_SLIP:
        fields = {
            "employer_name": ExtractedField(
                field_key="employer_name",
                raw_value="Infosys BPM Technologies",
                masked_value="Infosys BPM Technologies",
                confidence=0.96,
                user_confirmed=False
            ),
            "net_monthly_salary": ExtractedField(
                field_key="net_monthly_salary",
                raw_value="65000",
                masked_value="65000",
                confidence=0.92,
                user_confirmed=False
            ),
            "pay_period": ExtractedField(
                field_key="pay_period",
                raw_value="September 2026",
                masked_value="September 2026",
                confidence=0.97,
                user_confirmed=False
            ),
        }
    elif document_type == DocumentType.AADHAAR_CARD:
        fields = {
            "aadhaar_number": ExtractedField(
                field_key="aadhaar_number",
                raw_value="987654321098",
                masked_value=mask_pii_string("aadhaar_number", "987654321098"),
                confidence=0.99,
                user_confirmed=False
            ),
            "name": ExtractedField(
                field_key="name",
                raw_value="Rajesh Kumar Verma",
                masked_value="Rajesh Kumar Verma",
                confidence=0.96,
                user_confirmed=False
            ),
        }
    elif document_type == DocumentType.BANK_STATEMENT:
        fields = {
            "bank_name": ExtractedField(
                field_key="bank_name",
                raw_value="HDFC Bank Ltd",
                masked_value="HDFC Bank Ltd",
                confidence=0.97,
                user_confirmed=False
            ),
            "account_number_last4": ExtractedField(
                field_key="account_number_last4",
                raw_value="4321",
                masked_value="******4321",
                confidence=0.95,
                user_confirmed=False
            ),
            "average_balance": ExtractedField(
                field_key="average_balance",
                raw_value="48200",
                masked_value="48200",
                confidence=0.91,
                user_confirmed=False
            ),
        }

    return DocumentOCRResponse(
        document_id=doc_id,
        document_type=document_type,
        preflight=preflight,
        fields=fields,
        overall_confidence=0.95,
        requires_manual_confirmation=True,  # Mandatory human confirmation as per RBI guidelines
    )
