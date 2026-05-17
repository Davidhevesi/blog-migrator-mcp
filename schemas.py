"""Output contract for the blog migrator MCP server."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ImageRef(BaseModel):
    url: str
    alt: str = ""
    local_path: str | None = None  # set after download_images


class NormalizedPost(BaseModel):
    # Identity
    url: str
    slug: str = ""
    platform: Literal["wordpress", "squarespace", "generic"] = "generic"

    # Content
    title: str = ""
    body_markdown: str = ""
    excerpt: str = ""

    # Metadata
    author: str = ""
    published_at: datetime | None = None
    updated_at: datetime | None = None
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    # Media
    images: list[ImageRef] = Field(default_factory=list)
    featured_image: ImageRef | None = None

    # Discovery
    canonical_url: str = ""
    language: str = ""

    # Quality signals
    word_count: int = 0
    warnings: list[str] = Field(default_factory=list)

    @field_validator("slug", mode="before")
    @classmethod
    def derive_slug(cls, v: str) -> str:
        return v or ""

    @model_validator(mode="after")
    def auto_slug(self) -> "NormalizedPost":
        if not self.slug and self.url:
            path = self.url.rstrip("/").rsplit("/", 1)[-1]
            path = re.sub(r"[^a-z0-9-]", "-", path.lower())
            path = re.sub(r"-+", "-", path).strip("-")
            self.slug = path
        if not self.word_count and self.body_markdown:
            self.word_count = len(self.body_markdown.split())
        return self
