import hmac
import hashlib
import time
from typing import Dict, Any, Optional
import httpx
from app.config import settings

class StripeServiceError(Exception):
    """Custom exception for Stripe provider operations."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

def create_stripe_checkout_session(
    amount_paise: int,
    currency: str,
    order_id: str,
    user_id: str,
    idempotency_key: str,
    customer_email: Optional[str] = None,
    return_url_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a hosted Stripe Checkout Session for cross-platform wallet top-ups."""
    try:
        settings.validate_stripe_credentials()
    except RuntimeError as exc:
        raise StripeServiceError(str(exc), status_code=503) from exc

    if settings.STRIPE_SECRET_KEY.startswith("rk_"):
        raise StripeServiceError("Stripe restricted keys cannot create Checkout Sessions; configure a standard test secret key.", 503)

    metadata = {"order_id": order_id, "user_id": user_id, "purpose": "wallet_topup"}
    return_url = (return_url_override or settings.STRIPE_RETURN_URL).rstrip("/")
    success_url = f"{return_url}?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{return_url}?payment=cancelled&order_id={order_id}"
    payload = {
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": order_id,
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": currency.lower(),
        "line_items[0][price_data][unit_amount]": str(amount_paise),
        "line_items[0][price_data][product_data][name]": "Sahayak wallet top-up",
    }
    for key, value in metadata.items():
        payload[f"metadata[{key}]"] = value
        payload[f"payment_intent_data[metadata][{key}]"] = value
    if customer_email:
        payload["customer_email"] = customer_email

    headers = {
        "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Idempotency-Key": f"checkout_{idempotency_key}",
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post("https://api.stripe.com/v1/checkout/sessions", data=payload, headers=headers)
        data = response.json()
        if response.status_code >= 400:
            error = data.get("error", {})
            raise StripeServiceError(error.get("message", "Stripe Checkout Session creation failed."), response.status_code)
        if not data.get("id") or not data.get("url"):
            raise StripeServiceError("Stripe did not return a valid hosted checkout session.", 502)
        return {"id": data["id"], "url": data["url"]}
    except httpx.RequestError as exc:
        raise StripeServiceError("Could not reach Stripe. Retry this payment shortly.", 502) from exc

def create_stripe_payment_intent(
    amount_paise: int,
    currency: str = "inr",
    idempotency_key: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
    customer_email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a real Stripe PaymentIntent. Provider configuration or network errors
    fail closed; this function never fabricates Stripe-shaped IDs or client secrets.
    """
    try:
        settings.validate_stripe_credentials()
    except RuntimeError as exc:
        raise StripeServiceError(str(exc), status_code=503) from exc

    sec_key = settings.STRIPE_SECRET_KEY
    if sec_key.startswith("rk_"):
        raise StripeServiceError("A standard Stripe secret key is required for PaymentIntents.", 503)
    if sec_key.startswith(("sk_test_", "sk_live_")):
        headers = {
            "Authorization": f"Bearer {sec_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        payload = {
            "amount": str(amount_paise),
            "currency": currency.lower(),
            "automatic_payment_methods[enabled]": "true",
        }
        if metadata:
            for k, v in metadata.items():
                payload[f"metadata[{k}]"] = str(v)
        if customer_email:
            payload["receipt_email"] = customer_email

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post("https://api.stripe.com/v1/payment_intents", data=payload, headers=headers)
                if res.status_code >= 400:
                    err_json = res.json().get("error", {})
                    raise StripeServiceError(
                        message=err_json.get("message", "Stripe PaymentIntent creation failed"),
                        status_code=res.status_code
                    )
                data = res.json()
                if not data.get("id") or not data.get("client_secret"):
                    raise StripeServiceError("Stripe did not return a valid PaymentIntent.", status_code=502)
                return {
                    "id": data["id"],
                    "client_secret": data["client_secret"],
                    "status": data.get("status", "requires_payment_method"),
                    "livemode": data.get("livemode", False),
                }
        except httpx.RequestError as exc:
            raise StripeServiceError("Could not reach Stripe. Retry this payment shortly.", status_code=502) from exc
    raise StripeServiceError("A valid Stripe secret key is required.", status_code=503)

def verify_stripe_webhook_signature(
    raw_payload: bytes,
    sig_header: str,
    webhook_secret: Optional[str] = None,
    tolerance_seconds: int = 300
) -> bool:
    """
    Verifies Stripe HMAC-SHA256 webhook signature following Stripe specification:
    Header: t=timestamp,v1=signature
    Signed data: timestamp.raw_payload
    """
    secret = webhook_secret or settings.STRIPE_WEBHOOK_SECRET
    if not secret:
        return False

    if not sig_header:
        return False

    # 1. Parse header components
    timestamp: Optional[int] = None
    signatures = []
    for item in sig_header.split(","):
        parts = item.strip().split("=", 1)
        if len(parts) == 2:
            key, val = parts[0], parts[1]
            if key == "t":
                try:
                    timestamp = int(val)
                except ValueError:
                    return False
            elif key == "v1":
                signatures.append(val)

    if timestamp is None or not signatures:
        return False

    # 2. Verify freshness to protect against replay attacks
    now = int(time.time())
    if abs(now - timestamp) > tolerance_seconds:
        return False

    # 3. Compute expected signature
    signed_payload = f"{timestamp}.".encode("utf-8") + raw_payload
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256
    ).hexdigest()

    # 4. Constant-time comparison
    for sig in signatures:
        if hmac.compare_digest(expected_sig, sig):
            return True

    return False

def compute_payload_hash(payload: bytes) -> str:
    """Compute SHA-256 fingerprint of raw webhook request body."""
    return hashlib.sha256(payload).hexdigest()


