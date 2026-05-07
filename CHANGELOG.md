# Changelog

All notable changes to drape will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-04-09

### Added

- Initial release of drape
- Core masking utility: first 3 characters + ellipsis pattern
- Python CLI: `drape` command-line tool
- Python API: `parse_env_file()` and `mask_value()` functions
- Claude Code integration: PreToolUse hook for automatic masking on `Read` calls
- Comprehensive test suite with 11+ tests
- Security threat model documentation
- Support for `.env` and `*.env` file patterns

### Features

- Parse `.env` files in KEY=VALUE format
- Mask secrets to 3 chars + "..." for safe LLM inspection
- Ignore comments and empty lines
- Handle whitespace gracefully
- Support values containing equals signs
- Package installable via pip

### Known Limitations

- Single-line values only (multiline JSON in values won't parse)
- No quote handling (outputs raw)
- KEY=VALUE format only (no YAML/JSON)
- Fixed masking pattern (not customizable yet)

## [0.2.0] - 2026-05-06

### Added

- **Configurable prefix length** via `--prefix-chars` CLI flag and
  `DRAPE_PREFIX_CHARS` env var (honored by both CLI and the hook).
- **Hard 25%-of-length cap** on the revealed prefix (minimum 1 char) so
  short secrets stay mostly hidden regardless of the configured prefix.
- **Pattern-aware credential detection** via the `detect-secrets` library:
  AWS keys, GitHub/GitLab tokens, Slack, Stripe, Twilio, SendGrid, Mailchimp,
  Discord, npm, JWT, and private keys are replaced with `<credential-type>`
  labels that leak the type but no characters of the secret.
- **Entropy-aware masking**: values below `--entropy-threshold` (default 3.0
  bits/char) render as `<low-entropy-secret>`. Catches dictionary-word
  passwords whose 3-char prefix would otherwise leak meaningful information.
- **Surrounding-quote stripping**: `KEY="abcd"` now reveals chars from `abcd`
  rather than `"abcd"`.
- **`.env.sops` support**: the CLI auto-detects SOPS-encrypted files, shells
  out to `sops -d`, and masks the in-process plaintext before printing. The
  hook intercepts `.env.sops` reads the same way. Plaintext is never written
  to disk and never returned to the caller.
- **YAML / JSON / TOML key-pattern masking** (`--format yaml|json|toml`).
  Walks the document and masks any leaf value whose key contains a
  secret-looking substring (`password`, `token`, `secret`, `api_key`,
  `auth`, `credential`, `private_key`, `access_key`, `client_secret`,
  `session`, `cookie`, `salt`, `signature`).
- **Hook expansion**: in addition to `Read`, the PreToolUse hook now
  intercepts `Grep` on secrets files (re-greps against the masked
  rendering) and `Bash` commands that try to read a secrets file directly
  (`cat`/`head`/`tail`/`less`/`more`/`grep`/`rg`/`ag`/`sed`/`awk`/`cut`
  on `.env`-shaped paths) — denied with a redirect to `drape`.
- **Append-only JSONL audit log** at `$DRAPE_AUDIT_LOG`. Records that a
  file was masked plus key count and format; never records values.
- **`pytest-cov` coverage configured** in `pyproject.toml`. 84% line coverage
  at release.
- Optional extras: `drape[yaml]`, `drape[toml]`, `drape[all]`.

### Changed

- `mask_value()` now takes optional `prefix_chars`, `entropy_threshold`, and
  `use_patterns` arguments.
- `parse_env_file()` forwards the same options.
- Package classifier upgraded from `Alpha` to `Beta`.
- Renamed package from `envmask` to `drape` (project rename — no API surface
  changes beyond the import path and the `drape` CLI entrypoint).

### Migration notes

- The default behavior changes for short and low-entropy values. A 4-char
  value previously showed `abc...`; it now shows `<low-entropy-secret>` (or
  `a...` if entropy is high enough). Set `--entropy-threshold 0` to restore
  the v0.1.0 reveal-everything-above-1-char behavior.
- Known-credential values (AWS keys, GitHub tokens, etc.) now render as
  `<credential-type>` instead of a 3-char prefix. Pass `--no-patterns` to
  restore the prefix behavior.

## Future Releases

### [0.3.0] - Planned

- [ ] Custom masking patterns via configuration file (mask string, per-key
      overrides)
- [ ] On-demand unmasking with re-authentication
- [ ] Better error messages and logging

### [1.0.0] - Planned

- [ ] Stable API and CLI
- [ ] Full plugin support for Claude Code
- [ ] Integration with secret managers (1Password, Vault)
- [ ] Audit logging
