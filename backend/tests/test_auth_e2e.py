import pytest
from app.models.schemas import ConsentScope

# ----------------- REGISTRATION TESTS -----------------

def test_register_email_success(client):
    res = client.post("/api/auth/register", json={
        "email": "priya.sharma@example.com",
        "password": "SecurePassword123!",
        "full_name": "Priya Sharma"
    })
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "priya.sharma@example.com"
    assert data["user"]["full_name"] == "Priya Sharma"
    assert data["user"]["auth_provider"] == "email"
    assert data["user"]["is_active"] is True

def test_register_duplicate_email_conflict(client):
    # First registration
    client.post("/api/auth/register", json={
        "email": "duplicate.test@example.com",
        "password": "SecurePassword123!",
        "full_name": "Duplicate Test"
    })
    # Second registration with same email
    res2 = client.post("/api/auth/register", json={
        "email": "duplicate.test@example.com",
        "password": "AnotherPassword456!",
        "full_name": "Duplicate Test 2"
    })
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"].lower()

def test_register_weak_password_validation(client):
    # Short password
    res1 = client.post("/api/auth/register", json={
        "email": "weak1@example.com",
        "password": "123",
        "full_name": "Weak User"
    })
    assert res1.status_code == 422

    # Password with no digits
    res2 = client.post("/api/auth/register", json={
        "email": "weak2@example.com",
        "password": "onlylettersandlong",
        "full_name": "Weak User"
    })
    assert res2.status_code == 422
    assert "numeric digit" in res2.json()["detail"].lower()

# ----------------- STRICT LOGIN TESTS (UNREGISTERED MUST FAIL) -----------------

def test_login_unregistered_email_strictly_fails(client):
    """STRICT REQUIREMENT: Without registration no one can login."""
    res = client.post("/api/auth/login", json={
        "email": "ghost.user@notregistered.com",
        "password": "SomePassword123!"
    })
    assert res.status_code == 401
    assert "register first" in res.json()["detail"].lower()

def test_login_wrong_password_fails(client):
    client.post("/api/auth/register", json={
        "email": "wrongpw@example.com",
        "password": "CorrectPassword123!",
        "full_name": "Wrong PW Tester"
    })
    res = client.post("/api/auth/login", json={
        "email": "wrongpw@example.com",
        "password": "IncorrectPassword999!"
    })
    assert res.status_code == 401
    assert "invalid email or password" in res.json()["detail"].lower()

