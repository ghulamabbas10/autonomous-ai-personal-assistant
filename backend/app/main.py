from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.database.session import Database
from app.security.rate_limit import RateLimiter, RedisRateLimiter


def create_app(
    settings: Settings | None = None,
    database: Database | None = None,
    rate_limiter: RateLimiter | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_database = database or Database(resolved_settings)
    resolved_rate_limiter = rate_limiter or RedisRateLimiter(
        Redis.from_url(resolved_settings.redis_url, decode_responses=True)
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = resolved_settings
        app.state.database = resolved_database
        app.state.rate_limiter = resolved_rate_limiter
        yield
        await resolved_rate_limiter.close()
        await resolved_database.dispose()

    configure_logging(resolved_settings.log_level)
    app = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        docs_url="/api/docs" if resolved_settings.app_env != "production" else None,
        openapi_url="/api/openapi.json" if resolved_settings.app_env != "production" else None,
        lifespan=lifespan,
    )
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    return app


app = create_app()
