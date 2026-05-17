"""WordPress adapter — REST API primary, HTML fallback."""
from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from platforms.base import BasePlatformAdapter
from schemas import ImageRef, NormalizedPost


class WordPressAdapter(BasePlatformAdapter):
    name = "wordpress"

    def identify(self, url: str, html: str) -> bool:
        if "/wp-content/" in html or "/wp-json/" in html:
            return True
        if 'name="generator" content="WordPress' in html:
            return True
        return False

    # REST API -----------------------------------------------------------------

    @staticmethod
    def _api_base(url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/wp-json/wp/v2"

    async def _fetch_via_api(
        self, url: str, client: httpx.AsyncClient
    ) -> NormalizedPost | None:
        """Try to find this post via the WP REST API by slug."""
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        api_base = self._api_base(url)
        try:
            r = await client.get(
                f"{api_base}/posts",
                params={"slug": slug, "_embed": 1},
                timeout=15,
            )
            if r.status_code != 200:
                return None
            data = r.json()
            if not data:
                return None
            return self._map_api_post(data[0], url)
        except Exception:
            return None

    def _map_api_post(self, post: dict, fallback_url: str) -> NormalizedPost:
        import trafilatura

        raw_html = post.get("content", {}).get("rendered", "")
        body_md = trafilatura.extract(
            raw_html, include_images=True, output_format="markdown"
        ) or ""

        pub = post.get("date_gmt") or post.get("date")
        mod = post.get("modified_gmt") or post.get("modified")

        def _dt(s: str | None) -> datetime | None:
            if not s:
                return None
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                return None

        # Author from _embedded
        author = ""
        embedded = post.get("_embedded", {})
        authors = embedded.get("author", [])
        if authors:
            author = authors[0].get("name", "")

        # Categories / tags from _embedded terms
        categories: list[str] = []
        tags: list[str] = []
        for term_group in embedded.get("wp:term", []):
            for term in term_group:
                if term.get("taxonomy") == "category":
                    categories.append(term["name"])
                elif term.get("taxonomy") == "post_tag":
                    tags.append(term["name"])

        # Featured image
        featured: ImageRef | None = None
        fi_list = embedded.get("wp:featuredmedia", [])
        if fi_list:
            fi = fi_list[0]
            featured = ImageRef(
                url=fi.get("source_url", ""),
                alt=fi.get("alt_text", ""),
            )

        # Inline images from rendered HTML
        soup = BeautifulSoup(raw_html, "lxml")
        images = _extract_images(soup)

        link = post.get("link") or fallback_url

        return NormalizedPost(
            url=link,
            platform="wordpress",
            title=BeautifulSoup(
                post.get("title", {}).get("rendered", ""), "lxml"
            ).get_text(),
            body_markdown=body_md,
            excerpt=BeautifulSoup(
                post.get("excerpt", {}).get("rendered", ""), "lxml"
            ).get_text().strip(),
            author=author,
            published_at=_dt(pub),
            updated_at=_dt(mod),
            categories=categories,
            tags=tags,
            images=images,
            featured_image=featured,
            canonical_url=link,
        )

    # HTML fallback ------------------------------------------------------------

    async def _fetch_via_html(
        self, url: str, client: httpx.AsyncClient
    ) -> NormalizedPost:
        import trafilatura

        r = await client.get(url, timeout=20)
        r.raise_for_status()
        html = r.text
        soup = self._soup(html)

        body_md = trafilatura.extract(
            html, include_images=True, output_format="markdown", url=url
        ) or ""

        title = soup.find("h1")
        title_str = title.get_text().strip() if title else self._meta(soup, "og:title")

        pub_str = (
            self._meta(soup, "article:published_time")
            or self._meta(soup, "datePublished")
        )
        mod_str = self._meta(soup, "article:modified_time")

        def _dt(s: str) -> datetime | None:
            if not s:
                return None
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                return None

        author = self._meta(soup, "author") or self._meta(soup, "article:author")
        categories = [
            t.get_text().strip()
            for t in soup.select("a[rel='category tag'], .cat-links a")
        ]
        tags = [t.get_text().strip() for t in soup.select(".tags-links a")]

        images = _extract_images(soup)

        fi_url = self._meta(soup, "og:image")
        featured = ImageRef(url=fi_url) if fi_url else None

        warnings = []
        if not body_md:
            warnings.append("trafilatura returned empty body")

        return NormalizedPost(
            url=url,
            platform="wordpress",
            title=title_str,
            body_markdown=body_md,
            excerpt=self._meta(soup, "og:description"),
            author=author,
            published_at=_dt(pub_str),
            updated_at=_dt(mod_str),
            categories=list(set(categories)),
            tags=list(set(tags)),
            images=images,
            featured_image=featured,
            canonical_url=self._meta(soup, "og:url") or url,
            warnings=warnings,
        )

    # Entry point --------------------------------------------------------------

    async def scrape(self, url: str, client: httpx.AsyncClient) -> NormalizedPost:
        post = await self._fetch_via_api(url, client)
        if post:
            return post
        return await self._fetch_via_html(url, client)


def _extract_images(soup: BeautifulSoup) -> list[ImageRef]:
    images: list[ImageRef] = []
    seen: set[str] = set()
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if src and src not in seen:
            seen.add(src)
            images.append(ImageRef(url=src, alt=img.get("alt", "")))
    return images
