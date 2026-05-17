# Blog Migrator MCP

An MCP server that scrapes and migrates blog posts from any public website. Supports WordPress, Squarespace, and generic sites.

## Tools

| Tool | Description |
|---|---|
| `discover_blog` | Find all post URLs on a site |
| `scrape_post` | Scrape a single post into structured data |
| `download_images` | Download all images from a scraped post locally |

## Setup

**Requirements:** Python 3.11+

```bash
# Clone and install
git clone <repo>
cd blog-migrator-mcp

python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Running the Server

```bash
# Development mode (with MCP inspector)
fastmcp dev server.py

# Or run directly
python server.py
```

## Adding to Claude Code

Add the server to your Claude Code MCP config (`~/.claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "blog-migrator": {
      "command": "python",
      "args": ["/path/to/blog-migrator-mcp/server.py"]
    }
  }
}
```

## Usage Workflow

### 1. Discover posts

```
discover_blog(site_url="https://example.com", max_posts=500)
```

Returns a list of discovered post URLs with confidence scores:

```json
[
  { "url": "https://example.com/my-post", "source": "wp_api", "confidence": 0.95 },
  { "url": "https://example.com/another", "source": "sitemap", "confidence": 0.80 }
]
```

**Discovery strategy (tried in order):**
1. WordPress REST API (`confidence: 0.95`)
2. XML Sitemap (`confidence: 0.80`)
3. RSS/Atom feed (`confidence: 0.70`)

### 2. Scrape a post

```
scrape_post(url="https://example.com/my-post")
```

Returns a `NormalizedPost` with:

```json
{
  "url": "https://example.com/my-post",
  "slug": "my-post",
  "platform": "wordpress",
  "title": "My Post Title",
  "body_markdown": "# My Post\n\nContent here...",
  "excerpt": "Short description",
  "author": "Jane Doe",
  "published_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-16T08:00:00Z",
  "categories": ["Tech", "News"],
  "tags": ["python", "mcp"],
  "images": [{ "url": "https://example.com/img.jpg", "alt": "image", "local_path": null }],
  "featured_image": null,
  "canonical_url": "https://example.com/my-post",
  "language": "en",
  "word_count": 423,
  "warnings": []
}
```

### 3. Download images (optional)

```
download_images(
  post_data=<output from scrape_post>,
  output_dir="/absolute/path/to/output",
  concurrency=4
)
```

Downloads all images to `output_dir/<slug>/` and returns the updated post with `local_path` set on each image.

## Supported Platforms

- **WordPress** — uses REST API for metadata, falls back to HTML scraping
- **Squarespace** — HTML scraping with Squarespace-specific selectors
- **Generic** — trafilatura-based content extraction for any site

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```
