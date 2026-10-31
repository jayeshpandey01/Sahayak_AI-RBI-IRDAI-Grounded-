import base64
import json
from unittest.mock import AsyncMock, patch
import pytest
from app.ai.provider_clients import GroundedAnswer
from app.models.schemas import LanguageCode

VALID_WAV_HEADER = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"


def test_voice_chat_e2e_successful_regulatory_flow(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)

    with patch("app.services.voice_agent_service.transcribe_audio", new_callable=AsyncMock) as mock_stt, \
         patch("app.services.voice_agent_service.synthesize_speech", new_callable=AsyncMock) as mock_tts:
        
        mock_stt.return_value = "Can a recovery agent call me at night or harass me?"
        mock_tts.return_value = b"FAKE_SYNTHESIZED_MP3_AUDIO_BYTES"

        res = client.post(
            "/api/chat/voice/e2e",
            data={
                "language": "en",
                "allow_external_processing": "true",
            },
            files={"file": ("query.wav", VALID_WAV_HEADER, "audio/wav")}
        )

        assert res.status_code == 200
        data = res.json()
        assert data["transcript"] == "Can a recovery agent call me at night or harass me?"
        assert "recovery agents are strictly prohibited" in data["reply_text"].lower() or "08:00" in data["reply_text"]
        assert data["audio_base64"] is not None
        assert data["content_type"] == "audio/mpeg"
        assert data["rag_info"] is not None
        assert any(c["citation_id"] == "rbi_recovery_agents_conduct_v1" for c in data["rag_info"]["citations"])
        assert "timings" in data
        assert data["timings"]["total_ms"] >= 0


def test_voice_chat_underwriting_refusal_and_guardrails(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)

    with patch("app.services.voice_agent_service.transcribe_audio", new_callable=AsyncMock) as mock_stt, \
         patch("app.services.voice_agent_service.synthesize_speech", new_callable=AsyncMock) as mock_tts:
        
        mock_stt.return_value = "Will my loan be approved guaranteed?"
        mock_tts.return_value = b"FAKE_REFUSAL_AUDIO"

        res = client.post(
            "/api/chat/voice/e2e",
            data={
                "language": "en",
                "allow_external_processing": "true",
            },
            files={"file": ("query.wav", VALID_WAV_HEADER, "audio/wav")}
        )

        assert res.status_code == 200
        data = res.json()
        assert data["transcript"] == "Will my loan be approved guaranteed?"
        assert "cannot assess your creditworthiness" in data["reply_text"] or "decision" in data["reply_text"]
        assert data["human_handoff"] is not None
        assert data["human_handoff"]["escalation_level"] == "L1_UNDERWRITING_SPECIALIST"


def test_voice_chat_unsupported_audio_rejected(client):
    res = client.post(
        "/api/chat/voice/e2e",
        data={"language": "en", "allow_external_processing": "true"},
        files={"file": ("fake.txt", b"plain text", "text/plain")}
    )
    assert res.status_code == 415


def test_voice_chat_empty_audio_rejected(client):
    res = client.post(
        "/api/chat/voice/e2e",
        data={"language": "en", "allow_external_processing": "true"},
        files={"file": ("empty.wav", b"", "audio/wav")}
    )
    assert res.status_code == 422


def test_voice_chat_alias_endpoint(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)

    with patch("app.services.voice_agent_service.transcribe_audio", new_callable=AsyncMock) as mock_stt:
        mock_stt.return_value = "What is Key Fact Statement?"
        res = client.post(
            "/api/chat/voice/voice-chat",
            data={"language": "en", "allow_external_processing": "true"},
            files={"file": ("query.wav", VALID_WAV_HEADER, "audio/wav")}
        )
        assert res.status_code == 200
        data = res.json()
        assert "Key Fact Statement" in data["reply_text"]


def test_chat_endpoint_include_audio_generation(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)

    with patch("app.api.chat.generate_grounded_answer", new_callable=AsyncMock) as mock_gen, \
         patch("app.api.chat.synthesize_speech", new_callable=AsyncMock) as mock_tts:
        
        mock_gen.return_value = GroundedAnswer(
            answer="Under RBI Digital Lending Directions, regulated lenders must provide a standardized Key Fact Statement (KFS).",
            citation_ids=["rbi_digital_lending_kfs_v1"],
            uncertainty=False,
        )
        mock_tts.return_value = b"SYNTHESIZED_ANSWER_AUDIO"

        res = client.post(
            "/api/chat",
            json={
                "message": "What is the KFS rule under RBI?",
                "language": "en",
                "allow_external_processing": True,
                "include_audio": True,
            }
        )

        assert res.status_code == 200
        data = res.json()
        assert "Key Fact Statement" in data["reply"]
        assert data["audio_base64"] is not None
        decoded = base64.b64decode(data["audio_base64"])
        assert decoded == b"SYNTHESIZED_ANSWER_AUDIO"


