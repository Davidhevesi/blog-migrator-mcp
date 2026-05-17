"""Abstract base for platform adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod

import httpx
from bs4 import BeautifulSoup

from schemas import NormalizedPost


class BasePlatformAdapter(ABC):
    """Base class for all platform-specific scrapers."""

    name: str = "base"

    @abstractmethod
    def identify(self, url: str, html: str) -> bool:
        """Return True if this adapter should handle the given page."""
        ...

    @abstractmethod
    async def scrape(self, url: str, client: httpx.AsyncClient) -> NormalizedPost:
        """Fetch and return a fully populated NormalizedPost."""
        ...

    # Shared helpers -----------------------------------------------------------

    @staticmethod
    def _soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    @staticmethod
    def _meta(soup: BeautifulSoup, name: str) -> str:
        tag = soup.find("meta", attrs={"name": name}) or soup.find(
            "meta", attrs={"property": name}
        )
        if tag and tag.get("content"):
            return tag["content"].strip()
        return ""
