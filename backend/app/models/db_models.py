import json
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, Numeric, ForeignKey, UniqueConstraint
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # Nullable for pure OAuth / Google users
    full_name = Column(String(255), nullable=True)
    auth_provider = Column(String(32), default="email", nullable=False)  # "email", "google"
    google_sub = Column(String(128), unique=True, index=True, nullable=True)
    role = Column(String(32), default="borrower", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

class PasswordResetTokenModel(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False)
    token_hash = Column(String(128), index=True, nullable=False)
    otp_code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

class JourneyModel(Base):
    __tablename__ = "journeys"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=True, default="user_sahayak_demo")
    stage = Column(String, nullable=False, default="INTENT_CAPTURED", index=True)
    language = Column(String, nullable=False, default="en")
    loan_amount = Column(Numeric(12, 2), nullable=False)
    preferred_tenure_months = Column(Integer, nullable=False)
    maximum_emi = Column(Numeric(12, 2), nullable=True)
    purpose = Column(String(255), nullable=False, default="Personal Loan")
    selected_offer_id = Column(String, nullable=True)
    customer_confirmed = Column(Boolean, nullable=False, default=False)
    ready_for_handoff = Column(Boolean, nullable=False, default=False)
    human_review_required = Column(Boolean, nullable=False, default=False)
    human_review_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class LoanProductModel(Base):
    """Versioned catalogue record; source_type distinguishes real and demo data."""
    __tablename__ = "loan_products"

    offer_id = Column(String(64), primary_key=True)
    lender_id = Column(String(64), index=True, nullable=False)
    lender_name = Column(String(150), nullable=False)
    product_name = Column(String(150), nullable=False, default="Personal Loan")
    loan_type = Column(String(32), nullable=False, default="personal")
    min_amount = Column(Numeric(14, 2), nullable=False)
    max_amount = Column(Numeric(14, 2), nullable=False)
    annual_interest_rate_percent = Column(Numeric(6, 3), nullable=False)
    processing_fee_percent = Column(Numeric(6, 3), nullable=False, default=0)
    processing_fee_gst_percent = Column(Numeric(6, 3), nullable=False, default=18)
    min_tenure_months = Column(Integer, nullable=False)
    max_tenure_months = Column(Integer, nullable=False)
    min_monthly_income = Column(Numeric(14, 2), nullable=True)
    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)
    employment_types_json = Column(Text, nullable=False, default="[]")
    locations_json = Column(Text, nullable=False, default="[]")
    kfs_version = Column(String(64), nullable=False)
    kfs_effective_date = Column(String(32), nullable=False)
    source_name = Column(String(150), nullable=True)
    source_url = Column(String(1000), nullable=True)
    source_type = Column(String(24), nullable=False, default="synthetic")
    last_verified_at = Column(DateTime, nullable=True)
    status = Column(String(24), nullable=False, default="active", index=True)
    disclaimer = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class LoanRateHistoryModel(Base):
    __tablename__ = "loan_rate_history"

    id = Column(String(64), primary_key=True)
    offer_id = Column(String(64), ForeignKey("loan_products.offer_id", ondelete="CASCADE"), index=True, nullable=False)
    annual_interest_rate_percent = Column(Numeric(6, 3), nullable=False)
    processing_fee_percent = Column(Numeric(6, 3), nullable=False)
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=True)
    source_name = Column(String(150), nullable=True)
    source_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

class ConsentAuditModel(Base):
    __tablename__ = "consent_audits"

    consent_id = Column(String, primary_key=True, index=True)
    journey_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    scope = Column(String, nullable=False)
    purpose = Column(String(500), nullable=False)
    is_granted = Column(Boolean, nullable=False)
    ip_address = Column(String(100), nullable=True)
    user_agent = Column(String(255), nullable=True)
    tamper_hash = Column(String(128), nullable=False)
    timestamp = Column(DateTime, default=utcnow, nullable=False)

class IdempotencyModel(Base):
    __tablename__ = "idempotency_keys"

    idempotency_key = Column(String, primary_key=True, index=True)
    endpoint = Column(String, nullable=False)
    request_hash = Column(String(128), nullable=False)
    response_status = Column(Integer, nullable=False)
    response_body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

