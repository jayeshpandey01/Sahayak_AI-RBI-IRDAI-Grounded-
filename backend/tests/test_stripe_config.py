import pytest
from pydantic import ValidationError
from app.config import Settings


def test_valid_test_credentials():
    """Verify that correctly formatted test-mode keys pass validation."""
    s = Settings(
        STRIPE_MODE="test",
        STRIPE_SECRET_KEY="sk_test_sample1234567890",
        STRIPE_PUBLISHABLE_KEY="pk_test_sample1234567890",
        STRIPE_WEBHOOK_SECRET="whsec_sample1234567890",
    )
    assert s.STRIPE_MODE == "test"
    assert s.STRIPE_SECRET_KEY.startswith("sk_test_")
    assert s.STRIPE_PUBLISHABLE_KEY.startswith("pk_test_")
    assert s.STRIPE_WEBHOOK_SECRET.startswith("whsec_")
    # Should not raise
    s.validate_stripe_credentials()


def test_restricted_key_in_test_mode():
    """Verify that restricted test keys (rk_test_...) are accepted."""
    s = Settings(
        STRIPE_MODE="test",
        STRIPE_SECRET_KEY="rk_test_restricted12345",
        STRIPE_PUBLISHABLE_KEY="pk_test_sample12345",
        STRIPE_WEBHOOK_SECRET="whsec_sample12345",
    )
    assert s.STRIPE_SECRET_KEY.startswith("rk_test_")


def test_env_string_sanitization():
    """Verify that whitespace and enclosing quotes are safely stripped."""
    s = Settings(
        STRIPE_MODE=' "test" ',
        STRIPE_SECRET_KEY=" 'sk_test_clean_me' ",
        STRIPE_PUBLISHABLE_KEY=' "pk_test_clean_me" ',
        STRIPE_WEBHOOK_SECRET=" 'whsec_clean_me' ",
    )
    assert s.STRIPE_MODE == "test"
    assert s.STRIPE_SECRET_KEY == "sk_test_clean_me"
    assert s.STRIPE_PUBLISHABLE_KEY == "pk_test_clean_me"
    assert s.STRIPE_WEBHOOK_SECRET == "whsec_clean_me"


def test_mode_mismatch_test_mode_with_live_secret():
    """Verify that supplying sk_live_ when mode is 'test' fails immediately."""
    with pytest.raises(ValidationError, match="Mode mismatch: Live key supplied while STRIPE_MODE is 'test'"):
        Settings(
            STRIPE_MODE="test",
            STRIPE_SECRET_KEY="sk_live_accidental_live_key",
            STRIPE_PUBLISHABLE_KEY="pk_test_sample",
            STRIPE_WEBHOOK_SECRET="whsec_sample",
        )


def test_mode_mismatch_test_mode_with_live_publishable():
    """Verify that supplying pk_live_ when mode is 'test' fails immediately."""
    with pytest.raises(ValidationError, match="Mode mismatch: Live key supplied while STRIPE_MODE is 'test'"):
        Settings(
            STRIPE_MODE="test",
            STRIPE_SECRET_KEY="sk_test_sample",
            STRIPE_PUBLISHABLE_KEY="pk_live_accidental_live_key",
            STRIPE_WEBHOOK_SECRET="whsec_sample",
        )


def test_mode_mismatch_live_mode_with_test_key():
    """Verify that supplying sk_test_ when mode is 'live' fails immediately."""
    with pytest.raises(ValidationError, match="Mode mismatch: Test key supplied while STRIPE_MODE is 'live'"):
        Settings(
            STRIPE_MODE="live",
            STRIPE_LIVE_ENABLED=True,
            STRIPE_FINANCIAL_SERVICES_APPROVED=True,
            STRIPE_SECRET_KEY="sk_test_test_key_in_live",
            STRIPE_PUBLISHABLE_KEY="pk_live_sample",
            STRIPE_WEBHOOK_SECRET="whsec_sample",
        )


