from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.config import Settings
from app.database.models import AuditLog, User, UserSession
from app.database.session import Database
from app.main import create_app
from app.security.rate_limit import MemoryRateLimiter


@pytest.fixture
async def auth_client(tmp_path: object) -> AsyncIterator[tuple[AsyncClient, Database]]:
    database_path = str(tmp_path) + "/auth-test.db"
    settings = Settings(
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{database_path}",
        session_secret="a-test-secret-that-is-long-enough",
        auth_rate_limit_attempts=5,
        _env_file=None,
    )
    database = Database(settings)
    async with database.engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: User.__table__.create(sync_connection, checkfirst=True)
        )
        await connection.run_sync(
            lambda sync_connection: UserSession.__table__.create(sync_connection, checkfirst=True)
        )
        await connection.run_sync(
            lambda sync_connection: AuditLog.__table__.create(sync_connection, checkfirst=True)
        )
    app = create_app(settings, database, MemoryRateLimiter())
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, database


async def test_register_me_csrf_logout_flow(
    auth_client: tuple[AsyncClient, Database],
) -> None:
    client, database = auth_client
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "Person@Example.com",
            "password": "A secure passphrase 42",
            "display_name": "Test Person",
            "timezone": "Asia/Karachi",
        },
    )
    assert registration.status_code == 201
    payload = registration.json()
    assert payload["user"]["email"] == "person@example.com"
    assert client.cookies.get("assistant_session")
    assert client.cookies.get("assistant_csrf") == payload["csrf_token"]

    current_user = await client.get("/api/v1/auth/me")
    assert current_user.status_code == 200
    assert current_user.json()["display_name"] == "Test Person"

    rejected_logout = await client.post("/api/v1/auth/logout")
    assert rejected_logout.status_code == 403

    logout = await client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": payload["csrf_token"]},
    )
    assert logout.status_code == 200
    assert (await client.get("/api/v1/auth/me")).status_code == 401

    async with database.session_factory() as session:
        user = await session.scalar(select(User))
        stored_session = await session.scalar(select(UserSession))
        audit_count = await session.scalar(select(func.count()).select_from(AuditLog))
    assert user is not None and user.password_hash.startswith("$argon2id$")
    assert stored_session is not None and stored_session.revoked_at is not None
    assert audit_count == 2


async def test_duplicate_registration_and_login(auth_client: tuple[AsyncClient, Database]) -> None:
    client, _ = auth_client
    registration_payload = {
        "email": "duplicate@example.com",
        "password": "Strong password 42",
        "display_name": "Duplicate",
    }
    first_registration = await client.post("/api/v1/auth/register", json=registration_payload)
    duplicate_registration = await client.post("/api/v1/auth/register", json=registration_payload)
    assert first_registration.status_code == 201
    assert duplicate_registration.status_code == 409

    client.cookies.clear()
    invalid = await client.post(
        "/api/v1/auth/login",
        json={"email": "duplicate@example.com", "password": "wrong"},
    )
    assert invalid.status_code == 401

    valid = await client.post(
        "/api/v1/auth/login",
        json={"email": "DUPLICATE@example.com", "password": "Strong password 42"},
    )
    assert valid.status_code == 200


async def test_authentication_rate_limit(tmp_path: object) -> None:
    settings = Settings(
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path}/rate-limit.db",
        session_secret="a-test-secret-that-is-long-enough",
        auth_rate_limit_attempts=2,
        _env_file=None,
    )
    database = Database(settings)
    async with database.engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: User.__table__.create(sync_connection, checkfirst=True)
        )
        await connection.run_sync(
            lambda sync_connection: UserSession.__table__.create(sync_connection, checkfirst=True)
        )
        await connection.run_sync(
            lambda sync_connection: AuditLog.__table__.create(sync_connection, checkfirst=True)
        )
    app = create_app(settings, database, MemoryRateLimiter())
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            credentials = {"email": "absent@example.com", "password": "wrong"}
            assert (await client.post("/api/v1/auth/login", json=credentials)).status_code == 401
            assert (await client.post("/api/v1/auth/login", json=credentials)).status_code == 401
            limited = await client.post("/api/v1/auth/login", json=credentials)
            assert limited.status_code == 429
            assert 1 <= int(limited.headers["Retry-After"]) <= 900
