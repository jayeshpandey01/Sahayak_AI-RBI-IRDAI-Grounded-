from decimal import Decimal
from typing import List, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models.db_models import UserModel, PaymentOrderModel, PaymentAIConsentAuditModel, DemoTransferModel
from app.models.schemas import (
    CreatePaymentOrderRequest,
    PaymentOrderResponse,
    WebhookResponse,
    PaymentOrderStatus,
    PaymentPurpose,
    PaymentReconcileResponse,
    WalletBalanceResponse,
    PaymentHistoryItem,
    DemoTransferCreateRequest,
    DemoTransferResponse,
)
from app.api.dependencies import get_current_user, get_admin_user
from app.services.payment_service import (
    create_payment_order,
    create_wallet_checkout_order,
    get_payment_order,
    list_user_payment_orders,
    process_stripe_webhook,
    reconcile_stale_payment_orders,
)
from app.services.credit_score_service import build_payment_behaviour_estimate

router = APIRouter(prefix="/api/v1", tags=["Payment Orders & Gateways"])


@router.get("/credit-profile/payment-behaviour", summary="Get the signed-in user's demo payment-behaviour indicator")
def get_payment_behaviour_estimate(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Returns a clearly non-bureau estimate from explicit simulated repayments only."""
    return build_payment_behaviour_estimate(db, current_user.id)


@router.post("/demo/transfers", status_code=status.HTTP_410_GONE,
             summary="Retired non-debiting send demo endpoint")
def create_demo_transfer(
    payload: DemoTransferCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Prevent old clients from recording a send that does not debit demo funds."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="This non-debiting demo send endpoint is retired. Use /api/v1/demo-wallet/transfers.",
    )


@router.get("/demo/transfers", response_model=List[DemoTransferResponse],
            summary="List the signed-in user's simulated send records")
def list_demo_transfers(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=100),
):
    transfers = db.query(DemoTransferModel).filter(
        DemoTransferModel.user_id == current_user.id,
    ).order_by(DemoTransferModel.created_at.desc()).limit(limit).all()
    return [DemoTransferResponse(
        transfer_id=item.id, recipient_label=item.recipient_label,
        amount_rupees=Decimal(item.amount_paise) / Decimal(100),
        status=item.status, created_at=item.created_at,
    ) for item in transfers]

def model_to_response(order: PaymentOrderModel) -> PaymentOrderResponse:
    """Format SQLAlchemy PaymentOrderModel into typed PaymentOrderResponse."""
    return PaymentOrderResponse(
        order_id=order.id,
        user_id=order.user_id,
        status=PaymentOrderStatus(order.status),
        purpose=PaymentPurpose(order.purpose),
        amount_rupees=Decimal(order.amount_paise) / Decimal(100),
        amount_paise=order.amount_paise,
        currency=order.currency,
        merchant_display_name="Sahayak AI",
        client_secret=order.stripe_client_secret,
        publishable_key=settings.STRIPE_PUBLISHABLE_KEY,
        checkout_url=order.get_metadata().get("_stripe_checkout_url"),
        stripe_payment_intent_id=order.stripe_payment_intent_id,
        provider=getattr(order, "provider", "stripe") or "stripe",
        provider_transaction_id=getattr(order, "provider_transaction_id", None),
        checkout_token=getattr(order, "_checkout_token", None),
        merchant_id=None,
        reference_id=order.reference_id,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )

@router.post(
    "/payment-orders",
    response_model=PaymentOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create authenticated Stripe wallet top-up PaymentIntent order"
)
def create_payment_order_endpoint(
    payload: CreatePaymentOrderRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key")
):
    """
    Creates a server-authorized payment order and corresponding Stripe PaymentIntent.
    Enforces idempotency replay and prevents client amount tampering.
    """
    user_id = current_user.id
    if payload.purpose != PaymentPurpose.WALLET_TOPUP:
        raise HTTPException(
            status_code=422,
            detail="This Stripe demo currently supports wallet top-ups only. Loan fees and repayments require an integrated lender; transfers are not supported.",
        )
    if payload.currency.lower() != "inr":
        raise HTTPException(status_code=422, detail="This Stripe wallet demo accepts INR orders only.")
    idempotency_key = x_idempotency_key or f"idem_{uuid4().hex[:16]}"

    order = create_payment_order(
        db=db,
        user_id=user_id,
        payload=payload,
        idempotency_key=idempotency_key
    )
    return model_to_response(order)


@router.post("/wallet/payment-orders", response_model=PaymentOrderResponse,
             status_code=status.HTTP_201_CREATED, summary="Create authenticated Stripe wallet checkout")
def create_wallet_checkout_order_endpoint(
    payload: CreatePaymentOrderRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
):
    origin = request.headers.get("origin", "").rstrip("/")
    allowed_origin = origin if origin in settings.ALLOWED_ORIGINS else None
    order = create_wallet_checkout_order(
        db=db, user_id=current_user.id, payload=payload,
        idempotency_key=x_idempotency_key or f"wallet_{uuid4().hex}",
        return_url_override=f"{allowed_origin}/" if allowed_origin else None,
    )
    return model_to_response(order)


@router.get("/wallet/payment-orders/{order_id}", response_model=PaymentOrderResponse,
            summary="Get authenticated Stripe wallet checkout status")
def get_wallet_checkout_order_endpoint(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    order = db.query(PaymentOrderModel).filter(
        PaymentOrderModel.id == order_id,
        PaymentOrderModel.user_id == current_user.id,
        PaymentOrderModel.purpose == PaymentPurpose.WALLET_TOPUP.value,
        PaymentOrderModel.provider == "stripe",
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Wallet payment order not found.")
    return model_to_response(order)


@router.get("/wallet/payment-orders", response_model=List[PaymentHistoryItem],
            summary="List authenticated user's payment history")
def list_wallet_payment_orders_endpoint(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=100),
):
    """List only this user's wallet orders, omitting checkout secrets."""
    orders = db.query(PaymentOrderModel).filter(
        PaymentOrderModel.user_id == current_user.id,
        PaymentOrderModel.purpose == PaymentPurpose.WALLET_TOPUP.value,
        PaymentOrderModel.provider == "stripe",
    ).order_by(PaymentOrderModel.created_at.desc()).limit(limit).all()
    return [PaymentHistoryItem(
        order_id=o.id, status=PaymentOrderStatus(o.status),
        purpose=PaymentPurpose(o.purpose), amount_rupees=Decimal(o.amount_paise) / Decimal(100),
        currency=o.currency, provider=o.provider, reference_id=o.reference_id,
        created_at=o.created_at, updated_at=o.updated_at,
    ) for o in orders]


@router.get("/wallet/balance", response_model=WalletBalanceResponse, summary="Get server-authoritative wallet credits")
def get_wallet_balance_endpoint(
    db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user),
):
    from sqlalchemy import func
    from app.models.db_models import WalletLedgerEntryModel
    total = db.query(func.coalesce(func.sum(WalletLedgerEntryModel.amount_paise), 0)).filter(
        WalletLedgerEntryModel.user_id == current_user.id
    ).scalar()
    entries = db.query(WalletLedgerEntryModel).filter(
        WalletLedgerEntryModel.user_id == current_user.id
    ).order_by(WalletLedgerEntryModel.created_at.desc()).limit(50).all()
    return WalletBalanceResponse(
        balance_paise=int(total), credited_total_paise=int(total), currency="inr",
        ledger_entries=[{"payment_order_id": e.payment_order_id, "amount_paise": e.amount_paise,
                         "currency": e.currency, "created_at": e.created_at} for e in entries],
    )


