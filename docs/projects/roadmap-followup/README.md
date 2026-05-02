---
title: envmask Roadmap Follow-up
status: active
repos: [envmask]
started: 2026-05-02
last_updated: 2026-05-02
next_step: Decide whether `.env.sops` in-memory decrypt+mask support belongs in v0.2.0 or v0.3.0; open issue on pike00/envmask if pursued
---

# envmask Roadmap Follow-up

## Goal

Track ongoing development of envmask beyond v0.1.0 — feature decisions, integration points (homelab agent-task-runner is the first downstream consumer), and roadmap progress. envmask is the "agent secrets harness": a Claude Code PreToolUse hook that masks `.env` values to first-3-chars + ellipsis so LLMs see `POSTGRES_PASSWORD=wFw...` instead of the raw secret.

## Tasks

### v0.2.0 (target Q3 2026)

- [ ] Decide v0.2.0 vs v0.3.0 placement for `.env.sops` in-memory decrypt + mask support
- [ ] Open GitHub issue on pike00/envmask for `.env.sops` support (if pursued)
- [ ] Implement `.env.local`, `.env.production`, `.env.staging` variant matching
- [ ] Configurable file-pattern allowlist (which files the hook masks)
- [ ] Custom masking patterns via config file (`mask_chars: 5`, `mask_pattern: "***"`)
- [ ] Hook configuration via env vars
- [ ] `--debug` flag + better error messages
- [ ] Optional audit logging (log masked operations)
- [ ] GitHub Actions CI/CD pipeline
- [ ] Automated PyPI publishing on GitHub releases
- [ ] Code coverage reports
- [ ] 100% type hint coverage

### v0.3.0 (target Q4 2026)

- [ ] YAML config file masking
- [ ] JSON file masking (mask keys matching `password`, `api_key`, `token`, etc.)
- [ ] TOML support
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

### 2026-05-02

- Cloned pike00/envmask to `~/projects/envmask` (was missing locally; v0.1.0 shipped 2026-04-09, three commits, repo quiet since).
- Rediscovered envmask while answering "where did I leave off with the agent secrets harness?" — it was not tracked as a project anywhere (not in Homelab `docs/projects/`, not in MEMORY.md). This README is the first project-tracking shell for it.
- Cross-referenced with the homelab `agent-task-runner` project: the ad-hoc `just sopsx <file> -d | grep -iE 'token|bot' | sed 's/=[^=]*$/=REDACTED/'` pattern (used to let agents peek at SOPS-encrypted `.env.sops` files without exposing values) is the same shape as what envmask does for plaintext `.env`. SOPS support in envmask would replace that pipeline cleanly.
- Decided to track envmask development inside the envmask repo (here) rather than under Homelab — separate repo, separate project surface.

## Notes

### 2026-05-02

- **Decisions:** Project tracking lives in `pike00/envmask` under `docs/projects/`, not in Homelab. Slug `roadmap-followup` chosen over `v0.2-planning` so the same project can carry through v0.3.0 and v1.0.0 work without renaming.
- **Gotchas:** envmask currently masks plaintext `.env` files only — explicitly excludes `.env.sops` per the file-pattern logic. The `KEY=val...` first-3-chars pattern leaks "this key has a value of length ≥ 3" but no more (10^18 brute-force space for any further chars). Single-line KEY=VALUE only — multiline JSON in `.env` values won't parse correctly.
- **Issues:** No CI/CD pipeline yet (v0.2.0 roadmap item). No automated PyPI publishing — `docs/PUBLISHING.md` describes a manual `twine upload` flow. Zero open GitHub issues as of 2026-05-02. Repo last commit 2026-04-09 — three weeks idle.
- **Accomplished:** Repo cloned to `~/projects/envmask`. Project README created to track follow-up. No code changes to envmask itself this session.
