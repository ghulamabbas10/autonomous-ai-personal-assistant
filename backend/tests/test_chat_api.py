from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.agents.providers.mock import MockLLMProvider
from app.agents.runtime import ConversationalAgent
from app.core.config import Settings
from app.database.models import AuditLog, Conversation, Message, User, UserSession
from app.database.session import Database
from app.main import create_app
from app.security.rate_limit import MemoryRateLimiter


@pytest.fixture
async def chat_client(tmp_path: object) -> AsyncIterator[tuple[AsyncClient, Database]]:
    settings = Settings(
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path}/chat-test.db",
        session_secret="a-test-secret-that-is-long-enough",
        _env_file=None,
    )
    database = Database(settings)
    async with database.engine.begin() as connection:
        for table in (
            User.__table__,
            UserSession.__table__,
            Conversation.__table__,
            Message.__table__,
            AuditLog.__table__,
        ):
            await connection.run_sync(
                lambda sync_connection, current=table: current.create(
                    sync_connection, checkfirst=True
                )
            )
    agent = ConversationalAgent(MockLLMProvider(), settings)
    app = create_app(settings, database, MemoryRateLimiter(), agent)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            registration = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "chat@example.com",
                    "password": "Strong password 42",
                    "display_name": "Chat User",
                },
            )
            assert registration.status_code == 201
            client.headers["X-CSRF-Token"] = registration.json()["csrf_token"]
            yield client, database


async def test_chat_persists_and_resumes_conversation(
    chat_client: tuple[AsyncClient, Database],
) -> None:
    client, database = chat_client
    first = await client.post("/api/v1/chat", json={"content": "Help me focus"})
    assert first.status_code == 201
    payload = first.json()
    conversation_id = payload["conversation"]["id"]
    assert payload["provider"] == "mock"
    assert "no external AI service" in payload["assistant_message"]["content"]

    second = await client.post(
        "/api/v1/chat", json={"content": "Continue", "conversation_id": conversation_id}
    )
    assert second.status_code == 201
    detail = await client.get(f"/api/v1/chat/conversations/{conversation_id}")
    assert [message["role"] for message in detail.json()["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert len((await client.get("/api/v1/chat/conversations")).json()) == 1

    async with database.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Message)) == 4
        assert await session.scalar(select(func.count()).select_from(AuditLog)) == 3


async def test_chat_requires_csrf_and_hides_unknown_conversation(
    chat_client: tuple[AsyncClient, Database],
) -> None:
    client, _ = chat_client
    csrf = client.headers.pop("X-CSRF-Token")
    assert (await client.post("/api/v1/chat", json={"content": "hello"})).status_code == 403
    client.headers["X-CSRF-Token"] = csrf
    response = await client.post(
        "/api/v1/chat",
        json={"content": "hello", "conversation_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},
    )
    assert response.status_code == 404