class DocumentModel(Base):
    __tablename__ = "documents"

    document_id = Column(String, primary_key=True, index=True)
    journey_id = Column(String, index=True, nullable=False)
    document_type = Column(String, nullable=False)
    quality_score = Column(Float, nullable=False)
    fields_json = Column(Text, nullable=False, default="{}")
    is_confirmed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    def get_fields(self):
        try:
            return json.loads(self.fields_json)
        except Exception:
            return {}

class PaymentOrderModel(Base):
    __tablename__ = "payment_orders"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), index=True, nullable=False)
    purpose = Column(String(64), nullable=False)
    amount_paise = Column(Integer, nullable=False)
    currency = Column(String(10), default="inr", nullable=False)
    status = Column(String(32), default="CREATED", nullable=False, index=True)
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)
    stripe_payment_intent_id = Column(String(128), index=True, nullable=True)
    stripe_client_secret = Column(String(255), nullable=True)
    provider = Column(String(32), nullable=False, default="stripe", index=True)
    provider_transaction_id = Column(String(128), nullable=True, index=True)
    reference_id = Column(String(128), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    def get_metadata(self):
        try:
            return json.loads(self.metadata_json) if self.metadata_json else {}
        except Exception:
            return {}

class ProviderEventModel(Base):
    __tablename__ = "provider_events"

    id = Column(String(64), primary_key=True, index=True)
    provider = Column(String(32), default="stripe", nullable=False)
    event_id = Column(String(128), unique=True, index=True, nullable=False)
    event_type = Column(String(64), nullable=False, index=True)
    payload_hash = Column(String(64), nullable=False)
    payload_json = Column(Text, nullable=False)
    processed = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

class PaymentAuditLogModel(Base):
    __tablename__ = "payment_audit_logs"

    id = Column(String(64), primary_key=True, index=True)
    order_id = Column(String(64), index=True, nullable=False)
    previous_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=False)
    triggered_by = Column(String(32), nullable=False)  # API, WEBHOOK, RECONCILIATION, ADMIN
    reason = Column(String(255), nullable=True)
    event_id = Column(String(128), nullable=True)
    timestamp = Column(DateTime, default=utcnow, nullable=False)


