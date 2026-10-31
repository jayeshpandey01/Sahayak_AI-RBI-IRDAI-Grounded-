import json
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.config import settings
from app.models.db_models import (
    PaymentOrderModel,
    ProviderEventModel,
    PaymentAuditLogModel,
    UserModel,
    JourneyModel,
    WalletLedgerEntryModel,
)
from app.models.schemas import (
    PaymentPurpose,
    PaymentOrderStatus,
    CreatePaymentOrderRequest,
    PaymentOrderResponse,
    WebhookResponse,
)
from app.services.stripe_service import (
    create_stripe_payment_intent,
    create_stripe_checkout_session,
    verify_stripe_webhook_signature,
    compute_payload_hash,
    StripeServiceError,
)
from app.services.financial_calculator import get_offer_by_id, calculate_kfs_emi
from app.services.supabase_service import sync_payment_order_to_supabase, sync_audit_log_to_supabase


def create_wallet_checkout_order(
    db: Session,
    user_id: str,
    payload: CreatePaymentOrderRequest,
    idempotency_key: str,
    return_url_override: Optional[str] = None,
) -> PaymentOrderModel:
    """Create an authenticated Stripe-hosted checkout order for a wallet top-up."""
    if payload.purpose != PaymentPurpose.WALLET_TOPUP or payload.currency.lower() != "inr":
        raise HTTPException(status_code=422, detail="Stripe wallet checkout requires purpose=wallet_topup and currency=INR.")
    if payload.amount_rupees is None or payload.amount_rupees * 100 != int(payload.amount_rupees * 100):
        raise HTTPException(status_code=422, detail="Top-up amount must be a whole number of paise.")
    try:
        settings.validate_stripe_credentials()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Stripe checkout is not configured on the backend.") from exc

    amount_paise = resolve_order_amount_paise(db, user_id, payload)
    existing = db.query(PaymentOrderModel).filter(PaymentOrderModel.idempotency_key == idempotency_key).first()
    if existing:
        if (existing.user_id != user_id or existing.amount_paise != amount_paise
                or existing.purpose != PaymentPurpose.WALLET_TOPUP.value
                or existing.currency != "inr" or existing.provider != "stripe"):
            raise HTTPException(status_code=409, detail="Idempotency key was already used for different payment data.")
        if existing.provider_transaction_id:
            return existing
        order = existing
    else:
        now = datetime.now(timezone.utc)
        order = PaymentOrderModel(
            id=f"po_{uuid4().hex[:16]}", user_id=user_id,
            purpose=PaymentPurpose.WALLET_TOPUP.value, amount_paise=amount_paise,
            currency="inr", status=PaymentOrderStatus.CREATED.value,
            idempotency_key=idempotency_key, provider="stripe",
            metadata_json=json.dumps(payload.metadata or {}), created_at=now, updated_at=now,
        )
        db.add(order)
        db.add(PaymentAuditLogModel(
            id=f"pal_{uuid4().hex[:16]}", order_id=order.id, previous_status=None,
            new_status=PaymentOrderStatus.CREATED.value, triggered_by="API",
            reason="Authenticated Stripe wallet checkout initiated", timestamp=now,
        ))
        db.commit()
        db.refresh(order)

    try:
        session = create_stripe_checkout_session(
            amount_paise=amount_paise, currency="inr", order_id=order.id,
            user_id=user_id, idempotency_key=idempotency_key,
            customer_email=payload.customer_email,
            return_url_override=return_url_override,
        )
    except StripeServiceError as exc:
        order.status = PaymentOrderStatus.FAILED.value
        order.updated_at = datetime.now(timezone.utc)
        db.add(PaymentAuditLogModel(
            id=f"pal_{uuid4().hex[:16]}", order_id=order.id,
            previous_status=PaymentOrderStatus.CREATED.value,
            new_status=PaymentOrderStatus.FAILED.value, triggered_by="STRIPE_API",
            reason=f"Stripe checkout error: {exc.message[:180]}", timestamp=datetime.now(timezone.utc),
        ))
        db.commit()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    metadata = order.get_metadata()
    metadata["_stripe_checkout_url"] = session["url"]
    order.metadata_json = json.dumps(metadata)
    order.provider_transaction_id = session["id"]
    order.status = PaymentOrderStatus.REQUIRES_ACTION.value
    order.version += 1
    order.updated_at = datetime.now(timezone.utc)
    db.add(PaymentAuditLogModel(
        id=f"pal_{uuid4().hex[:16]}", order_id=order.id,
        previous_status=PaymentOrderStatus.CREATED.value,
        new_status=PaymentOrderStatus.REQUIRES_ACTION.value, triggered_by="STRIPE_API",
        reason="Stripe Checkout Session created", timestamp=datetime.now(timezone.utc),
    ))
    db.commit()
    db.refresh(order)
    return order

