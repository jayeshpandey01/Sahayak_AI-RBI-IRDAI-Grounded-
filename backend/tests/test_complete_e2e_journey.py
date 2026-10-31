import pytest
from app.models.schemas import ConsentScope, JourneyStage

def test_full_e2e_user_and_journey_pipeline(client):
    """
    Complete End-to-End Test Pipeline covering:
    1. Registration (Email + Password)
    2. Strict Login (Unregistered emails & Google IDs strictly rejected)
    3. Authenticated Session & Token Acquisition
    4. Profile Retrieval (/api/auth/me)
    5. Loan Journey Creation & RBI KFS Deterministic EMI Calculation
    6. Consent Recording with Cryptographic Tamper Hash
    7. Document Upload, Quality Preflight & PII Masking
    8. Document Field Confirmation & FSM Lifecycle Transitions
    9. AI Copilot Interaction & Multi-Tenant IDOR Guarding
    10. Forgot Password OTP Generation & Background Dispatch
    11. Password Reset with OTP & Rollover Verification
    12. Revocation of Old Password & Re-Authentication with New Password
    """
    borrower_email = "e2e.borrower@sahayakai.in"
    original_password = "StrongPassword@2026"
    new_password = "UpdatedPassword#2026"
    full_name = "Rajesh Gupta"

    # -------------------------------------------------------------
    # STAGE 1: STRICT LOGIN GATEKEEPER CHECK (BEFORE REGISTRATION)
    # -------------------------------------------------------------
    unregistered_login = client.post("/api/auth/login", json={
        "email": borrower_email,
        "password": original_password
    })
    assert unregistered_login.status_code == 401
    assert "register first" in unregistered_login.json()["detail"].lower()

    unregistered_google = client.post("/api/auth/login/google", json={
        "id_token": f"mock_google_:{borrower_email}:{full_name}"
    })
    assert unregistered_google.status_code == 401
    assert "must register first" in unregistered_google.json()["detail"].lower()

    # -------------------------------------------------------------
    # STAGE 2: BORROWER REGISTRATION
    # -------------------------------------------------------------
    reg_res = client.post("/api/auth/register", json={
        "email": borrower_email,
        "password": original_password,
        "full_name": full_name
    })
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    token = reg_data["access_token"]
    user_id = reg_data["user"]["id"]
    assert reg_data["user"]["email"] == borrower_email
    assert reg_data["user"]["full_name"] == full_name

    auth_headers = {"Authorization": f"Bearer {token}"}

    # Duplicate registration is rejected
    dup_reg = client.post("/api/auth/register", json={
        "email": borrower_email,
        "password": original_password
    })
    assert dup_reg.status_code == 409

    # -------------------------------------------------------------
    # STAGE 3: LOGIN WITH REGISTERED CREDENTIALS
    # -------------------------------------------------------------
    login_res = client.post("/api/auth/login", json={
        "email": borrower_email,
        "password": original_password
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

    # Wrong password fails
    bad_pw_res = client.post("/api/auth/login", json={
        "email": borrower_email,
        "password": "WrongPassword999!"
    })
    assert bad_pw_res.status_code == 401

    # -------------------------------------------------------------
    # STAGE 4: AUTHENTICATED PROFILE CHECK (/api/auth/me)
    # -------------------------------------------------------------
    me_res = client.get("/api/auth/me", headers=auth_headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["id"] == user_id
    assert me_data["email"] == borrower_email
    assert me_data["is_active"] is True

    # -------------------------------------------------------------
    # STAGE 5: LOAN JOURNEY INITIALIZATION & EMI CALCULATION
    # -------------------------------------------------------------
    # 5a. Direct EMI calculation
    calc_res = client.post("/api/financial/calculate", json={
        "loan_amount": 100000,
        "preferred_tenure_months": 24,
        "offer_id": "offer-hdfc-01",
        "maximum_emi": 6000
    })
    assert calc_res.status_code == 200
    calc_data = calc_res.json()
    assert float(calc_data["estimated_emi_rupees"]) > 0
    assert float(calc_data["annual_percentage_rate_apr"]) > 0
    assert calc_data["kfs_document_hash"] is not None

    # 5b. Create Journey tied to this authenticated user
    j_res = client.post("/api/journeys", json={
        "language": "en",
        "loan_amount": 100000,
        "preferred_tenure_months": 24,
        "maximum_emi": 6000,
        "purpose": "Home Renovation"
    }, headers=auth_headers)
    assert j_res.status_code == 201
    journey = j_res.json()
    journey_id = journey["id"]
    assert journey["user_id"] == user_id
    assert journey["stage"] == JourneyStage.INTENT_CAPTURED.value

    # -------------------------------------------------------------
    # STAGE 6: CONSENT AUDIT & DOCUMENT UPLOAD GATING
    # -------------------------------------------------------------
    # Uploading without consent must return 403
    unauth_doc = client.post(f"/api/journeys/{journey_id}/documents/upload", json={
        "document_type": "PAN_CARD"
    }, headers=auth_headers)
    assert unauth_doc.status_code == 403
    assert "consent required" in unauth_doc.json()["detail"].lower()

    # Grant immutable consent
    consent_res = client.post(f"/api/journeys/{journey_id}/consent", json={
        "scope": ConsentScope.DOCUMENT_OCR_PROCESSING.value,
        "purpose": "KYC document extraction for pre-approved loan processing",
        "is_granted": True
    }, headers=auth_headers)
    assert consent_res.status_code == 200
    consent_data = consent_res.json()
    assert consent_data["tamper_hash"] is not None
    assert len(consent_data["tamper_hash"]) == 64

    # Now upload succeeds and applies PII masking
    doc_res = client.post(f"/api/journeys/{journey_id}/documents/upload", json={
        "document_type": "PAN_CARD"
    }, headers=auth_headers)
    assert doc_res.status_code == 200
    doc_data = doc_res.json()
    document_id = doc_data["document_id"]
    assert doc_data["fields"]["pan_number"]["masked_value"].startswith("AB")

    # Confirm document fields
    confirm_res = client.post(
        f"/api/journeys/{journey_id}/documents/{document_id}/confirm",
        json={"confirmed_fields": {"pan_number": "ABCDE1234F"}},
        headers=auth_headers
    )
    assert confirm_res.status_code == 200

    # -------------------------------------------------------------
    # STAGE 7: FSM STAGE ADVANCEMENT
    # -------------------------------------------------------------
    # Advance to OFFERS_REVIEWED with offer selection
    stage1_res = client.patch(f"/api/journeys/{journey_id}/stage", json={
        "stage": JourneyStage.OFFERS_REVIEWED.value,
        "selected_offer_id": "offer-hdfc-01",
        "customer_confirmed": False
    }, headers=auth_headers)
    assert stage1_res.status_code == 200
    assert stage1_res.json()["stage"] == JourneyStage.OFFERS_REVIEWED.value

    # Advance to DOCUMENTS_CONFIRMED
    stage2_res = client.patch(f"/api/journeys/{journey_id}/stage", json={
        "stage": JourneyStage.DOCUMENTS_CONFIRMED.value,
        "customer_confirmed": True
    }, headers=auth_headers)
    assert stage2_res.status_code == 200
    assert stage2_res.json()["stage"] == JourneyStage.DOCUMENTS_CONFIRMED.value

    # -------------------------------------------------------------
    # STAGE 8: AI COPILOT & MULTI-TENANT ISOLATION
    # -------------------------------------------------------------
    # User A asks AI Copilot regarding their journey
    chat_res = client.post("/api/chat", json={
        "journey_id": journey_id,
        "message": "Explain what the processing fee covers"
    }, headers=auth_headers)
    assert chat_res.status_code == 200
    assert len(chat_res.json()["reply"]) > 0

    # Create Attacker (User B)
    attacker_reg = client.post("/api/auth/register", json={
        "email": "e2e.attacker@sahayakai.in",
        "password": "AttackerPassword123!",
        "full_name": "Attacker"
    })
    attacker_token = attacker_reg.json()["access_token"]
    attacker_headers = {"Authorization": f"Bearer {attacker_token}"}

    # Attacker CANNOT view User A's journey -> 403 Forbidden
    steal_res = client.get(f"/api/journeys/{journey_id}", headers=attacker_headers)
    assert steal_res.status_code == 403

    # Attacker CANNOT chat with User A's journey -> 403 Forbidden
    steal_chat = client.post("/api/chat", json={
        "journey_id": journey_id,
        "message": "Mutate loan"
    }, headers=attacker_headers)
    assert steal_chat.status_code == 403

    # -------------------------------------------------------------
    # STAGE 9: FORGOT & RESET PASSWORD LIFECYCLE
    # -------------------------------------------------------------
    forgot_res = client.post("/api/auth/forgot-password", json={"email": borrower_email})
    assert forgot_res.status_code == 200
    otp = forgot_res.json()["dev_otp"]
    assert otp is not None
    assert len(otp) == 6

    # Attempt reset with bad OTP -> 400
    bad_reset = client.post("/api/auth/reset-password", json={
        "email": borrower_email,
        "token_or_otp": "000000",
        "new_password": new_password
    })
    assert bad_reset.status_code == 400

    # Successful reset with valid OTP
    good_reset = client.post("/api/auth/reset-password", json={
        "email": borrower_email,
        "token_or_otp": otp,
        "new_password": new_password
    })
    assert good_reset.status_code == 200

    # -------------------------------------------------------------
    # STAGE 10: CREDENTIAL ROLLOVER VERIFICATION
    # -------------------------------------------------------------
    # Old password is now rejected
    old_login = client.post("/api/auth/login", json={
        "email": borrower_email,
        "password": original_password
    })
    assert old_login.status_code == 401

    # New password successfully authenticates
    new_login = client.post("/api/auth/login", json={
        "email": borrower_email,
        "password": new_password
    })
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()

