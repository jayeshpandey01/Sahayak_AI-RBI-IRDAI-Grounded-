from uuid import uuid4

def test_idempotent_journey_creation_replay(client):
    idempotency_key = f"key_retry_{uuid4().hex}"
    payload = {
        "language": "en",
        "loan_amount": 75000,
        "preferred_tenure_months": 24,
        "maximum_emi": 4000,
        "purpose": "Home Renovations"
    }
    headers = {"X-Idempotency-Key": idempotency_key}

    # Initial POST
    res1 = client.post("/api/journeys", json=payload, headers=headers)
    assert res1.status_code == 201
    data1 = res1.json()

    # Replay POST with exact same key and payload
    res2 = client.post("/api/journeys", json=payload, headers=headers)
    assert res2.status_code == 201
    assert res2.headers.get("X-Cache-Lookup") == "IDEMPOTENCY_HIT"
    data2 = res2.json()

    # Must return identical journey record without creating a second entry
    assert data1["id"] == data2["id"]
    assert data1["loan_amount"] == data2["loan_amount"]

def test_idempotency_key_payload_conflict(client):
    idempotency_key = f"key_conflict_{uuid4().hex}"
    headers = {"X-Idempotency-Key": idempotency_key}

    res1 = client.post("/api/journeys", json={
        "language": "en",
        "loan_amount": 50000,
        "preferred_tenure_months": 12,
        "purpose": "Travel"
    }, headers=headers)
    assert res1.status_code == 201

    # Same key but changed payload
    res2 = client.post("/api/journeys", json={
        "language": "en",
        "loan_amount": 99000,
        "preferred_tenure_months": 36,
        "purpose": "Travel"
    }, headers=headers)
    assert res2.status_code == 409
    assert "reused with different request payload" in res2.json()["detail"]