def resolve_order_amount_paise(
    db: Session,
    user_id: str,
    payload: CreatePaymentOrderRequest
) -> int:
    """
    Determines canonical amount in minor units (paise) derived from server-side financial state.
    Never trusts client amounts for loan-backed transactions (processing fees or EMI repayments).
    """
    if payload.purpose in (PaymentPurpose.PROCESSING_FEE, PaymentPurpose.LOAN_PROCESSING_FEE):
        if not payload.reference_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="reference_id (journey_id) is required for processing fee payments."
            )
        journey = db.query(JourneyModel).filter(JourneyModel.id == payload.reference_id).first()
        if not journey:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan journey not found.")
        if journey.user_id and journey.user_id != "user_sahayak_demo":
            if not user_id or user_id != journey.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized: Cannot pay processing fee for another user's journey."
                )

        offer = get_offer_by_id(journey.selected_offer_id, db) if journey.selected_offer_id else None
        if offer is None:
            raise HTTPException(status_code=409, detail="Select an active loan product before creating this payment.")
        emi_calc = calculate_kfs_emi(
            principal=journey.loan_amount,
            tenure_months=journey.preferred_tenure_months,
            offer=offer
        )
        return int(emi_calc.total_upfront_deductions_rupees * 100)

    elif payload.purpose == PaymentPurpose.EMI_REPAYMENT:
        if not payload.reference_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="reference_id (journey_id) is required for EMI repayments."
            )
        journey = db.query(JourneyModel).filter(JourneyModel.id == payload.reference_id).first()
        if not journey:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan journey not found.")
        if journey.user_id and journey.user_id != "user_sahayak_demo":
            if not user_id or user_id != journey.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized: Cannot pay EMI for another user's journey."
                )

        offer = get_offer_by_id(journey.selected_offer_id, db) if journey.selected_offer_id else None
        if offer is None:
            raise HTTPException(status_code=409, detail="Select an active loan product before creating this payment.")
        emi_calc = calculate_kfs_emi(
            principal=journey.loan_amount,
            tenure_months=journey.preferred_tenure_months,
            offer=offer
        )
        return int(emi_calc.estimated_emi_rupees * 100)

    elif payload.purpose == PaymentPurpose.VERIFICATION_DEPOSIT:
        return 100  # Fixed ₹1.00

    else:
        # Wallet topup or general payment
        if payload.amount_rupees is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="amount_rupees is required for this payment purpose."
            )
        return int(payload.amount_rupees * 100)

