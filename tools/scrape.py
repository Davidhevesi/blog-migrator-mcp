"""scrape_post tool — detect platform, dispatch to adapter, return NormalizedPost."""
from __future__ import annotations

import httpx

from client import RateLimitedClient
from platforms.base import BasePlatformAdapter
from platforms.generic import GenericAdapter
from platforms.squarespace import SquarespaceAdapter
from platforms.wordpress import WordPressAdapter
from schemas import NormalizedPost

_ADAPTERS: list[BasePlatformAdapter] = [
    WordPressAdapter(),
    SquarespaceAdapter(),
    GenericAdapter(),  # must be last — always matches
]


async def scrape_post(url: str, client: RateLimitedClient) -> NormalizedPost:
    """Scrape a single blog post URL and return a NormalizedPost.

    Platform detection is done by fetching the page once and passing
    the HTML to each adapter's `identify()` in priority order.
    """
    try:
        r = await client.get(url, timeout=20)
        html = r.text if r.status_code == 200 else ""
    except httpx.RequestError as exc:
        return NormalizedPost(url=url, warnings=[f"Request failed: {exc}"])

    adapter = _pick_adapter(url, html)
    return await adapter.scrape(url, client)


def _pick_adapter(url: str, html: str) -> BasePlatformAdapter:
    for adapter in _ADAPTERS:
        if adapter.identify(url, html):
            return adapter
    return _ADAPTERS[-1]  # GenericAdapter
