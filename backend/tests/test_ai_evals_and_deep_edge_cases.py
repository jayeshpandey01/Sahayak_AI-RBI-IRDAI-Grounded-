import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
import httpx
from app.ai.provider_clients import GroundedAnswer, sanitize_provider_text
from app.ai.rag_engine import query_grounded_rag
from app.api.chat import _contains_untrusted_number, _validated_citations
from app.models.schemas import GroundedCitation, GroundedRAGResponse, LanguageCode

# -------------------------------------------------------------
# 1. EVALUATION SUITE: ai_cases.v1.jsonl HARNESS
# -------------------------------------------------------------

def test_evaluation_cases_from_jsonl():
    evals_path = Path(__file__).resolve().parent.parent / "evals" / "ai_cases.v1.jsonl"
    assert evals_path.exists(), "ai_cases.v1.jsonl must exist"

    cases = []
    with open(evals_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

    assert len(cases) == 17, "Expected 17 evaluation cases in ai_cases.v1.jsonl"

    for case in cases:
        query = case["query"]
        expected_ids = case["expected_source_ids"]
        risk = case["risk"]

        if risk == "underwriting":
            from app.ai.guardrails import check_underwriting_guardrails
            is_blocked, refusal, _ = check_underwriting_guardrails(query)
            assert is_blocked is True
            assert refusal is not None
        elif expected_ids:
            rag = query_grounded_rag(query)
            assert rag is not None, f"Failed retrieval for query: {query}"
            retrieved_ids = [c.citation_id for c in rag.citations]
            assert any(eid in retrieved_ids for eid in expected_ids), (
                f"Expected one of {expected_ids} but got {retrieved_ids} for query: {query}"
            )

# -------------------------------------------------------------
# 2. UNTRUSTED NUMBER & HALLUCINATION REJECTION TESTS
# -------------------------------------------------------------

def test_untrusted_number_detection_flags_hallucinated_amounts():
    citations = [
        GroundedCitation(
            citation_id="doc1",
            document_name="Policy",
            version="2026-v1",
            clause="Terms",
            snippet="The maximum allowed tenure is 36 months under rule 2026."
        )
    ]
    # Allowed numbers: 36, 2026

    # Hallucinated interest rate or EMI number "4500" not in snippet:
    hallucinated_answer = "Your monthly EMI will be 4,500 rupees for 36 months."
    assert _contains_untrusted_number(hallucinated_answer, citations) is True

    # Safe answer containing only cited numbers:
    safe_answer = "Under policy 2026, the maximum tenure allowed is 36 months."
    assert _contains_untrusted_number(safe_answer, citations) is False

def test_untrusted_number_detection_with_no_numbers():
    citations = [
        GroundedCitation(
            citation_id="doc1",
            document_name="Policy",
            version="2026-v1",
            clause="Terms",
            snippet="Sahayak is an informational assistant, not a lender."
        )
    ]
    answer = "Sahayak cannot approve your loan."
    assert _contains_untrusted_number(answer, citations) is False

def test_citation_validation_rejects_forged_citations():
    rag_info = GroundedRAGResponse(
        answer="Approved source text",
        citations=[
            GroundedCitation(
                citation_id="sahayak_scope_v1",
                document_name="Policy",
                version="2026-v1",
                clause="Scope",
                snippet="Approved snippet"
            )
        ],
        source_documents=["Policy (2026-v1)"],
        confidence=0.9,
        disclaimer="Disclaimer"
    )

    # Valid citation id from evidence:
    valid = _validated_citations(rag_info, ["sahayak_scope_v1"])
    assert len(valid) == 1
    assert valid[0].citation_id == "sahayak_scope_v1"

    # Forged citation id hallucinated by LLM:
    forged = _validated_citations(rag_info, ["fabricated_law_v9"])
    assert len(forged) == 0

    # Mixed valid + forged citation IDs fails completely:
    mixed = _validated_citations(rag_info, ["sahayak_scope_v1", "fabricated_law_v9"])
    assert len(mixed) == 0

# -------------------------------------------------------------
# 3. CONVERSATION TURN BOUNDARY & PROMPT EXHAUSTION DEFENSE
# -------------------------------------------------------------

def test_conversation_character_limit_validation():
    from app.models.schemas import ChatInputRequest, ConversationTurn
    # Valid 8 turns with 1000 chars each:
    turns = [ConversationTurn(role="user", content="A" * 1000) for _ in range(8)]
    req = ChatInputRequest(message="test", conversation=turns)
    assert len(req.conversation) == 8

    # Over 8000 total characters raises ValueError:
    with pytest.raises(ValueError, match="exceeds the session limit"):
        ChatInputRequest.limit_conversation_chars(turns + [ConversationTurn(role="user", content="B")])

def test_conversation_turn_count_limit_api(client):
    # A conversation exceeding 8 turns must be rejected by Pydantic max_length (422):
    turns = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"Turn {i}"} for i in range(9)]
    res = client.post("/api/chat", json={
        "message": "Hello",
        "conversation": turns
    })
    assert res.status_code == 422
    assert "at most 8 items" in str(res.json())

