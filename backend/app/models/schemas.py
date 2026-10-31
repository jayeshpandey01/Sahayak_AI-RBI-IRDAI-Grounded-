from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import date, datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

class JourneyStage(str, Enum):
    INTENT_CAPTURED = "INTENT_CAPTURED"
    OFFERS_REVIEWED = "OFFERS_REVIEWED"
    DOCUMENTS_CONFIRMED = "DOCUMENTS_CONFIRMED"
    READY_FOR_HANDOFF = "READY_FOR_HANDOFF"

class DocumentType(str, Enum):
    PAN_CARD = "PAN_CARD"
    AADHAAR_CARD = "AADHAAR_CARD"
    SALARY_SLIP = "SALARY_SLIP"
    BANK_STATEMENT = "BANK_STATEMENT"

class ConsentScope(str, Enum):
    CREDIT_BUREAU_INQUIRY = "credit_bureau_inquiry"
    DOCUMENT_OCR_PROCESSING = "document_ocr_processing"
    LENDER_OFFER_FETCHING = "lender_offer_fetching"
    APPLICATION_HANDOFF = "application_handoff"

class LanguageCode(str, Enum):
    EN = "en"
    HI = "hi"
    MR = "mr"
    HINGLISH = "hinglish"

# ----------------- AUTHENTICATION & IDENTITY SCHEMAS -----------------

class AuthProvider(str, Enum):
    EMAIL = "email"
    GOOGLE = "google"

class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="Strong password (min 8, max 128 chars)")
    full_name: Optional[str] = Field(default=None, max_length=150)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if "@" not in clean or "." not in clean.split("@")[-1]:
            raise ValueError("Invalid email format")
        return clean

class LoginRequest(BaseModel):
    email: str
    password: str = Field(..., max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

class GoogleAuthRequest(BaseModel):
    id_token: str = Field(..., description="Google ID Token / Credential")
    full_name: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

class ForgotPasswordResponse(BaseModel):
    success: bool = True
    message: str
    dev_otp: Optional[str] = None
    dev_reset_token: Optional[str] = None

class ResetPasswordRequest(BaseModel):
    email: str
    token_or_otp: str = Field(..., max_length=128, description="Password reset token or 6-digit OTP code")
    new_password: str = Field(..., min_length=8, max_length=128, description="New strong password")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    auth_provider: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=150)

class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse

class MessageResponse(BaseModel):
    success: bool = True
    message: str

# ----------------- FINANCIAL CONTRACTS -----------------

class AmortizationItem(BaseModel):
    month: int
    opening_balance: Decimal
    emi: Decimal
    principal_component: Decimal
    interest_component: Decimal
    closing_balance: Decimal

class LenderOffer(BaseModel):
    offer_id: str
    lender_id: str
    lender_name: str
    annual_interest_rate_percent: Decimal = Field(..., ge=0, le=50)
    processing_fee_percent: Decimal = Field(..., ge=0, le=10)
    processing_fee_gst_percent: Decimal = Field(default=Decimal("18.0"))
    min_amount: Decimal
    max_amount: Decimal
    min_tenure_months: int
    max_tenure_months: int
    kfs_version: str
    kfs_effective_date: str
    disclaimer: str = "Indicative synthetic offer matching RBI KFS standards."
    product_name: str = "Personal Loan"
    loan_type: str = "personal"
    min_monthly_income: Optional[Decimal] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    employment_types: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    source_type: str = "synthetic"
    last_verified_at: Optional[datetime] = None
    status: str = "active"
    eligibility_data_missing: bool = False
    missing_criteria: List[str] = Field(default_factory=list)