@router.post("/payments/ai-context-consent", summary="Record consent for AI use of a payment summary")
def record_payment_ai_context_consent(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    granted = payload.get("is_granted")
    if not isinstance(granted, bool):
        raise HTTPException(status_code=422, detail="is_granted must be a boolean.")
    audit = PaymentAIConsentAuditModel(
        id=f"paic_{uuid4().hex[:20]}", user_id=current_user.id,
        scope="ai_payment_context_processing", is_granted=granted,
    )
    db.add(audit)
    db.commit()
    return {"recorded": True, "scope": audit.scope, "is_granted": audit.is_granted, "created_at": audit.created_at}

@router.get(
    "/payment-orders/{order_id}",
    response_model=PaymentOrderResponse,
    summary="Get canonical payment order status"
)
def get_payment_order_endpoint(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieve payment order canonical status with tenant isolation enforcement.
    """
    order = get_payment_order(db=db, order_id=order_id, current_user=current_user)
    return model_to_response(order)

@router.get(
    "/payment-orders",
    response_model=List[PaymentOrderResponse],
    summary="List caller payment orders"
)
def list_payment_orders_endpoint(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=100)
):
    """
    List historical payment orders for the authenticated user.
    """
    orders = list_user_payment_orders(db=db, user_id=current_user.id, limit=limit)
    return [model_to_response(o) for o in orders]

@router.post(
    "/webhooks/stripe",
    response_model=WebhookResponse,
    summary="Stripe signed webhook listener"
)
async def stripe_webhook_endpoint(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature")
):
    """
    Receives and authoritatively verifies signed webhook events from Stripe.
    Performs deduplication and transitions payment orders into terminal states.
    """
    raw_payload = await request.body()
    return process_stripe_webhook(
        db=db,
        raw_payload=raw_payload,
        sig_header=stripe_signature
    )

@router.post(
    "/payments/reconcile",
    response_model=PaymentReconcileResponse,
    summary="Stale payment intent reconciliation sweeper"
)
def reconcile_payments_endpoint(
    db: Session = Depends(get_db),
    older_than_minutes: int = Query(default=15, ge=0, le=1440),
    limit: int = Query(default=50, ge=1, le=100),
    admin_user: UserModel = Depends(get_admin_user)
):
    """
    Restricted administrative sweeper that queries unconfirmed payment orders
    and reconciles status against Stripe. Enforces admin RBAC and batch query bounds.
    """
    result = reconcile_stale_payment_orders(
        db=db,
        older_than_minutes=older_than_minutes,
        limit=limit
    )
    return PaymentReconcileResponse(
        reconciled_count=result["reconciled_count"],
        orders_checked=result["orders_checked"],
        details=result["details"]
    )