# -------------------------------------------------------------
# 4. PROVIDER OUTAGE & RESILIENCE TESTS (OpenRouter & Sarvam)
# -------------------------------------------------------------

def test_chat_openrouter_http_error_falls_closed(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "sk-or-test-key")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # Simulate OpenRouter 502 Bad Gateway
        mock_post.side_effect = httpx.HTTPStatusError("Bad Gateway", request=None, response=httpx.Response(502))
        res = client.post("/api/chat", json={
            "message": "What does Sahayak do?",
            "language": "en",
            "allow_external_processing": True
        })
        assert res.status_code == 200
        data = res.json()
        assert "temporarily unavailable" in data["reply"]

def test_chat_openrouter_timeout_falls_closed(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "sk-or-test-key")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Connection timed out")
        res = client.post("/api/chat", json={
            "message": "What does Sahayak do?",
            "language": "en",
            "allow_external_processing": True
        })
        assert res.status_code == 200
        data = res.json()
        assert "temporarily unavailable" in data["reply"]

def test_chat_openrouter_uncertainty_flag_returns_fallback(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "sk-or-test-key")

    with patch("app.api.chat.generate_grounded_answer", new_callable=AsyncMock) as mock_answer:
        mock_answer.return_value = GroundedAnswer(
            answer="I am not sure about this policy.",
            citation_ids=[],
            uncertainty=True
        )
        res = client.post("/api/chat", json={
            "message": "What does Sahayak do?",
            "language": "en",
            "allow_external_processing": True
        })
        assert res.status_code == 200
        data = res.json()
        # Uncertainty flag triggers safe fallback:
        assert "don't have a reliable approved source" in data["reply"]

def test_chat_openrouter_untrusted_number_rejects_answer(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "sk-or-test-key")

    with patch("app.api.chat.generate_grounded_answer", new_callable=AsyncMock) as mock_answer:
        mock_answer.return_value = GroundedAnswer(
            answer="Your interest rate is guaranteed at 7.5% per annum.",
            citation_ids=["sahayak_scope_v1"],
            uncertainty=False
        )
        res = client.post("/api/chat", json={
            "message": "What does Sahayak do?",
            "language": "en",
            "allow_external_processing": True
        })
        assert res.status_code == 200
        data = res.json()
        assert "temporarily unavailable" in data["reply"]

# -------------------------------------------------------------
# 5. ALL AUDIO FORMAT MAGIC BYTES RECOGNITION & REJECTION
# -------------------------------------------------------------

@pytest.mark.parametrize("content_type, magic_bytes", [
    ("audio/wav", b"RIFF\x24\x00\x00\x00WAVEfmt "),
    ("audio/x-wav", b"RIFF\x24\x00\x00\x00WAVEfmt "),
    ("audio/mpeg", b"ID3\x03\x00\x00\x00\x00\x00\x00"),
    ("audio/mpeg", b"\xff\xfb\x90\x00" + b"\x00" * 20),
    ("audio/mp4", b"\x00\x00\x00\x18ftypisom" + b"\x00" * 10),
    ("audio/x-m4a", b"\x00\x00\x00\x20ftypM4A " + b"\x00" * 10),
    ("audio/aac", b"\xff\xf1\x50\x80" + b"\x00" * 20),
    ("audio/ogg", b"OggS\x00\x02\x00\x00" + b"\x00" * 20),
    ("audio/webm", bytes.fromhex("1a45dfa3") + b"\x00" * 20),
    ("audio/flac", b"fLaC\x00\x00\x00\x22" + b"\x00" * 20),
])
def test_voice_transcribe_all_allowed_audio_formats(client, monkeypatch, content_type, magic_bytes):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)

    with patch("app.api.voice.transcribe_audio", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = "Test audio recognized"
        res = client.post(
            "/api/chat/voice/transcribe",
            data={"language": "en", "allow_external_processing": "true"},
            files={"file": ("test_file", magic_bytes, content_type)}
        )
        assert res.status_code == 200
        assert res.json()["transcript"] == "Test audio recognized"

@pytest.mark.parametrize("content_type", [
    "audio/wav", "audio/mpeg", "audio/mp4", "audio/ogg", "audio/webm", "audio/flac"
])
def test_voice_transcribe_corrupted_magic_bytes_rejected(client, monkeypatch, content_type):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)

    corrupted_bytes = b"CORRUPTED_NON_AUDIO_HEADER" * 5
    res = client.post(
        "/api/chat/voice/transcribe",
        data={"language": "en", "allow_external_processing": "true"},
        files={"file": ("corrupted_file", corrupted_bytes, content_type)}
    )
    assert res.status_code == 415
    assert "does not match its declared format" in res.json()["detail"]

