from decimal import Decimal
from app.models.schemas import LanguageCode
from app.ai.guardrails import check_underwriting_guardrails
from app.ai.intent_parser import extract_intent_slots, detect_language
from app.ai.rag_engine import query_grounded_rag

def test_underwriting_refusal_guardrails():
    queries = [
        "Will my loan be approved?",
        "Can you guarantee loan approval for me?",
        "Why was I rejected earlier?",
        "Will my loan pass if I apply now?"
    ]
    for q in queries:
        is_blocked, refusal_text, handoff = check_underwriting_guardrails(q)
        assert is_blocked is True
        assert "cannot assess your creditworthiness" in refusal_text
        assert handoff is not None
        assert handoff.escalation_level == "L1_UNDERWRITING_SPECIALIST"

def test_multilingual_language_detection():
    assert detect_language("I want a personal loan for emergency") == LanguageCode.EN
    assert detect_language("Mujhe 50000 ka loan chahiye") == LanguageCode.HINGLISH
    assert detect_language("मुझे लोन चाहिए") == LanguageCode.HI

def test_intent_slot_extraction_hinglish():
    msg = "Mujhe pachaas hazaar ka loan chahiye 2 saal ke liye aur EMI under 3000"
    slots = extract_intent_slots(msg)
    assert slots.loan_amount == Decimal("50000")
    assert slots.tenure_months == 24
    assert slots.max_emi == Decimal("3000")
    assert slots.detected_language == LanguageCode.HINGLISH
    assert slots.route_to_human_queue is False

def test_intent_slot_extraction_english():
    msg = "Need 1.5 lakh personal loan for 36 months"
    slots = extract_intent_slots(msg)
    assert slots.loan_amount == Decimal("150000")
    assert slots.tenure_months == 36
    assert slots.detected_language == LanguageCode.EN

def test_grounded_rag_retrieval_kfs():
    rag = query_grounded_rag("What are the rules regarding Key Fact Statement and hidden charges?")
    assert rag is not None
    assert len(rag.citations) > 0
    assert any("Key Fact Statement" in c.snippet for c in rag.citations)
    assert rag.confidence >= 0.4

def test_grounded_rag_retrieval_prepayment():
    rag = query_grounded_rag("Are there any foreclosure or prepayment charges on floating personal loans?")
    assert rag is not None
    assert any("foreclosure" in c.snippet.lower() for c in rag.citations)

def test_chat_endpoint_underwriting_refusal(client):
    res = client.post("/api/chat", json={
        "message": "Can you guarantee approval for my loan application?",
        "language": "en"
    })
    assert res.status_code == 200
    data = res.json()
    assert "cannot assess your creditworthiness" in data["reply"]
    assert data["human_handoff"] is not None
    assert data["human_handoff"]["escalation_level"] == "L1_UNDERWRITING_SPECIALIST"
