from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Protocol

from redis.asyncio import Redis


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after: int


class RateLimiter(Protocol):
    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult: ...

    async def close(self) -> None: ...


class RedisRateLimiter:
    """Fixed-window limiter backed by Redis and safe across API replicas."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        namespaced_key = f"auth-rate:{key}"
        async with self.redis.pipeline(transaction=True) as pipeline:
            pipeline.incr(namespaced_key)
            pipeline.ttl(namespaced_key)
            count, ttl = await pipeline.execute()
        count = int(count)
        ttl = int(ttl)
        if count == 1 or ttl < 0:
            await self.redis.expire(namespaced_key, window_seconds)
            ttl = window_seconds
        return RateLimitResult(allowed=count <= limit, retry_after=max(ttl, 1))

    async def close(self) -> None:
        await self.redis.aclose()


class MemoryRateLimiter:
    """Deterministic process-local limiter for tests only."""

    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self.clock = clock
        self.attempts: dict[str, deque[float]] = defaultdict(deque)

    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        now = self.clock()
        attempts = self.attempts[key]
        while attempts and attempts[0] <= now - window_seconds:
            attempts.popleft()
        attempts.append(now)
        allowed = len(attempts) <= limit
        retry_after = max(1, int(window_seconds - (now - attempts[0])))
        return RateLimitResult(allowed=allowed, retry_after=retry_after)

    async def close(self) -> None:
        return None