class LoanProductUpsert(BaseModel):
    offer_id: str = Field(..., min_length=3, max_length=64)
    lender_id: str = Field(..., min_length=2, max_length=64)
    lender_name: str = Field(..., min_length=2, max_length=150)
    product_name: str = Field(default="Personal Loan", min_length=2, max_length=150)
    loan_type: str = Field(default="personal", min_length=2, max_length=32)
    min_amount: Decimal = Field(..., ge=1000, le=50000000)
    max_amount: Decimal = Field(..., ge=1000, le=50000000)
    annual_interest_rate_percent: Decimal = Field(..., ge=0, le=50)
    processing_fee_percent: Decimal = Field(default=Decimal("0"), ge=0, le=10)
    processing_fee_gst_percent: Decimal = Field(default=Decimal("18"), ge=0, le=100)
    min_tenure_months: int = Field(..., ge=1, le=360)
    max_tenure_months: int = Field(..., ge=1, le=360)
    min_monthly_income: Optional[Decimal] = Field(default=None, gt=0)
    min_age: Optional[int] = Field(default=None, ge=18, le=100)
    max_age: Optional[int] = Field(default=None, ge=18, le=100)
    employment_types: List[str] = Field(default_factory=list, max_length=20)
    locations: List[str] = Field(default_factory=list, max_length=100)
    kfs_version: str = Field(..., min_length=1, max_length=64)
    kfs_effective_date: str = Field(..., min_length=1, max_length=32)
    source_name: Optional[str] = Field(default=None, max_length=150)
    source_url: Optional[str] = Field(default=None, max_length=1000)
    source_type: str = Field(default="synthetic", pattern="^(synthetic|official|partner)$")
    last_verified_at: Optional[datetime] = None
    status: str = Field(default="active", pattern="^(active|inactive|needs_review)$")
    disclaimer: str = Field(..., min_length=1, max_length=500)

    @field_validator("employment_types", "locations")
    @classmethod
    def normalize_filters(cls, values: List[str]) -> List[str]:
        return sorted({value.strip().lower() for value in values if value.strip()})

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.max_amount < self.min_amount:
            raise ValueError("max_amount must be greater than or equal to min_amount")
        if self.max_tenure_months < self.min_tenure_months:
            raise ValueError("max_tenure_months must be greater than or equal to min_tenure_months")
        if self.min_age and self.max_age and self.max_age < self.min_age:
            raise ValueError("max_age must be greater than or equal to min_age")
        return self


class LoanRateHistoryResponse(BaseModel):
    annual_interest_rate_percent: Decimal
    processing_fee_percent: Decimal
    valid_from: datetime
    valid_until: Optional[datetime] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class EMICalculationRequest(BaseModel):
    loan_amount: Decimal = Field(..., ge=1000, le=5000000)
    tenure_months: Optional[int] = Field(default=None, ge=1, le=84)
    preferred_tenure_months: Optional[int] = Field(default=None, ge=1, le=84)
    offer_id: str = Field(default="offer-hdfc-01")
    maximum_emi: Optional[Decimal] = Field(default=None, ge=1)
    purpose: str = Field(default="Personal Loan", max_length=200)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("tenure_months", mode="before")
    @classmethod
    def set_tenure(cls, v, info):
        if v is not None:
            return v
        data = info.data if hasattr(info, "data") else {}
        return data.get("preferred_tenure_months", 24)

class EMICalculationResponse(BaseModel):
    offer_id: str
    lender_name: str
    principal_rupees: Decimal
    tenure_months: int
    annual_interest_rate_percent: Decimal
    monthly_interest_rate: Decimal
    estimated_emi_rupees: Decimal
    total_interest_rupees: Decimal
    processing_fee_rupees: Decimal
    illustrative_processing_fee_rupees: Optional[Decimal] = None
    processing_fee_gst_rupees: Decimal
    total_upfront_deductions_rupees: Decimal
    net_disbursed_amount_rupees: Decimal
    total_repayment_rupees: Decimal
    annual_percentage_rate_apr: Decimal
    within_user_emi_limit: Optional[bool] = None
    kfs_document_hash: str
    assumptions: List[str]

# ----------------- DOCUMENT OCR & PREFLIGHT -----------------

class DocumentPreflightResult(BaseModel):
    is_valid_format: bool
    quality_score: float = Field(..., ge=0.0, le=1.0)
    orientation_correct: bool
    blur_detected: bool
    cropped_detected: bool
    error_message: Optional[str] = None

