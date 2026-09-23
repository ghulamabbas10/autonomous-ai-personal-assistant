import hashlib
import hmac
import secrets


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str, secret: str) -> str:
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def token_matches(token: str, expected_hash: str, secret: str) -> bool:
    return hmac.compare_digest(hash_token(token, secret), expected_hash)
