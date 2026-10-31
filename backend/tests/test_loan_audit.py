from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import create_access_token
from app.models.db_models import UserModel


@pytest.fixture
def auth_headers(db_session):
    user = UserModel(
        id="user_audit_test_01",
        email="audit_user@example.com",
        full_name="Audit Tester",
        role="borrower",
        is_active=True,
    )
    db_session.merge(user)
    db_session.flush()
    token = create_access_token(user_id=user.id, email=user.email, role=user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_user_headers(db_session):
    user = UserModel(
        id="user_audit_test_02",
        email="other_user@example.com",
        full_name="Other Tester",
        role="borrower",
        is_active=True,
    )
    db_session.merge(user)
    db_session.flush()
    token = create_access_token(user_id=user.id, email=user.email, role=user.role)
    return {"Authorization": f"Bearer {token}"}


def test_list_user_loans_seeds_default_demo_portfolio(client, auth_headers):
    response = client.get("/api/loans", headers=auth_headers)
    assert response.status_code == 200
    loans = response.json()
    assert len(loans) >= 3

    lenders = [l["lender_name"] for l in loans]
    assert "HDFC Bank" in lenders
    assert "Bajaj Finserv" in lenders
    assert "KreditBee" in lenders

    # Check structure
    hdfc_loan = next(l for l in loans if l["lender_name"] == "HDFC Bank")
    assert hdfc_loan["lender_type"] == "BANK"
    assert hdfc_loan["loan_type"] == "PERSONAL"
    assert Decimal(str(hdfc_loan["interest_rate_percent"])) == Decimal("12.50")
    assert Decimal(str(hdfc_loan["outstanding_principal"])) > 0


def test_create_and_delete_user_loan(client, auth_headers):
    payload = {
        "lender_name": "Tata Capital",
        "lender_type": "NBFC",
        "loan_type": "AUTO",
        "original_principal": 150000.0,
        "outstanding_principal": 120000.0,
        "interest_rate_percent": 11.75,
        "tenure_months": 36,
        "remaining_tenure_months": 28,
        "emi_due_day": 7,
    }
    response = client.post("/api/loans", json=payload, headers=auth_headers)
    assert response.status_code == 201
    created = response.json()
    loan_id = created["id"]
    assert created["lender_name"] == "Tata Capital"
    assert Decimal(str(created["emi_amount"])) > 0
    assert created["status"] == "ACTIVE"
    assert "next_due_date" in created

    # Fetch detail
    get_res = client.get(f"/api/loans/{loan_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == loan_id

    # Delete loan
    del_res = client.delete(f"/api/loans/{loan_id}", headers=auth_headers)
    assert del_res.status_code == 200

    # Verify not found
    get_again = client.get(f"/api/loans/{loan_id}", headers=auth_headers)
    assert get_again.status_code == 404


def test_update_user_loan(client, auth_headers):
    # First ensure loans exist
    list_res = client.get("/api/loans", headers=auth_headers)
    loan_id = list_res.json()[0]["id"]

    update_payload = {
        "outstanding_principal": 15000.0,
        "status": "RESTRUCTURED",
        "notes": "Updated after partial repayment",
    }
    res = client.put(f"/api/loans/{loan_id}", json=update_payload, headers=auth_headers)
    assert res.status_code == 200
    updated = res.json()
    assert Decimal(str(updated["outstanding_principal"])) == Decimal("15000.00")
    assert updated["status"] == "RESTRUCTURED"
    assert updated["notes"] == "Updated after partial repayment"


def test_loan_audit_report_generation(client, auth_headers):
    # Request audit with monthly income ₹50,000
    audit_req = {
        "monthly_income": 50000.0,
        "extra_monthly_prepayment": 1500.0,
    }
    response = client.post("/api/loans/audit", json=audit_req, headers=auth_headers)
    assert response.status_code == 200
    report = response.json()

    assert report["total_loans_count"] >= 3
    assert report["active_loans_count"] >= 3
    assert Decimal(str(report["total_outstanding_principal"])) > 0
    assert Decimal(str(report["total_monthly_emi"])) > 0
    assert Decimal(str(report["foir_percent"])) > 0
    assert report["foir_risk_level"] in ["SAFE", "MODERATE", "HIGH_RISK", "CRITICAL"]

    # High interest loans identified
    assert report["high_interest_loans_count"] >= 2  # Bajaj 17.5% and KreditBee 24%
    assert Decimal(str(report["total_monthly_interest_leakage"])) > 0

    # Refinancing opportunities found
    assert len(report["refinancing_opportunities"]) > 0
    best_opp = report["refinancing_opportunities"][0]
    assert best_opp["catalogue_offer_lender"] is not None
    assert Decimal(str(best_opp["catalogue_offer_rate"])) <= Decimal("11.50")

    # Prepayment simulation included
    assert report["prepayment_simulation"] is not None
    assert report["prepayment_simulation"]["months_saved"] >= 0
    assert Decimal(str(report["prepayment_simulation"]["interest_saved_rupees"])) >= 0

    # Calendar items
    assert len(report["emi_calendar"]) >= 3

    # AI insights & Action plan
    assert len(report["ai_insights"]) > 0
    assert len(report["action_plan"]) > 0
    assert len(report["rbi_guideline_notes"]) > 0


def test_prepayment_simulation_endpoint(client, auth_headers):
    # Extra monthly payment of ₹2,000
    sim_req = {
        "extra_monthly_prepayment": 2000.0,
        "lump_sum_prepayment": 0.0,
    }
    res = client.post("/api/loans/simulate-prepayment", json=sim_req, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["simulation_mode"] == "EXTRA_MONTHLY"
    assert data["months_saved"] > 0
    assert Decimal(str(data["interest_saved_rupees"])) > 0
    assert "saves you" in data["advice"]

    # Lump sum payment of ₹15,000
    lump_req = {
        "extra_monthly_prepayment": 0.0,
        "lump_sum_prepayment": 15000.0,
    }
    lump_res = client.post("/api/loans/simulate-prepayment", json=lump_req, headers=auth_headers)
    assert lump_res.status_code == 200
    lump_data = lump_res.json()
    assert lump_data["simulation_mode"] == "LUMP_SUM"
    assert lump_data["months_saved"] > 0
    assert Decimal(str(lump_data["interest_saved_rupees"])) > 0


def test_refinance_opportunities_endpoint(client, auth_headers):
    res = client.get("/api/loans/refinance-opportunities", headers=auth_headers)
    assert res.status_code == 200
    opps = res.json()
    assert len(opps) >= 1
    # Check that high interest loan (e.g. KreditBee 24%) is highlighted
    rates = [Decimal(str(o["current_interest_rate"])) for o in opps]
    assert any(r >= Decimal("17.00") for r in rates)


def test_unauthenticated_fallback_access(client):
    # Unauthenticated access falls back to demo mode gracefully
    res = client.get("/api/loans")
    assert res.status_code == 200
    loans = res.json()
    assert len(loans) >= 3


def test_user_data_isolation(client, auth_headers, other_user_headers):
    # Create loan under user 1
    create_payload = {
        "lender_name": "Axis Bank",
        "lender_type": "BANK",
        "loan_type": "PERSONAL",
        "original_principal": 200000.0,
        "interest_rate_percent": 13.0,
        "tenure_months": 24,
    }
    res1 = client.post("/api/loans", json=create_payload, headers=auth_headers)
    assert res1.status_code == 201
    user1_loan_id = res1.json()["id"]

    # User 2 attempts to view user 1's loan
    res2 = client.get(f"/api/loans/{user1_loan_id}", headers=other_user_headers)
    assert res2.status_code == 404

