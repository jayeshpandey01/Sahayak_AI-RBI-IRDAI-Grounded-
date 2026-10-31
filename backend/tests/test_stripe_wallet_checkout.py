import hashlib
import hmac
import json
import time
from uuid import uuid4

from app.config import settings


def _new_user(client):
    response = client.post("/api/auth/register", json={
        "email": f"stripe.wallet.{uuid4().hex[:10]}@example.test",
        "password": "StrongPassword123!",
        "full_name": "Stripe Wallet Tester",
    })
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_wallet_checkout_requires_login(client):
    response = client.post("/api/v1/wallet/payment-orders", json={
        "amount_rupees": 250,
        "currency": "inr",
        "purpose": "wallet_topup",
    })
    assert response.status_code == 401


def test_stripe_checkout_webhook_credits_wallet_once(client, monkeypatch):
    from app.services import payment_service

    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_unit_test")
    monkeypatch.setattr(settings, "STRIPE_PUBLISHABLE_KEY", "pk_test_unit_test")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_unit_test_secret")
    monkeypatch.setattr(
        payment_service,
        "create_stripe_checkout_session",
        lambda **kwargs: {"id": "cs_test_unit", "url": "https://checkout.stripe.test/session"},
    )
    headers = _new_user(client)

    response = client.post(
        "/api/v1/wallet/payment-orders",
        json={"amount_rupees": 250, "currency": "inr", "purpose": "wallet_topup"},
        headers={**headers, "X-Idempotency-Key": f"wallet-{uuid4().hex}"},
    )
    assert response.status_code == 201
    order = response.json()
    assert order["provider"] == "stripe"
    assert order["checkout_url"] == "https://checkout.stripe.test/session"
    assert order["status"] == "REQUIRES_ACTION"

    payload = json.dumps({
        "id": f"evt_{uuid4().hex}",
        "type": "checkout.session.completed",
        "data": {"object": {
            "object": "checkout.session",
            "id": "cs_test_unit",
            "client_reference_id": order["order_id"],
            "metadata": {"order_id": order["order_id"], "user_id": order["user_id"]},
            "payment_intent": "pi_test_unit",
            "payment_status": "paid",
            "amount_total": 25000,
            "currency": "inr",
        }},
    }).encode()
    timestamp = int(time.time())
    digest = hmac.new(
        b"whsec_unit_test_secret", f"{timestamp}.".encode() + payload, hashlib.sha256,
    ).hexdigest()
    webhook_headers = {"stripe-signature": f"t={timestamp},v1={digest}"}

    first = client.post("/api/v1/webhooks/stripe", content=payload, headers=webhook_headers)
    second = client.post("/api/v1/webhooks/stripe", content=payload, headers=webhook_headers)
    assert first.status_code == second.status_code == 200
    assert client.get(f"/api/v1/wallet/payment-orders/{order['order_id']}", headers=headers).json()["status"] == "SUCCEEDED"
    balance = client.get("/api/v1/wallet/balance", headers=headers)
    assert balance.status_code == 200
    assert balance.json()["balance_paise"] == 25000
    assert len(balance.json()["ledger_entries"]) == 1
    history = client.get("/api/v1/wallet/payment-orders", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["order_id"] == order["order_id"]
    assert history.json()[0]["status"] == "SUCCEEDED"
    assert "client_secret" not in history.json()[0]
    assert "checkout_url" not in history.json()[0]
