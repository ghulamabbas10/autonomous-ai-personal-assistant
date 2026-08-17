from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


class FakeConnection:
    async def execute(self, statement: Any) -> None:
        return None


class FakeEngine:
    @asynccontextmanager
    async def connect(self) -> AsyncIterator[FakeConnection]:
        yield FakeConnection()


class FakeDatabase:
    engine = FakeEngine()

    async def dispose(self) -> None:
        return None


async def test_liveness_does_not_check_dependencies() -> None:
    app = create_app(
        Settings(app_name="Test Assistant", app_env="test", _env_file=None),
        FakeDatabase(),  # type: ignore[arg-type]
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Test Assistant",
        "database": "not_checked",
    }


async def test_readiness_checks_database() -> None:
    app = create_app(
        Settings(app_env="test", _env_file=None),
        FakeDatabase(),  # type: ignore[arg-type]
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"
