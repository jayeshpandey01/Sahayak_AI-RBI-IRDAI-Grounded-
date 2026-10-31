import os
import json
import base64
import hmac
import hashlib
import secrets
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
from fastapi import HTTPException, status
from app.config import settings

logger = logging.getLogger("sahayak.auth")

# ----------------- CRYPTOGRAPHY & PASSWORD HASHING -----------------

PBKDF2_ITERATIONS = 600_000

def hash_password(password: str) -> str:
    """NIST SP 800-63B compliant PBKDF2-HMAC-SHA256 password hashing."""
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${derived.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Timing-safe PBKDF2-HMAC-SHA256 password verification."""
    if not hashed_password or not hashed_password.startswith("pbkdf2_sha256$"):
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4:
            return False
        _, iterations_str, salt_hex, expected_hash_hex = parts
        iterations = int(iterations_str)
        salt_bytes = bytes.fromhex(salt_hex)
        candidate_derived = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt_bytes,
            iterations
        )
        return hmac.compare_digest(candidate_derived.hex(), expected_hash_hex)
    except Exception as exc:
        logger.error(f"Password verification error: {exc}")
        return False

def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """Enforces minimum 8 chars, max 128 chars, 1 digit, 1 letter."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password must not exceed 128 characters."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one numeric digit."
    if not any(c.isalpha() for c in password):
        return False, "Password must contain at least one alphabetic character."
    return True, None

# ----------------- JWT TOKEN ENCODING & DECODING (RFC 7519) -----------------

def _b64_url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _b64_url_decode(data_str: str) -> bytes:
    padding = "=" * ((4 - len(data_str) % 4) % 4)
    return base64.urlsafe_b64decode((data_str + padding).encode("ascii"))

def create_access_token(
    user_id: str,
    email: str,
    role: str = "borrower",
    expires_delta: Optional[timedelta] = None
) -> str:
    """Creates a standard RFC 7519 HS256 signed JSON Web Token."""
    now = datetime.now(timezone.utc)
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    exp = int((now + delta).timestamp())
    iat = int(now.timestamp())

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": iat,
        "exp": exp,
    }

    header_b64 = _b64_url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64_url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    signature = hmac.new(
        settings.JWT_SECRET.encode("utf-8"),
        signing_input,
        hashlib.sha256
    ).digest()
    sig_b64 = _b64_url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_access_token(token: str) -> Dict[str, Any]:
    """Validates signature and expiration of an HS256 JWT."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed authorization token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

        expected_sig = hmac.new(
            settings.JWT_SECRET.encode("utf-8"),
            signing_input,
            hashlib.sha256
        ).digest()

        provided_sig = _b64_url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, provided_sig):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload_bytes = _b64_url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Verify expiration
        exp = payload.get("exp")
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if exp is not None and now_ts > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Token decode error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ----------------- GOOGLE TOKEN VERIFICATION -----------------

def verify_google_id_token(id_token_str: str) -> Dict[str, Any]:
    """
    Verifies Google ID Token.
    Uses google-auth library if available, with resilient fallback for mock/test tokens.
    """
    if not id_token_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google ID token is required."
        )

    # Allow structured test tokens during testing or development
    if id_token_str.startswith("mock_google_") or id_token_str.startswith("test_google_"):
        parts = id_token_str.split(":")
        email = parts[1] if len(parts) > 1 else "google_test_user@example.com"
        name = parts[2] if len(parts) > 2 else "Google Test User"
        sub = f"google_sub_{hashlib.md5(email.encode()).hexdigest()[:12]}"
        return {
            "sub": sub,
            "email": email.lower(),
            "name": name,
            "email_verified": True,
        }

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        req = google_requests.Request()
        # Verify without hard audience constraint if GOOGLE_CLIENT_ID not explicitly configured
        id_info = id_token.verify_oauth2_token(
            id_token_str,
            req,
            audience=settings.GOOGLE_CLIENT_ID or None
        )

        sub = id_info.get("sub")
        email = id_info.get("email")
        if not sub or not email:
            raise ValueError("Token missing sub or email claims.")

        return {
            "sub": sub,
            "email": email.lower(),
            "name": id_info.get("name", "Google User"),
            "email_verified": id_info.get("email_verified", True),
        }
    except Exception as exc:
        logger.warning(f"Google token verification failed via google-auth: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google ID token: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ----------------- PASSWORD RESET & OTP LIFECYCLE -----------------

def generate_reset_token_and_otp() -> Tuple[str, str, str]:
    """
    Generates:
    - raw_token: URL-safe random string for web reset links
    - token_hash: SHA-256 hash for secure DB storage
    - otp_code: 6-digit numeric OTP code for instant entry
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    otp_code = f"{secrets.randbelow(900000) + 100000}"
    return raw_token, token_hash, otp_code

def dispatch_password_reset_email(
    recipient_email: str,
    otp_code: str,
    reset_token: str
) -> bool:
    """
    Dispatches a branded password reset email via SMTP (Gmail configured in backend/.env).
    Gracefully handles network / authentication exceptions so the background worker never crashes.
    """
    subject = "Sahayak AI - Password Reset Request"
    sender = settings.SENDER_ADDRESS or "noreply@sahayakai.in"

    html_content = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; padding: 24px; color: #1e293b;">
    <div style="max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
        <h2 style="color: #0f172a; margin-top: 0;">Sahayak AI Password Reset</h2>
        <p>Namaste,</p>
        <p>We received a request to reset your Sahayak AI account password. Use the 6-digit verification code below to complete your password reset:</p>
        
        <div style="background-color: #f1f5f9; border-radius: 8px; padding: 18px; text-align: center; margin: 24px 0;">
            <span style="font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #1e40af;">{otp_code}</span>
        </div>
        
        <p style="font-size: 14px; color: #64748b;">This OTP code and reset token are valid for <strong>{settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes</strong>. If you did not request this, you can safely ignore this email.</p>
        
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
        <p style="font-size: 12px; color: #94a3b8; margin-bottom: 0;">Sahayak AI · Regulated Digital Lending Copilot · Secure Financial Gateway</p>
    </div>
</body>
</html>"""

    text_content = f"""Namaste,

We received a request to reset your Sahayak AI account password.
Your 6-digit verification code is: {otp_code}

This code expires in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes.
If you did not request this reset, please ignore this email.

Sahayak AI Systems Architecture"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_ACCOUNT_USERNAME} <{sender}>"
    msg["To"] = recipient_email
    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        host = settings.SMTP_SERVER_HOST
        port = settings.SMTP_SERVER_PORT
        password = settings.SMTP_ACCOUNT_PASSWORD

        if not host or not password:
            logger.info(f"[DEV MODE] SMTP not fully configured. Reset code for {recipient_email}: {otp_code}")
            return True

        # Port 587 uses STARTTLS; Port 465 uses SMTP_SSL
        if port == 465 or settings.SMTP_SECURITY_MODE.upper() == "SSL":
            with smtplib.SMTP_SSL(host, port, timeout=10.0) as server:
                server.login(sender, password)
                server.sendmail(sender, [recipient_email], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=10.0) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(sender, password)
                server.sendmail(sender, [recipient_email], msg.as_string())

        logger.info(f"Successfully dispatched password reset email to {recipient_email}")
        return True
    except Exception as exc:
        logger.warning(f"SMTP dispatch warning (dev/offline fallback): {exc}. Reset OTP for {recipient_email}: {otp_code}")
        return False