def create_payment_order(
    db: Session,
    user_id: str,
    payload: CreatePaymentOrderRequest,
    idempotency_key: str
) -> PaymentOrderModel:
    """
    Creates an authoritative, server-priced payment order and links it to a Stripe PaymentIntent.
    Enforces strict idempotency and short-lived database transactions.
    """
    amount_paise = resolve_order_amount_paise(db=db, user_id=user_id, payload=payload)

    # 1. Idempotency Check: Replay if matching, Conflict if differing payload
    existing_order = (
        db.query(PaymentOrderModel)
        .filter(PaymentOrderModel.idempotency_key == idempotency_key)
        .first()
    )

    if existing_order:
        if (
            existing_order.user_id == user_id
            and existing_order.amount_paise == amount_paise
            and existing_order.purpose == payload.purpose.value
            and existing_order.currency == payload.currency.lower()
        ):
            # Safe replay of existing order
            return existing_order
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency conflict: An order with this key already exists with different payload parameters."
            )

    order_id = f"po_{uuid4().hex[:16]}"
    now = datetime.now(timezone.utc)

    # 2. Claim order in DB with status CREATED inside short transaction
    order = PaymentOrderModel(
        id=order_id,
        user_id=user_id,
        purpose=payload.purpose.value,
        amount_paise=amount_paise,
        currency=payload.currency.lower(),
        status=PaymentOrderStatus.CREATED.value,
        idempotency_key=idempotency_key,
        reference_id=payload.reference_id,
        version=1,
        metadata_json=json.dumps(payload.metadata or {}),
        created_at=now,
        updated_at=now,
    )
    audit_init = PaymentAuditLogModel(
        id=f"pal_{uuid4().hex[:16]}",
        order_id=order_id,
        previous_status=None,
        new_status=PaymentOrderStatus.CREATED.value,
        triggered_by="API",
        reason="Order initiated",
        timestamp=now
    )
    db.add(order)
    db.add(audit_init)
    db.commit()
    if order:
        sync_payment_order_to_supabase({
            "id": order.id,
            "status": order.status,
            "completed_at": order.completed_at,
            "version": order.version,
            "updated_at": order.updated_at,
        })

    # 3. Create Stripe PaymentIntent outside long-held DB locks
    metadata = {
        "order_id": order_id,
        "user_id": user_id,
        "purpose": payload.purpose.value,
        "reference_id": payload.reference_id or "",
    }
    if payload.metadata:
        for k, v in payload.metadata.items():
            metadata[k] = str(v)

    try:
        stripe_intent = create_stripe_payment_intent(
            amount_paise=amount_paise,
            currency=payload.currency.lower(),
            idempotency_key=f"stripe_idem_{idempotency_key}",
            metadata=metadata,
            customer_email=payload.customer_email
        )
    except StripeServiceError as exc:
        order.status = PaymentOrderStatus.FAILED.value
        order.updated_at = datetime.now(timezone.utc)
        audit_fail = PaymentAuditLogModel(
            id=f"pal_{uuid4().hex[:16]}",
            order_id=order_id,
            previous_status=PaymentOrderStatus.CREATED.value,
            new_status=PaymentOrderStatus.FAILED.value,
            triggered_by="STRIPE_API",
            reason=f"Stripe error: {exc.message}",
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit_fail)
        db.commit()
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    # 4. Update order with client secret and transition to REQUIRES_ACTION
    order.stripe_payment_intent_id = stripe_intent["id"]
    order.stripe_client_secret = stripe_intent.get("client_secret")
    order.status = PaymentOrderStatus.REQUIRES_ACTION.value
    order.version += 1
    order.updated_at = datetime.now(timezone.utc)

    audit_prog = PaymentAuditLogModel(
        id=f"pal_{uuid4().hex[:16]}",
        order_id=order_id,
        previous_status=PaymentOrderStatus.CREATED.value,
        new_status=PaymentOrderStatus.REQUIRES_ACTION.value,
        triggered_by="STRIPE_API",
        reason="PaymentIntent created successfully",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit_prog)
    db.commit()
    db.refresh(order)

    # Fail-safe mirror to Supabase cloud datastore
    sync_payment_order_to_supabase({
        "id": order.id,
        "user_id": order.user_id,
        "purpose": order.purpose,
        "amount_paise": order.amount_paise,
        "currency": order.currency,
        "status": order.status,
        "idempotency_key": order.idempotency_key,
        "stripe_payment_intent_id": order.stripe_payment_intent_id,
        "reference_id": order.reference_id,
        "version": order.version,
        "created_at": order.created_at,
    })
    sync_audit_log_to_supabase({
        "id": audit_prog.id,
        "order_id": audit_prog.order_id,
        "previous_status": audit_prog.previous_status,
        "new_status": audit_prog.new_status,
        "triggered_by": audit_prog.triggered_by,
        "reason": audit_prog.reason,
        "timestamp": audit_prog.timestamp,
    })

    return order

def get_payment_order(
    db: Session,
    order_id: str,
    current_user: Optional[UserModel]
) -> PaymentOrderModel:
    """
    Retrieve payment order with strict multi-tenant isolation.
    """
    order = db.query(PaymentOrderModel).filter(PaymentOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Payment order not found")

    if order.user_id != "user_sahayak_demo":
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view this payment order.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if order.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to view another user's payment order."
            )

    return order

def list_user_payment_orders(
    db: Session,
    user_id: str,
    limit: int = 50
) -> List[PaymentOrderModel]:
    """Retrieve orders belonging to user."""
    return (
        db.query(PaymentOrderModel)
        .filter(PaymentOrderModel.user_id == user_id)
        .order_by(PaymentOrderModel.created_at.desc())
        .limit(limit)
        .all()
    )

