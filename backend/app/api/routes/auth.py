import hashlib

from fastapi import APIRouter, HTTPException, Request, Response, status
from redis.exceptions import RedisError

from app.api.auth_schemas import (
    AuthenticationResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    UserResponse,
)
from app.api.dependencies import (
    AuthServiceDependency,
    CsrfPrincipal,
    CurrentPrincipal,
    RateLimiterDependency,
)
from app.core.config import Settings
from app.security.auth import EmailAlreadyExistsError, InvalidCredentialsError, IssuedSession

router = APIRouter(prefix="/auth", tags=["authentication"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _rate_key(action: str, request: Request, email: str) -> str:
    identity = f"{_client_ip(request) or 'unknown'}:{email.strip().casefold()}"
    digest = hashlib.sha256(identity.encode()).hexdigest()
    return f"{action}:{digest}"


async def _enforce_rate_limit(
    action: str,
    request: Request,
    email: str,
    limiter: RateLimiterDependency,
) -> None:
    settings: Settings = request.app.state.settings
    try:
        result = await limiter.check(
            _rate_key(action, request, email),
            settings.auth_rate_limit_attempts,
            settings.auth_rate_limit_window_seconds,
        )
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="authentication service temporarily unavailable",
        ) from exc
    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many authentication attempts",
            headers={"Retry-After": str(result.retry_after)},
        )


def _set_auth_cookies(response: Response, issued: IssuedSession, settings: Settings) -> None:
    secure = settings.app_env in {"staging", "production"}
    max_age = settings.session_ttl_hours * 3600
    response.set_cookie(
        settings.session_cookie_name,
        issued.session_token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        issued.csrf_token,
        max_age=max_age,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )


def _clear_auth_cookies(response: Response, settings: Settings) -> None:
    secure = settings.app_env in {"staging", "production"}
    response.delete_cookie(
        settings.session_cookie_name, httponly=True, secure=secure, samesite="lax", path="/"
    )
    response.delete_cookie(
        settings.csrf_cookie_name, httponly=False, secure=secure, samesite="lax", path="/"
    )


@router.post(
    "/register",
    response_model=AuthenticationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    limiter: RateLimiterDependency,
    service: AuthServiceDependency,
) -> AuthenticationResponse:
    await _enforce_rate_limit("register", request, str(payload.email), limiter)
    try:
        issued = await service.register(
            email=str(payload.email),
            password=payload.password,
            display_name=payload.display_name,
            timezone=payload.timezone,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except EmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="an account with this email already exists",
        ) from exc
    settings: Settings = request.app.state.settings
    _set_auth_cookies(response, issued, settings)
    return AuthenticationResponse(
        user=UserResponse.model_validate(issued.user), csrf_token=issued.csrf_token
    )


@router.post("/login", response_model=AuthenticationResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    limiter: RateLimiterDependency,
    service: AuthServiceDependency,
) -> AuthenticationResponse:
    await _enforce_rate_limit("login", request, str(payload.email), limiter)
    try:
        issued = await service.login(
            email=str(payload.email),
            password=payload.password,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid email or password",
        ) from exc
    settings: Settings = request.app.state.settings
    _set_auth_cookies(response, issued, settings)
    return AuthenticationResponse(
        user=UserResponse.model_validate(issued.user), csrf_token=issued.csrf_token
    )


@router.get("/me", response_model=UserResponse)
async def me(principal: CurrentPrincipal) -> UserResponse:
    return UserResponse.model_validate(principal.user)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    principal: CsrfPrincipal,
    service: AuthServiceDependency,
) -> MessageResponse:
    await service.logout(principal)
    _clear_auth_cookies(response, request.app.state.settings)
    return MessageResponse(message="logged out")
