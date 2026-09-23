from app.security.passwords import PasswordManager
from app.security.rate_limit import MemoryRateLimiter
from app.security.tokens import generate_token, hash_token, token_matches


def test_password_hash_is_argon2id_and_verifies() -> None:
    manager = PasswordManager()
    password_hash = manager.hash("Correct Horse 42")
    assert password_hash.startswith("$argon2id$")
    assert manager.verify(password_hash, "Correct Horse 42")
    assert not manager.verify(password_hash, "wrong password")


def test_session_tokens_are_hashed_with_secret() -> None:
    token = generate_token()
    digest = hash_token(token, "test-secret")
    assert token not in digest
    assert token_matches(token, digest, "test-secret")
    assert not token_matches(token, digest, "another-secret")


async def test_memory_rate_limiter_enforces_window() -> None:
    now = 10.0
    limiter = MemoryRateLimiter(clock=lambda: now)
    assert (await limiter.check("login:key", 2, 60)).allowed
    assert (await limiter.check("login:key", 2, 60)).allowed
    result = await limiter.check("login:key", 2, 60)
    assert not result.allowed
    assert result.retry_after == 60
