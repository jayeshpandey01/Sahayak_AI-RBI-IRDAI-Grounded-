import hmac
import hashlib
import time
import json
from uuid import uuid4
import pytest
from app.config import settings
from app.models.db_models import UserModel
from app.services.auth_service import create_access_token


@pytest.fixture(autouse=True)
def authenticate_payment_order_tests(client, monkeypatch):
    """Payment-order behavior is exercised as an authenticated account by default."""
    response = client.post("/api/auth/register", json={
        "email": f"payment_test_{uuid4().hex[:10]}@example.com",
        "password": "Password123!",
        "full_name": "Payment Test User",
    })
    assert response.status_code == 201
    client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})
    monkeypatch.setattr(
        "app.services.payment_service.create_stripe_payment_intent",
        lambda **kwargs: {
            "id": f"pi_test_{uuid4().hex[:16]}",
            "client_secret": f"pi_test_{uuid4().hex[:16]}_secret_fixture",
            "status": "requires_payment_method",
            "livemode": False,
        },
    )

def test_create_payment_order_success(client):
    idem_key = f"idem_test_{uuid4().hex[:12]}"
    res = client.post(
        "/api/v1/payment-orders",
        json={
            "amount_rupees": 5000.0,
            "purpose": "wallet_topup",
            "currency": "inr",
        },
        headers={"X-Idempotency-Key": idem_key}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["order_id"].startswith("po_")
    assert data["status"] == "REQUIRES_ACTION"
    assert data["purpose"] == "wallet_topup"
    assert float(data["amount_rupees"]) == 5000.0
    assert data["amount_paise"] == 500000
    assert data["currency"] == "inr"
    assert "client_secret" in data
    assert "stripe_payment_intent_id" in data


def test_wallet_payment_history_is_owner_scoped_and_secret_free(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.payment_service.create_stripe_checkout_session",
        lambda **kwargs: {"id": "cs_test_history", "url": "https://checkout.example/test"},
    )
    created = client.post("/api/v1/wallet/payment-orders", json={
        "amount_rupees": 250,
        "purpose": "wallet_topup",
        "currency": "inr",
    })
    assert created.status_code == 201

    history = client.get("/api/v1/wallet/payment-orders")
    assert history.status_code == 200
    assert len(history.json()) == 1
    item = history.json()[0]
    assert item["order_id"] == created.json()["order_id"]
    assert item["status"] == "REQUIRES_ACTION"
    assert item["amount_rupees"] == "250"
    assert "client_secret" not in item
    assert "checkout_url" not in item

    other = client.post("/api/auth/register", json={
        "email": f"other_history_{uuid4().hex[:8]}@example.com",
        "password": "Password123!",
        "full_name": "Other User",
    }).json()
    other_history = client.get(
        "/api/v1/wallet/payment-orders",
        headers={"Authorization": f"Bearer {other['access_token']}"},
    )
    assert other_history.status_code == 200
    assert other_history.json() == []

def test_idempotent_order_creation_replay(client):
    idem_key = f"idem_replay_{uuid4().hex[:12]}"
    payload = {
        "amount_rupees": 1500.0,
        "purpose": "wallet_topup",
        "currency": "inr",
    }
    # 1. First attempt
    res1 = client.post("/api/v1/payment-orders", json=payload, headers={"X-Idempotency-Key": idem_key})
    assert res1.status_code == 201
    order1 = res1.json()

    # 2. Second attempt with exact same key & payload
    res2 = client.post("/api/v1/payment-orders", json=payload, headers={"X-Idempotency-Key": idem_key})
    assert res2.status_code == 201
    order2 = res2.json()

    # Must return identical order
    assert order1["order_id"] == order2["order_id"]
    assert order1["stripe_payment_intent_id"] == order2["stripe_payment_intent_id"]

def test_idempotent_order_creation_conflict(client):
    idem_key = f"idem_conflict_{uuid4().hex[:12]}"
    # 1. First attempt with 1000 rupees
    res1 = client.post(
        "/api/v1/payment-orders",
        json={"amount_rupees": 1000.0, "purpose": "wallet_topup"},
        headers={"X-Idempotency-Key": idem_key}
    )
    assert res1.status_code == 201

    # 2. Second attempt with same key but differing amount
    res2 = client.post(
        "/api/v1/payment-orders",
        json={"amount_rupees": 2000.0, "purpose": "wallet_topup"},
        headers={"X-Idempotency-Key": idem_key}
    )
    assert res2.status_code == 409
    assert "idempotency key reused" in res2.json()["detail"].lower()

def test_payment_order_amount_bounds(client):
    # Zero amount rejected
    res1 = client.post("/api/v1/payment-orders", json={"amount_rupees": 0})
    assert res1.status_code == 422

    # Negative amount rejected
    res2 = client.post("/api/v1/payment-orders", json={"amount_rupees": -500})
    assert res2.status_code == 422

    # Excess amount beyond 50 lakhs ceiling rejected
    res3 = client.post("/api/v1/payment-orders", json={"amount_rupees": 6000000})
    assert res3.status_code == 422

def test_get_payment_order_canonical_status(client):
    # 1. Create order
    res = client.post(
        "/api/v1/payment-orders",
        json={"amount_rupees": 2500.0, "purpose": "wallet_topup"}
    )
    assert res.status_code == 201
    order_id = res.json()["order_id"]

    # 2. Fetch canonical status
    get_res = client.get(f"/api/v1/payment-orders/{order_id}")
    assert get_res.status_code == 200
    assert get_res.json()["order_id"] == order_id
    assert get_res.json()["status"] == "REQUIRES_ACTION"

def test_get_nonexistent_payment_order_404(client):
    res = client.get("/api/v1/payment-orders/po_nonexistent_999")
    assert res.status_code == 404

def test_multi_tenant_isolation_payment_order(client):
    # 1. Register User A
    user_a_email = f"user_a_{uuid4().hex[:8]}@example.com"
    reg_a = client.post("/api/auth/register", json={
        "email": user_a_email,
        "password": "Password123!",
        "full_name": "User A"
    })
    token_a = reg_a.json()["access_token"]

    # 2. Register User B
    user_b_email = f"user_b_{uuid4().hex[:8]}@example.com"
    reg_b = client.post("/api/auth/register", json={
        "email": user_b_email,
        "password": "Password123!",
        "full_name": "User B"
    })
    token_b = reg_b.json()["access_token"]

    # 3. User A creates order
    res_a = client.post(
        "/api/v1/payment-orders",
        json={"amount_rupees": 1000.0, "purpose": "wallet_topup"},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res_a.status_code == 201
    order_id = res_a.json()["order_id"]

    # 4. User B attempts to read User A's order -> 403 Forbidden
    res_b = client.get(
        f"/api/v1/payment-orders/{order_id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res_b.status_code == 403
    assert "forbidden" in res_b.json()["detail"].lower()

def test_stripe_webhook_succeeded_state_transition(client, monkeypatch):
    # Configure test webhook secret
    test_whsec = "whsec_test_secret_for_pytest_123"
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", test_whsec)

    # 1. Create order
    res = client.post(
        "/api/v1/payment-orders",
        json={"amount_rupees": 750.0, "purpose": "wallet_topup"}
    )
    assert res.status_code == 201
    order = res.json()
    intent_id = order["stripe_payment_intent_id"]

    # 2. Construct signed Stripe event payload
    event_id = f"evt_test_{uuid4().hex[:12]}"
    event_payload = json.dumps({
        "id": event_id,
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": intent_id,
                "amount": 75000,
                "currency": "inr",
                "status": "succeeded"
            }
        }
    }).encode("utf-8")

    timestamp = int(time.time())
    sig = hmac.new(
        test_whsec.encode("utf-8"),
        f"{timestamp}.".encode("utf-8") + event_payload,
        hashlib.sha256
    ).hexdigest()
    sig_header = f"t={timestamp},v1={sig}"

    # 3. Post webhook
    wh_res = client.post(
        "/api/v1/webhooks/stripe",
        content=event_payload,
        headers={"stripe-signature": sig_header, "Content-Type": "application/json"}
    )
    assert wh_res.status_code == 200
    assert wh_res.json()["received"] is True

    # 4. Verify order state transitioned to SUCCEEDED
    get_res = client.get(f"/api/v1/payment-orders/{order['order_id']}")
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "SUCCEEDED"

def test_stripe_webhook_deduplication(client, monkeypatch):
    test_whsec = "whsec_test_secret_for_dedupe_456"
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", test_whsec)

    # Create order
    res = client.post("/api/v1/payment-orders", json={"amount_rupees": 500.0})
    order = res.json()
    intent_id = order["stripe_payment_intent_id"]

    event_id = f"evt_dedupe_{uuid4().hex[:12]}"
    event_payload = json.dumps({
        "id": event_id,
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": intent_id, "amount": 50000, "currency": "inr"}}
    }).encode("utf-8")

    timestamp = int(time.time())
    sig = hmac.new(
        test_whsec.encode("utf-8"),
        f"{timestamp}.".encode("utf-8") + event_payload,
        hashlib.sha256
    ).hexdigest()
    sig_header = f"t={timestamp},v1={sig}"

    # Deliver 1st time
    res1 = client.post(
        "/api/v1/webhooks/stripe",
        content=event_payload,
        headers={"stripe-signature": sig_header}
    )
    assert res1.status_code == 200

    # Deliver 2nd time (duplicate replay)
    res2 = client.post(
        "/api/v1/webhooks/stripe",
        content=event_payload,
        headers={"stripe-signature": sig_header}
    )
    assert res2.status_code == 200
    assert res2.json()["received"] is True

def test_stripe_webhook_invalid_signature_rejected(client, monkeypatch):
    test_whsec = "whsec_strict_signature_789"
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", test_whsec)

    payload = json.dumps({"id": "evt_fake", "type": "payment_intent.succeeded"}).encode("utf-8")
    fake_header = "t=1234567890,v1=invalid_tampered_signature"

    res = client.post(
        "/api/v1/webhooks/stripe",
        content=payload,
        headers={"stripe-signature": fake_header}
    )
    assert res.status_code == 400
    assert "signature" in res.json()["detail"].lower()

def test_create_payment_order_server_derived_processing_fee(client):
    # 1. Create a loan journey
    j_res = client.post(
        "/api/journeys",
        json={
            "loan_amount": 200000.0,
            "preferred_tenure_months": 24,
            "purpose": "Home Improvement",
            "language": "en"
        }
    )
    assert j_res.status_code == 201
    journey_id = j_res.json()["id"]

    # 2. Select an offer
    client.patch(
        f"/api/journeys/{journey_id}",
        json={"stage": "OFFERS_REVIEWED", "selected_offer_id": "offer-hdfc-01"}
    )

    # 3. Create payment order for processing fee without client-specified amount
    order_res = client.post(
        "/api/v1/payment-orders",
        json={
            "purpose": "processing_fee",
            "reference_id": journey_id,
            "currency": "inr"
        }
    )
    assert order_res.status_code == 422
    assert "wallet top-ups only" in order_res.json()["detail"]

def test_create_payment_order_server_derived_emi_repayment(client):
    # 1. Create loan journey
    j_res = client.post(
        "/api/journeys",
        json={
            "loan_amount": 100000.0,
            "preferred_tenure_months": 12,
            "purpose": "Emergency Funds"
        }
    )
    journey_id = j_res.json()["id"]

    # 2. Select offer
    client.patch(
        f"/api/journeys/{journey_id}",
        json={"stage": "OFFERS_REVIEWED", "selected_offer_id": "offer-sbi-02"}
    )

    # 3. Create EMI payment order
    order_res = client.post(
        "/api/v1/payment-orders",
        json={
            "purpose": "emi_repayment",
            "reference_id": journey_id
        }
    )
    assert order_res.status_code == 422
    assert "lender" in order_res.json()["detail"]

def test_stripe_webhook_out_of_order_failure_does_not_downgrade_succeeded(client, monkeypatch):
    test_whsec = "whsec_ooo_guard_secret"
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", test_whsec)

    # 1. Create order
    res = client.post("/api/v1/payment-orders", json={"amount_rupees": 1200.0})
    order = res.json()
    intent_id = order["stripe_payment_intent_id"]

    # 2. Succeeded webhook arrives first
    succ_payload = json.dumps({
        "id": f"evt_succ_{uuid4().hex[:12]}",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": intent_id, "amount": 120000, "currency": "inr"}}
    }).encode("utf-8")
    ts1 = int(time.time())
    sig1 = hmac.new(test_whsec.encode("utf-8"), f"{ts1}.".encode("utf-8") + succ_payload, hashlib.sha256).hexdigest()
    client.post("/api/v1/webhooks/stripe", content=succ_payload, headers={"stripe-signature": f"t={ts1},v1={sig1}"})

    order_after_succ = client.get(f"/api/v1/payment-orders/{order['order_id']}").json()
    assert order_after_succ["status"] == "SUCCEEDED"

    # 3. Out-of-order delayed failure webhook arrives later
    fail_payload = json.dumps({
        "id": f"evt_fail_{uuid4().hex[:12]}",
        "type": "payment_intent.payment_failed",
        "data": {"object": {"id": intent_id, "amount": 120000, "currency": "inr"}}
    }).encode("utf-8")
    ts2 = int(time.time())
    sig2 = hmac.new(test_whsec.encode("utf-8"), f"{ts2}.".encode("utf-8") + fail_payload, hashlib.sha256).hexdigest()
    res_delayed = client.post("/api/v1/webhooks/stripe", content=fail_payload, headers={"stripe-signature": f"t={ts2},v1={sig2}"})
    assert res_delayed.status_code == 200

    # 4. Status must REMAIN SUCCEEDED (no degradation)
    order_after_fail = client.get(f"/api/v1/payment-orders/{order['order_id']}").json()
    assert order_after_fail["status"] == "SUCCEEDED"

def test_stripe_webhook_amount_mismatch_quarantines_to_reconciliation(client, monkeypatch):
    test_whsec = "whsec_mismatch_secret"
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", test_whsec)

    # 1. Create order for ₹1,000 (100,000 paise)
    res = client.post("/api/v1/payment-orders", json={"amount_rupees": 1000.0})
    order = res.json()
    intent_id = order["stripe_payment_intent_id"]

    # 2. Tampered webhook arrives with only ₹10 (1,000 paise)
    mismatch_payload = json.dumps({
        "id": f"evt_mismatch_{uuid4().hex[:12]}",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": intent_id, "amount": 1000, "currency": "inr"}}
    }).encode("utf-8")
    ts = int(time.time())
    sig = hmac.new(test_whsec.encode("utf-8"), f"{ts}.".encode("utf-8") + mismatch_payload, hashlib.sha256).hexdigest()
    client.post("/api/v1/webhooks/stripe", content=mismatch_payload, headers={"stripe-signature": f"t={ts},v1={sig}"})

    # 3. Status must transition to RECONCILIATION_REQUIRED, NOT SUCCEEDED!
    order_checked = client.get(f"/api/v1/payment-orders/{order['order_id']}").json()
    assert order_checked["status"] == "RECONCILIATION_REQUIRED"

def test_reconciliation_sweeper_endpoint(client, db_session):
    admin_id = f"admin_{uuid4().hex[:8]}"
    admin_user = UserModel(
        id=admin_id,
        email=f"{admin_id}@sahayak.ai",
        full_name="Admin Ops",
        role="admin",
        is_active=True
    )
    db_session.add(admin_user)
    db_session.commit()
    admin_token = create_access_token(user_id=admin_id, email=admin_user.email, role="admin")

    res = client.post(
        "/api/v1/payments/reconcile?older_than_minutes=0&limit=50",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "reconciled_count" in data
    assert "orders_checked" in data
    assert isinstance(data["details"], list)

def test_wallet_topup_credits_ledger_and_reflects_in_balance(client, monkeypatch):
    """Verify that a successful wallet topup writes a ledger entry and updates balance."""
    test_whsec = "whsec_wallet_topup_test_secret"
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", test_whsec)

    # 1. Register a new user
    user_email = f"wallet.user.{uuid4().hex[:8]}@sahayakai.in"
    reg_res = client.post("/api/auth/register", json={
        "email": user_email,
        "password": "StrongPassword123!",
        "full_name": "Wallet Tester"
    })
    assert reg_res.status_code == 201
    user_token = reg_res.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 2. Check initial wallet balance is 0
    bal_res1 = client.get("/api/v1/wallet/balance", headers=user_headers)
    assert bal_res1.status_code == 200
    assert bal_res1.json()["balance_paise"] == 0
    assert bal_res1.json()["ledger_entries"] == []

    # 3. Create a wallet top-up order for ₹2,500
    order_res = client.post(
        "/api/v1/payment-orders",
        json={"amount_rupees": 2500.0, "purpose": "wallet_topup", "currency": "inr"},
        headers=user_headers
    )
    assert order_res.status_code == 201
    order_data = order_res.json()
    intent_id = order_data["stripe_payment_intent_id"]

    # 4. Webhook arrives indicating payment succeeded
    event_payload = json.dumps({
        "id": f"evt_wallet_{uuid4().hex[:12]}",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": intent_id,
                "amount": 250000,
                "currency": "inr",
                "status": "succeeded"
            }
        }
    }).encode("utf-8")
    ts = int(time.time())
    sig = hmac.new(test_whsec.encode("utf-8"), f"{ts}.".encode("utf-8") + event_payload, hashlib.sha256).hexdigest()

    wh_res = client.post(
        "/api/v1/webhooks/stripe",
        content=event_payload,
        headers={"stripe-signature": f"t={ts},v1={sig}", "Content-Type": "application/json"}
    )
    assert wh_res.status_code == 200

    # 5. Check wallet balance now reflects ₹2,500 (250,000 paise)
    bal_res2 = client.get("/api/v1/wallet/balance", headers=user_headers)
    assert bal_res2.status_code == 200
    bal_data = bal_res2.json()
    assert bal_data["balance_paise"] == 250000
    assert len(bal_data["ledger_entries"]) == 1
    assert bal_data["ledger_entries"][0]["amount_paise"] == 250000
    assert bal_data["ledger_entries"][0]["payment_order_id"] == order_data["order_id"]

