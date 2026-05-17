"""download_images tool — async download of all images in a NormalizedPost."""
from __future__ import annotations

import asyncio
import hashlib
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from client import RateLimitedClient
from schemas import ImageRef, NormalizedPost


async def download_images(
    post: NormalizedPost,
    output_dir: str,
    client: RateLimitedClient,
    concurrency: int = 4,
) -> NormalizedPost:
    """Download all images in post.images and post.featured_image.

    Saves files to output_dir/<slug>/<filename>.
    Updates ImageRef.local_path on each image.
    Returns a new NormalizedPost with updated image paths.
    """
    base = Path(output_dir) / (post.slug or "post")
    base.mkdir(parents=True, exist_ok=True)

    all_refs = list(post.images)
    if post.featured_image and post.featured_image not in all_refs:
        all_refs.append(post.featured_image)

    semaphore = asyncio.Semaphore(concurrency)

    async def _download(ref: ImageRef) -> ImageRef:
        async with semaphore:
            filename = _slug_filename(ref.url)
            dest = base / filename
            if dest.exists():
                return ImageRef(url=ref.url, alt=ref.alt, local_path=str(dest))
            try:
                r = await client.get(ref.url, timeout=30)
                r.raise_for_status()
                dest.write_bytes(r.content)
                return ImageRef(url=ref.url, alt=ref.alt, local_path=str(dest))
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                return ImageRef(
                    url=ref.url,
                    alt=ref.alt,
                    local_path=None,
                )

    results = await asyncio.gather(*[_download(ref) for ref in all_refs])

    # Rebuild image lists with updated local_path
    updated_images: list[ImageRef] = []
    updated_featured: ImageRef | None = post.featured_image

    result_map = {r.url: r for r in results}

    for img in post.images:
        updated = result_map.get(img.url, img)
        updated_images.append(updated)

    if post.featured_image:
        updated_featured = result_map.get(post.featured_image.url, post.featured_image)

    return post.model_copy(
        update={"images": updated_images, "featured_image": updated_featured}
    )


def _slug_filename(url: str) -> str:
    """Derive a safe filename from a URL, preserving extension."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    name = path.rsplit("/", 1)[-1].split("?")[0]

    # Preserve extension
    if "." in name:
        stem, ext = name.rsplit(".", 1)
        ext = re.sub(r"[^a-zA-Z0-9]", "", ext)[:6]
    else:
        stem, ext = name, "jpg"

    # Slugify stem
    stem = re.sub(r"[^a-z0-9-]", "-", stem.lower())
    stem = re.sub(r"-+", "-", stem).strip("-")[:60]

    if not stem:
        stem = hashlib.md5(url.encode()).hexdigest()[:12]

    return f"{stem}.{ext}" if ext else stem
