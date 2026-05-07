#!/usr/bin/env bash
# Install drape as a Claude Code PreToolUse hook
#
# This script:
# 1. Installs drape package globally or in a venv
# 2. Copies the hook script to your Claude Code config directory
# 3. Updates .claude/settings.json to use the hook
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

# 1. Install drape package
echo "📦 Installing drape package..."

# Get the Python executable path
PYTHON_BIN=$(python3 -c "import sys; print(sys.executable)" 2>/dev/null) || PYTHON_BIN="python3"

if [[ "$INSTALL_MODE" == "global" ]]; then
  pip install --upgrade drape
  DRAPE_HOOK="$PYTHON_BIN -m drape.hook"
else
  pip install -e "$SCRIPT_DIR"
  DRAPE_HOOK="$PYTHON_BIN -m drape.hook"
fi
echo "   ✓ drape installed (using $PYTHON_BIN)"
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
            "command": "python3 -m drape.hook"
          }
        ]
      }
    ]
  }
}
EOF
else
  # Check if hook already exists
  if grep -q "drape.hook" "$SETTINGS_FILE" 2>/dev/null; then
    echo "   ⚠️  Hook already configured in settings.json"
  else
    echo "   Adding PreToolUse hook to existing settings.json..."
    # Backup
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup"
    # Use Python to insert hook (jq not always available)
    python3 << PYTHON_EOF
import json
with open('$SETTINGS_FILE') as f:
    config = json.load(f)
if 'hooks' not in config:
    config['hooks'] = {}
if 'PreToolUse' not in config['hooks']:
    config['hooks']['PreToolUse'] = []
hook_entry = {
    "matcher": "Read",
    "hooks": [{"type": "command", "command": "python3 -m drape.hook"}]
}
if not any(h.get("matcher") == "Read" for h in config['hooks']['PreToolUse']):
    config['hooks']['PreToolUse'].insert(0, hook_entry)
with open('$SETTINGS_FILE', 'w') as f:
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
$PYTHON_BIN -c "from drape import mask_value; print('✓ drape package importable')"
$PYTHON_BIN -c "import drape.hook; print('✓ drape.hook module available')"
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
echo "To uninstall, remove the PreToolUse hook from .claude/settings.json"
echo
