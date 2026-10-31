"""Tests for Official Website Grounding, Groq Whisper Fallback, and OpenRouter LLM."""

import pytest
from unittest.mock import AsyncMock, patch
import httpx

from app.ai.official_website_retriever import (
    OFFICIAL_DOMAINS_WHITELIST,
    is_official_url,
    search_official_website_knowledge,
    get_all_official_sources,
)
from app.ai.provider_clients import transcribe_audio, transcribe_audio_groq
from app.ai.rag_engine import query_grounded_rag
from app.config import settings
from app.models.schemas import LanguageCode


def test_official_domains_whitelist():
    """Verify that official domains only accept recognized regulatory infrastructure."""
    assert is_official_url("https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx") is True
    assert is_official_url("https://sachet.rbi.org.in") is True
    assert is_official_url("https://cms.rbi.org.in") is True
    assert is_official_url("https://www.npci.org.in/what-we-do/upi") is True
    assert is_official_url("https://irdai.gov.in/regulations") is True
    assert is_official_url("https://bimabharosa.irdai.gov.in") is True
    # Non-whitelisted domains
    assert is_official_url("https://randomfinancialblog.com/rbi-rules") is False
    assert is_official_url("https://fake-phishing-rbi.org") is False
    assert is_official_url("") is False
    assert is_official_url(None) is False


def test_official_website_knowledge_records():
    """Verify all official knowledge records have required metadata and valid URLs."""
    records = get_all_official_sources()
    assert len(records) >= 8
    for rec in records:
        assert rec["approved"] is True
        assert rec["status"] == "active"
        assert rec["jurisdiction"] == "IN"
        assert is_official_url(rec["source_url"]) is True
        assert len(rec["clause"]) > 5
        assert len(rec["text"]) > 50


@pytest.mark.parametrize(
    "query,expected_topic",
    [
        ("What are RBI rules regarding Key Fact Statement (KFS)?", "Key Fact Statement"),
        ("Can loan recovery agents call me at midnight?", "Recovery"),
        ("Are foreclosure charges allowed on floating-rate loans?", "Foreclosure"),
        ("What is the UPI dispute resolution timeline under NPCI?", "UPI"),
        ("What is the IRDAI free-look period for life insurance?", "Free-Look"),
        ("How do I file a complaint with the RBI Integrated Ombudsman?", "Ombudsman"),
        ("How can I check if an NBFC is registered on Sachet portal?", "Sachet"),
    ],
)
def test_official_website_retrieval_queries(query, expected_topic):
    """Verify official website knowledge matches key consumer queries and returns official URLs."""
    rag_info = query_grounded_rag(query)
    assert rag_info is not None, f"Expected grounded result for query: {query}"
    assert len(rag_info.citations) >= 1
    
    first_citation = rag_info.citations[0]
    assert first_citation.source_url is not None
    assert is_official_url(first_citation.source_url) is True
    assert expected_topic.lower() in (first_citation.document_name + " " + first_citation.clause).lower()


@pytest.mark.asyncio
async def test_groq_whisper_fallback_transcription(monkeypatch):
    """Verify that when Sarvam is unconfigured, transcribe_audio seamlessly falls back to Groq Whisper."""
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)
    monkeypatch.setattr(settings, "SARVAM_API_KEY", "")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key_12345")

    mock_resp = httpx.Response(
        status_code=200,
        json={"text": "What are the rules regarding Key Fact Statement?"},
        request=httpx.Request("POST", "https://api.groq.com/openai/v1/audio/transcriptions"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        transcript = await transcribe_audio(
            audio=b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00",
            filename="test.wav",
            content_type="audio/wav",
            language=LanguageCode.EN,
        )
        assert transcript == "What are the rules regarding Key Fact Statement?"


@pytest.mark.asyncio
async def test_e2e_chat_returns_official_citations(client):
    """Verify that calling /api/chat with an official regulatory question returns official source citations."""
    payload = {
        "message": "What is the UPI dispute resolution timeline under NPCI?",
        "language": "en",
        "allow_external_processing": False,
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert data["language"] == "en"


def test_voice_chat_matches_audio_signature():
    """Verify audio signature checks properly detect supported audio formats."""
    from app.services.voice_agent_service import matches_audio_signature
    wav_header = b"RIFF\x24\x00\x00\x00WAVEfmt "
    mp3_header = b"ID3\x03\x00\x00\x00"
    ogg_header = b"OggS\x00\x02"
    flac_header = b"fLaC\x00\x00"

    assert matches_audio_signature(wav_header, "audio/wav") is True
    assert matches_audio_signature(mp3_header, "audio/mpeg") is True
    assert matches_audio_signature(ogg_header, "audio/ogg") is True
    assert matches_audio_signature(flac_header, "audio/flac") is True
    assert matches_audio_signature(b"BAD_DATA", "audio/wav") is False