def test_login_registered_email_success(client):
    client.post("/api/auth/register", json={
        "email": "raj.kumar@example.com",
        "password": "RajPassword123!",
        "full_name": "Raj Kumar"
    })
    res = client.post("/api/auth/login", json={
        "email": "raj.kumar@example.com",
        "password": "RajPassword123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "raj.kumar@example.com"
    assert data["user"]["full_name"] == "Raj Kumar"

# ----------------- GOOGLE AUTH TESTS (STRICT LOGIN GATING) -----------------

def test_register_google_success(client):
    res = client.post("/api/auth/register/google", json={
        "id_token": "mock_google_:arjun.verma@gmail.com:Arjun Verma",
        "full_name": "Arjun Verma"
    })
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "arjun.verma@gmail.com"
    assert data["user"]["auth_provider"] == "google"

def test_register_google_duplicate_fails(client):
    token = "mock_google_:dup.google@gmail.com:Duplicate Google"
    client.post("/api/auth/register/google", json={"id_token": token})
    res2 = client.post("/api/auth/register/google", json={"id_token": token})
    assert res2.status_code == 409
    assert "already registered" in res2.json()["detail"].lower()

def test_login_unregistered_google_strictly_fails(client):
    """STRICT REQUIREMENT: Unregistered Google users CANNOT login directly."""
    res = client.post("/api/auth/login/google", json={
        "id_token": "mock_google_:unregistered.google@gmail.com:Unregistered Google"
    })
    assert res.status_code == 401
    assert "must register first" in res.json()["detail"].lower()

def test_login_registered_google_success(client):
    token = "mock_google_:vikram.aditya@gmail.com:Vikram Aditya"
    # 1. Register first
    reg_res = client.post("/api/auth/register/google", json={"id_token": token})
    assert reg_res.status_code == 201

    # 2. Login now succeeds
    login_res = client.post("/api/auth/login/google", json={"id_token": token})
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()
    assert login_res.json()["user"]["email"] == "vikram.aditya@gmail.com"

def test_google_user_cannot_login_with_blank_password(client):
    token = "mock_google_:onlygoogle@gmail.com:Only Google User"
    client.post("/api/auth/register/google", json={"id_token": token})

    res = client.post("/api/auth/login", json={
        "email": "onlygoogle@gmail.com",
        "password": "SomePassword123!"
    })
    assert res.status_code == 401
    assert "please sign in with google" in res.json()["detail"].lower()

# ----------------- FORGOT & RESET PASSWORD TESTS -----------------

def test_forgot_password_and_reset_flow(client):
    # 1. Register user
    email = "anita.desai@example.com"
    client.post("/api/auth/register", json={
        "email": email,
        "password": "OldPassword123!",
        "full_name": "Anita Desai"
    })

    # 2. Request password reset
    forgot_res = client.post("/api/auth/forgot-password", json={"email": email})
    assert forgot_res.status_code == 200
    forgot_data = forgot_res.json()
    assert forgot_data["success"] is True
    assert forgot_data["dev_otp"] is not None
    otp_code = forgot_data["dev_otp"]
    assert len(otp_code) == 6

    # 3. Attempt reset with wrong OTP -> 400 Bad Request
    bad_reset = client.post("/api/auth/reset-password", json={
        "email": email,
        "token_or_otp": "000000",
        "new_password": "NewPassword456!"
    })
    assert bad_reset.status_code == 400

    # 4. Attempt reset with weak password -> 422
    weak_reset = client.post("/api/auth/reset-password", json={
        "email": email,
        "token_or_otp": otp_code,
        "new_password": "short"
    })
    assert weak_reset.status_code == 422

    # 5. Reset with valid OTP and strong new password
    good_reset = client.post("/api/auth/reset-password", json={
        "email": email,
        "token_or_otp": otp_code,
        "new_password": "NewPassword456!"
    })
    assert good_reset.status_code == 200
    assert good_reset.json()["success"] is True

    # 6. Verify old password no longer works
    old_login = client.post("/api/auth/login", json={
        "email": email,
        "password": "OldPassword123!"
    })
    assert old_login.status_code == 401

    # 7. Verify new password works
    new_login = client.post("/api/auth/login", json={
        "email": email,
        "password": "NewPassword456!"
    })
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()

    # 8. Verify OTP cannot be reused
    reuse_reset = client.post("/api/auth/reset-password", json={
        "email": email,
        "token_or_otp": otp_code,
        "new_password": "AnotherPassword789!"
    })
    assert reuse_reset.status_code == 400

def test_forgot_password_unregistered_email_enumeration_safe(client):
    res = client.post("/api/auth/forgot-password", json={"email": "nobody@nowhere.com"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["dev_otp"] is None

# ----------------- PROTECTED /api/auth/me & ROUTE GUARDS -----------------

def test_protected_me_endpoint(client):
    # Unauthenticated request -> 401
    unauth_res = client.get("/api/auth/me")
    assert unauth_res.status_code == 401

    # Invalid token -> 401
    bad_token_res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.jwt.signature"})
    assert bad_token_res.status_code == 401

    # Register and obtain valid token
    reg = client.post("/api/auth/register", json={
        "email": "me.endpoint@example.com",
        "password": "MePassword123!",
        "full_name": "Me Endpoint User"
    })
    token = reg.json()["access_token"]

    # Authenticated request -> 200
    auth_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert auth_res.status_code == 200
    assert auth_res.json()["email"] == "me.endpoint@example.com"
    assert auth_res.json()["full_name"] == "Me Endpoint User"

def test_update_authenticated_profile(client):
    # 1. Register user
    reg_res = client.post("/api/auth/register", json={
        "email": "update.profile@example.com",
        "password": "Password123!",
        "full_name": "Initial Name"
    })
    token = reg_res.json()["access_token"]

    # 2. Update full_name via PATCH /api/auth/me
    patch_res = client.patch(
        "/api/auth/me",
        json={"full_name": "Updated Name"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["full_name"] == "Updated Name"

    # 3. Verify GET /api/auth/me returns updated name
    get_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert get_res.status_code == 200
    assert get_res.json()["full_name"] == "Updated Name"

    # 4. Reject blank name
    bad_res = client.patch(
        "/api/auth/me",
        json={"full_name": "   "},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert bad_res.status_code == 422

# ----------------- DATA ISOLATION (M2 ACCEPTANCE CRITERIA) -----------------

def test_user_data_isolation(client):
    """Verifies that User A cannot access User B's journey records."""
    # 1. Register User A
    user_a = client.post("/api/auth/register", json={
        "email": "user.a@example.com",
        "password": "PasswordUserA123!",
        "full_name": "User Alpha"
    }).json()
    token_a = user_a["access_token"]

    # 2. Register User B
    user_b = client.post("/api/auth/register", json={
        "email": "user.b@example.com",
        "password": "PasswordUserB123!",
        "full_name": "User Beta"
    }).json()
    token_b = user_b["access_token"]

    # 3. User A creates a journey
    j_res = client.post("/api/journeys", json={
        "language": "en",
        "loan_amount": 100000,
        "preferred_tenure_months": 36,
        "purpose": "Personal expansion"
    }, headers={"Authorization": f"Bearer {token_a}"})
    assert j_res.status_code == 201
    journey_id = j_res.json()["id"]

    # 4. User A can view own journey
    res_a = client.get(f"/api/journeys/{journey_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    assert res_a.json()["id"] == journey_id

    # 5. User B tries to view User A's journey -> 403 Forbidden
    res_b = client.get(f"/api/journeys/{journey_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 403
    assert "do not have permission" in res_b.json()["detail"].lower()