# -------------------------------------------------------------
# 6. VOICE SPEAK BOUNDARY & INPUT VALIDATION
# -------------------------------------------------------------

def test_voice_speak_text_length_exceeded(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "AI_EXTERNAL_PROCESSING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REAL_USER_ROLLOUT_APPROVED", True)

    oversized_text = "A" * 2501
    res = client.post(
        "/api/chat/voice/speak",
        data={"text": oversized_text, "language": "en", "allow_external_processing": "true"}
    )
    assert res.status_code == 422


# -------------------------------------------------------------
# 7. RAG_DOCS.MD COMPLIANCE, METADATA & MULTI-COLLECTION TESTS
# -------------------------------------------------------------

def test_rag_docs_metadata_validation():
    from app.ai.knowledge_base import KNOWLEDGE_SOURCES
    from app.ai.knowledge_ingestion import validate_document_metadata

    assert len(KNOWLEDGE_SOURCES) >= 16
    for doc in KNOWLEDGE_SOURCES:
        is_valid, errors = validate_document_metadata(doc)
        assert is_valid is True, f"Document {doc.get('id')} failed validation: {errors}"
        assert doc["collection_type"] in {"regulatory", "provider", "assistant_policy"}
        assert doc["source_url"].startswith("http")
        assert doc["status"] == "active"


def test_rag_source_freshness_audit():
    from app.ai.rag_engine import inspect_source_freshness
    freshness = inspect_source_freshness()
    assert freshness["total_sources"] >= 16
    assert freshness["active_sources"] == freshness["total_sources"]
    assert freshness["expired_sources"] == 0
    assert "regulatory" in freshness["collections"]
    assert "provider" in freshness["collections"]
    assert "assistant_policy" in freshness["collections"]


def test_rag_collection_type_filtering():
    from app.ai.rag_engine import query_grounded_rag
    # Scope to regulatory collection only
    res_reg = query_grounded_rag("Key Fact Statement", collection_type="regulatory")
    assert res_reg is not None
    assert all(c.collection_type == "regulatory" for c in res_reg.citations)

    # Scope to assistant policy only
    res_pol = query_grounded_rag("what does sahayak do", collection_type="assistant_policy")
    assert res_pol is not None
    assert all(c.collection_type == "assistant_policy" for c in res_pol.citations)


def test_untrusted_number_detection_with_regulatory_figures():
    from app.models.schemas import GroundedCitation
    from app.api.chat import _contains_untrusted_number

    citations = [
        GroundedCitation(
            citation_id="rbi_recovery_agents_conduct_v1",
            document_name="RBI Fair Practices Code",
            version="2022-09-v1",
            clause="Calling hours",
            snippet="Recovery agents are prohibited from calling before 08:00 AM or after 07:00 PM."
        ),
        GroundedCitation(
            citation_id="rbi_cooling_off_v1",
            document_name="RBI Digital Lending",
            version="2022-09-v1",
            clause="Cooling off",
            snippet="Cooling-off period is 3 days for loans of 7 days or more."
        )
    ]

    # Valid answer using only numbers cited in snippet: 8, 7, 3
    valid_answer = "Recovery agents can only call between 8:00 AM and 7:00 PM, with a 3 day cooling-off period."
    assert _contains_untrusted_number(valid_answer, citations) is False

    # Hallucinated answer inventing 9999 rupees or 45% APR:
    invalid_answer = "Recovery agents can call at 8:00 AM and fee is 9999 rupees."
    assert _contains_untrusted_number(invalid_answer, citations) is True


def test_inactive_or_expired_source_exclusion():
    from app.ai.rag_engine import _source_is_current_and_approved

    active_source = {
        "approved": True,
        "allowed_use": "assistant_grounding",
        "jurisdiction": "IN",
        "status": "active",
        "effective_date": "2024-01-01",
        "review_due": "2028-01-01",
    }
    assert _source_is_current_and_approved(active_source) is True

    # Superseded status must be rejected
    superseded = dict(active_source, status="superseded")
    assert _source_is_current_and_approved(superseded) is False

    # Past review_due date must be rejected
    expired = dict(active_source, review_due="2020-01-01")
    assert _source_is_current_and_approved(expired) is False

    # Future effective_date must be rejected
    future = dict(active_source, effective_date="2099-01-01")
    assert _source_is_current_and_approved(future) is False

