---
title: drape Roadmap Follow-up
status: active
repos: [drape]
started: 2026-05-02
last_updated: 2026-05-10
next_step: Plan v0.4.0 scope — remaining v0.2.0 items (file-pattern allowlist, custom masking patterns, hook env-var config, --debug flag, code coverage, type hints) plus Docker Compose env-var masking and multi-hook configs from v0.3.0
---

# drape Roadmap Follow-up

## Goal

Track ongoing development of drape beyond v0.1.0 — feature decisions, integration points (homelab agent-task-runner is the first downstream consumer), and roadmap progress. drape is the "agent secrets harness": a Claude Code PreToolUse hook that masks `.env` values to first-3-chars + ellipsis so LLMs see `POSTGRES_PASSWORD=wFw...` instead of the raw secret.

## Tasks

### v0.2.0 (target Q3 2026)

- [x] Decide v0.2.0 vs v0.3.0 placement for `.env.sops` in-memory decrypt + mask support (shipped in v0.2.0 via `src/drape/sops.py`)
- [x] Open GitHub issue on pike00/drape for `.env.sops` support (moot — shipped directly in v0.2.0)
- [ ] Implement `.env.local`, `.env.production`, `.env.staging` variant matching
- [ ] Configurable file-pattern allowlist (which files the hook masks)
- [ ] Custom masking patterns via config file (`mask_chars: 5`, `mask_pattern: "***"`)
- [ ] Hook configuration via env vars
- [ ] `--debug` flag + better error messages
- [x] Optional audit logging (log masked operations) — `src/drape/audit.py`
- [x] GitHub Actions CI/CD pipeline — `.github/workflows/release.yml`
- [x] Automated PyPI publishing on GitHub releases — OIDC trusted publishing (commit a30ef3d)
- [ ] Code coverage reports
- [ ] 100% type hint coverage

### v0.3.0 (target Q4 2026)

- [x] YAML config file masking — `src/drape/formats.py`
- [x] JSON file masking (mask keys matching `password`, `api_key`, `token`, etc.) — `src/drape/formats.py`
- [x] TOML support — `src/drape/formats.py`
- [ ] Docker Compose env-var masking
- [ ] Multiple hook configurations per project

### v1.0.0 (target 2027 Q1)

- [ ] 1Password CLI integration
- [ ] HashiCorp Vault integration
- [ ] AWS Secrets Manager integration
- [ ] On-demand unmasking with credential prompt
- [ ] Claude Code plugin with auto-discovery
- [ ] Settings UI

## Session Log

### 2026-05-10

- Headless housekeeping pass (`/project-save-all`). README claimed v0.1.0 / 2026-04-09 quiet repo — reality: 13 commits since 2026-05-02, v0.2.0 and v0.3.1 both published to PyPI, GHA release workflow live with OIDC trusted publishing.
- Checked off shipped items grounded in verified evidence: `.env.sops` decrypt+mask (`src/drape/sops.py`), audit logging (`src/drape/audit.py`), CI/CD pipeline (`.github/workflows/release.yml`), automated PyPI publishing (commit a30ef3d), and YAML/JSON/TOML support (`src/drape/formats.py`).
- Bumped `last_updated` to 2026-05-10 and rewrote `next_step` — old one ("decide v0.2.0 vs v0.3.0 for sops support") moot since both versions shipped. New next step scopes v0.4.0.
- Left unchanged (insufficient evidence): file-pattern allowlist, custom masking patterns, hook env-var config, `--debug` flag, code coverage, type hint coverage, `.env.local/.production/.staging` variants, Docker Compose env masking, multi-hook configs.

### 2026-05-02

- Cloned pike00/drape to `~/projects/drape` (was missing locally; v0.1.0 shipped 2026-04-09, three commits, repo quiet since).
- Rediscovered drape while answering "where did I leave off with the agent secrets harness?" — it was not tracked as a project anywhere (not in Homelab `docs/projects/`, not in MEMORY.md). This README is the first project-tracking shell for it.
- Cross-referenced with the homelab `agent-task-runner` project: the ad-hoc `just sopsx <file> -d | grep -iE 'token|bot' | sed 's/=[^=]*$/=REDACTED/'` pattern (used to let agents peek at SOPS-encrypted `.env.sops` files without exposing values) is the same shape as what drape does for plaintext `.env`. SOPS support in drape would replace that pipeline cleanly.
- Decided to track drape development inside the drape repo (here) rather than under Homelab — separate repo, separate project surface.

## Notes

### 2026-05-02

- **Decisions:** Project tracking lives in `pike00/drape` under `docs/projects/`, not in Homelab. Slug `roadmap-followup` chosen over `v0.2-planning` so the same project can carry through v0.3.0 and v1.0.0 work without renaming.
- **Gotchas:** drape currently masks plaintext `.env` files only — explicitly excludes `.env.sops` per the file-pattern logic. The `KEY=val...` first-3-chars pattern leaks "this key has a value of length ≥ 3" but no more (10^18 brute-force space for any further chars). Single-line KEY=VALUE only — multiline JSON in `.env` values won't parse correctly.
- **Issues:** No CI/CD pipeline yet (v0.2.0 roadmap item). No automated PyPI publishing — `docs/PUBLISHING.md` describes a manual `twine upload` flow. Zero open GitHub issues as of 2026-05-02. Repo last commit 2026-04-09 — three weeks idle.
- **Accomplished:** Repo cloned to `~/projects/drape`. Project README created to track follow-up. No code changes to drape itself this session.