def test_voice_demo_html_endpoint(client):
    res = client.get("/api/chat/voice/demo")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Sahayak AI — Realtime Voice Agent Demo" in res.text
    assert "Sarvam AI" in res.text


def test_websocket_voice_stream_lifecycle(client):
    with client.websocket_connect("/api/chat/voice/ws") as websocket:
        # Handshake
        websocket.send_json({"type": "init", "language": "en", "allow_external_processing": True})
        ready_msg = websocket.receive_json()
        assert ready_msg["event"] == "ready"

        # Send text turn over websocket
        websocket.send_json({
            "type": "text",
            "message": "What is cooling off period under RBI rules?",
            "include_audio": False
        })

        processing_msg = websocket.receive_json()
        assert processing_msg["event"] == "processing"

        completed_msg = websocket.receive_json()
        assert completed_msg["event"] == "completed"
        assert "cooling-off" in completed_msg["reply_text"].lower()
        assert completed_msg["rag_info"] is not None


@pytest.mark.asyncio
async def test_google_tts_fallback_when_sarvam_unconfigured(monkeypatch):
    """Verify that synthesize_speech gracefully falls back to Google TTS when SARVAM_API_KEY is missing."""
    import httpx
    from app.config import settings
    from app.ai.provider_clients import synthesize_speech

    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)
    monkeypatch.setattr(settings, "SARVAM_API_KEY", "")

    mock_mp3 = b"\xff\xfb\x90\x00FAKE_MP3_FRAME_DATA"
    mock_resp = httpx.Response(
        status_code=200,
        content=mock_mp3,
        request=httpx.Request("GET", "https://translate.google.com/translate_tts"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        audio_bytes = await synthesize_speech("Hello, I am Sahayak AI.", LanguageCode.EN)
        assert len(audio_bytes) > 0
        assert mock_mp3 in audio_bytes


def test_voice_chat_synthesizes_speech_on_fallback_or_empty_transcript(client, monkeypatch):
    """Verify that even when STT returns empty or query is unknown, Voice Agent still speaks the fallback aloud."""
    from app.config import settings

    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)

    with patch("app.services.voice_agent_service.transcribe_audio", new_callable=AsyncMock) as mock_stt, \
         patch("app.services.voice_agent_service.synthesize_speech", new_callable=AsyncMock) as mock_tts:

        mock_stt.return_value = ""  # Silent or unrecognizable audio
        mock_tts.return_value = b"SYNTHESIZED_FALLBACK_AUDIO"

        res = client.post(
            "/api/chat/voice/e2e",
            data={"language": "en", "allow_external_processing": "true"},
            files={"file": ("query.wav", VALID_WAV_HEADER, "audio/wav")}
        )

        assert res.status_code == 200
        data = res.json()
        assert data["transcript"] == ""
        assert "reliable approved source" in data["reply_text"].lower() or "person" in data["reply_text"].lower()
        # Voice agent must reply with voice even on fallback!
        assert data["audio_base64"] is not None
        assert base64.b64decode(data["audio_base64"]) == b"SYNTHESIZED_FALLBACK_AUDIO"


def test_voice_chat_accepts_browser_mime_with_codecs(client, monkeypatch):
    """Verify that browser MediaRecorder content types like audio/webm;codecs=opus are accepted."""
    from app.config import settings

    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)

    with patch("app.services.voice_agent_service.transcribe_audio", new_callable=AsyncMock) as mock_stt, \
         patch("app.services.voice_agent_service.synthesize_speech", new_callable=AsyncMock) as mock_tts:

        mock_stt.return_value = "What is Key Fact Statement?"
        mock_tts.return_value = b"FAKE_AUDIO_BYTES"

        res = client.post(
            "/api/chat/voice/e2e",
            data={"language": "en", "allow_external_processing": "true"},
            files={"file": ("recording.webm", VALID_WAV_HEADER, "audio/webm;codecs=opus")}
        )

        assert res.status_code == 200
        data = res.json()
        assert data["transcript"] == "What is Key Fact Statement?"


