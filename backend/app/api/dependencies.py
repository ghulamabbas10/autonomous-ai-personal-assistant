from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import Database
from app.security.auth import (
    AuthenticatedPrincipal,
    AuthService,
    InvalidCsrfTokenError,
    InvalidSessionError,
)
from app.security.rate_limit import RateLimiter


def get_database(request: Request) -> Database:
    return cast(Database, request.app.state.database)


async def get_session(
    database: Annotated[Database, Depends(get_database)],
) -> AsyncIterator[AsyncSession]:
    async for session in database.session():
        yield session


SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def get_rate_limiter(request: Request) -> RateLimiter:
    return cast(RateLimiter, request.app.state.rate_limiter)


def get_auth_service(request: Request, session: SessionDependency) -> AuthService:
    return AuthService(session, request.app.state.settings)


async def get_current_principal(
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthenticatedPrincipal:
    raw_token = request.cookies.get(request.app.state.settings.session_cookie_name)
    try:
        return await service.authenticate(raw_token)
    except InvalidSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
        ) from exc


async def require_csrf(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> AuthenticatedPrincipal:
    try:
        service.validate_csrf(principal, csrf_token)
    except InvalidCsrfTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid CSRF token",
        ) from exc
    return principal


CurrentPrincipal = Annotated[AuthenticatedPrincipal, Depends(get_current_principal)]
CsrfPrincipal = Annotated[AuthenticatedPrincipal, Depends(require_csrf)]
RateLimiterDependency = Annotated[RateLimiter, Depends(get_rate_limiter)]
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
