"""
Rate Limiting Middleware

Token bucket rate limiting with in-memory storage.
"""

import time
from collections import defaultdict
from typing import Callable, Dict

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, requests_per_minute: int = 60, burst: int = 10):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Sustained rate limit
            burst: Burst capacity (max tokens)
        """
        self.rate = requests_per_minute / 60.0  # tokens per second
        self.burst = burst
        self.buckets: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"tokens": burst, "last_update": time.time()}
        )

    def _refill_bucket(self, bucket: Dict[str, float]) -> None:
        """Refill bucket based on elapsed time."""
        now = time.time()
        elapsed = now - bucket["last_update"]
        bucket["tokens"] = min(self.burst, bucket["tokens"] + elapsed * self.rate)
        bucket["last_update"] = now

    def check_rate_limit(self, key: str) -> bool:
        """
        Check if request is within rate limit.

        Args:
            key: Rate limit key (e.g., IP address, user ID)

        Returns:
            True if within limit, False otherwise
        """
        bucket = self.buckets[key]
        self._refill_bucket(bucket)

        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True

        return False

    def get_retry_after(self, key: str) -> int:
        """
        Get seconds until rate limit resets.

        Args:
            key: Rate limit key

        Returns:
            Seconds until next token available
        """
        bucket = self.buckets[key]
        self._refill_bucket(bucket)

        if bucket["tokens"] >= 1:
            return 0

        tokens_needed = 1 - bucket["tokens"]
        return int(tokens_needed / self.rate) + 1


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, requests_per_minute: int = 60, burst: int = 10):
        """
        Initialize middleware.

        Args:
            app: FastAPI app
            requests_per_minute: Sustained rate limit
            burst: Burst capacity
        """
        super().__init__(app)
        self.limiter = RateLimiter(requests_per_minute, burst)

    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request with rate limiting.

        Args:
            request: HTTP request
            call_next: Next middleware/endpoint

        Returns:
            HTTP response

        Raises:
            HTTPException: If rate limit exceeded
        """
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Use client IP as rate limit key
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit
        if not self.limiter.check_rate_limit(client_ip):
            retry_after = self.limiter.get_retry_after(client_ip)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        return response
