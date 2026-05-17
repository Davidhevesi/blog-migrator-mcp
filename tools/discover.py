"""discover_blog tool — find all post URLs on a blog site."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

import httpx

from client import RateLimitedClient


class DiscoveredPost:
    def __init__(self, url: str, source: str, confidence: float) -> None:
        self.url = url
        self.source = source  # "wp_api" | "sitemap" | "rss"
        self.confidence = confidence

    def to_dict(self) -> dict:
        return {"url": self.url, "source": self.source, "confidence": self.confidence}


async def discover_blog(
    site_url: str,
    client: RateLimitedClient,
    max_posts: int = 500,
) -> list[dict]:
    """Discover all blog post URLs for a site.

    Strategy (in order):
    1. WordPress REST API  → confidence 0.95
    2. Sitemap XML         → confidence 0.80
    3. RSS feed            → confidence 0.70

    Returns a list of dicts with keys: url, source, confidence.
    """
    origin = _origin(site_url)

    # 1. WordPress REST API
    posts = await _try_wp_api(origin, client, max_posts)
    if posts:
        return [p.to_dict() for p in posts]

    # 2. Sitemap
    posts = await _try_sitemap(origin, client, max_posts)
    if posts:
        return [p.to_dict() for p in posts]

    # 3. RSS
    posts = await _try_rss(origin, client, max_posts)
    return [p.to_dict() for p in posts]


# ---------------------------------------------------------------------------
# WordPress REST API
# ---------------------------------------------------------------------------

async def _try_wp_api(
    origin: str, client: RateLimitedClient, max_posts: int
) -> list[DiscoveredPost]:
    api_base = f"{origin}/wp-json/wp/v2/posts"
    posts: list[DiscoveredPost] = []
    page = 1
    per_page = 100

    while len(posts) < max_posts:
        try:
            r = await client.get(
                api_base,
                params={"per_page": per_page, "page": page, "fields": "link"},
                timeout=15,
            )
        except httpx.RequestError:
            break

        if r.status_code != 200:
            break

        data = r.json()
        if not isinstance(data, list) or not data:
            break

        for item in data:
            link = item.get("link") or item.get("url") or item.get("guid", {}).get("rendered", "")
            if link:
                posts.append(DiscoveredPost(url=link, source="wp_api", confidence=0.95))

        # Check if more pages exist
        total_pages = int(r.headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break
        page += 1

    return posts[: max_posts]


# ---------------------------------------------------------------------------
# Sitemap
# ---------------------------------------------------------------------------

SITEMAP_CANDIDATES = [
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap-posts-post-1.xml",
    "/wp-sitemap.xml",
    "/post-sitemap.xml",
]

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


async def _try_sitemap(
    origin: str, client: RateLimitedClient, max_posts: int
) -> list[DiscoveredPost]:
    for path in SITEMAP_CANDIDATES:
        url = origin + path
        try:
            r = await client.get(url, timeout=15)
        except httpx.RequestError:
            continue
        if r.status_code != 200:
            continue

        try:
            root = ET.fromstring(r.text)
        except ET.ParseError:
            continue

        tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag

        if tag == "sitemapindex":
            # Recurse into child sitemaps
            posts: list[DiscoveredPost] = []
            for loc in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
                child_url = loc.text or ""
                child_posts = await _fetch_sitemap_urls(child_url, client, max_posts)
                posts.extend(child_posts)
                if len(posts) >= max_posts:
                    break
            if posts:
                return posts[: max_posts]

        elif tag == "urlset":
            return _parse_urlset(root, max_posts)

    return []


async def _fetch_sitemap_urls(
    url: str, client: RateLimitedClient, max_posts: int
) -> list[DiscoveredPost]:
    try:
        r = await client.get(url, timeout=15)
    except httpx.RequestError:
        return []
    if r.status_code != 200:
        return []
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return []
    return _parse_urlset(root, max_posts)


def _parse_urlset(root: ET.Element, max_posts: int) -> list[DiscoveredPost]:
    posts: list[DiscoveredPost] = []
    for loc in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
        url = loc.text or ""
        if url and _looks_like_post(url):
            posts.append(DiscoveredPost(url=url, source="sitemap", confidence=0.80))
        if len(posts) >= max_posts:
            break
    return posts


def _looks_like_post(url: str) -> bool:
    """Heuristic: exclude obvious non-post URLs."""
    skip = {"/tag/", "/category/", "/author/", "/page/", "?", "#", "/feed"}
    return not any(s in url for s in skip)


# ---------------------------------------------------------------------------
# RSS
# ---------------------------------------------------------------------------

RSS_CANDIDATES = ["/feed", "/feed/", "/rss.xml", "/rss", "/atom.xml"]


async def _try_rss(
    origin: str, client: RateLimitedClient, max_posts: int
) -> list[DiscoveredPost]:
    for path in RSS_CANDIDATES:
        url = origin + path
        try:
            r = await client.get(url, timeout=15)
        except httpx.RequestError:
            continue
        if r.status_code != 200:
            continue

        try:
            root = ET.fromstring(r.text)
        except ET.ParseError:
            continue

        posts: list[DiscoveredPost] = []
        for link in root.iter("link"):
            text = link.text or ""
            if text.startswith("http") and _looks_like_post(text):
                posts.append(DiscoveredPost(url=text, source="rss", confidence=0.70))
        # Atom feeds
        for entry in root.iter("{http://www.w3.org/2005/Atom}link"):
            href = entry.get("href") or ""
            if href.startswith("http") and _looks_like_post(href):
                posts.append(DiscoveredPost(url=href, source="rss", confidence=0.70))

        if posts:
            return posts[: max_posts]

    return []


def _origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"
