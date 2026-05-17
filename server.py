"""Blog Migrator MCP Server.

Tools:
  - discover_blog(site_url)           → list of post URLs with confidence scores
  - scrape_post(url)                  → NormalizedPost as JSON dict
  - download_images(post_data, dir)   → NormalizedPost with local_path set on images
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path when running via `fastmcp dev server.py`
sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP

from client import build_client
from schemas import NormalizedPost
from tools.discover import discover_blog as _discover_blog
from tools.images import download_images as _download_images
from tools.scrape import scrape_post as _scrape_post

mcp = FastMCP(
    "Blog Migrator",
    instructions=(
        "Scrape blog posts from any public website and return normalized structured data. "
        "Use discover_blog first to get post URLs, then scrape_post on each URL, "
        "and optionally download_images to save images locally."
    ),
)


@mcp.tool()
async def discover_blog(
    site_url: str,
    max_posts: int = 500,
) -> list[dict]:
    """Discover all blog post URLs on a site.

    Args:
        site_url: The homepage or blog index URL (e.g. https://example.com).
        max_posts: Maximum number of post URLs to return (default 500).

    Returns:
        List of dicts with keys: url (str), source (str), confidence (float 0–1).
        source is one of: "wp_api", "sitemap", "rss".
    """
    async with build_client() as client:
        return await _discover_blog(site_url, client, max_posts=max_posts)


@mcp.tool()
async def scrape_post(url: str) -> dict:
    """Scrape a single blog post URL and return normalized structured data.

    Args:
        url: Full URL of the blog post to scrape.

    Returns:
        NormalizedPost as a JSON-serializable dict with fields:
          url, slug, platform, title, body_markdown, excerpt,
          author, published_at, updated_at, categories, tags,
          images, featured_image, canonical_url, language,
          word_count, warnings.
    """
    async with build_client() as client:
        post = await _scrape_post(url, client)
        return post.model_dump(mode="json")


@mcp.tool()
async def download_images(
    post_data: dict,
    output_dir: str,
    concurrency: int = 4,
) -> dict:
    """Download all images from a scraped post to a local directory.

    Args:
        post_data: A NormalizedPost dict as returned by scrape_post.
        output_dir: Absolute path to the directory where images should be saved.
                    A subdirectory named after the post slug will be created.
        concurrency: Number of concurrent downloads (default 4).

    Returns:
        Updated NormalizedPost dict with local_path set on each downloaded image.
    """
    post = NormalizedPost(**post_data)
    async with build_client() as client:
        updated = await _download_images(post, output_dir, client, concurrency=concurrency)
        return updated.model_dump(mode="json")


if __name__ == "__main__":
    mcp.run()
