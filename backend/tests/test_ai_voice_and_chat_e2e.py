import base64
import io
import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import httpx
from app.models.schemas import LanguageCode
from app.models.db_models import DemoRepaymentModel, JourneyModel, UserLoanModel, UserModel
from app.services.auth_service import hash_password, create_access_token
from app.services.voice_agent_service import process_text_chat, process_voice_chat

@pytest.fixture
def test_users(db_session):
    u1 = UserModel(
        id=f"usr_owner_{uuid4().hex[:8]}",
        email=f"owner_{uuid4().hex[:8]}@sahayak.test",
        password_hash=hash_password("OwnerSecurePass123!"),
        full_name="Owner User",
        is_active=True,
    )
    u2 = UserModel(
        id=f"usr_attacker_{uuid4().hex[:8]}",
        email=f"attacker_{uuid4().hex[:8]}@sahayak.test",
        password_hash=hash_password("AttackerSecurePass123!"),
        full_name="Attacker User",
        is_active=True,
    )
    db_session.add_all([u1, u2])
    db_session.commit()
    db_session.refresh(u1)
    db_session.refresh(u2)
    return {
        "owner": u1,
        "owner_token": create_access_token(u1.id, u1.email),
        "attacker": u2,
        "attacker_token": create_access_token(u2.id, u2.email),
    }

@pytest.fixture
def private_journey(db_session, test_users):
    journey = JourneyModel(
        id=f"jrn_priv_{uuid4().hex[:8]}",
        user_id=test_users["owner"].id,
        language="en",
        loan_amount=150000.0,
        preferred_tenure_months=24,
        purpose="Medical",
    )
    db_session.add(journey)
    db_session.commit()
    db_session.refresh(journey)
    return journey

# ----------------- CHAT ENDPOINT & IDOR TESTS -----------------

def test_chat_anonymous_access_without_journey(client):
    res = client.post("/api/chat", json={
        "message": "What does Sahayak do?",
        "language": "en",
        "allow_external_processing": False
    })
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert data["language"] == "en"

def test_chat_idor_unauthenticated_cannot_access_private_journey(client, private_journey):
    res = client.post("/api/chat", json={
        "message": "Help me with my loan",
        "journey_id": private_journey.id,
        "language": "en"
    })
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]

def test_chat_idor_cross_tenant_cannot_access_private_journey(client, private_journey, test_users):
    res = client.post(
        "/api/chat",
        json={
            "message": "Help me with my loan",
            "journey_id": private_journey.id,
            "language": "en"
        },
        headers={"Authorization": f"Bearer {test_users['attacker_token']}"}
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]

def test_chat_owner_can_access_private_journey(client, private_journey, test_users):
    res = client.post(
        "/api/chat",
        json={
            "message": "What is Sahayak scope?",
            "journey_id": private_journey.id,
            "language": "en",
            "allow_external_processing": False
        },
        headers={"Authorization": f"Bearer {test_users['owner_token']}"}
    )
    assert res.status_code == 200
    assert "reply" in res.json()

def test_chat_underwriting_refusal_marks_human_review_on_journey(client, private_journey, test_users, db_session):
    res = client.post(
        "/api/chat",
        json={
            "message": "Can you guarantee approval for my loan application?",
            "journey_id": private_journey.id,
            "language": "en"
        },
        headers={"Authorization": f"Bearer {test_users['owner_token']}"}
    )
    assert res.status_code == 200
    assert res.json()["human_handoff"] is not None
    db_session.refresh(private_journey)
    assert private_journey.human_review_required is True
    assert "underwriting decision" in private_journey.human_review_reason

