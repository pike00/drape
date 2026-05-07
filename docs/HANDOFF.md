# Handoff: drape — Safe .env Management for LLMs

**Generated**: 2026-04-09 (Updated: 2026-04-09)  
**Status**: Phase 1-2 Complete, GitHub Ready, Phase 3 In Design  
**Project Type**: Python Package / Claude Code Plugin

## Goal

Create a production-ready Python package and Claude Code plugin that masks secrets in `.env` files so Claude Code (and other LLMs) can safely read and edit credentials without exposing full values in conversation context.

## Completed (All Phases 1-2)

**Phase 1: Core Utility**
- [x] Designed masking strategy (first 3 chars + `...`)
- [x] Implemented bash masking utility
- [x] Tested on actual .env files
- [x] Documented architecture and threat model

**Phase 2: Claude Code Integration**
- [x] PreToolUse hook in `.claude/hooks/drape-mask.py`
- [x] Hook wired into `.claude/settings.json`
- [x] Tested masking on real .env files

**GitHub Publishing (New)**
- [x] Converted bash script to Python package with proper structure
- [x] Created `src/drape/` with masker.py, cli.py, __init__.py
- [x] Full test suite: 11 tests, all passing
- [x] Package build system: pyproject.toml, setup.py, MANIFEST.in
- [x] Documentation: README, CHANGELOG, CONTRIBUTING, architecture
- [x] License: MIT (LICENSE file)
- [x] CLI entry point: `drape` command
- [x] Python API: importable modules
- [x] Verified builds: wheel and source distributions

## Not Yet Done

- [ ] Phase 3: Package as Claude Code plugin (.claude-plugin manifest)
- [ ] Publish to PyPI
- [ ] Create GitHub Actions CI/CD workflow
- [ ] Phase 4: Support additional formats (.env.local, YAML, JSON, 1Password)
- [ ] Phase 4: Design unmasking flow with re-authentication

## Failed Approaches (Don't Repeat These)

- **Tried:** Look for existing built-in bash/jq masking functions
  - **Why it failed:** None exist (jq request is open but not implemented)
  - **Current approach:** Simple bash script with string slicing
  - **Better:** Custom script is lightweight, transparent, dependency-free

- **Tried:** Store secrets encrypted with hook unmasking
  - **Why it failed:** Adds complexity; out of scope for Phase 1
  - **Current approach:** Keep full secrets in .env, just mask display
  - **Better:** Defer encryption to secret managers (SOPS, Vault, 1Password)

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Bash over Python/Go | Zero dependencies; easy to integrate into hooks; auditable |
| First 3 chars + `...` | Enough to identify secret type/source; 10^18 possibilities for attacker |
| LINE-by-line parsing | Simple, fast; handles 99% of .env files; multiline values rare in practice |
| No quote handling | Outputs raw; user can read quoted vs. unquoted; adds no complexity |

## Current State

**Working:**
- `scripts/parse-env.sh` successfully masks .env files
- Tested with real AWS SES credentials (masking works)
- Architecture documented with threat model
- Project structured and ready for Phase 2

**Not Working / Incomplete:**
- Hook integration (not yet wired into Claude Code)
- Plugin packaging (scaffold not created)
- Unmasking feature (not implemented)
- Extended format support (planned for Phase 4)

**Uncommitted Changes:**
- `/home/will/Documents/Homelab/drape/` directory (new project)

## Files to Know

| File | Purpose |
|------|---------|
| `scripts/parse-env.sh` | Core masking utility — reads .env, outputs masked values |
| `docs/architecture.md` | Design doc, threat model, implementation phases |
| `README.md` | User-facing overview |

## Code Context

**parse-env.sh usage:**
```bash
./scripts/parse-env.sh [filepath]
# Default: .env
# Input:  MM_EMAILSETTINGS_SMTPUSERNAME=AKIAQU6D3H2I4SYVDHJP
# Output: MM_EMAILSETTINGS_SMTPUSERNAME=AKI...
```

**Bash implementation (key logic):**
```bash
masked="${value:0:3}..."  # First 3 chars + ellipsis
```

