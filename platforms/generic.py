"""Generic adapter using trafilatura — fallback for all unrecognized platforms."""
from __future__ import annotations

from datetime import datetime

import httpx
import trafilatura
from bs4 import BeautifulSoup

from platforms.base import BasePlatformAdapter
from schemas import ImageRef, NormalizedPost


class GenericAdapter(BasePlatformAdapter):
    name = "generic"

    def identify(self, url: str, html: str) -> bool:
        return True  # always matches as fallback

    async def scrape(self, url: str, client: httpx.AsyncClient) -> NormalizedPost:
        r = await client.get(url, timeout=20)
        r.raise_for_status()
        html = r.text
        soup = self._soup(html)

        body_md = trafilatura.extract(
            html, include_images=True, output_format="markdown", url=url
        ) or ""

        # Title: prefer h1 > og:title > <title>
        h1 = soup.find("h1")
        title = (
            h1.get_text().strip()
            if h1
            else (self._meta(soup, "og:title") or (soup.title.string if soup.title else ""))
        )

        pub = self._meta(soup, "article:published_time") or self._meta(
            soup, "datePublished"
        )
        mod = self._meta(soup, "article:modified_time")

        def _dt(s: str) -> datetime | None:
            if not s:
                return None
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                return None

        author = self._meta(soup, "author") or self._meta(soup, "article:author")
        excerpt = self._meta(soup, "og:description") or self._meta(
            soup, "description"
        )
        fi_url = self._meta(soup, "og:image")
        featured = ImageRef(url=fi_url) if fi_url else None

        images: list[ImageRef] = []
        seen: set[str] = set()
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if src and src not in seen:
                seen.add(src)
                images.append(ImageRef(url=src, alt=img.get("alt", "")))

        lang_tag = soup.find("html")
        lang = lang_tag.get("lang", "") if lang_tag else ""

        warnings = []
        if not body_md:
            warnings.append("trafilatura returned empty body — page may require JS")

        return NormalizedPost(
            url=url,
            platform="generic",
            title=title,
            body_markdown=body_md,
            excerpt=excerpt,
            author=author,
            published_at=_dt(pub),
            updated_at=_dt(mod),
            images=images,
            featured_image=featured,
            canonical_url=self._meta(soup, "og:url") or url,
            language=lang,
            warnings=warnings,
        )