def process_stripe_webhook(
    db: Session,
    raw_payload: bytes,
    sig_header: Optional[str]
) -> WebhookResponse:
    """
    Validates webhook signature, deduplicates provider events, and transitions
    payment order state authoritatively with terminal state protection.
    """
    # 1. Signature Verification (Fail-Closed)
    if settings.STRIPE_MODE == "simulator":
        pass  # Permitted in offline simulator testing
    elif not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe webhook secret is not configured on the server."
        )
    elif not sig_header or not verify_stripe_webhook_signature(raw_payload, sig_header):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook signature"
        )

    # 2. Parse Event Payload
    try:
        event = json.loads(raw_payload.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON in webhook body"
        )

    event_id = event.get("id")
    event_type = event.get("type")
    if not event_id or not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event id or type in webhook payload"
        )

    # 3. Deduplication Check
    existing_event = (
        db.query(ProviderEventModel)
        .filter(ProviderEventModel.event_id == event_id)
        .first()
    )
    if existing_event and existing_event.processed:
        return WebhookResponse(
            received=True,
            event_id=event_id,
            event_type=event_type,
            processed=True
        )

    # 4. State Machine Transition with Out-of-Order Invariant Guard
    event_obj = event.get("data", {}).get("object", {})
    intent_id = event_obj.get("id") if event_obj.get("object") != "checkout.session" else None
    checkout_order_id = None
    if event_obj.get("object") == "checkout.session":
        checkout_order_id = (event_obj.get("metadata") or {}).get("order_id") or event_obj.get("client_reference_id")
    elif event_obj.get("object") != "checkout.session":
        checkout_order_id = (event_obj.get("metadata") or {}).get("order_id")
    error_msg: Optional[str] = None
    order: Optional[PaymentOrderModel] = None

    if intent_id or checkout_order_id:
        order_query = db.query(PaymentOrderModel)
        if checkout_order_id:
            order = order_query.filter(PaymentOrderModel.id == checkout_order_id).first()
        else:
            order = order_query.filter(PaymentOrderModel.stripe_payment_intent_id == intent_id).first()

        if order and order.provider == "stripe":
            # Out-of-order terminal protection: Never downgrade SUCCEEDED state!
            if order.status == PaymentOrderStatus.SUCCEEDED.value:
                # Terminal state invariant: ignore late failure or cancellation events
                pass
            elif event_type in ("checkout.session.expired", "checkout.session.async_payment_failed"):
                prev = order.status
                order.status = (PaymentOrderStatus.EXPIRED.value
                                if event_type == "checkout.session.expired"
                                else PaymentOrderStatus.FAILED.value)
                order.version += 1
                order.updated_at = datetime.now(timezone.utc)
                db.add(PaymentAuditLogModel(
                    id=f"pal_{uuid4().hex[:16]}", order_id=order.id,
                    previous_status=prev, new_status=order.status,
                    triggered_by="WEBHOOK", reason=f"Webhook {event_type} received",
                    event_id=event_id, timestamp=datetime.now(timezone.utc),
                ))
            elif event_type in ("payment_intent.succeeded", "checkout.session.completed", "checkout.session.async_payment_succeeded"):
                is_checkout = event_obj.get("object") == "checkout.session"
                metadata = event_obj.get("metadata") or {}
                amount_received = event_obj.get("amount_total") if is_checkout else event_obj.get("amount_received", event_obj.get("amount"))
                currency_received = event_obj.get("currency", "").lower()
                checkout_paid = not is_checkout or event_obj.get("payment_status") == "paid"
                checkout_matches = (
                    (not metadata.get("order_id") or metadata.get("order_id") == order.id)
                    and (not metadata.get("user_id") or metadata.get("user_id") == order.user_id)
                    and (not is_checkout or event_obj.get("client_reference_id") == order.id)
                )
                if is_checkout and not checkout_paid and checkout_matches:
                    prev = order.status
                    order.status = PaymentOrderStatus.PROCESSING.value
                    order.version += 1
                    order.updated_at = datetime.now(timezone.utc)
                    db.add(PaymentAuditLogModel(
                        id=f"pal_{uuid4().hex[:16]}", order_id=order.id,
                        previous_status=prev, new_status=PaymentOrderStatus.PROCESSING.value,
                        triggered_by="WEBHOOK", reason="Checkout completed; asynchronous payment is pending",
                        event_id=event_id, timestamp=datetime.now(timezone.utc),
                    ))
                elif (
                    amount_received == order.amount_paise
                    and currency_received == order.currency.lower()
                    and checkout_paid
                    and checkout_matches
                ):
                    prev = order.status
                    order.status = PaymentOrderStatus.SUCCEEDED.value
                    order.completed_at = datetime.now(timezone.utc)
                    if is_checkout and event_obj.get("payment_intent"):
                        order.stripe_payment_intent_id = event_obj.get("payment_intent")
                    elif event_obj.get("object") == "payment_intent":
                        order.stripe_payment_intent_id = event_obj.get("id")
                    order.version += 1
                    order.updated_at = datetime.now(timezone.utc)
                    if order.purpose == PaymentPurpose.WALLET_TOPUP.value:
                        existing = db.query(WalletLedgerEntryModel).filter(
                            WalletLedgerEntryModel.payment_order_id == order.id
                        ).first()
                        if not existing:
                            db.add(WalletLedgerEntryModel(
                                id=f"wle_{uuid4().hex[:20]}",
                                user_id=order.user_id,
                                payment_order_id=order.id,
                                amount_paise=order.amount_paise,
                                currency=order.currency.lower(),
                            ))
                    audit = PaymentAuditLogModel(
                        id=f"pal_{uuid4().hex[:16]}",
                        order_id=order.id,
                        previous_status=prev,
                        new_status=PaymentOrderStatus.SUCCEEDED.value,
                        triggered_by="WEBHOOK",
                        reason=f"Webhook {event_type} verified",
                        event_id=event_id,
                        timestamp=datetime.now(timezone.utc)
                    )
                    db.add(audit)
                else:
                    prev = order.status
                    order.status = PaymentOrderStatus.RECONCILIATION_REQUIRED.value
                    order.version += 1
                    order.updated_at = datetime.now(timezone.utc)
                    error_msg = f"Amount/Currency mismatch: expected {order.amount_paise} {order.currency}, got {amount_received} {currency_received}"
                    audit = PaymentAuditLogModel(
                        id=f"pal_{uuid4().hex[:16]}",
                        order_id=order.id,
                        previous_status=prev,
                        new_status=PaymentOrderStatus.RECONCILIATION_REQUIRED.value,
                        triggered_by="WEBHOOK",
                        reason=error_msg,
                        event_id=event_id,
                        timestamp=datetime.now(timezone.utc)
                    )
                    db.add(audit)

            elif event_type == "payment_intent.payment_failed":
                prev = order.status
                order.status = PaymentOrderStatus.FAILED.value
                order.version += 1
                order.updated_at = datetime.now(timezone.utc)
                audit = PaymentAuditLogModel(
                    id=f"pal_{uuid4().hex[:16]}",
                    order_id=order.id,
                    previous_status=prev,
                    new_status=PaymentOrderStatus.FAILED.value,
                    triggered_by="WEBHOOK",
                    reason="Webhook payment_intent.payment_failed received",
                    event_id=event_id,
                    timestamp=datetime.now(timezone.utc)
                )
                db.add(audit)

            elif event_type == "payment_intent.canceled":
                prev = order.status
                order.status = PaymentOrderStatus.CANCELED.value
                order.version += 1
                order.updated_at = datetime.now(timezone.utc)
                audit = PaymentAuditLogModel(
                    id=f"pal_{uuid4().hex[:16]}",
                    order_id=order.id,
                    previous_status=prev,
                    new_status=PaymentOrderStatus.CANCELED.value,
                    triggered_by="WEBHOOK",
                    reason="Webhook payment_intent.canceled received",
                    event_id=event_id,
                    timestamp=datetime.now(timezone.utc)
                )
                db.add(audit)

    # 5. Record Provider Event
    payload_hash = compute_payload_hash(raw_payload)
    if not existing_event:
        provider_event = ProviderEventModel(
            id=f"evt_{uuid4().hex[:16]}",
            provider="stripe",
            event_id=event_id,
            event_type=event_type,
            payload_hash=payload_hash,
            payload_json=raw_payload.decode("utf-8"),
            processed=True,
            error_message=error_msg,
            created_at=datetime.now(timezone.utc),
        )
        db.add(provider_event)
    else:
        existing_event.processed = True
        existing_event.error_message = error_msg

    db.commit()
    if order:
        sync_payment_order_to_supabase({
            "id": order.id,
            "status": order.status,
            "completed_at": order.completed_at,
            "version": order.version,
            "updated_at": order.updated_at,
        })

    return WebhookResponse(
        received=True,
        event_id=event_id,
        event_type=event_type,
        processed=True
    )