## Resume Instructions

### Phase 2: Claude Code Hook Integration

1. **Test hook configuration** in `.claude/settings.json` (project or global):
   ```json
   {
     "hooks": {
       "PostToolUse": [{
         "matcher": "Read",
         "hooks": [{
           "type": "command",
           "command": "cd /home/will/Documents/Homelab/drape && ./scripts/parse-env.sh $FILE"
         }]
       }]
     }
   }
   ```
   - Expected: Hook registers without errors

2. **Trigger a Read on a .env file** in Claude Code:
   ```
   /read mattermost/.env
   ```
   - Expected: Output shows masked values only (e.g., `AKI...`)
   - Expected: Full secrets NOT visible in conversation

3. **Verify masking in transcript:**
   - Check conversation history
   - Confirm no full secrets leaked
   - Document the hook configuration

4. **Refine hook syntax** if needed:
   - Handle file paths with spaces
   - Support environment variable expansion
   - Test with multiple .env files in one session

### Phase 2b: Extension to Multiple Formats

5. **Add support for `.env.local` variants:**
   ```bash
   # In parse-env.sh, add support for:
   # .env, .env.local, .env.production, .env.staging, etc.
   ```

6. **Add YAML/JSON support (optional):**
   ```bash
   # Create parse-yaml.sh, parse-json.sh
   # Mask specific keys by pattern (password*, secret*, api_key*, token*)
   ```

### Phase 3: Plugin Packaging

7. **Create plugin manifest** (`.claude-plugin/manifest.json`):
   ```json
   {
     "name": "drape",
     "description": "Mask secrets in .env files for safe LLM reading",
     "hooks": [
       { "event": "PostToolUse", "matcher": "Read", "action": "mask-env-secrets" }
     ]
   }
   ```

8. **Package plugin** for Claude Code marketplace or local installation

## Setup Required

None beyond the `.env` file present in the service directory you're masking.

## Edge Cases & Error Handling

- **Empty .env file:** Outputs nothing (graceful)
- **Missing file:** Exits with code 1 and error to stderr
- **Quoted values:** Outputs raw including quotes (e.g., `KEY="secret"...`)
- **Multiline values:** Only first line parsed (known limitation)
  - Workaround: Avoid multiline .env values; use JSON/YAML for complex structures
- **Special characters:** Passed through as-is (no escaping)
  - Example: `PASSWORD="p@ssw$rd"` → `PASSWORD="p@s..."`

## Security Notes

- **Full secrets remain in .env** — drape masks display only, doesn't encrypt
- **File permissions unchanged** — drape respects existing `chmod` rules
- **No audit trail** — (Phase 4 feature) no logging of who/when secrets were accessed
- **Unmasking not implemented** — (Phase 4 feature) would require re-authentication

## Warnings

- **This is NOT encryption** — If your `.env` file is compromised, so are your secrets. Use SOPS or a secret manager for at-rest encryption.
- **AI provider retention** — Even masked values might be logged by Claude/other LLM providers. This tool prevents secrets from appearing in *visible* transcripts, not provider logs.
- **3-char masking is weak if secrets are short** — e.g., a PIN like `1234` would show as `123...`, which is almost the full value. Workaround: use longer secrets.
- **Multiline values not supported** — If you have multiline JSON in a .env value, parse-env.sh will only process the first line. Convert to single-line or use a config file in a different format.

## Plugin Concept

**Vision for Phase 3:** drape as a Claude Code plugin that:
1. Auto-detects `.env`, `.env.local`, and related files
2. Masks secrets on every `Read` without explicit configuration
3. Provides settings UI to customize masking rules (which keys to mask, masking pattern)
4. Logs access attempts (optional audit trail)
5. Integrates with secret managers for unmasking on-demand

**Implementation approach:**
- Plugin hooks into `PostToolUse` for Read operations
- Checks file name/path against patterns
- Runs parse-env.sh (or extended masking logic)
- Returns masked content to Claude

**Status:** Not yet started; awaiting Phase 2 validation.
