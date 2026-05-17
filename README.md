# Blog Migrator MCP

This tool lets Claude scrape and migrate blog posts from any public website — extracting the title, body, images, author, tags, and more as clean, structured data. It works with Claude Desktop and Claude Code.

---

## Quick Setup (5 minutes, no technical knowledge needed)

### Step 1 — Install uv

Open **Terminal** (press `Cmd + Space`, type "Terminal", press Enter) and run:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close Terminal and reopen it before continuing.

---

### Step 2 — Add to Claude Desktop

1. Open Claude Desktop
2. Click **Claude** in the Mac menu bar → **Settings** → **Developer** → **Edit Config**

   This opens a file called `claude_desktop_config.json`.

3. Replace the entire contents with the following (or add the `mcpServers` block if you already have other servers):

```json
{
  "mcpServers": {
    "blog-migrator": {
      "command": "uvx",
      "args": ["--from", "/path/to/blog-migrator-mcp", "blog-migrator-mcp"]
    }
  }
}
```

4. Replace `/path/to/blog-migrator-mcp` with the actual path to this folder.

   **Easy way to get the path:** Open Terminal, type `echo ` (with a space after), then drag the `blog-migrator-mcp` folder from Finder into the Terminal window. The path will appear automatically. Copy it.

5. Save the file and **quit and reopen Claude Desktop**.

---

### Step 3 — Confirm it worked

After reopening Claude Desktop, look for a **hammer icon** in the chat input area. If you see it, the tool is ready.

---

## How to Use It

Paste prompts like these into Claude:

- *"Discover all blog posts on https://example.com and list the URLs."*
- *"Scrape the post at https://example.com/my-post and give me the title, body, and tags."*
- *"Scrape this post and download all its images to my Desktop."*

Claude will call the right tools automatically.

---

## Troubleshooting

**Hammer icon is missing**
- Make sure you quit Claude Desktop completely (Cmd + Q) and reopened it after saving the config.
- Double-check the path in the config — it must be the exact location of the `blog-migrator-mcp` folder on your Mac.

**"uvx not found" error**
- Close and reopen Terminal after installing `uv`, then try the setup again.
- If the problem persists, run `echo $PATH` and confirm `~/.local/bin` is listed.

**Site blocked or no posts found**
- Some sites block automated scrapers. Try a different blog URL to confirm the tool is working.

**Wrong path in config**
- Use the drag-to-Terminal trick to get an accurate path — do not type it manually.

---

## One-Click Installer (macOS)

Instead of editing the config file manually, you can run the installer script:

```
bash /path/to/blog-migrator-mcp/install.sh
```

This will install `uv` if needed and automatically add the server to your Claude Desktop config without overwriting any existing settings.

---

## Once Published to GitHub (cleaner setup)

Once this package is published, you can use this simpler config instead:

```json
{
  "mcpServers": {
    "blog-migrator": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/yourusername/blog-migrator-mcp", "blog-migrator-mcp"]
    }
  }
}
```

No folder path needed — `uvx` will download and run it directly.

---

## Claude Code (developer)

If you use Claude Code in the terminal, add the server with:

```
claude mcp add blog-migrator -- uvx --from /path/to/blog-migrator-mcp blog-migrator-mcp
```

---

## For Developers

**Install locally:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**Run the dev server with hot reload:**

```bash
fastmcp dev server.py
```

**Run tests:**

```bash
pytest
```

### Tools

| Tool | Description |
|------|-------------|
| `discover_blog(site_url, max_posts)` | Returns a list of post URLs with confidence scores. Tries WordPress API, sitemap, and RSS feed. |
| `scrape_post(url)` | Scrapes a single post and returns a `NormalizedPost` dict. |
| `download_images(post_data, output_dir, concurrency)` | Downloads all images from a scraped post to a local directory. |

### NormalizedPost schema

```
url, slug, platform, title, body_markdown, excerpt,
author, published_at, updated_at, categories, tags,
images, featured_image, canonical_url, language,
word_count, warnings
```

### Supported Platforms

- **WordPress** — uses REST API for metadata, falls back to HTML scraping
- **Squarespace** — HTML scraping with Squarespace-specific selectors
- **Generic** — trafilatura-based content extraction for any site