def reconcile_stale_payment_orders(
    db: Session,
    older_than_minutes: int = 15,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Sweeper that queries unconfirmed payment orders (CREATED, REQUIRES_ACTION, PROCESSING)
    older than threshold, polls Stripe API for current intent state, and reconciles local DB.
    Enforces a bounded batch limit and connection-pooled HTTP client.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)
    stale_orders = (
        db.query(PaymentOrderModel)
        .filter(
            PaymentOrderModel.status.in_([
                PaymentOrderStatus.CREATED.value,
                PaymentOrderStatus.REQUIRES_ACTION.value,
                PaymentOrderStatus.PROCESSING.value,
            ]),
            PaymentOrderModel.created_at <= cutoff
        )
        .order_by(PaymentOrderModel.created_at.asc())
        .limit(limit)
        .all()
    )

    reconciled = []
    if stale_orders and settings.STRIPE_SECRET_KEY and settings.STRIPE_SECRET_KEY.startswith(("sk_test_", "sk_live_")):
        headers = {"Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}"}
        try:
            with httpx.Client(timeout=10.0) as client:
                for order in stale_orders:
                    if not order.stripe_payment_intent_id:
                        continue
                    try:
                        resp = client.get(
                            f"https://api.stripe.com/v1/payment_intents/{order.stripe_payment_intent_id}",
                            headers=headers
                        )
                        if resp.status_code == 200:
                            stripe_data = resp.json()
                            st_status = stripe_data.get("status")
                            if st_status == "succeeded" and order.status != PaymentOrderStatus.SUCCEEDED.value:
                                prev = order.status
                                order.status = PaymentOrderStatus.SUCCEEDED.value
                                order.completed_at = datetime.now(timezone.utc)
                                order.version += 1
                                if order.purpose == PaymentPurpose.WALLET_TOPUP.value:
                                    existing = db.query(WalletLedgerEntryModel).filter(
                                        WalletLedgerEntryModel.payment_order_id == order.id
                                    ).first()
                                    if not existing:
                                        db.add(WalletLedgerEntryModel(
                                            id=f"wle_{uuid4().hex[:20]}",
                                            user_id=order.user_id,
                                            payment_order_id=order.id,
                                            amount_paise=order.amount_paise,
                                            currency=order.currency.lower(),
                                        ))
                                audit = PaymentAuditLogModel(
                                    id=f"pal_{uuid4().hex[:16]}",
                                    order_id=order.id,
                                    previous_status=prev,
                                    new_status=PaymentOrderStatus.SUCCEEDED.value,
                                    triggered_by="RECONCILIATION",
                                    reason="Reconciled from Stripe API status succeeded",
                                    timestamp=datetime.now(timezone.utc)
                                )
                                db.add(audit)
                                reconciled.append({"order_id": order.id, "action": "marked_succeeded"})
                            elif st_status == "canceled" and order.status != PaymentOrderStatus.CANCELED.value:
                                prev = order.status
                                order.status = PaymentOrderStatus.CANCELED.value
                                order.version += 1
                                audit = PaymentAuditLogModel(
                                    id=f"pal_{uuid4().hex[:16]}",
                                    order_id=order.id,
                                    previous_status=prev,
                                    new_status=PaymentOrderStatus.CANCELED.value,
                                    triggered_by="RECONCILIATION",
                                    reason="Reconciled from Stripe API status canceled",
                                    timestamp=datetime.now(timezone.utc)
                                )
                                db.add(audit)
                                reconciled.append({"order_id": order.id, "action": "marked_canceled"})
                    except Exception:
                        pass
        except Exception:
            pass

    db.commit()
    return {
        "orders_checked": len(stale_orders),
        "reconciled_count": len(reconciled),
        "details": reconciled
    }
