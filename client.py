"""Shared httpx client factory with browser headers and rate limiting."""
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
}


class RateLimitedClient:
    """Thin wrapper around httpx.AsyncClient with per-host rate limiting."""

    def __init__(self, requests_per_second: float = 1.0) -> None:
        self._interval = 1.0 / requests_per_second
        self._last: dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._client = httpx.AsyncClient(
            headers=BROWSER_HEADERS,
            follow_redirects=True,
            timeout=httpx.Timeout(30.0),
        )

    async def _throttle(self, host: str) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._interval - (now - self._last.get(host, 0))
            if wait > 0:
                await asyncio.sleep(wait)
            self._last[host] = time.monotonic()

    async def get(self, url: str, **kwargs) -> httpx.Response:
        from urllib.parse import urlparse

        host = urlparse(url).netloc
        await self._throttle(host)
        return await self._client.get(url, **kwargs)

    @property
    def headers(self) -> httpx.Headers:
        return self._client.headers

    async def aclose(self) -> None:
        await self._client.aclose()


@asynccontextmanager
async def build_client(
    requests_per_second: float = 1.0,
) -> AsyncGenerator[RateLimitedClient, None]:
    client = RateLimitedClient(requests_per_second=requests_per_second)
    try:
        yield client
    finally:
        await client.aclose()
