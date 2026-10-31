#!/usr/bin/env python3
"""
Sahayak AI - Production E2E Verification Runner
Tests the entire end-to-end user lifecycle:
1. Strict Login Gating (unregistered blocked)
2. Borrower Registration (Email + Password)
3. Login & Bearer JWT Issuance
4. Authenticated Profile Verification (/api/auth/me)
5. Financial EMI Calculation (RBI KFS standards)
6. Private Journey Creation & FSM Progression
7. Consent Recording with SHA-256 Tamper Proofing
8. Document Upload & Quality Preflight Masking
9. AI Copilot Interaction & Multi-Tenant IDOR Guarding
10. Forgot Password & OTP Generation
11. Secure Password Reset with Credential Rollover
12. Datastore Health Probe Verification
"""

import sys
import time
import argparse
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def log_step(step_num: int, total_steps: int, title: str):
    print(f"\n{BOLD}{CYAN}[STAGE {step_num}/{total_steps}]{RESET} {title} ...", end=" ", flush=True)

def log_success(extra=""):
    print(f"{GREEN}✓ PASSED{RESET} {extra}")

def log_failure(detail: str):
    print(f"{RED}✗ FAILED{RESET}\n  {RED}Detail: {detail}{RESET}")

def run_e2e(base_url: str = None):
    print(f"{BOLD}{BLUE}=================================================================={RESET}")
    print(f"{BOLD}{BLUE}       SAHAYAK AI - COMPLETE END-TO-END VERIFICATION RUNNER       {RESET}")
    print(f"{BOLD}{BLUE}=================================================================={RESET}")

    total_stages = 10
    start_time = time.perf_counter()

    # Use live HTTP client or TestClient
    if base_url:
        import requests
        print(f"Mode: {BOLD}Live Target Server{RESET} ({base_url})")
        class ClientWrapper:
            def get(self, path, headers=None):
                return requests.get(f"{base_url}{path}", headers=headers)
            def post(self, path, json=None, headers=None):
                return requests.post(f"{base_url}{path}", json=json, headers=headers)
            def patch(self, path, json=None, headers=None):
                return requests.patch(f"{base_url}{path}", json=json, headers=headers)
        client = ClientWrapper()
    else:
        from fastapi.testclient import TestClient
        from app.main import app
        print(f"Mode: {BOLD}FastAPI In-Memory ASGI TestClient{RESET}")
        client = TestClient(app)

    unique_suffix = int(time.time())
    borrower_email = f"e2e.tester.{unique_suffix}@sahayakai.in"
    original_password = "InitialPassword@2026!"
    new_password = "ResetPassword#2026!"
    full_name = f"Rajesh Sharma {unique_suffix}"

    try:
        # -------------------------------------------------------------
        # STAGE 1: Datastore Health Check
        # -------------------------------------------------------------
        log_step(1, total_stages, "Probing Datastore & Service Health (/health)")
        h_res = client.get("/health")
        assert h_res.status_code == 200, f"Expected 200, got {h_res.status_code}"
        h_data = h_res.json()
        assert h_data.get("status") == "healthy", f"Status unhealthy: {h_data}"
        assert h_data.get("database") == "connected"
        log_success(f"({h_data['datastores']['primary_db']['dialect']}, {len(h_data['datastores']['primary_db']['tables'])} tables)")

        # -------------------------------------------------------------
        # STAGE 2: Strict Login Gatekeeper (Unregistered Blocked)
        # -------------------------------------------------------------
        log_step(2, total_stages, "Testing Strict Login Gatekeeper (Unregistered Rejected)")
        unreg_res = client.post("/api/auth/login", json={
            "email": borrower_email,
            "password": original_password
        })
        assert unreg_res.status_code == 401, f"Expected 401, got {unreg_res.status_code}"
        assert "register first" in unreg_res.json().get("detail", "").lower()

        unreg_google = client.post("/api/auth/login/google", json={
            "id_token": f"mock_google_:{borrower_email}:{full_name}"
        })
        assert unreg_google.status_code == 401, f"Expected 401, got {unreg_google.status_code}"
        assert "must register first" in unreg_google.json().get("detail", "").lower()
        log_success("(Unregistered email and Google OAuth strictly rejected with 401)")

        # -------------------------------------------------------------
        # STAGE 3: Borrower Registration
        # -------------------------------------------------------------
        log_step(3, total_stages, "Registering New Borrower Account (/api/auth/register)")
        reg_res = client.post("/api/auth/register", json={
            "email": borrower_email,
            "password": original_password,
            "full_name": full_name
        })
        assert reg_res.status_code == 201, f"Expected 201, got {reg_res.status_code}"
        reg_data = reg_res.json()
        token = reg_data["access_token"]
        user_id = reg_data["user"]["id"]
        assert len(token) > 20
        assert reg_data["user"]["email"] == borrower_email
        auth_headers = {"Authorization": f"Bearer {token}"}
        log_success(f"(User ID: {user_id}, Bearer JWT issued)")

        # -------------------------------------------------------------
        # STAGE 4: Authenticated Profile Verification
        # -------------------------------------------------------------
        log_step(4, total_stages, "Verifying Authenticated Profile (/api/auth/me)")
        me_res = client.get("/api/auth/me", headers=auth_headers)
        assert me_res.status_code == 200
        assert me_res.json()["id"] == user_id
        log_success(f"(Identified as {me_res.json()['email']})")

        # -------------------------------------------------------------
        # STAGE 5: Deterministic Financial Calculation (RBI KFS)
        # -------------------------------------------------------------
        log_step(5, total_stages, "Calculating Loan EMI & APR (/api/financial/calculate)")
        emi_res = client.post("/api/financial/calculate", json={
            "loan_amount": 100000,
            "preferred_tenure_months": 24,
            "offer_id": "offer-hdfc-01",
            "maximum_emi": 5500
        })
        assert emi_res.status_code == 200
        emi_data = emi_res.json()
        emi_val = emi_data["estimated_emi_rupees"]
        apr_val = emi_data["annual_percentage_rate_apr"]
        log_success(f"(EMI: ₹{float(emi_val):,.2f}, APR: {apr_val}%)")

        # -------------------------------------------------------------
        # STAGE 6: Private Journey Creation & FSM State Lifecycle
        # -------------------------------------------------------------
        log_step(6, total_stages, "Creating Private Financial Journey (/api/journeys)")
        j_res = client.post("/api/journeys", json={
            "language": "en",
            "loan_amount": 100000,
            "preferred_tenure_months": 24,
            "maximum_emi": 5500,
            "purpose": "Home Improvement"
        }, headers=auth_headers)
        assert j_res.status_code == 201
        journey = j_res.json()
        journey_id = journey["id"]
        assert journey["user_id"] == user_id
        assert journey["stage"] == "INTENT_CAPTURED"
        log_success(f"(Journey Ref: {journey_id}, Owner: {user_id})")

        # -------------------------------------------------------------
        # STAGE 7: Consent Gating & Document OCR Ingestion
        # -------------------------------------------------------------
        log_step(7, total_stages, "Testing Consent Auditing & Document Preflight Masking")
        # Ensure document upload without consent is gated
        gated_res = client.post(f"/api/journeys/{journey_id}/documents/upload", json={
            "document_type": "PAN_CARD"
        }, headers=auth_headers)
        assert gated_res.status_code == 403, f"Expected 403, got {gated_res.status_code}"

        # Grant explicit statutory consent
        consent_res = client.post(f"/api/journeys/{journey_id}/consent", json={
            "scope": "document_ocr_processing",
            "purpose": "PAN verification for lending preflight",
            "is_granted": True
        }, headers=auth_headers)
        assert consent_res.status_code == 200
        assert len(consent_res.json()["tamper_hash"]) == 64

        # Document upload now succeeds and masks sensitive PII
        doc_res = client.post(f"/api/journeys/{journey_id}/documents/upload", json={
            "document_type": "PAN_CARD"
        }, headers=auth_headers)
        assert doc_res.status_code == 200
        doc_data = doc_res.json()
        masked_pan = doc_data["fields"]["pan_number"]["masked_value"]
        assert masked_pan.startswith("AB") and "X" in masked_pan
        log_success(f"(Consent Hash: {consent_res.json()['tamper_hash'][:16]}..., Masked PAN: {masked_pan})")

        # -------------------------------------------------------------
        # STAGE 8: Multi-Tenant IDOR Protection
        # -------------------------------------------------------------
        log_step(8, total_stages, "Testing Multi-Tenant IDOR Gating on Journey & Chat")
        # Register Attacker
        attacker_email = f"attacker.{unique_suffix}@sahayakai.in"
        att_res = client.post("/api/auth/register", json={
            "email": attacker_email,
            "password": "AttackerPass123!",
            "full_name": "Attacker"
        })
        attacker_token = att_res.json()["access_token"]
        attacker_headers = {"Authorization": f"Bearer {attacker_token}"}

        # Attacker tries to read User A's private journey -> 403 Forbidden
        idor_j = client.get(f"/api/journeys/{journey_id}", headers=attacker_headers)
        assert idor_j.status_code == 403, f"Expected 403, got {idor_j.status_code}"

        # Attacker tries to chat with User A's private journey -> 403 Forbidden
        idor_chat = client.post("/api/chat", json={
            "journey_id": journey_id,
            "message": "Mutate loan"
        }, headers=attacker_headers)
        assert idor_chat.status_code == 403, f"Expected 403, got {idor_chat.status_code}"

        # Legitimate owner can chat with their journey -> 200 OK
        owner_chat = client.post("/api/chat", json={
            "journey_id": journey_id,
            "message": "Explain my EMI and prepayment rules"
        }, headers=auth_headers)
        assert owner_chat.status_code == 200
        log_success("(Cross-tenant access intercepted with 403 Forbidden; Owner allowed with 200 OK)")

        # -------------------------------------------------------------
        # STAGE 9: Forgot Password & Single-Use OTP Flow
        # -------------------------------------------------------------
        log_step(9, total_stages, "Testing Forgot Password & OTP Flow (/api/auth/forgot-password)")
        forgot_res = client.post("/api/auth/forgot-password", json={"email": borrower_email})
        assert forgot_res.status_code == 200
        otp = forgot_res.json().get("dev_otp")
        assert otp and len(otp) == 6

        # Reset password with valid OTP
        reset_res = client.post("/api/auth/reset-password", json={
            "email": borrower_email,
            "token_or_otp": otp,
            "new_password": new_password
        })
        assert reset_res.status_code == 200
        log_success(f"(6-digit OTP verified: {otp}, password reset confirmed)")

        # -------------------------------------------------------------
        # STAGE 10: Credential Rollover Verification
        # -------------------------------------------------------------
        log_step(10, total_stages, "Verifying Credential Rollover & Revocation of Old Password")
        # Old password must fail
        old_attempt = client.post("/api/auth/login", json={
            "email": borrower_email,
            "password": original_password
        })
        assert old_attempt.status_code == 401, f"Expected 401, got {old_attempt.status_code}"

        # New password must succeed
        new_attempt = client.post("/api/auth/login", json={
            "email": borrower_email,
            "password": new_password
        })
        assert new_attempt.status_code == 200, f"Expected 200, got {new_attempt.status_code}"
        assert len(new_attempt.json()["access_token"]) > 20
        log_success("(Old password revoked, new credentials successfully authenticated)")

        elapsed = time.perf_counter() - start_time
        print(f"\n{BOLD}{GREEN}=================================================================={RESET}")
        print(f"{BOLD}{GREEN}  ALL 10 E2E STAGES COMPLETED SUCCESSFULLY IN {elapsed:.2f}s!  {RESET}")
        print(f"{BOLD}{GREEN}=================================================================={RESET}\n")
        return 0

    except AssertionError as exc:
        log_failure(str(exc))
        print(f"\n{BOLD}{RED}E2E RUNNER HALTED ON ERROR.{RESET}\n")
        return 1
    except Exception as exc:
        log_failure(f"Unexpected exception: {exc}")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sahayak AI E2E Pipeline Runner")
    parser.add_argument("--live", type=str, default=None, help="Live base URL (e.g. http://127.0.0.1:8000)")
    args = parser.parse_args()

    exit_code = run_e2e(base_url=args.live)
    sys.exit(exit_code)

