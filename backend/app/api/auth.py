import hashlib
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models.db_models import UserModel, PasswordResetTokenModel
from app.models.schemas import (
    RegisterRequest,
    LoginRequest,
    GoogleAuthRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    UserProfileResponse,
    UpdateProfileRequest,
    AuthTokenResponse,
    MessageResponse,
)
from app.services.auth_service import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    verify_google_id_token,
    generate_reset_token_and_otp,
    dispatch_password_reset_email,
)
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication & Identity"])

# ----------------- REGISTRATION -----------------

@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register_with_email(
    payload: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user using email and a strong password.
    Rejects duplicate emails with 409 Conflict.
    """
    # 1. Enforce password complexity
    is_valid, error_msg = validate_password_strength(payload.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_msg or "Password does not meet strength requirements."
        )

    # 2. Check for duplicate user
    existing_user = db.query(UserModel).filter(UserModel.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please log in."
        )

    # 3. Create user
    user_id = f"usr_{uuid4().hex[:16]}"
    hashed_pw = hash_password(payload.password)

    new_user = UserModel(
        id=user_id,
        email=payload.email,
        password_hash=hashed_pw,
        full_name=payload.full_name or payload.email.split("@")[0].capitalize(),
        auth_provider="email",
        role="borrower",
        is_active=True,
        is_verified=True,
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 4. Generate JWT
    access_token = create_access_token(
        user_id=new_user.id,
        email=new_user.email,
        role=new_user.role
    )

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserProfileResponse.model_validate(new_user)
    )

@router.post("/register/google", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register_with_google(
    payload: GoogleAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user using a verified Google ID token.
    Rejects already-registered users with 409 Conflict.
    """
    google_info = verify_google_id_token(payload.id_token)
    google_sub = google_info["sub"]
    google_email = google_info["email"]

    # Check if user already exists
    existing_user = db.query(UserModel).filter(
        (UserModel.email == google_email) | (UserModel.google_sub == google_sub)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account is already registered for this Google account. Please log in."
        )

    user_id = f"usr_{uuid4().hex[:16]}"
    new_user = UserModel(
        id=user_id,
        email=google_email,
        password_hash=None,
        full_name=payload.full_name or google_info.get("name") or google_email.split("@")[0].capitalize(),
        auth_provider="google",
        google_sub=google_sub,
        role="borrower",
        is_active=True,
        is_verified=True,
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(
        user_id=new_user.id,
        email=new_user.email,
        role=new_user.role
    )

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserProfileResponse.model_validate(new_user)
    )

# ----------------- LOGIN (STRICT GATEKEEPER) -----------------

@router.post("/login", response_model=AuthTokenResponse)
def login_with_email(
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user using email and password.
    STRICT CONSTRAINT: If user is not registered, login is strictly rejected.
    """
    user = db.query(UserModel).filter(UserModel.email == payload.email).first()

    # STRICT GATEKEEPER CHECK: Without registration, no one can login!
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found. Please register first before logging in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.auth_provider == "google" and not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account was registered using Google. Please sign in with Google.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or disabled.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role
    )

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserProfileResponse.model_validate(user)
    )

@router.post("/login/google", response_model=AuthTokenResponse)
def login_with_google(
    payload: GoogleAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user using Google ID token.
    STRICT CONSTRAINT: If the Google account is not registered, login is strictly rejected.
    """
    google_info = verify_google_id_token(payload.id_token)
    google_sub = google_info["sub"]
    google_email = google_info["email"]

    user = db.query(UserModel).filter(
        (UserModel.email == google_email) | (UserModel.google_sub == google_sub)
    ).first()

    # STRICT GATEKEEPER CHECK: Without registration, no one can login!
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No registered account found for this Google email. You must register first.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or disabled.",
        )

    # Link Google sub if not previously populated
    if not user.google_sub:
        user.google_sub = google_sub
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role
    )

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserProfileResponse.model_validate(user)
    )

# ----------------- FORGOT & RESET PASSWORD -----------------

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def request_password_reset(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Requests a password reset token and 6-digit OTP.
    Dispatches asynchronous email notification in the background via SMTP.
    """
    user = db.query(UserModel).filter(UserModel.email == payload.email).first()

    dev_otp = None
    dev_token = None

    if user and user.is_active:
        # Invalidate existing unused reset tokens for this user
        db.query(PasswordResetTokenModel).filter(
            PasswordResetTokenModel.user_id == user.id,
            PasswordResetTokenModel.is_used == False
        ).update({"is_used": True})

        raw_token, token_hash, otp_code = generate_reset_token_and_otp()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)

        reset_entry = PasswordResetTokenModel(
            id=f"rst_{uuid4().hex[:16]}",
            user_id=user.id,
            token_hash=token_hash,
            otp_code=otp_code,
            expires_at=expires_at,
            is_used=False
        )
        db.add(reset_entry)
        db.commit()

        # Enqueue background email dispatch task
        background_tasks.add_task(
            dispatch_password_reset_email,
            recipient_email=user.email,
            otp_code=otp_code,
            reset_token=raw_token
        )

        if settings.ENVIRONMENT != "production":
            dev_otp = otp_code
            dev_token = raw_token

    # Return standard response to protect against user enumeration
    return ForgotPasswordResponse(
        success=True,
        message="If an account with that email exists, password reset instructions have been sent.",
        dev_otp=dev_otp,
        dev_reset_token=dev_token
    )

@router.post("/reset-password", response_model=MessageResponse)
def execute_password_reset(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Resets user password using a valid, unexpired, single-use token or 6-digit OTP code.
    """
    # 1. Enforce password complexity
    is_valid, error_msg = validate_password_strength(payload.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_msg or "Password does not meet strength requirements."
        )

    user = db.query(UserModel).filter(UserModel.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset request."
        )

    # 2. Match token_hash or OTP code
    candidate_hash = hashlib.sha256(payload.token_or_otp.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)

    reset_token = (
        db.query(PasswordResetTokenModel)
        .filter(
            PasswordResetTokenModel.user_id == user.id,
            PasswordResetTokenModel.is_used == False,
            PasswordResetTokenModel.expires_at > now,
            (PasswordResetTokenModel.otp_code == payload.token_or_otp)
            | (PasswordResetTokenModel.token_hash == candidate_hash)
        )
        .order_by(PasswordResetTokenModel.created_at.desc())
        .first()
    )

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or already-used password reset token/OTP."
        )

    # 3. Apply password update & consume token
    user.password_hash = hash_password(payload.new_password)
    if user.auth_provider == "google":
        # Allow user to now also log in via email/password
        user.auth_provider = "email"
    reset_token.is_used = True
    db.commit()

    return MessageResponse(
        success=True,
        message="Your password has been successfully reset. You can now log in with your new password."
    )

# ----------------- CURRENT USER PROFILE -----------------

@router.get("/me", response_model=UserProfileResponse)
def get_authenticated_profile(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieve authenticated user profile. Requires Bearer JWT.
    """
    return UserProfileResponse.model_validate(current_user)

@router.patch("/me", response_model=UserProfileResponse)
def update_authenticated_profile(
    payload: UpdateProfileRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update authenticated user profile (e.g. full_name). Requires Bearer JWT.
    """
    if payload.full_name is not None:
        clean_name = payload.full_name.strip()
        if not clean_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Full name cannot be blank."
            )
        current_user.full_name = clean_name
    db.commit()
    db.refresh(current_user)
    return UserProfileResponse.model_validate(current_user)


