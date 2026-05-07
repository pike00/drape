# drape Setup Guide

**Purpose:** Protect secrets when using Claude Code with `.env` files.

When Claude Code reads a `.env` file, drape automatically masks secrets so they never appear in the LLM conversation. This prevents:
- Secrets leaking into conversation transcripts
- Provider caching of full credentials
- Accidental copy-paste of credentials into chat

## Installation

### Quick Start

drape is installed via [uv](https://docs.astral.sh/uv/). Install uv first if you don't have it.

```bash
# Install drape (via PyPI)
uv tool install drape

# OR install from source
git clone https://github.com/pike00/drape.git
cd drape
uv tool install .

# Set up Claude Code hook (from drape directory)
bash scripts/install-claude-hook.sh --project-dir /path/to/your/project
```

The script will:
1. Install the drape package via `uv tool install`
2. Configure `.claude/settings.json` to use the `drape-hook` command
3. Verify installation

### Manual Installation

If you prefer to do it manually:

**1. Install the package:**
```bash
uv tool install drape
```

This places `drape` and `drape-hook` on your PATH (by default in `~/.local/bin`). If they aren't found, run `uv tool update-shell` once.

**2. Update `.claude/settings.json`:**
Add this to your Claude Code project config:

```json
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
```

**3. Restart Claude Code** to load the new settings.

## Usage

Once installed, using Claude Code is normal — the masking happens automatically:

```
User: /read .env
Claude Code: (hook intercepts)
Claude sees: 
  POSTGRES_PASSWORD=wFw...
  AWS_SECRET_KEY=BD5...
```

Claude can now safely read `.env` files without seeing full secrets.

## How It Works

1. **PreToolUse Hook:** When Claude Code tries to `Read` a file, drape intercepts first
2. **File Detection:** Checks if the target matches `.env` patterns
3. **Masking:** Masks each value to first 3 chars + "..."
4. **Denial:** Denies the raw Read and returns masked content as the denial reason
5. **Result:** Claude sees masked values instead of secrets

This approach is safe because:
- Hook runs before the file is read
- Masking happens in your local environment (Claude doesn't see full secrets)
- First 3 chars + "..." is enough to identify secrets without revealing them
- Full secrets remain in your actual `.env` file (unmodified)

## What Gets Masked

✅ Files matched:
- `.env`
- `app.env`, `production.env`, etc.

❌ Files NOT masked:
- `.env.example` (typically not sensitive)
- `.env.sops` (already encrypted)
- `.env.json`, `.env.yaml` (use format-specific tools)

## Customization

### Mask Pattern

The reveal length is controlled by `DRAPE_PREFIX_CHARS` (default `3`). Set it as an environment variable for the hook command in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "DRAPE_PREFIX_CHARS=5 drape-hook"
          }
        ]
      }
    ]
  }
}
```

See the README's "Configuration" section for the full list of env vars (`DRAPE_ENTROPY_THRESHOLD`, `DRAPE_HOOK_PATTERNS`, `DRAPE_AUDIT_LOG`, `DRAPE_LOG_LEVEL`).

### File Patterns

To mask additional formats, modify the hook in your `.claude/settings.json` or file an issue at:
https://github.com/pike00/drape/issues

(Future versions will support configuration files.)

## Troubleshooting

**Hook not firing?**
- Restart Claude Code (settings.json changes require reload)
- Check that `.claude/settings.json` has valid JSON: `uvx --quiet python -m json.tool .claude/settings.json`
- Verify drape is installed: `uv tool list | grep drape` and `which drape-hook`

**Seeing raw secrets instead of masked values?**
- Ensure the hook is in `.claude/settings.json` under `PreToolUse` (not `PostToolUse`)
- Check file permissions: `.env` must be readable by the hook
- Verify file matches `.env` pattern (not `.env.example`)

**Hook has an error?**
- Test manually: `echo '{"tool_input":{"file_path":".env"}}' | drape-hook`
- Should output JSON with `hookSpecificOutput` field

## Security Notes

This tool prevents secrets from appearing in visible LLM transcripts, but:

- **Full secrets remain in `.env`** — If your `.env` is compromised, so are your secrets. Use SOPS or a secret manager for at-rest encryption.
- **LLM provider retention** — Even masked values might be logged by Claude/other providers. This tool prevents secrets from appearing in *visible* transcripts, not provider logs.
- **Masking is weak for short secrets** — A PIN like `1234` shows as `123...`, which is almost the full value. Use longer secrets.

See [docs/architecture.md](architecture.md) for detailed threat model.

## Uninstall

**Remove the hook:**
1. Edit `.claude/settings.json`
2. Delete the PreToolUse hook block for `Read`/`drape.hook`

**Uninstall the package:**
```bash
uv tool uninstall drape
```

## Next Steps

- Read `.env` files normally in Claude Code
- Try asking Claude to review or modify your configuration
- Report issues: https://github.com/pike00/drape/issues

## Global Installation (All Projects)

To use drape across all Claude Code projects, update your global `.claude/settings.json`:

```bash
# Edit ~/.claude/settings.json (or create it)
# Add the PreToolUse hook section above
```

Then it will apply to all projects that don't have local `.claude/settings.json` overrides.