def test_chat_home_loan_advice_uses_authenticated_db_profile(client, private_journey, test_users, db_session):
    owner = test_users["owner"]
    db_session.add(UserLoanModel(
        id=f"loan_profile_{uuid4().hex[:8]}", user_id=owner.id,
        lender_name="Example Bank", lender_type="BANK", loan_type="PERSONAL",
        account_number="PL-PRIVATE-1234", original_principal=300000,
        outstanding_principal=195000, interest_rate_percent=12.5,
        tenure_months=36, remaining_tenure_months=22, emi_amount=10037,
        emi_due_day=5, next_due_date="2026-11-05", status="ACTIVE",
        notes="SIMULATED DEMO DATA ONLY — not a real lender account",
    ))
    db_session.add(DemoRepaymentModel(
        id=f"repay_profile_{uuid4().hex[:8]}", user_id=owner.id,
        journey_id=private_journey.id, due_at=datetime.now(timezone.utc),
        amount_paise=1003700, status="PAID_ON_TIME", source="simulation",
    ))
    db_session.commit()

    response = client.post(
        "/api/chat",
        json={
            "message": "According to the DB can you suggest should I take home loan?",
            "language": "en",
            "allow_external_processing": False,
        },
        headers={"Authorization": f"Bearer {test_users['owner_token']}"},
    )

    assert response.status_code == 200
    reply = response.json()["reply"]
    assert "Example Bank" in reply
    assert "₹10,037/month" in reply
    assert "₹195,000" in reply
    assert "simulated demo record" in reply
    assert "no home-loan products" in reply
    assert "does not contain monthly take-home income" in reply
    assert "PL-PRIVATE-1234" not in reply

def test_voice_text_and_transcribed_chat_use_the_same_profile_db_answer(private_journey, test_users, db_session):
    owner = test_users["owner"]
    db_session.add(UserLoanModel(
        id=f"loan_voice_{uuid4().hex[:8]}", user_id=owner.id,
        lender_name="Voice Test Bank", lender_type="BANK", loan_type="PERSONAL",
        account_number="VOICE-PRIVATE-1234", original_principal=200000,
        outstanding_principal=120000, interest_rate_percent=12,
        tenure_months=24, remaining_tenure_months=12, emi_amount=9500,
        emi_due_day=5, next_due_date="2026-11-05", status="ACTIVE",
    ))
    db_session.commit()
    question = "According to the DB can you suggest should I take home loan?"

    text_response = asyncio.run(process_text_chat(
        message=question, language=LanguageCode.EN, allow_external_processing=False,
        db=db_session, current_user=owner,
    ))
    voice_response = asyncio.run(process_voice_chat(
        audio_bytes=b"", content_type="audio/wav", language=LanguageCode.EN,
        allow_external_processing=False, db=db_session, current_user=owner,
        client_transcript=question,
    ))

    assert "Voice Test Bank" in text_response.reply_text
    assert "₹9,500/month" in text_response.reply_text
    assert text_response.reply_text == voice_response.reply_text

# ----------------- IDEMPOTENCY BYPASS TESTS -----------------

def test_chat_bypasses_idempotency_cache(client):
    idempotency_key = f"key_chat_{uuid4().hex}"
    headers = {"X-Idempotency-Key": idempotency_key}
    payload = {
        "message": "What does Sahayak do?",
        "language": "en",
        "allow_external_processing": False
    }

    res1 = client.post("/api/chat", json=payload, headers=headers)
    assert res1.status_code == 200
    assert "X-Cache-Lookup" not in res1.headers

    res2 = client.post("/api/chat", json=payload, headers=headers)
    assert res2.status_code == 200
    assert res2.headers.get("X-Cache-Lookup") != "IDEMPOTENCY_HIT"

def test_voice_speak_bypasses_idempotency_cache(client):
    idempotency_key = f"key_voice_{uuid4().hex}"
    headers = {"X-Idempotency-Key": idempotency_key}
    data = {
        "text": "Hello world",
        "language": "en",
        "allow_external_processing": "false"
    }

    res = client.post("/api/chat/voice/speak", data=data, headers=headers)
    assert res.status_code == 403
    assert "X-Cache-Lookup" not in res.headers

# ----------------- VOICE TRANSCRIBE TESTS -----------------

def test_voice_transcribe_consent_required(client):
    fake_wav = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 20
    res = client.post(
        "/api/chat/voice/transcribe",
        data={"language": "en", "allow_external_processing": "false"},
        files={"file": ("test.wav", fake_wav, "audio/wav")}
    )
    assert res.status_code == 403
    assert "External AI processing consent is required" in res.json()["detail"]

