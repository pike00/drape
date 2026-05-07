#!/usr/bin/env bash
# Install drape as a Claude Code PreToolUse hook
#
# This script:
# 1. Installs drape via `uv tool install`
# 2. Updates .claude/settings.json to use the `drape-hook` command
#
# Usage:
#   ./scripts/install-claude-hook.sh [--project-dir /path/to/project]
#   ./scripts/install-claude-hook.sh --global

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="${1:-.}"
INSTALL_MODE="local"  # local or global

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir)
      PROJECT_DIR="$2"
      shift 2
      ;;
    --global)
      INSTALL_MODE="global"
      shift
      ;;
    *)
      echo "Usage: $0 [--project-dir /path] [--global]"
      exit 1
      ;;
  esac
done

echo "drape Claude Code Installation"
echo "=================================="
echo

# Resolve paths
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
CLAUDE_DIR="$PROJECT_DIR/.claude"
HOOKS_DIR="$CLAUDE_DIR/hooks"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

echo "Project directory: $PROJECT_DIR"
echo "Claude config: $CLAUDE_DIR"
echo

# 1. Verify uv is available
if ! command -v uv >/dev/null 2>&1; then
  echo "❌ uv not found on PATH. Install it first: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

# 2. Install drape package via uv
echo "📦 Installing drape via uv tool..."

if [[ "$INSTALL_MODE" == "global" ]]; then
  uv tool install --upgrade drape
else
  uv tool install --upgrade --from "$SCRIPT_DIR" drape
fi

DRAPE_HOOK="drape-hook"

# Verify the hook command landed on PATH (uv tool install puts it in ~/.local/bin)
if ! command -v drape-hook >/dev/null 2>&1; then
  echo "   ⚠️  drape-hook not on PATH. Run 'uv tool update-shell' or add ~/.local/bin to PATH."
fi
echo "   ✓ drape installed (hook command: $DRAPE_HOOK)"
echo

# 2. Create hooks directory
echo "📂 Setting up hook directory..."
mkdir -p "$HOOKS_DIR"
echo "   ✓ $HOOKS_DIR created"
echo

# 3. Copy hook script
echo "🔗 Linking drape hook..."
# The hook can just use the package directly, no need to copy
echo "   ✓ Hook ready (uses installed package)"
echo

# 4. Update settings.json
echo "⚙️  Updating .claude/settings.json..."

if [[ ! -f "$SETTINGS_FILE" ]]; then
  echo "   Creating new $SETTINGS_FILE..."
  cat > "$SETTINGS_FILE" << 'EOF'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "drape-hook"
          }
        ]
      }
    ]
  }
}
EOF
else
  # Check if hook already exists
  if grep -qE "drape-hook|drape\.hook" "$SETTINGS_FILE" 2>/dev/null; then
    echo "   ⚠️  Hook already configured in settings.json"
  else
    echo "   Adding PreToolUse hook to existing settings.json..."
    # Backup
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup"
    # Use uv-managed python via uvx to insert hook (jq not always available)
    uvx --quiet python - "$SETTINGS_FILE" << 'PYTHON_EOF'
import json, sys
path = sys.argv[1]
with open(path) as f:
    config = json.load(f)
config.setdefault("hooks", {}).setdefault("PreToolUse", [])
hook_entry = {
    "matcher": "Read",
    "hooks": [{"type": "command", "command": "drape-hook"}]
}
if not any(h.get("matcher") == "Read" for h in config["hooks"]["PreToolUse"]):
    config["hooks"]["PreToolUse"].insert(0, hook_entry)
with open(path, "w") as f:
    json.dump(config, f, indent=2)
PYTHON_EOF
    echo "   ✓ Hook added (backup saved to settings.json.backup)"
  fi
fi
echo

# 5. Verify installation
echo "✅ Verification"
echo "==============="
echo
uv tool run --from drape python -c "from drape import mask_value; print('✓ drape package importable')"
uv tool run --from drape python -c "import drape.hook; print('✓ drape.hook module available')"
echo "✓ .claude/settings.json configured"
echo

echo "🎉 Installation complete!"
echo
echo "Next steps:"
echo "1. Restart Claude Code to reload settings"
echo "2. Try reading a .env file:"
echo "   /read .env"
echo "3. You should see masked secrets (e.g., AKI...)"
echo
echo "To uninstall:"
echo "  uv tool uninstall drape"
echo "  # then remove the PreToolUse hook from .claude/settings.json"
echo