def test_live_mode_gate_without_flag():
    """Verify that live mode fails closed if STRIPE_LIVE_ENABLED is False."""
    with pytest.raises(ValidationError, match="Stripe live mode requires explicit STRIPE_LIVE_ENABLED=true"):
        Settings(
            STRIPE_MODE="live",
            STRIPE_LIVE_ENABLED=False,
            STRIPE_SECRET_KEY="sk_live_sample",
            STRIPE_PUBLISHABLE_KEY="pk_live_sample",
            STRIPE_WEBHOOK_SECRET="whsec_sample",
        )


def test_live_mode_requires_financial_services_approval():
    """Live credentials alone cannot turn on wallet/lending transactions."""
    with pytest.raises(ValidationError, match="requires explicit written provider approval"):
        Settings(
            STRIPE_MODE="live",
            STRIPE_LIVE_ENABLED=True,
            STRIPE_SECRET_KEY="sk_live_sample",
            STRIPE_PUBLISHABLE_KEY="pk_live_sample",
            STRIPE_WEBHOOK_SECRET="whsec_sample",
        )


def test_invalid_mode_rejected():
    """Verify that modes other than 'test' or 'live' are rejected."""
    with pytest.raises(ValidationError, match="Invalid STRIPE_MODE 'sandbox'"):
        Settings(
            STRIPE_MODE="sandbox",
            STRIPE_SECRET_KEY="sk_test_sample",
        )


def test_invalid_webhook_secret_prefix():
    """Verify that webhook secrets must start with 'whsec_'."""
    with pytest.raises(ValidationError, match="STRIPE_WEBHOOK_SECRET must start with 'whsec_'"):
        Settings(
            STRIPE_MODE="test",
            STRIPE_SECRET_KEY="sk_test_sample",
            STRIPE_PUBLISHABLE_KEY="pk_test_sample",
            STRIPE_WEBHOOK_SECRET="invalid_secret_without_prefix",
        )


def test_validate_stripe_credentials_runtime_check():
    """Verify that validate_stripe_credentials raises RuntimeError if any key is missing."""
    s = Settings(
        STRIPE_MODE="test",
        STRIPE_SECRET_KEY="",
        STRIPE_PUBLISHABLE_KEY="pk_test_sample",
        STRIPE_WEBHOOK_SECRET="whsec_sample",
    )
    with pytest.raises(RuntimeError, match="STRIPE_SECRET_KEY is not configured or is empty"):
        s.validate_stripe_credentials()


def test_runtime_live_payment_gate_requires_provider_approval():
    """The runtime guard remains effective if settings are changed after construction."""
    s = Settings(
        STRIPE_MODE="test",
        STRIPE_SECRET_KEY="sk_test_sample",
        STRIPE_PUBLISHABLE_KEY="pk_test_sample",
        STRIPE_WEBHOOK_SECRET="whsec_sample",
    )
    s.STRIPE_MODE = "live"
    s.STRIPE_LIVE_ENABLED = True
    with pytest.raises(RuntimeError, match="explicit written provider approval"):
        s.validate_stripe_credentials()


def test_payment_intent_fails_closed_without_provider_credentials(monkeypatch):
    from app.config import settings
    from app.services.stripe_service import StripeServiceError, create_stripe_payment_intent

    monkeypatch.setattr(settings, "STRIPE_MODE", "test")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "")
    monkeypatch.setattr(settings, "STRIPE_PUBLISHABLE_KEY", "")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "")
    with pytest.raises(StripeServiceError, match="STRIPE_SECRET_KEY is not configured"):
        create_stripe_payment_intent(amount_paise=10000)


def test_no_actual_secrets_in_example_files():
    """Verify that .env.example files only contain non-sensitive placeholders."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    backend_example = (repo_root / "backend/.env.example").read_text()
    smartbank_path = repo_root / "smartbank/.env.example"
    smartbank_example = smartbank_path.read_text() if smartbank_path.exists() else ""

    # Neither file should have real secret prefixes with populated entropy
    assert "sk_live_" not in backend_example
    assert "sk_live_" not in smartbank_example
    assert "whsec_5" not in backend_example  # typical real Stripe CLI generated format

    # Smartbank example should never have secret or webhook keys
    if smartbank_example:
        assert "STRIPE_SECRET_KEY" not in smartbank_example
        assert "STRIPE_WEBHOOK_SECRET" not in smartbank_example