class ExtractedField(BaseModel):
    field_key: str
    raw_value: str
    masked_value: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    user_confirmed: bool = False

class DocumentOCRResponse(BaseModel):
    document_id: str
    document_type: DocumentType
    preflight: DocumentPreflightResult
    fields: Dict[str, ExtractedField]
    overall_confidence: float
    requires_manual_confirmation: bool

class DocumentConfirmationRequest(BaseModel):
    confirmed_fields: Dict[str, str]

# ----------------- CONSENT & AUDIT -----------------

class ConsentRecord(BaseModel):
    consent_id: str
    journey_id: str
    user_id: str
    scope: ConsentScope
    purpose: str
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_granted: bool
    tamper_hash: str

class ConsentRequest(BaseModel):
    scope: ConsentScope
    purpose: str
    is_granted: bool

# ----------------- AI INTENT & RAG -----------------

class IntentSlotExtraction(BaseModel):
    loan_amount: Optional[Decimal] = None
    tenure_months: Optional[int] = None
    max_emi: Optional[Decimal] = None
    purpose: Optional[str] = None
    detected_language: LanguageCode = LanguageCode.EN
    confidence: float
    clarification_required: Optional[str] = None
    route_to_human_queue: bool = False
    refusal_reason: Optional[str] = None

class GroundedCitation(BaseModel):
    citation_id: str
    document_name: str
    version: str
    clause: str
    snippet: str
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    document_type: Optional[str] = None
    financial_category: Optional[str] = None
    provider_name: Optional[str] = None
    effective_from: Optional[str] = None
    status: Optional[str] = None
    collection_type: Optional[str] = None

class GroundedRAGResponse(BaseModel):
    answer: str
    citations: List[GroundedCitation]
    source_documents: List[str]
    confidence: float
    disclaimer: str

class ConversationTurn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=2500)

class ChatInputRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    journey_id: Optional[str] = None
    language: LanguageCode = LanguageCode.EN
    conversation: List[ConversationTurn] = Field(default_factory=list, max_length=8)
    allow_external_processing: bool = True
    payment_order_id: Optional[str] = Field(default=None, max_length=64)
    include_payment_context: bool = False
    include_audio: bool = False

    @field_validator("conversation")
    @classmethod
    def limit_conversation_chars(cls, turns: List[ConversationTurn]) -> List[ConversationTurn]:
        if sum(len(turn.content) for turn in turns) > 8000:
            raise ValueError("Conversation context exceeds the session limit")
        return turns

class VoiceTranscriptionResponse(BaseModel):
    transcript: str
    language: LanguageCode
    requires_user_review: bool = True

class VoiceSynthesisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2500)
    language: LanguageCode
    allow_external_processing: bool = True

class VoiceSynthesisResponse(BaseModel):
    audio_base64: str
    content_type: str = "audio/mpeg"
    language: LanguageCode

class HumanReviewHandoff(BaseModel):
    reason: str
    escalation_level: str = "L1_FINANCIAL_SPECIALIST"
    timestamp: datetime
    unresolved_discrepancies: List[str]
    case_summary: Dict[str, Any]

class VoiceChatTimingBreakdown(BaseModel):
    stt_ms: int = 0
    rag_ms: int = 0
    llm_ms: int = 0
    tts_ms: int = 0
    total_ms: int = 0

class VoiceChatResponse(BaseModel):
    transcript: str
    reply_text: str
    audio_base64: Optional[str] = None
    content_type: str = "audio/mpeg"
    language: LanguageCode = LanguageCode.EN
    rag_info: Optional[GroundedRAGResponse] = None
    timings: VoiceChatTimingBreakdown = Field(default_factory=VoiceChatTimingBreakdown)
    human_handoff: Optional[HumanReviewHandoff] = None
    slot_updates: Optional[IntentSlotExtraction] = None
    requires_user_review: bool = False

