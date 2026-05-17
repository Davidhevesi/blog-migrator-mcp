"""Squarespace adapter — sitemap-based discovery, HTML + microdata extraction.

Note: Squarespace sits behind Cloudflare/Fastly. A realistic browser User-Agent
is required. Even then, some requests may return 403; warnings are surfaced on
the NormalizedPost rather than raising so the caller can decide what to do.
"""
from __future__ import annotations

import re
from datetime import datetime

import httpx
import trafilatura
from bs4 import BeautifulSoup

from platforms.base import BasePlatformAdapter
from schemas import ImageRef, NormalizedPost


class SquarespaceAdapter(BasePlatformAdapter):
    name = "squarespace"

    def identify(self, url: str, html: str) -> bool:
        return (
            "squarespace.com" in url
            or "static1.squarespace.com" in html
            or 'data-controller="HeaderLockManager"' in html
            or "Squarespace.afterBodyLoad" in html
        )

    async def scrape(self, url: str, client: httpx.AsyncClient) -> NormalizedPost:
        warnings: list[str] = []

        try:
            r = await client.get(url, timeout=20)
        except httpx.RequestError as exc:
            return NormalizedPost(
                url=url,
                platform="squarespace",
                warnings=[f"Request failed: {exc}"],
            )

        if r.status_code == 403:
            warnings.append(
                f"403 Forbidden — Cloudflare/Fastly may be blocking the request. "
                f"Headers sent: User-Agent={client.headers.get('user-agent', 'none')}"
            )
            return NormalizedPost(
                url=url,
                platform="squarespace",
                warnings=warnings,
            )

        if r.status_code != 200:
            warnings.append(f"Unexpected HTTP {r.status_code}")
            return NormalizedPost(url=url, platform="squarespace", warnings=warnings)

        html = r.text
        soup = self._soup(html)

        body_md = trafilatura.extract(
            html, include_images=True, output_format="markdown", url=url
        ) or ""
        if not body_md:
            warnings.append(
                "trafilatura returned empty body — template chrome may dominate"
            )

        title = self._extract_title(soup)
        pub, mod = self._extract_dates(soup)
        author = self._extract_author(soup)
        excerpt = self._meta(soup, "og:description") or self._meta(soup, "description")
        fi_url = self._meta(soup, "og:image")
        featured = ImageRef(url=fi_url) if fi_url else None
        images = self._extract_images(soup)
        lang_tag = soup.find("html")
        lang = lang_tag.get("lang", "") if lang_tag else ""

        categories: list[str] = []
        tags: list[str] = []
        for a in soup.select("a.blog-categories-item, a[data-layout-label='Post Tags']"):
            text = a.get_text().strip()
            if text:
                tags.append(text)

        return NormalizedPost(
            url=url,
            platform="squarespace",
            title=title,
            body_markdown=body_md,
            excerpt=excerpt,
            author=author,
            published_at=pub,
            updated_at=mod,
            categories=categories,
            tags=tags,
            images=images,
            featured_image=featured,
            canonical_url=self._meta(soup, "og:url") or url,
            language=lang,
            warnings=warnings,
        )

    # Helpers ------------------------------------------------------------------

    def _extract_title(self, soup: BeautifulSoup) -> str:
        # Squarespace puts the post title in <h1 class="entry-title">
        for sel in ("h1.entry-title", "h1.blog-item-title", "h1"):
            tag = soup.select_one(sel)
            if tag:
                return tag.get_text().strip()
        return self._meta(soup, "og:title")

    def _extract_dates(
        self, soup: BeautifulSoup
    ) -> tuple[datetime | None, datetime | None]:
        def _dt(s: str | None) -> datetime | None:
            if not s:
                return None
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                return None

        # JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json

                data = json.loads(script.string or "")
                if isinstance(data, list):
                    data = data[0]
                pub = data.get("datePublished") or data.get("dateCreated")
                mod = data.get("dateModified")
                if pub:
                    return _dt(pub), _dt(mod)
            except Exception:
                pass

        # Microdata / meta tags
        pub = self._meta(soup, "article:published_time") or self._meta(
            soup, "datePublished"
        )
        mod = self._meta(soup, "article:modified_time")
        if not pub:
            time_tag = soup.find("time", attrs={"datetime": True})
            if time_tag:
                pub = time_tag["datetime"]
        return _dt(pub), _dt(mod)

    def _extract_author(self, soup: BeautifulSoup) -> str:
        for sel in (
            'a[href*="/author/"]',
            ".author-name",
            ".blog-author-title",
        ):
            tag = soup.select_one(sel)
            if tag:
                return tag.get_text().strip()
        return self._meta(soup, "author") or self._meta(soup, "article:author")

    @staticmethod
    def _extract_images(soup: BeautifulSoup) -> list[ImageRef]:
        images: list[ImageRef] = []
        seen: set[str] = set()
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            # Squarespace image URLs often have query params; strip for dedup
            clean = src.split("?")[0]
            if src and clean not in seen:
                seen.add(clean)
                images.append(ImageRef(url=src, alt=img.get("alt", "")))
        return images
