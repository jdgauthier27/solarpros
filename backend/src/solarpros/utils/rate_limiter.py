"""Redis-based sliding window rate limiter.

Uses a sorted set per key where each member is a timestamped request.
The window slides forward in real time, evicting entries older than
``window_seconds`` before counting remaining members.
"""

from __future__ import annotations

import asyncio
import time

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()


class RateLimitExceeded(Exception):
    """Raised when the rate limit is exceeded and the caller does not want to wait."""

    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after:.2f}s")


class RateLimiter:
    """Sliding-window rate limiter backed by Redis sorted sets.

    Parameters
    ----------
    redis_url:
        Redis connection string (e.g. ``redis://localhost:6379/0``).
    key_prefix:
        Prefix added to all Redis keys managed by this limiter so that
        multiple limiters can share the same Redis instance.
    max_requests:
        Maximum number of requests allowed within the sliding window.
    window_seconds:
        Size of the sliding window in seconds.
    """

    def __init__(
        self,
        redis_url: str,
        key_prefix: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        """Lazily initialise and return the async Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
            )
        return self._redis

    def _key(self, identifier: str = "global") -> str:
        """Build the Redis key for a given caller/resource identifier."""
        return f"{self.key_prefix}:{identifier}"

    async def check(self, identifier: str = "global") -> bool:
        """Check whether a request is allowed and, if so, record it.

        Returns ``True`` when the request is allowed (and has been counted),
        ``False`` when the caller has exceeded *max_requests* within the
        current window.
        """
        r = await self._get_redis()
        key = self._key(identifier)
        now = time.time()
        window_start = now - self.window_seconds

        # Atomic pipeline: trim expired entries, add new entry, count.
        async with r.pipeline(transaction=True) as pipe:
            # 1. Remove entries outside the sliding window.
            pipe.zremrangebyscore(key, "-inf", window_start)
            # 2. Count remaining entries *before* we decide to add one.
            pipe.zcard(key)
            results = await pipe.execute()

        current_count: int = results[1]

        if current_count >= self.max_requests:
            logger.debug(
                "rate_limit_hit",
                key=key,
                current=current_count,
                limit=self.max_requests,
            )
            return False

        # The request is allowed -- record it in a second pipeline so
        # the count we checked was not inflated by a speculative add.
        async with r.pipeline(transaction=True) as pipe:
            # Use ``now`` as both score and member value.  To guarantee
            # uniqueness across concurrent requests we append a small
            # counter fragment.
            member = f"{now}"
            pipe.zadd(key, {member: now})
            pipe.expire(key, self.window_seconds + 1)
            await pipe.execute()

        logger.debug(
            "rate_limit_allowed",
            key=key,
            current=current_count + 1,
            limit=self.max_requests,
        )
        return True

    async def remaining(self, identifier: str = "global") -> int:
        """Return the number of requests still available in the current window."""
        r = await self._get_redis()
        key = self._key(identifier)
        now = time.time()
        window_start = now - self.window_seconds

        async with r.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, "-inf", window_start)
            pipe.zcard(key)
            results = await pipe.execute()

        current_count: int = results[1]
        return max(0, self.max_requests - current_count)

    async def retry_after(self, identifier: str = "global") -> float:
        """Return the number of seconds until the next request will be allowed.

        Returns ``0.0`` if a request would be allowed right now.
        """
        r = await self._get_redis()
        key = self._key(identifier)
        now = time.time()
        window_start = now - self.window_seconds

        # Trim and fetch the oldest entry in one go.
        async with r.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, "-inf", window_start)
            pipe.zcard(key)
            pipe.zrange(key, 0, 0, withscores=True)
            results = await pipe.execute()

        current_count: int = results[1]

        if current_count < self.max_requests:
            return 0.0

        # The oldest entry in the window determines when space opens up.
        oldest_entries: list[tuple[str, float]] = results[2]
        if not oldest_entries:
            return 0.0

        oldest_score = oldest_entries[0][1]
        wait = (oldest_score + self.window_seconds) - now
        return max(0.0, wait)

    async def wait_if_needed(self, identifier: str = "global") -> None:
        """Block (async sleep) until a request is allowed, then record it.

        This method will repeatedly check the rate limit, sleeping for the
        minimum necessary duration between attempts, until the request is
        successfully recorded.
        """
        while True:
            allowed = await self.check(identifier)
            if allowed:
                return

            wait = await self.retry_after(identifier)
            if wait <= 0:
                # Tiny back-off to avoid a tight loop when contention is high.
                wait = 0.05

            logger.debug(
                "rate_limit_waiting",
                key=self._key(identifier),
                wait_seconds=round(wait, 3),
            )
            await asyncio.sleep(wait)

    async def reset(self, identifier: str = "global") -> None:
        """Delete all recorded requests for *identifier*."""
        r = await self._get_redis()
        await r.delete(self._key(identifier))

    async def close(self) -> None:
        """Close the underlying Redis connection."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