class ChatResponse(BaseModel):
    reply: str
    language: LanguageCode = LanguageCode.EN
    slot_updates: Optional[IntentSlotExtraction] = None
    rag_info: Optional[GroundedRAGResponse] = None
    human_handoff: Optional[HumanReviewHandoff] = None
    payment_context: Optional[Dict[str, Any]] = None
    audio_base64: Optional[str] = None

# ----------------- JOURNEY LIFECYCLE -----------------

class JourneyCreateRequest(BaseModel):
    language: LanguageCode = LanguageCode.EN
    loan_amount: Decimal = Field(..., ge=1000, le=5000000)
    preferred_tenure_months: int = Field(..., ge=1, le=84)
    maximum_emi: Optional[Decimal] = None
    purpose: str = Field(default="Personal Loan", max_length=200)

class JourneyUpdateRequest(BaseModel):
    stage: JourneyStage
    customer_confirmed: bool = False
    selected_offer_id: Optional[str] = None

class JourneyStateResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    stage: JourneyStage
    language: LanguageCode
    loan_amount: Decimal
    preferred_tenure_months: int
    maximum_emi: Optional[Decimal] = None
    purpose: str
    selected_offer: Optional[LenderOffer] = None
    calculation_summary: Optional[EMICalculationResponse] = None
    documents: List[DocumentOCRResponse] = []
    missing_items: List[str] = []
    customer_confirmed: bool = False
    ready_for_handoff: bool = False
    human_review_required: bool = False
    human_review_reason: Optional[str] = None
    updated_at: datetime

# ----------------- PAYMENT ORDERS & STRIPE SCHEMAS -----------------

class PaymentPurpose(str, Enum):
    WALLET_TOPUP = "wallet_topup"
    EMI_REPAYMENT = "emi_repayment"
    LOAN_PROCESSING_FEE = "loan_processing_fee"
    PROCESSING_FEE = "processing_fee"
    VERIFICATION_DEPOSIT = "verification_deposit"

class PaymentOrderStatus(str, Enum):
    CREATED = "CREATED"
    REQUIRES_ACTION = "REQUIRES_ACTION"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    DISPUTED = "DISPUTED"

class CreatePaymentOrderRequest(BaseModel):
    amount_rupees: Optional[Decimal] = Field(default=None, ge=1, le=5000000, description="Amount in INR (derived by server if purpose has reference_id)")
    purpose: PaymentPurpose = Field(default=PaymentPurpose.WALLET_TOPUP)
    currency: str = Field(default="inr", max_length=10)
    reference_id: Optional[str] = Field(default=None, max_length=128)
    metadata: Optional[Dict[str, Any]] = None
    customer_email: Optional[str] = None

class PaymentOrderResponse(BaseModel):
    order_id: str
    user_id: str
    status: PaymentOrderStatus
    purpose: PaymentPurpose
    amount_rupees: Decimal
    amount_paise: int
    currency: str
    merchant_display_name: str = "Sahayak AI"
    client_secret: Optional[str] = None
    checkout_url: Optional[str] = None
    publishable_key: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    provider: str = "stripe"
    provider_transaction_id: Optional[str] = None
    checkout_token: Optional[str] = None
    merchant_id: Optional[str] = None
    reference_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaymentHistoryItem(BaseModel):
    """Owner-visible payment history without checkout secrets or callback data."""
    order_id: str
    status: PaymentOrderStatus
    purpose: PaymentPurpose
    amount_rupees: Decimal
    currency: str
    provider: str
    reference_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DemoTransferCreateRequest(BaseModel):
    recipient_label: str = Field(..., min_length=1, max_length=120)
    amount_rupees: Decimal = Field(..., gt=0, le=100000)
    note: Optional[str] = Field(default=None, max_length=240)


class DemoTransferResponse(BaseModel):
    transfer_id: str
    recipient_label: str
    amount_rupees: Decimal
    currency: str = "INR"
    status: str = "SIMULATED"
    is_simulation: bool = True
    message: str = "Demo only. No money was sent."
    created_at: datetime