def test_voice_transcribe_service_disabled(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", False)
    fake_wav = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 20
    res = client.post(
        "/api/chat/voice/transcribe",
        data={"language": "en", "allow_external_processing": "true"},
        files={"file": ("test.wav", fake_wav, "audio/wav")}
    )
    assert res.status_code == 503
    assert "Voice services are not enabled" in res.json()["detail"]

def test_voice_transcribe_unsupported_mimetype(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)
    res = client.post(
        "/api/chat/voice/transcribe",
        data={"language": "en", "allow_external_processing": "true"},
        files={"file": ("test.txt", b"plain text", "text/plain")}
    )
    assert res.status_code == 415
    assert "Unsupported audio format" in res.json()["detail"]

def test_voice_transcribe_mime_spoofing_detected(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)
    # Claims to be audio/wav but doesn't have RIFF....WAVE header
    fake_audio = b"MALICIOUS_BYTES_NOT_A_WAV_FILE"
    res = client.post(
        "/api/chat/voice/transcribe",
        data={"language": "en", "allow_external_processing": "true"},
        files={"file": ("spoof.wav", fake_audio, "audio/wav")}
    )
    assert res.status_code == 415
    assert "does not match its declared format" in res.json()["detail"]

def test_voice_transcribe_success_mocked(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)
    fake_wav = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 20

    with patch("app.api.voice.transcribe_audio", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = "Mujhe personal loan chahiye"
        res = client.post(
            "/api/chat/voice/transcribe",
            data={"language": "hinglish", "allow_external_processing": "true"},
            files={"file": ("audio.wav", fake_wav, "audio/wav")}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["transcript"] == "Mujhe personal loan chahiye"
        assert data["language"] == "hinglish"
        assert data["requires_user_review"] is True

# ----------------- VOICE SPEAK TESTS -----------------

def test_voice_speak_consent_required(client):
    res = client.post(
        "/api/chat/voice/speak",
        data={"text": "Hello world", "language": "en", "allow_external_processing": "false"}
    )
    assert res.status_code == 403
    assert "External AI processing consent is required" in res.json()["detail"]

def test_voice_speak_service_disabled(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", False)
    res = client.post(
        "/api/chat/voice/speak",
        data={"text": "Hello world", "language": "en", "allow_external_processing": "true"}
    )
    assert res.status_code == 503
    assert "Voice services are not enabled" in res.json()["detail"]

def test_voice_speak_empty_text(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)
    res = client.post(
        "/api/chat/voice/speak",
        data={"text": "   ", "language": "en", "allow_external_processing": "true"}
    )
    assert res.status_code == 422
    assert "Text is required" in res.json()["detail"]

def test_voice_speak_success_mocked(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)

    with patch("app.api.voice.synthesize_speech", new_callable=AsyncMock) as mock_synthesize:
        mock_synthesize.return_value = b"\xff\xfb\x90\x00" + b"\x00" * 50  # mock mp3 bytes
        res = client.post(
            "/api/chat/voice/speak",
            data={"text": "Namaste Sahayak", "language": "hi", "allow_external_processing": "true"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "audio_base64" in data
        assert data["content_type"] == "audio/mpeg"
        assert data["language"] == "hi"

# ----------------- PII SANITIZATION TESTS -----------------

def test_pii_sanitization_patterns():
    from app.ai.provider_clients import sanitize_provider_text

    text = "User ABCDE1234F with phone 9876543210 and email user@example.com asked about ₹50,000 for acct: 123456789012"
    sanitized = sanitize_provider_text(text)
    assert "[PAN REDACTED]" in sanitized
    assert "ABCDE1234F" not in sanitized
    assert "[PHONE REDACTED]" in sanitized
    assert "9876543210" not in sanitized
    assert "[EMAIL REDACTED]" in sanitized
    assert "user@example.com" not in sanitized
    assert "[AMOUNT REDACTED]" in sanitized
    assert "50,000" not in sanitized
    assert "[ACCOUNT REDACTED]" in sanitized
    assert "123456789012" not in sanitized

def test_voice_transcribe_empty_audio_returns_422(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)
    res = client.post(
        "/api/chat/voice/transcribe",
        data={"language": "en", "allow_external_processing": "true"},
        files={"file": ("empty.wav", b"", "audio/wav")}
    )
    assert res.status_code == 422
    assert "Audio content is empty" in res.json()["detail"]

def test_native_hindi_devanagari_retrieval():
    from app.ai.rag_engine import query_grounded_rag
    result = query_grounded_rag("क्या मेरा लोन मिलेगा")
    assert result is not None
    assert len(result.citations) > 0
    assert any("sahayak_scope_v1" == c.citation_id for c in result.citations)

