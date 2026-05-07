# drape Architecture

## Overview

**drape** is a credential masking utility designed to make `.env` file management safe for AI agents like Claude Code.

## Problem

When an LLM reads a plaintext `.env` file, all secrets are visible in the conversation context:
```
MM_EMAILSETTINGS_SMTPUSERNAME=AKIAQU6D3H2I4SYVDHJP
MM_EMAILSETTINGS_SMTPPASSWORD=BD5w5gQ2mLPvBfgWBVgfi+OD3vzi441//QlruXrMo8oZ
```

This is a security risk — credentials could be:
- Logged in conversation transcripts
- Cached by the LLM provider
- Exposed if the session is compromised

## Solution

Mask secrets by showing only the first 3 characters + ellipsis:
```
MM_EMAILSETTINGS_SMTPUSERNAME=AKI...
MM_EMAILSETTINGS_SMTPPASSWORD=BD5...
```

This retains enough information to identify a credential (which service, which key), while hiding the actual secret.

## Implementation Phases

### Phase 1: Core Utility (MVP)
- [x] Bash script that parses KEY=VALUE format
- [x] Masks values to 3 chars + `...`
- [x] Can be invoked manually or from scripts
- Status: **DONE** (`scripts/parse-env.sh`)

### Phase 2: Claude Code Integration
- [x] PreToolUse hook in `.claude/settings.json` intercepts `Read` on `.env` files
- [x] Python hook script at `.claude/hooks/drape-mask.py`
- [x] Hook denies raw Read and returns masked content as denial reason
- [x] Tested with real `.env` files (mattermost)
- Status: **DONE**

### Phase 3: Plugin
- [ ] Package as Claude Code plugin
- [ ] Auto-discover and mask `.env` files
- [ ] Settings UI for masking rules
- Status: **FUTURE**

### Phase 4: Extended Features
- [ ] Support for other secret formats (YAML, JSON, .env.local variants)
- [ ] Unmasking on-demand (requires re-authentication)
- [ ] Audit logging (who requested unmasking)
- [ ] Integration with secret managers (1Password, Vault)
- Status: **FUTURE**

## Current Design

### `scripts/parse-env.sh`

Simple bash script that:
1. Reads a `.env` file line-by-line
2. Splits on `=` to separate KEY from VALUE
3. Outputs `KEY=${VALUE:0:3}...` (first 3 chars + ellipsis)
4. Skips comments and empty lines

**Limitations:**
- Doesn't handle multiline values (each line treated independently)
- Doesn't unquote values (outputs raw including quotes)
- No special handling for escape sequences

**Why this approach:**
- Zero dependencies (no jq, no Python needed)
- Transparent and auditable
- Easy to integrate into hooks

### Integration Points

**Current (Phase 2) -- PreToolUse hook:**
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Read",
      "hooks": [{
        "type": "command",
        "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/drape-mask.py"
      }]
    }]
  }
}
```

The hook receives tool input as JSON on stdin, checks if the file matches `.env` patterns, and returns a `permissionDecision: "deny"` with masked content as the reason. PostToolUse was not viable because it cannot modify built-in tool output.

**Long-term (Phase 3):**
- Claude Code plugin that intercepts `Read` calls
- Automatically detects `.env` files
- Applies masking without user configuration

## Security Considerations

### What We're Protecting Against

1. **Transcript logging** — Secrets shouldn't appear in conversation history
2. **Provider retention** — LLM providers shouldn't cache full secrets
3. **Accidental sharing** — Screenshots/exports shouldn't leak credentials
4. **Copy-paste errors** — User shouldn't accidentally paste full secret into chat

### What We're NOT Protecting Against

1. **Compromised claude.ai account** — If someone has access to your Claude account, they can read `.env` files anyway
2. **Keyloggers** — If your machine is compromised, masking won't help
3. **Permissions escalation** — drape respects existing file permissions
4. **Unmasking** — A future unmasking feature would need strong auth (MFA, 2FA)

### Threat Model

- **Attacker:** Someone with read access to conversation transcripts (e.g., via Claude billing page, archive, export)
- **Goal:** Extract credentials from transcripts
- **Mitigation:** First 3 chars don't uniquely identify a credential; full secret is hidden

**Example:**
```
Masked:   AKIAQU6D3H2I4SYVDHJP → AKI...
Attacker sees: AKI...
Can they brute-force? No — 10^18 possibilities, impractical
Can they guess from pattern? No — AWS access key format is known, but first 3 chars vary
```

## File Structure

```
drape/
├── README.md                  # Overview
├── docs/
│   └── architecture.md        # This file
├── scripts/
│   ├── parse-env.sh          # Core masking utility
│   └── (future: hook installer, unmasking, etc.)
└── tests/
    └── (future: test suite)
```

## Next Steps

1. **Build plugin scaffold:** Create the plugin manifest and boilerplate
2. **Extended formats:** Support .env.local, .env.production, YAML, JSON
3. **Unmasking:** Design safe re-authentication flow for full secret retrieval
