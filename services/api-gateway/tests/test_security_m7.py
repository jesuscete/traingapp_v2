import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.models import AuthSession

BODY = {"email": "m7@example.com", "password": "password123", "name": "Jota"}


def _login(client: TestClient, remember: bool = True) -> dict[str, str]:
    creds = {"email": BODY["email"], "password": BODY["password"], "remember": remember}
    response = client.post("/auth/login", json=creds)
    assert response.status_code == 200, response.text
    return response.json()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_short_access_token_and_rotating_refresh(client: TestClient) -> None:
    client.post("/auth/register", json=BODY)
    tokens = _login(client)
    claims = jwt.decode(
        tokens["access_token"], settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    assert claims["exp"] - datetime.now(UTC).timestamp() <= 15 * 60 + 5
    assert tokens["expires_in"] == 15 * 60 and len(tokens["refresh_token"]) > 40

    rotated = client.post("/auth/refresh", json={"refreshToken": tokens["refresh_token"]})
    assert rotated.status_code == 200
    new = rotated.json()
    assert new["refresh_token"] != tokens["refresh_token"]
    assert client.get("/profile", headers=_auth(new["access_token"])).status_code == 200

    # Reutilizar el refresh viejo (robado) revoca toda la sesión, también el nuevo.
    reuse = client.post("/auth/refresh", json={"refreshToken": tokens["refresh_token"]})
    assert reuse.status_code == 401
    assert (
        client.post("/auth/refresh", json={"refreshToken": new["refresh_token"]}).status_code == 401
    )


def test_logout_and_logout_all(client: TestClient) -> None:
    client.post("/auth/register", json=BODY)
    phone, laptop = _login(client), _login(client)
    assert (
        client.post("/auth/logout", json={"refreshToken": phone["refresh_token"]}).status_code
        == 204
    )
    assert (
        client.post("/auth/refresh", json={"refreshToken": phone["refresh_token"]}).status_code
        == 401
    )
    assert (
        client.post("/auth/refresh", json={"refreshToken": laptop["refresh_token"]}).status_code
        == 200
    )

    laptop = _login(client)
    assert client.post("/auth/logout-all", headers=_auth(laptop["access_token"])).status_code == 204
    # El token de acceso vivo deja de valer al momento (versión de token).
    assert client.get("/profile", headers=_auth(laptop["access_token"])).status_code == 401
    assert (
        client.post("/auth/refresh", json={"refreshToken": laptop["refresh_token"]}).status_code
        == 401
    )


def test_expired_refresh_is_rejected(
    client: TestClient, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    client.post("/auth/register", json=BODY)
    tokens = _login(client, remember=False)

    async def expire() -> None:
        async with db_session_factory() as session:
            await session.execute(
                update(AuthSession).values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
            )
            await session.commit()

    asyncio.run(expire())
    assert (
        client.post("/auth/refresh", json={"refreshToken": tokens["refresh_token"]}).status_code
        == 401
    )


def test_login_lockout_after_failed_attempts(client: TestClient) -> None:
    client.post("/auth/register", json=BODY)
    bad = {"email": BODY["email"], "password": "incorrecta"}
    for _ in range(5):
        assert client.post("/auth/login", json=bad).status_code == 401
    locked = client.post("/auth/login", json={**bad, "password": BODY["password"]})
    assert locked.status_code == 429 and "Retry-After" in locked.headers
    assert "intentos" in locked.json()["detail"]


def test_security_headers(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_export_and_delete_account(client: TestClient) -> None:
    tokens = client.post("/auth/register", json=BODY).json()
    headers = _auth(tokens["access_token"])
    client.post(
        "/sessions",
        json={
            "discipline": "running",
            "rawText": "carrera",
            "durationMinutes": 30,
            "performedAt": datetime.now(UTC).isoformat(),
        },
        headers=headers,
    )
    client.post("/goals", json={"kind": "event", "title": "Triatlón"}, headers=headers)
    export = client.get("/profile/export", headers=headers)
    assert export.status_code == 200 and "attachment" in export.headers["content-disposition"]
    data = export.json()["data"]
    assert data["users"][0]["email"] == BODY["email"]
    assert "hashed_password" not in data["users"][0]
    assert data.get("training_sessions") and data.get("user_goals"), sorted(data)
    assert all("token_hash" not in row for row in data.get("auth_sessions", []))

    wrong = client.post("/profile/delete", json={"password": "nope"}, headers=headers)
    assert wrong.status_code == 400
    assert (
        client.post(
            "/profile/delete", json={"password": BODY["password"]}, headers=headers
        ).status_code
        == 204
    )
    assert client.post("/auth/login", json=BODY).status_code == 401
    # Se puede volver a registrar con el mismo email: no quedan restos.
    assert client.post("/auth/register", json=BODY).status_code == 201


def test_env_helpers_replace_and_append(tmp_path: Path) -> None:
    from app.cli import _read_env, _set_env

    env = tmp_path / ".env"
    env.write_text(
        "# comentario\nAPP_USDA_API_KEY=abc\nAPP_INTERNAL_TOKEN=viejo\n", encoding="utf-8"
    )
    _set_env(env, {"APP_INTERNAL_TOKEN": "nuevo", "APP_JWT_SECRET": "x" * 40})
    values = _read_env(env)
    assert values == {
        "APP_USDA_API_KEY": "abc",
        "APP_INTERNAL_TOKEN": "nuevo",
        "APP_JWT_SECRET": "x" * 40,
    }
    assert env.read_text(encoding="utf-8").startswith("# comentario\n")
