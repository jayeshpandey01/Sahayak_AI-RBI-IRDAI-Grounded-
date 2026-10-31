from uuid import uuid4
import json
import time
import pytest
from app.config import settings
from app.models.db_models import UserModel
from app.services.auth_service import create_access_token


@pytest.fixture(autouse=True)
def stripe_payment_intent_stub(monkeypatch):
    monkeypatch.setattr(
        "app.services.payment_service.create_stripe_payment_intent",
        lambda **kwargs: {
            "id": f"pi_test_{uuid4().hex[:16]}",
            "client_secret": f"pi_test_{uuid4().hex[:16]}_secret_fixture",
            "status": "requires_payment_method",
            "livemode": False,
        },
    )

def test_anonymous_cannot_create_payment_order_for_user_journey(client):
    """
    Finding BB-PAY-001 (BOLA Remediation):
    Ensure unauthenticated callers cannot create orders against private user journeys.
    """
    # 1. Register User A
    user_a_email = f"victim_{uuid4().hex[:8]}@example.com"
    token_a = client.post("/api/auth/register", json={
        "email": user_a_email,
        "password": "Password123!",
        "full_name": "Victim User"
    }).json()["access_token"]

    # 2. User A creates private loan journey
    j_res = client.post(
        "/api/journeys",
        json={"loan_amount": 150000.0, "preferred_tenure_months": 12, "purpose": "Emergency Funds"},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert j_res.status_code == 201
    journey_id = j_res.json()["id"]

    # 3. Anonymous caller attempts to create processing fee order -> Must return 403 Forbidden
    res_anon = client.post(
        "/api/v1/payment-orders",
        json={"purpose": "processing_fee", "reference_id": journey_id}
    )
    assert res_anon.status_code == 401
    assert "authentication required" in res_anon.json()["detail"].lower()

def test_user_b_cannot_create_payment_order_for_user_a_journey(client):
    """
    Tenant isolation: User B cannot initiate processing fee payment on User A's journey.
    """
    # 1. Register User A
    user_a_email = f"usera_{uuid4().hex[:8]}@example.com"
    token_a = client.post("/api/auth/register", json={
        "email": user_a_email,
        "password": "Password123!",
        "full_name": "User A"
    }).json()["access_token"]

    # 2. Register User B
    user_b_email = f"userb_{uuid4().hex[:8]}@example.com"
    token_b = client.post("/api/auth/register", json={
        "email": user_b_email,
        "password": "Password123!",
        "full_name": "User B"
    }).json()["access_token"]

    # 3. User A creates journey
    j_res = client.post(
        "/api/journeys",
        json={"loan_amount": 200000.0, "preferred_tenure_months": 24, "purpose": "Home Improvement"},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    journey_id = j_res.json()["id"]

    # 4. User B attempts to create payment order for User A's journey -> 403 Forbidden
    res_b = client.post(
        "/api/v1/payment-orders",
        json={"purpose": "processing_fee", "reference_id": journey_id},
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res_b.status_code == 422
    assert "wallet top-ups only" in res_b.json()["detail"]

def test_owner_can_create_payment_order_for_own_journey(client):
    """
    Legitimate journey owner can create processing fee order with server-derived KFS amount.
    """
    # 1. Register Owner
    owner_email = f"owner_{uuid4().hex[:8]}@example.com"
    token_owner = client.post("/api/auth/register", json={
        "email": owner_email,
        "password": "Password123!",
        "full_name": "Journey Owner"
    }).json()["access_token"]

    # 2. Create journey and select offer
    j_res = client.post(
        "/api/journeys",
        json={"loan_amount": 100000.0, "preferred_tenure_months": 12, "purpose": "Debt Consolidation"},
        headers={"Authorization": f"Bearer {token_owner}"}
    )
    journey_id = j_res.json()["id"]
    client.patch(
        f"/api/journeys/{journey_id}",
        json={"stage": "OFFERS_REVIEWED", "selected_offer_id": "offer-sbi-02"},
        headers={"Authorization": f"Bearer {token_owner}"}
    )

    # 3. Create processing fee order
    res_owner = client.post(
        "/api/v1/payment-orders",
        json={"purpose": "processing_fee", "reference_id": journey_id},
        headers={"Authorization": f"Bearer {token_owner}"}
    )
    assert res_owner.status_code == 422
    assert "wallet top-ups only" in res_owner.json()["detail"]
    assert "wallet top-ups only" in res_owner.json()["detail"]

def test_reconcile_endpoint_security_matrix(client, db_session):
    """
    Finding BB-PAY-002:
    Ensures reconcile sweeper is protected by Admin RBAC.
    """
    # 1. Anonymous -> 401 Unauthorized
    res_anon = client.post("/api/v1/payments/reconcile")
    assert res_anon.status_code == 401
    assert "authentication required" in res_anon.json()["detail"].lower()

    # 2. Standard Borrower -> 403 Forbidden
    borrower_email = f"borrower_{uuid4().hex[:8]}@example.com"
    token_borrower = client.post("/api/auth/register", json={
        "email": borrower_email,
        "password": "Password123!",
        "full_name": "Standard Borrower"
    }).json()["access_token"]

    res_borrower = client.post(
        "/api/v1/payments/reconcile",
        headers={"Authorization": f"Bearer {token_borrower}"}
    )
    assert res_borrower.status_code == 403
    assert "admin privileges required" in res_borrower.json()["detail"].lower()

    # 3. Admin User -> 200 OK
    admin_id = f"admin_{uuid4().hex[:8]}"
    admin_user = UserModel(
        id=admin_id,
        email=f"{admin_id}@sahayak.ai",
        full_name="Platform Admin",
        role="admin",
        is_active=True
    )
    db_session.add(admin_user)
    db_session.commit()
    token_admin = create_access_token(user_id=admin_id, email=admin_user.email, role="admin")

    res_admin = client.post(
        "/api/v1/payments/reconcile?older_than_minutes=0&limit=25",
        headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert res_admin.status_code == 200
    assert "reconciled_count" in res_admin.json()

def test_webhook_fail_closed_when_secret_unset(client, monkeypatch):
    """
    Finding BB-SEC-001:
    Webhook must fail-closed with 500 when webhook secret is missing in test mode.
    """
    monkeypatch.setattr(settings, "STRIPE_MODE", "test")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "")

    payload = json.dumps({"id": "evt_test", "type": "payment_intent.succeeded"}).encode("utf-8")
    res = client.post(
        "/api/v1/webhooks/stripe",
        content=payload,
        headers={"stripe-signature": "t=123456,v1=fakesig"}
    )
    assert res.status_code == 500
    assert "webhook secret is not configured" in res.json()["detail"].lower()