class WalletBalanceResponse(BaseModel):
    balance_paise: int
    currency: str = "inr"
    credited_total_paise: int
    ledger_entries: List[Dict[str, Any]] = Field(default_factory=list)


class DemoWalletFundRequest(BaseModel):
    amount_rupees: Decimal = Field(..., gt=0, le=10000)


class DemoWalletTransferRequest(BaseModel):
    recipient_wallet_code: str = Field(..., min_length=8, max_length=24)
    amount_rupees: Decimal = Field(..., gt=0, le=100000)
    note: Optional[str] = Field(default=None, max_length=240)

    @field_validator("recipient_wallet_code")
    @classmethod
    def normalize_wallet_code(cls, value: str) -> str:
        return value.strip().upper()


class DemoWalletAccountResponse(BaseModel):
    wallet_code: str
    display_name: Optional[str] = None
    balance_paise: int
    currency: str = "INR"
    is_simulation: bool = True


class DemoWalletEntryResponse(BaseModel):
    transaction_id: str
    entry_type: str
    amount_paise: int
    currency: str = "INR"
    description: str
    counterparty_name: Optional[str] = None
    created_at: datetime
    is_simulation: bool = True


class DemoWalletMutationResponse(BaseModel):
    transaction_id: str
    amount_paise: int
    balance_paise: int
    status: str = "COMPLETED"
    recipient_name: Optional[str] = None
    is_simulation: bool = True


class DemoWalletMutationResponse(BaseModel):
    transaction_id: str
    amount_paise: int
    balance_paise: int
    status: str = "COMPLETED"
    recipient_name: Optional[str] = None
    is_simulation: bool = True

class WebhookResponse(BaseModel):
    received: bool = True
    event_id: str
    event_type: str
    processed: bool

class PaymentReconcileResponse(BaseModel):
    reconciled_count: int
    orders_checked: int
    details: List[Dict[str, Any]] = []


# ----------------- MULTI-PLATFORM LOANS & EMI AUDIT SCHEMAS -----------------

class LenderType(str, Enum):
    BANK = "BANK"
    NBFC = "NBFC"
    FINTECH = "FINTECH"


class LoanType(str, Enum):
    PERSONAL = "PERSONAL"
    HOME = "HOME"
    AUTO = "AUTO"
    EDUCATION = "EDUCATION"
    CONSUMER_DURABLE = "CONSUMER_DURABLE"
    CREDIT_LINE = "CREDIT_LINE"
    GOLD = "GOLD"


class LoanStatus(str, Enum):
    ACTIVE = "ACTIVE"
    OVERDUE = "OVERDUE"
    CLOSED = "CLOSED"
    RESTRUCTURED = "RESTRUCTURED"


class BillCategory(str, Enum):
    ELECTRICITY = "ELECTRICITY"
    RENT = "RENT"
    WATER = "WATER"
    GAS = "GAS"
    INTERNET = "INTERNET"
    MOBILE = "MOBILE"
    INSURANCE = "INSURANCE"
    SUBSCRIPTION = "SUBSCRIPTION"
    OTHER = "OTHER"


class BillFrequency(str, Enum):
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"


class RecurringBillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    category: BillCategory = BillCategory.OTHER
    payee: Optional[str] = Field(default=None, max_length=120)
    expected_amount_rupees: Optional[Decimal] = Field(default=None, gt=0, le=100000000)
    frequency: BillFrequency = BillFrequency.MONTHLY
    next_due_date: date
    reminder_days_before: int = Field(default=3, ge=0, le=30)
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def clean_bill_name(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Bill name cannot be blank")
        return clean


class RecurringBillUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    category: Optional[BillCategory] = None
    payee: Optional[str] = Field(default=None, max_length=120)
    expected_amount_rupees: Optional[Decimal] = Field(default=None, gt=0, le=100000000)
    frequency: Optional[BillFrequency] = None
    next_due_date: Optional[date] = None
    reminder_days_before: Optional[int] = Field(default=None, ge=0, le=30)
    is_active: Optional[bool] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class BillPaymentCreate(BaseModel):
    amount_rupees: Optional[Decimal] = Field(default=None, gt=0, le=100000000)
    note: Optional[str] = Field(default=None, max_length=240)


class RecurringBillResponse(BaseModel):
    id: str
    name: str
    category: BillCategory
    payee: Optional[str] = None
    expected_amount_rupees: Optional[Decimal] = None
    frequency: BillFrequency
    next_due_date: date
    reminder_days_before: int
    is_active: bool
    notes: Optional[str] = None
    due_status: str
    days_until_due: int
    created_at: datetime
    updated_at: datetime


class BillPaymentResponse(BaseModel):
    id: str
    bill_id: str
    bill_name: str
    due_date: date
    amount_rupees: Decimal
    paid_at: datetime
    note: Optional[str] = None


class UserLoanBase(BaseModel):
    lender_name: str = Field(..., max_length=128, description="Lender or Platform name (e.g. HDFC Bank, Bajaj Finserv, KreditBee)")
    lender_type: LenderType = Field(default=LenderType.BANK, description="Lender category: Bank, NBFC, or Fintech app")
    loan_type: LoanType = Field(default=LoanType.PERSONAL, description="Type of loan product")
    account_number: str = Field(..., max_length=64, description="Loan account number or reference identifier")
    original_principal: Decimal = Field(..., gt=0, description="Original loan amount disbursed in rupees")
    outstanding_principal: Decimal = Field(..., ge=0, description="Current remaining principal balance in rupees")
    interest_rate_percent: Decimal = Field(..., ge=0, le=100, description="Annual interest rate percentage (p.a.)")
    tenure_months: int = Field(..., gt=0, le=360, description="Original loan tenure in months")
    remaining_tenure_months: int = Field(..., ge=0, le=360, description="Remaining installments / months")
    emi_amount: Decimal = Field(..., ge=0, description="Monthly EMI repayment in rupees")
    emi_due_day: int = Field(default=5, ge=1, le=31, description="Day of month when EMI is debited (1-31)")
    next_due_date: str = Field(..., max_length=32, description="Next upcoming EMI due date (YYYY-MM-DD)")
    status: LoanStatus = Field(default=LoanStatus.ACTIVE, description="Loan status (ACTIVE, OVERDUE, CLOSED, RESTRUCTURED)")
    disbursement_date: Optional[str] = Field(default=None, max_length=32, description="Date of loan disbursement")
    processing_fee_paid: Decimal = Field(default=Decimal("0.00"), ge=0, description="Upfront processing fee paid in rupees")
    prepayment_penalty_percent: Decimal = Field(default=Decimal("0.00"), ge=0, description="Prepayment penalty percentage (0% for RBI floating personal loans)")
    notes: Optional[str] = Field(default=None, max_length=500, description="Additional loan notes or purpose")


class UserLoanCreate(BaseModel):
    lender_name: str = Field(..., min_length=2, max_length=128)
    lender_type: LenderType = Field(default=LenderType.BANK)
    loan_type: LoanType = Field(default=LoanType.PERSONAL)
    account_number: Optional[str] = Field(default=None, max_length=64)
    original_principal: Decimal = Field(..., gt=0)
    outstanding_principal: Optional[Decimal] = Field(default=None, ge=0)
    interest_rate_percent: Decimal = Field(..., ge=0, le=100)
    tenure_months: int = Field(..., gt=0, le=360)
    remaining_tenure_months: Optional[int] = Field(default=None, ge=0, le=360)
    emi_amount: Optional[Decimal] = Field(default=None, ge=0)
    emi_due_day: Optional[int] = Field(default=5, ge=1, le=31)
    next_due_date: Optional[str] = Field(default=None, max_length=32)
    status: LoanStatus = Field(default=LoanStatus.ACTIVE)
    disbursement_date: Optional[str] = Field(default=None, max_length=32)
    processing_fee_paid: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)
    prepayment_penalty_percent: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)
    notes: Optional[str] = Field(default=None, max_length=500)