class WalletLedgerEntryModel(Base):
    """Append-only wallet credits, unique per successful payment order."""
    __tablename__ = "wallet_ledger_entries"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    payment_order_id = Column(String(64), ForeignKey("payment_orders.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    amount_paise = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False, default="inr")
    entry_type = Column(String(24), nullable=False, default="CREDIT")
    created_at = Column(DateTime, default=utcnow, nullable=False)


class DemoRepaymentModel(Base):
    """Clearly simulated repayment events; never represent provider/lender settlement."""
    __tablename__ = "demo_repayments"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    journey_id = Column(String(64), ForeignKey("journeys.id", ondelete="CASCADE"), index=True, nullable=False)
    due_at = Column(DateTime, nullable=False)
    amount_paise = Column(Integer, nullable=False)
    status = Column(String(24), nullable=False)  # PAID_ON_TIME, PAID_LATE, MISSED, UPCOMING
    recorded_at = Column(DateTime, default=utcnow, nullable=False)
    source = Column(String(24), nullable=False, default="simulation")


class DemoTransferModel(Base):
    """Non-monetary send-flow demo record; never a Stripe transfer or payout."""
    __tablename__ = "demo_transfers"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    recipient_label = Column(String(120), nullable=False)
    amount_paise = Column(Integer, nullable=False)
    note = Column(String(240), nullable=True)
    status = Column(String(24), nullable=False, default="SIMULATED")
    created_at = Column(DateTime, default=utcnow, nullable=False)


class DemoWalletAccountModel(Base):
    """Non-cash demo wallet balance; isolated from Stripe test credits."""
    __tablename__ = "demo_wallet_accounts"

    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    wallet_code = Column(String(24), unique=True, index=True, nullable=False)
    balance_paise = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class DemoWalletEntryModel(Base):
    """Append-only credits and debits for simulated user-to-user transfers."""
    __tablename__ = "demo_wallet_entries"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_demo_wallet_user_idempotency"),)

    id = Column(String(64), primary_key=True, index=True)
    transaction_id = Column(String(64), index=True, nullable=False)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    counterparty_user_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    idempotency_key = Column(String(128), nullable=True)
    entry_type = Column(String(16), nullable=False)  # DEMO_FUND, CREDIT, DEBIT
    amount_paise = Column(Integer, nullable=False)
    description = Column(String(240), nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class PaymentAIConsentAuditModel(Base):
    """Immutable user-level consent records for sharing payment summaries with AI."""
    __tablename__ = "payment_ai_consent_audits"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    scope = Column(String(64), nullable=False, default="ai_payment_context_processing")
    is_granted = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class AIRateLimitBucketModel(Base):
    """Atomic fixed-window counters; actor identifiers are keyed hashes, never raw IDs/IPs."""
    __tablename__ = "ai_rate_limit_buckets"
    scope = Column(String(16), primary_key=True)  # global_minute, global_day, user_hour
    bucket_start = Column(DateTime, primary_key=True)
    actor_hash = Column(String(64), primary_key=True, default="global")
    request_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class UserLoanModel(Base):
    """Multi-platform user loans aggregated on a single unified audit dashboard."""
    __tablename__ = "user_loans"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    lender_name = Column(String(128), index=True, nullable=False)  # e.g. "HDFC Bank", "Bajaj Finance"
    lender_type = Column(String(32), default="BANK", nullable=False)  # BANK, NBFC, FINTECH
    loan_type = Column(String(32), default="PERSONAL", nullable=False)  # PERSONAL, HOME, AUTO, EDUCATION, CONSUMER_DURABLE, CREDIT_LINE, GOLD
    account_number = Column(String(64), nullable=False)
    original_principal = Column(Numeric(14, 2), nullable=False)
    outstanding_principal = Column(Numeric(14, 2), nullable=False)
    interest_rate_percent = Column(Numeric(6, 2), nullable=False)
    tenure_months = Column(Integer, nullable=False)
    remaining_tenure_months = Column(Integer, nullable=False)
    emi_amount = Column(Numeric(12, 2), nullable=False)
    emi_due_day = Column(Integer, default=5, nullable=False)  # 1-31
    next_due_date = Column(String(32), nullable=False)
    status = Column(String(32), default="ACTIVE", index=True, nullable=False)  # ACTIVE, OVERDUE, CLOSED, RESTRUCTURED
    disbursement_date = Column(String(32), nullable=True)
    processing_fee_paid = Column(Numeric(10, 2), default=0.00, nullable=False)
    prepayment_penalty_percent = Column(Numeric(5, 2), default=0.00, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class RecurringBillModel(Base):
    """User-entered recurring expense reminder; never triggers a payment."""
    __tablename__ = "recurring_bills"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(120), nullable=False)
    category = Column(String(32), nullable=False, default="OTHER")
    payee = Column(String(120), nullable=True)
    expected_amount_paise = Column(Integer, nullable=True)
    frequency = Column(String(16), nullable=False, default="MONTHLY")
    next_due_date = Column(String(10), nullable=False)
    schedule_day = Column(Integer, nullable=False, default=1)
    schedule_month = Column(Integer, nullable=True)
    reminder_days_before = Column(Integer, nullable=False, default=3)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class BillPaymentRecordModel(Base):
    """Manually recorded bill payments; unrelated to Stripe or wallet transfers."""
    __tablename__ = "bill_payment_records"
    __table_args__ = (UniqueConstraint("bill_id", "due_date", name="uq_bill_payment_occurrence"),)

    id = Column(String(64), primary_key=True, index=True)
    bill_id = Column(String(64), ForeignKey("recurring_bills.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    due_date = Column(String(10), nullable=False)
    amount_paise = Column(Integer, nullable=False)
    paid_at = Column(DateTime, default=utcnow, nullable=False)
    note = Column(String(240), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)


