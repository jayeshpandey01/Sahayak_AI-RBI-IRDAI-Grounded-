import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.ai.provider_clients import generate_grounded_answer
from app.ai.rate_limits import AIRateLimitExceeded, reserve_chat_request
from app.config import FREE_OPENROUTER_MODEL, Settings, settings
from app.models.db_models import AIRateLimitBucketModel
from app.models.schemas import LanguageCode


def test_config_rejects_paid_chat_model():
    with pytest.raises(ValueError, match="approved free model"):
        Settings(OPENROUTER_MODEL="anthropic/claude-sonnet-5.5")


def test_production_rollout_requires_quota_hash_key():
    with pytest.raises(ValueError, match="AI_RATE_LIMIT_HMAC_KEY is required"):
        Settings(
            ENVIRONMENT="production",
            AI_EXTERNAL_PROCESSING_ENABLED=True,
            AI_REAL_USER_ROLLOUT_APPROVED=True,
            AI_RATE_LIMIT_HMAC_KEY="",
        )


@pytest.mark.anyio
async def test_openrouter_request_is_pinned_and_privacy_filtered(monkeypatch):
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(settings, "OPENROUTER_MODEL", FREE_OPENROUTER_MODEL)
    monkeypatch.setattr(settings, "OPENROUTER_ENFORCE_ZDR", True)
    response = httpx.Response(200, request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"), json={
        "model": FREE_OPENROUTER_MODEL,
        "choices": [{"message": {"content": '{"answer":"Verified.","citation_ids":["s1"],"uncertainty":false}'}}],
    })
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=response) as post:
        answer = await generate_grounded_answer(
            "What is this?", LanguageCode.EN,
            [{"citation_id": "s1", "document_name": "Guide", "version": "v1", "clause": "1", "snippet": "Verified."}],
            [],
        )

    assert answer and answer.answer == "Verified."
    body = post.call_args.kwargs["json"]
    assert body["model"] == FREE_OPENROUTER_MODEL
    assert body["response_format"]["type"] == "json_schema"
    assert body["provider"] == {
        "data_collection": "deny", "zdr": True,
        "allow_fallbacks": False, "require_parameters": True,
    }


@pytest.mark.anyio
async def test_sarvam_asr_explicitly_disables_sdk_retries(monkeypatch):
    from app.ai import provider_clients

    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)
    monkeypatch.setattr(settings, "SARVAM_API_KEY", "test-key")
    transcribe = AsyncMock(return_value=SimpleNamespace(transcript="hello"))
    client = SimpleNamespace(speech_to_text=SimpleNamespace(transcribe=transcribe))
    with patch.object(provider_clients, "AsyncSarvamAI", return_value=client):
        result = await provider_clients.transcribe_audio(b"audio", "voice.wav", "audio/wav", LanguageCode.EN)
    assert result == "hello"
    assert transcribe.await_count == 1
    assert transcribe.call_args.kwargs["request_options"] == {"max_retries": 0}


def test_shared_quota_reserves_below_caps_and_rejects_extra(monkeypatch):
    test_engine = create_engine("sqlite://")
    AIRateLimitBucketModel.__table__.create(test_engine)
    test_session = sessionmaker(bind=test_engine)()
    monkeypatch.setattr(settings, "OPENROUTER_MINUTE_LIMIT", 2)
    monkeypatch.setattr(settings, "OPENROUTER_DAILY_LIMIT", 40)
    monkeypatch.setattr(settings, "AI_USER_HOURLY_LIMIT", 30)

    reserve_chat_request(test_session, "user-a")
    reserve_chat_request(test_session, "user-b")
    with pytest.raises(AIRateLimitExceeded):
        reserve_chat_request(test_session, "user-c")

    counts = {
        row.scope: row.request_count
        for row in test_session.query(AIRateLimitBucketModel).filter(AIRateLimitBucketModel.actor_hash == "global")
    }
    # Denied requests are recorded once and each bucket saturates at limit + 1.
    assert counts["global_minute"] == 3
    assert counts["global_day"] == 3
    test_session.close()
    test_engine.dispose()


def test_concurrent_chat_requests_never_exceed_shared_provider_limit(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'quota.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    AIRateLimitBucketModel.__table__.create(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(settings, "OPENROUTER_MINUTE_LIMIT", 10)
    monkeypatch.setattr(settings, "OPENROUTER_DAILY_LIMIT", 40)
    monkeypatch.setattr(settings, "AI_USER_HOURLY_LIMIT", 30)

    def reserve(index):
        session = sessions()
        try:
            reserve_chat_request(session, f"actor-{index}")
            return True
        except AIRateLimitExceeded:
            return False
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=8) as pool:
        accepted = list(pool.map(reserve, range(32)))
    assert sum(accepted) == 10
    with sessions() as session:
        minute = session.query(AIRateLimitBucketModel).filter_by(scope="global_minute", actor_hash="global").one()
        assert minute.request_count == 11  # capped at limit + one denied request
    engine.dispose()
