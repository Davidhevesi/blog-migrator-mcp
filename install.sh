#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/Library/Application Support/Claude"
CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"

echo "Blog Migrator MCP — Installer"
echo "=============================="
echo ""

# ── 1. Ensure uv is available ──────────────────────────────────────────────────
if ! command -v uvx &>/dev/null; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # Reload PATH so uvx is usable immediately in this session
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

  if ! command -v uvx &>/dev/null; then
    echo ""
    echo "ERROR: uv was installed but uvx is still not found."
    echo "Please close this Terminal window, reopen it, and run the installer again."
    exit 1
  fi
  echo "uv installed successfully."
else
  echo "uv already installed — skipping."
fi

echo ""

# ── 2. Locate Claude Desktop config ────────────────────────────────────────────
if [ ! -d "$CONFIG_DIR" ]; then
  echo "ERROR: Claude Desktop does not appear to be installed."
  echo "Expected config directory not found: $CONFIG_DIR"
  echo ""
  echo "Please install Claude Desktop from https://claude.ai/download and try again."
  exit 1
fi

# ── 3. Backup existing config ──────────────────────────────────────────────────
if [ -f "$CONFIG_FILE" ]; then
  BACKUP="$CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
  cp "$CONFIG_FILE" "$BACKUP"
  echo "Backed up existing config to:"
  echo "  $BACKUP"
else
  echo "No existing config found — creating a new one."
  echo "{}" > "$CONFIG_FILE"
fi

echo ""

# ── 4. Merge mcpServers entry using Python ─────────────────────────────────────
python3 - <<PYEOF
import json, sys, os

config_file = os.path.expanduser("$CONFIG_FILE")
script_dir = "$SCRIPT_DIR"
backup = "$BACKUP" if os.path.exists("$CONFIG_FILE") else None

try:
    with open(config_file, "r") as f:
        config = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    config = {}

if not isinstance(config, dict):
    config = {}

config.setdefault("mcpServers", {})

config["mcpServers"]["blog-migrator"] = {
    "command": "uvx",
    "args": ["--from", script_dir, "blog-migrator-mcp"]
}

with open(config_file, "w") as f:
    json.dump(config, f, indent=2)
    f.write("\n")

print("Config updated successfully.")
PYEOF

if [ $? -ne 0 ]; then
  echo ""
  echo "ERROR: Failed to update Claude Desktop config."
  if [ -n "${BACKUP:-}" ] && [ -f "$BACKUP" ]; then
    cp "$BACKUP" "$CONFIG_FILE"
    echo "Restored original config from backup."
  fi
  exit 1
fi

# ── 5. Done ────────────────────────────────────────────────────────────────────
echo ""
echo "=============================="
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Quit Claude Desktop completely (Cmd + Q)"
echo "  2. Reopen Claude Desktop"
echo "  3. Look for the hammer icon in the chat input — that means it's working"
echo ""
echo "Server path: $SCRIPT_DIR"