class UserLoanUpdate(BaseModel):
    lender_name: Optional[str] = Field(default=None, min_length=2, max_length=128)
    lender_type: Optional[LenderType] = None
    loan_type: Optional[LoanType] = None
    account_number: Optional[str] = Field(default=None, max_length=64)
    original_principal: Optional[Decimal] = Field(default=None, gt=0)
    outstanding_principal: Optional[Decimal] = Field(default=None, ge=0)
    interest_rate_percent: Optional[Decimal] = Field(default=None, ge=0, le=100)
    tenure_months: Optional[int] = Field(default=None, gt=0, le=360)
    remaining_tenure_months: Optional[int] = Field(default=None, ge=0, le=360)
    emi_amount: Optional[Decimal] = Field(default=None, ge=0)
    emi_due_day: Optional[int] = Field(default=None, ge=1, le=31)
    next_due_date: Optional[str] = Field(default=None, max_length=32)
    status: Optional[LoanStatus] = None
    disbursement_date: Optional[str] = None
    processing_fee_paid: Optional[Decimal] = None
    prepayment_penalty_percent: Optional[Decimal] = None
    notes: Optional[str] = None


class UserLoanResponse(UserLoanBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrepaymentSimulationRequest(BaseModel):
    target_loan_id: Optional[str] = Field(default=None, description="Specific loan to simulate prepayment for. If omitted, targets highest-interest loan.")
    extra_monthly_prepayment: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0, description="Additional monthly payment towards principal")
    lump_sum_prepayment: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0, description="One-time lump sum prepayment towards principal")


class PrepaymentSimulationResult(BaseModel):
    target_loan_id: str
    lender_name: str
    simulation_mode: str  # "EXTRA_MONTHLY" or "LUMP_SUM"
    prepayment_amount: Decimal
    original_tenure_remaining_months: int
    new_tenure_remaining_months: int
    months_saved: int
    original_remaining_interest: Decimal
    new_remaining_interest: Decimal
    interest_saved_rupees: Decimal
    advice: str


class RefinanceOpportunity(BaseModel):
    loan_id: str
    lender_name: str
    loan_type: str
    outstanding_principal: Decimal
    current_interest_rate: Decimal
    catalogue_offer_lender: str
    catalogue_offer_rate: Decimal
    monthly_saving_rupees: Decimal
    lifetime_saving_rupees: Decimal
    processing_fee_estimate: Decimal
    net_benefit_rupees: Decimal
    is_worthwhile: bool
    recommendation: str


class EMICalendarItem(BaseModel):
    loan_id: str
    lender_name: str
    loan_type: str
    account_number: str
    emi_amount: Decimal
    due_day: int
    next_due_date: str
    days_until_due: int
    status: str


class LoanAuditRequest(BaseModel):
    monthly_income: Optional[Decimal] = Field(default=Decimal("50000.00"), gt=0, description="Borrower's net monthly take-home income")
    target_loan_id: Optional[str] = Field(default=None, description="Optional target loan for prepayment simulation")
    extra_monthly_prepayment: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0, description="Simulate extra monthly prepayment")
    lump_sum_prepayment: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0, description="Simulate one-time lump-sum prepayment")


class LoanAuditReport(BaseModel):
    total_loans_count: int
    active_loans_count: int
    total_borrowed_principal: Decimal
    total_outstanding_principal: Decimal
    total_monthly_emi: Decimal
    total_remaining_interest: Decimal
    weighted_average_interest_rate: Decimal
    monthly_income: Decimal
    foir_percent: Decimal
    foir_risk_level: str  # "SAFE", "MODERATE", "HIGH_RISK", "CRITICAL"
    foir_advice: str
    high_interest_loans_count: int
    total_monthly_interest_leakage: Decimal
    refinancing_opportunities: List[RefinanceOpportunity]
    prepayment_simulation: Optional[PrepaymentSimulationResult] = None
    emi_calendar: List[EMICalendarItem]
    ai_insights: List[str]
    action_plan: List[str]
    rbi_guideline_notes: List[str]
    generated_at: str


