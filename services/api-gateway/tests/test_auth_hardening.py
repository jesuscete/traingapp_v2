import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token


def test_token_with_malformed_subject_returns_401(client: TestClient) -> None:
    token = create_access_token("not-a-uuid")
    response = client.get("/profile", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-Internal-Token": "wrong-token"},
        {"X-Internal-Token": "ñ-no-ascii".encode("latin-1")},
    ],
)
def test_internal_rejects_missing_or_wrong_token(
    client: TestClient, headers: dict[str, str | bytes]
) -> None:
    body = {"userId": str(uuid.uuid4()), "session": {}}
    response = client.post("/internal/sessions", json=body, headers=headers)
    assert response.status_code == 401


def test_internal_accepts_valid_token_past_auth(client: TestClient) -> None:
    body = {"userId": str(uuid.uuid4()), "session": {}}
    response = client.post(
        "/internal/sessions",
        json=body,
        headers={"X-Internal-Token": settings.internal_token},
    )
    assert response.status_code != 401
