from uuid import uuid4


def _register(client, tag: str) -> str:
    response = client.post("/api/auth/register", json={
        "email": f"{tag}_{uuid4().hex[:8]}@example.com",
        "password": "Password123!",
        "full_name": tag,
    })
    assert response.status_code == 201
    return response.json()["access_token"]


def test_loan_readiness_history_is_authenticated_and_owner_scoped(client):
    token_a = _register(client, "journey_owner")
    token_b = _register(client, "other_owner")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    created = client.post("/api/journeys", json={
        "loan_amount": 120000,
        "preferred_tenure_months": 12,
        "purpose": "Education",
        "language": "en",
    }, headers=headers_a)
    assert created.status_code == 201

    history = client.get("/api/journeys", headers=headers_a)
    assert history.status_code == 200
    assert [item["id"] for item in history.json()] == [created.json()["id"]]
    assert history.json()[0]["ready_for_handoff"] is False

    other_history = client.get("/api/journeys", headers=headers_b)
    assert other_history.status_code == 200
    assert other_history.json() == []

    anonymous = client.get("/api/journeys", headers={"Authorization": ""})
    assert anonymous.status_code == 401
