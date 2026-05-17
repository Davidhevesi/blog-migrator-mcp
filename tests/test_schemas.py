"""Unit tests for NormalizedPost schema."""
import pytest
from datetime import datetime, timezone

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import NormalizedPost, ImageRef


def test_normalized_post_minimal():
    post = NormalizedPost(url="https://example.com/blog/my-first-post")
    assert post.url == "https://example.com/blog/my-first-post"
    assert post.slug == "my-first-post"
    assert post.platform == "generic"
    assert post.warnings == []
    assert post.images == []


def test_slug_derived_from_url():
    post = NormalizedPost(url="https://blog.example.com/2024/01/hello-world/")
    assert post.slug == "hello-world"


def test_explicit_slug_respected():
    post = NormalizedPost(url="https://example.com/p/123", slug="custom-slug")
    assert post.slug == "custom-slug"


def test_word_count_auto_calculated():
    post = NormalizedPost(
        url="https://example.com/post",
        body_markdown="This is a five word sentence.",
    )
    assert post.word_count == 6


def test_word_count_not_overwritten_if_set():
    post = NormalizedPost(
        url="https://example.com/post",
        body_markdown="one two three",
        word_count=99,
    )
    assert post.word_count == 99


def test_image_ref():
    img = ImageRef(url="https://example.com/img.jpg", alt="A photo")
    assert img.local_path is None


def test_full_post():
    post = NormalizedPost(
        url="https://example.com/2024/my-post",
        platform="wordpress",
        title="My Post",
        body_markdown="# Hello\n\nThis is body text.",
        excerpt="Short excerpt",
        author="Jane Doe",
        published_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        categories=["Travel", "Food"],
        tags=["italy", "pasta"],
        images=[ImageRef(url="https://example.com/img.jpg", alt="pasta")],
        featured_image=ImageRef(url="https://example.com/hero.jpg"),
        canonical_url="https://example.com/2024/my-post",
        language="en",
        warnings=[],
    )
    assert post.title == "My Post"
    assert len(post.categories) == 2
    assert post.word_count > 0
    assert post.slug == "my-post"


def test_serialization():
    post = NormalizedPost(url="https://example.com/post", title="Test")
    data = post.model_dump(mode="json")
    assert isinstance(data, dict)
    assert data["title"] == "Test"
    assert data["published_at"] is None
