import os
import secrets
from pathlib import Path
from dotenv import load_dotenv, dotenv_values
from pydantic import BaseModel, field_validator, model_validator

FREE_OPENROUTER_MODEL = "nvidia/nemotron-3.5-super-vl:free"

# Canonical paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
CANONICAL_DB_PATH = BACKEND_DIR / "sahayak.db"
DEFAULT_SYNC_DB_URL = f"sqlite:///{CANONICAL_DB_PATH}"


def configured_origins() -> list[str]:
    value = os.getenv("ALLOWED_ORIGINS", "")
    if value.strip():
        return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:19006",
        "http://127.0.0.1:19006",
    ]

# Load backend/.env if present
env_path = BACKEND_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
# Support the repository-root .env used by Expo/local development as a fallback.
# Backend-specific values above take precedence because load_dotenv does not override.
root_env_path = BACKEND_DIR.parent / ".env"
if root_env_path.exists():
    for key, value in dotenv_values(root_env_path).items():
        if value is not None and not os.getenv(key):
            os.environ[key] = value

DEFAULT_ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    "production" if os.getenv("VERCEL_ENV", "").lower() == "production" else "development",
).lower()

class Settings(BaseModel):
    APP_NAME: str = "Sahayak AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = DEFAULT_ENVIRONMENT
    # Current SQLAlchemy data access uses a synchronous engine. Honor the
    # common DATABASE_URL setting when SYNC_DATABASE_URL is not supplied.
    DATABASE_URL: str = os.getenv("DATABASE_URL", DEFAULT_SYNC_DB_URL)
    SYNC_DATABASE_URL: str = os.getenv("SYNC_DATABASE_URL") or DATABASE_URL
    ALLOWED_ORIGINS: list[str] = configured_origins()
    RBI_MAX_LOAN_AMOUNT: int = 5_000_000
    RBI_MIN_LOAN_AMOUNT: int = 1_000
    DEFAULT_PROCESSING_GST_RATE: str = "18.0"

    # JWT Authentication
    JWT_SECRET: str = os.getenv("JWT_SECRET") or (
        secrets.token_urlsafe(48) if DEFAULT_ENVIRONMENT != "production" else ""
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    PASSWORD_RESET_EXPIRE_MINUTES: int = 15     # 15 minutes

    # SMTP Configuration
    SENDER_ADDRESS: str = os.getenv("SENDER_ADDRESS", "")
    SMTP_SERVER_HOST: str = os.getenv("SMTP_server_host", "smtp.gmail.com")
    SMTP_SERVER_PORT: int = int(os.getenv("SMTP_server_port", "587"))
    SMTP_ACCOUNT_USERNAME: str = os.getenv("SMTP_ACCOUNT_USERNAME", "")
    SMTP_ACCOUNT_PASSWORD: str = os.getenv("SMTP_ACCOUNT_PASSWORD", "")
    SMTP_SECURITY_MODE: str = os.getenv("SMTP_security_mode", "STARTTLS")

    # Google OAuth / Firebase Credentials
    FIREBASE_CREDENTIALS_PATH: str = os.getenv(
        "FIREBASE_CREDENTIALS_PATH",
        ""
    )
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    FIREBASE_PROJECT_ID: str = os.getenv("projectId", "sahayakai-1befa")

    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    SUPABASE_PUBLISHABLE_KEY: str = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "")
    SUPABASE_SECRET_KEY: str = os.getenv("SUPABASE_SECRET_KEY", "")
    SUPABASE_JWKS_URL: str = os.getenv("SUPABASE_JWKS_URL", "")
    SUPABASE_USERNAME: str = os.getenv("Superbase_username", "")
    SUPABASE_PASSWORD: str = os.getenv("superbase_password", "")

    # Stripe Payment Provider Configuration (Milestone S0)
    STRIPE_MODE: str = os.getenv("STRIPE_MODE", "test")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_LIVE_ENABLED: bool = os.getenv("STRIPE_LIVE_ENABLED", "false").lower() in ("true", "1", "yes")
    # This product's wallet/lending use case needs explicit written Stripe approval.
    # A live key by itself must never authorize financial-product transactions.
    STRIPE_FINANCIAL_SERVICES_APPROVED: bool = os.getenv("STRIPE_FINANCIAL_SERVICES_APPROVED", "false").lower() in ("true", "1", "yes")
    STRIPE_RETURN_URL: str = os.getenv("STRIPE_RETURN_URL", "ubankuapp://payment-return")

    # AI provider configuration. External processing is enabled by default in development when keys exist.
    AI_EXTERNAL_PROCESSING_ENABLED: bool = os.getenv(
        "AI_EXTERNAL_PROCESSING_ENABLED",
        "true" if DEFAULT_ENVIRONMENT != "production" else "false",
    ).lower() in ("true", "1", "yes")
    AI_REAL_USER_ROLLOUT_APPROVED: bool = os.getenv(
        "AI_REAL_USER_ROLLOUT_APPROVED",
        "true" if DEFAULT_ENVIRONMENT != "production" else "false",
    ).lower() in ("true", "1", "yes")
    AI_PAYMENT_CONTEXT_ENABLED: bool = os.getenv("AI_PAYMENT_CONTEXT_ENABLED", "false").lower() in ("true", "1", "yes")
    OPENROUTER_API_KEY: str = (os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API") or "").strip()
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", FREE_OPENROUTER_MODEL).strip()
    OPENROUTER_ENFORCE_ZDR: bool = os.getenv("OPENROUTER_ENFORCE_ZDR", "false").lower() in ("true", "1", "yes")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    OPENROUTER_TIMEOUT_SECONDS: float = float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "30"))
    OPENROUTER_DAILY_LIMIT: int = int(os.getenv("OPENROUTER_DAILY_LIMIT", "40"))
    OPENROUTER_MINUTE_LIMIT: int = int(os.getenv("OPENROUTER_MINUTE_LIMIT", "15"))
    AI_USER_HOURLY_LIMIT: int = int(os.getenv("AI_USER_HOURLY_LIMIT", "30"))
    AI_RATE_LIMIT_HMAC_KEY: str = os.getenv("AI_RATE_LIMIT_HMAC_KEY", "")
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "").strip()
    SARVAM_TIMEOUT_SECONDS: float = float(os.getenv("SARVAM_TIMEOUT_SECONDS", "8"))
    SARVAM_TTS_VOICE_EN: str = os.getenv("SARVAM_TTS_VOICE_EN", "simran_en_conversation")
    SARVAM_TTS_VOICE_HI: str = os.getenv("SARVAM_TTS_VOICE_HI", "roopa_hi_conversational")
    SARVAM_TTS_VOICE_MR: str = os.getenv("SARVAM_TTS_VOICE_MR", "ishita_mr_conversational")
    SARVAM_TTS_VOICE_HINGLISH: str = os.getenv("SARVAM_TTS_VOICE_HINGLISH", "ishita_enhi_companion")
    SARVAM_TTS_PACE: float = float(os.getenv("SARVAM_TTS_PACE", "1.0"))

    # Groq Whisper Cloud (High-speed Speech-to-Text Fallback)
    GROQ_API_KEY: str = (
        os.getenv("GROQ_API_KEY")
        or os.getenv("Groq_Whisper_Cloud")
        or os.getenv("GROQ_WHISPER_CLOUD")
        or ""
    ).strip().strip("'\"")
    GROQ_WHISPER_MODEL: str = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo").strip()
    GROQ_TIMEOUT_SECONDS: float = float(os.getenv("GROQ_TIMEOUT_SECONDS", "10"))

    @field_validator("OPENROUTER_MODEL")
    @classmethod
    def enforce_free_chat_model(cls, value: str) -> str:
        if value.strip() != FREE_OPENROUTER_MODEL:
            raise ValueError(f"OPENROUTER_MODEL must be the approved free model: {FREE_OPENROUTER_MODEL}")
        return value.strip()

    @field_validator("OPENROUTER_BASE_URL")
    @classmethod
    def enforce_openrouter_route(cls, value: str) -> str:
        if value.rstrip("/") != "https://openrouter.ai/api/v1":
            raise ValueError("OPENROUTER_BASE_URL must use the approved OpenRouter API route.")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_ai_free_tier_limits(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production":
            if not self.JWT_SECRET:
                raise ValueError("JWT_SECRET must be explicitly configured in production.")
            if "sqlite" in self.SYNC_DATABASE_URL.lower():
                raise ValueError("Production requires a persistent PostgreSQL DATABASE_URL; SQLite is not supported.")
            if not self.ALLOWED_ORIGINS or any(
                not origin.startswith("https://") for origin in self.ALLOWED_ORIGINS
            ):
                raise ValueError("Production ALLOWED_ORIGINS must list the HTTPS origins of deployed web clients.")
        if not 1 <= self.OPENROUTER_DAILY_LIMIT <= 40:
            raise ValueError("OPENROUTER_DAILY_LIMIT must be between 1 and the 40-request free-tier cap.")
        if not 1 <= self.OPENROUTER_MINUTE_LIMIT <= 15:
            raise ValueError("OPENROUTER_MINUTE_LIMIT must be between 1 and the 15-request free-tier cap.")
        if self.AI_USER_HOURLY_LIMIT < 1:
            raise ValueError("AI_USER_HOURLY_LIMIT must be positive.")
        if (
            self.ENVIRONMENT.lower() == "production"
            and self.AI_EXTERNAL_PROCESSING_ENABLED
            and self.AI_REAL_USER_ROLLOUT_APPROVED
            and not self.AI_RATE_LIMIT_HMAC_KEY
        ):
            raise ValueError("AI_RATE_LIMIT_HMAC_KEY is required for production AI rollout.")
        return self

    @field_validator("STRIPE_MODE", "STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET", mode="before")
    @classmethod
    def clean_env_strings(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().strip("'\"")
        return v

    @model_validator(mode="after")
    def validate_stripe_mode_and_keys(self) -> "Settings":
        mode = self.STRIPE_MODE.lower()
        if mode not in ("test", "live"):
            raise ValueError(f"Invalid STRIPE_MODE '{self.STRIPE_MODE}'. Must be 'test' or 'live'.")

        sec_key = self.STRIPE_SECRET_KEY
        pub_key = self.STRIPE_PUBLISHABLE_KEY
        wh_sec = self.STRIPE_WEBHOOK_SECRET

        if mode == "test":
            if sec_key.startswith("sk_live_") or sec_key.startswith("rk_live_") or pub_key.startswith("pk_live_"):
                raise ValueError("Mode mismatch: Live key supplied while STRIPE_MODE is 'test'.")
            if sec_key and not (sec_key.startswith("sk_test_") or sec_key.startswith("rk_test_")):
                raise ValueError("STRIPE_SECRET_KEY in test mode must start with 'sk_test_' or 'rk_test_'.")
            if pub_key and not pub_key.startswith("pk_test_"):
                raise ValueError("STRIPE_PUBLISHABLE_KEY in test mode must start with 'pk_test_'.")
            if wh_sec and not wh_sec.startswith("whsec_"):
                raise ValueError("STRIPE_WEBHOOK_SECRET must start with 'whsec_'.")

        elif mode == "live":
            if not self.STRIPE_LIVE_ENABLED:
                raise ValueError(
                    "Stripe live mode requires explicit STRIPE_LIVE_ENABLED=true sign-off and approval gate."
                )
            if sec_key.startswith("sk_test_") or sec_key.startswith("rk_test_") or pub_key.startswith("pk_test_"):
                raise ValueError("Mode mismatch: Test key supplied while STRIPE_MODE is 'live'.")
            if sec_key and not (sec_key.startswith("sk_live_") or sec_key.startswith("rk_live_")):
                raise ValueError("STRIPE_SECRET_KEY in live mode must start with 'sk_live_' or 'rk_live_'.")
            if pub_key and not pub_key.startswith("pk_live_"):
                raise ValueError("STRIPE_PUBLISHABLE_KEY in live mode must start with 'pk_live_'.")
            if wh_sec and not wh_sec.startswith("whsec_"):
                raise ValueError("STRIPE_WEBHOOK_SECRET in live mode must start with 'whsec_'.")
            if not self.STRIPE_FINANCIAL_SERVICES_APPROVED:
                raise ValueError(
                    "Stripe live mode for wallet/lending features requires explicit written provider approval and STRIPE_FINANCIAL_SERVICES_APPROVED=true."
                )

        return self

    def validate_stripe_credentials(self) -> None:
        """
        Validates that required Stripe credentials are configured and non-empty.
        Called by payment endpoints before processing any payment operations.
        """
        if self.STRIPE_MODE.lower() == "live" and not (
            self.STRIPE_LIVE_ENABLED and self.STRIPE_FINANCIAL_SERVICES_APPROVED
        ):
            raise RuntimeError(
                "Stripe live wallet/lending payments require live mode and explicit written provider approval."
            )
        if not self.STRIPE_SECRET_KEY:
            raise RuntimeError("STRIPE_SECRET_KEY is not configured or is empty.")
        if not self.STRIPE_PUBLISHABLE_KEY:
            raise RuntimeError("STRIPE_PUBLISHABLE_KEY is not configured or is empty.")
        if not self.STRIPE_WEBHOOK_SECRET:
            raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured or is empty.")

settings = Settings()
