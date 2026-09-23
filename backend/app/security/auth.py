from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.database.models import AuditLog, User, UserSession
from app.security.passwords import PasswordManager
from app.security.tokens import generate_token, hash_token, token_matches


class AuthenticationError(Exception):
    """Base class for expected authentication failures."""


class InvalidCredentialsError(AuthenticationError):
    pass


class EmailAlreadyExistsError(AuthenticationError):
    pass


class InvalidSessionError(AuthenticationError):
    pass


class InvalidCsrfTokenError(AuthenticationError):
    pass


@dataclass(frozen=True)
class IssuedSession:
    user: User
    session: UserSession
    session_token: str
    csrf_token: str


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user: User
    session: UserSession


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        passwords: PasswordManager | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.passwords = passwords or PasswordManager()
        self.secret = settings.session_secret.get_secret_value()

    async def register(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        timezone: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> IssuedSession:
        normalized_email = email.strip().casefold()
        existing = await self.session.scalar(select(User.id).where(User.email == normalized_email))
        if existing is not None:
            raise EmailAlreadyExistsError

        now = datetime.now(UTC)
        user = User(
            email=normalized_email,
            password_hash=self.passwords.hash(password),
            display_name=display_name.strip(),
            timezone=timezone,
        )
        self.session.add(user)
        await self.session.flush()
        issued = self._new_session(user, now, ip_address, user_agent)
        self.session.add(issued.session)
        self._audit(
            user_id=user.id,
            action="auth.register",
            resource_id=str(user.id),
            decision="allowed",
            details={"ip_address": ip_address},
        )
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise EmailAlreadyExistsError from exc
        return issued

    async def login(
        self,
        *,
        email: str,
        password: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> IssuedSession:
        normalized_email = email.strip().casefold()
        user = cast(
            User | None,
            await self.session.scalar(select(User).where(User.email == normalized_email)),
        )
        valid = False
        if user is None:
            self.passwords.verify_dummy(password)
        else:
            valid = self.passwords.verify(user.password_hash, password) and user.is_active

        if user is None or not valid:
            self._audit(
                user_id=user.id if user else None,
                action="auth.login",
                resource_id=str(user.id) if user else None,
                decision="denied",
                details={"ip_address": ip_address, "reason": "invalid_credentials"},
            )
            await self.session.commit()
            raise InvalidCredentialsError

        if self.passwords.needs_rehash(user.password_hash):
            user.password_hash = self.passwords.hash(password)
        now = datetime.now(UTC)
        issued = self._new_session(user, now, ip_address, user_agent)
        self.session.add(issued.session)
        self._audit(
            user_id=user.id,
            action="auth.login",
            resource_id=str(user.id),
            decision="allowed",
            details={"ip_address": ip_address},
        )
        await self.session.commit()
        return issued

    async def authenticate(self, raw_token: str | None) -> AuthenticatedPrincipal:
        if not raw_token:
            raise InvalidSessionError
        now = datetime.now(UTC)
        token_digest = hash_token(raw_token, self.secret)
        statement = (
            select(UserSession, User)
            .join(User, User.id == UserSession.user_id)
            .where(
                UserSession.token_hash == token_digest,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
                User.is_active.is_(True),
            )
        )
        row = (await self.session.execute(statement)).one_or_none()
        if row is None:
            raise InvalidSessionError
        user_session, user = row
        user_session.last_seen_at = now
        await self.session.commit()
        return AuthenticatedPrincipal(user=user, session=user_session)

    def validate_csrf(self, principal: AuthenticatedPrincipal, csrf_token: str | None) -> None:
        if not csrf_token or not token_matches(
            csrf_token, principal.session.csrf_token_hash, self.secret
        ):
            raise InvalidCsrfTokenError

    async def logout(self, principal: AuthenticatedPrincipal) -> None:
        now = datetime.now(UTC)
        principal.session.revoked_at = now
        self._audit(
            user_id=principal.user.id,
            action="auth.logout",
            resource_id=str(principal.session.id),
            decision="allowed",
            details={},
        )
        await self.session.commit()

    def _new_session(
        self,
        user: User,
        now: datetime,
        ip_address: str | None,
        user_agent: str | None,
    ) -> IssuedSession:
        raw_session_token = generate_token()
        raw_csrf_token = generate_token()
        user_session = UserSession(
            user_id=user.id,
            token_hash=hash_token(raw_session_token, self.secret),
            csrf_token_hash=hash_token(raw_csrf_token, self.secret),
            expires_at=now + timedelta(hours=self.settings.session_ttl_hours),
            last_seen_at=now,
            ip_address=ip_address,
            user_agent=user_agent[:512] if user_agent else None,
        )
        return IssuedSession(user, user_session, raw_session_token, raw_csrf_token)

    def _audit(
        self,
        *,
        user_id: Any,
        action: str,
        resource_id: str | None,
        decision: str,
        details: dict[str, Any],
    ) -> None:
        self.session.add(
            AuditLog(
                user_id=user_id,
                agent_run_id=None,
                occurred_at=datetime.now(UTC),
                actor_type="user",
                actor_id=str(user_id) if user_id else None,
                action=action,
                resource_type="authentication",
                resource_id=resource_id,
                decision=decision,
                risk_level=None,
                details=details,
            )
        )
