from app.middleware.pii_masking import scrub_pii
from app.models.schemas import ConsentScope

def test_pii_scrubber():
    raw = "Applicant PAN: ABCDE1234F, Aadhaar: 987654321098, Phone: 9876543210 applied today."
    clean = scrub_pii(raw)
    assert "ABCDE1234F" not in clean
    assert "987654321098" not in clean
    assert "9876543210" not in clean
    assert "[MASKED_PAN]" in clean
    assert "[MASKED_AADHAAR]" in clean
    assert "[MASKED_PHONE]" in clean

def test_consent_audit_and_document_gating(client):
    # 1. Create a journey
    j_res = client.post("/api/journeys", json={
        "language": "en",
        "loan_amount": 50000,
        "preferred_tenure_months": 24,
        "purpose": "Medical"
    })
    assert j_res.status_code == 201
    journey_id = j_res.json()["id"]

    # 2. Attempt doc upload BEFORE granting consent -> 403 Forbidden
    doc_res1 = client.post(f"/api/journeys/{journey_id}/documents/upload", json={
        "document_type": "PAN_CARD"
    })
    assert doc_res1.status_code == 403
    assert "Consent Required" in doc_res1.json()["detail"]

    # 3. Grant consent for DOCUMENT_OCR_PROCESSING
    consent_res = client.post(f"/api/journeys/{journey_id}/consent", json={
        "scope": ConsentScope.DOCUMENT_OCR_PROCESSING.value,
        "purpose": "Extract identity information from government photo ID for pre-qualification check",
        "is_granted": True
    })
    assert consent_res.status_code == 200
    consent_data = consent_res.json()
    assert consent_data["tamper_hash"] is not None
    assert len(consent_data["tamper_hash"]) == 64

    # 4. Now doc upload succeeds
    doc_res2 = client.post(f"/api/journeys/{journey_id}/documents/upload", json={
        "document_type": "PAN_CARD"
    })
    assert doc_res2.status_code == 200
    doc_data = doc_res2.json()
    assert doc_data["fields"]["pan_number"]["masked_value"].startswith("AB")

    # 5. Query immutable consent audit trail
    audit_res = client.get(f"/api/journeys/{journey_id}/consent/audit")
    assert audit_res.status_code == 200
    trail = audit_res.json()
    assert len(trail) >= 1
    assert trail[0]["scope"] == ConsentScope.DOCUMENT_OCR_PROCESSING.value

def test_journey_parameter_revision_rollback(client):
    # Create journey
    j_res = client.post("/api/journeys", json={
        "language": "en",
        "loan_amount": 50000,
        "preferred_tenure_months": 24,
        "purpose": "Home"
    })
    journey_id = j_res.json()["id"]

    # Select offer and advance to OFFERS_REVIEWED
    adv_res = client.patch(f"/api/journeys/{journey_id}/stage", json={
        "stage": "OFFERS_REVIEWED",
        "selected_offer_id": "offer-hdfc-01",
        "customer_confirmed": False
    })
    assert adv_res.status_code == 200
    assert adv_res.json()["stage"] == "OFFERS_REVIEWED"

    # User alters loan amount to 90,000 via revise endpoint
    rev_res = client.patch(f"/api/journeys/{journey_id}/revise", json={
        "language": "en",
        "loan_amount": 90000,
        "preferred_tenure_months": 36,
        "purpose": "Home Expansion"
    })
    assert rev_res.status_code == 200
    data = rev_res.json()
    # State must roll back to INTENT_CAPTURED and invalidate offer selection
    assert data["stage"] == "INTENT_CAPTURED"
    assert data["selected_offer"] is None
    assert float(data["loan_amount"]) == 90000.0
