# drape

<!-- BEGIN PROJECT-KIT — generated, do not edit by hand -->
## Project-kit recipes

This repo is managed by project-kit (skill version: 0.1.0, last refreshed: 2026-06-06).
All dev/test/release/deploy operations go through `just`.

### Quick reference

| Task | Command |
|---|---|
| Run all tests | `just test-all` |
| Backend tests | `just test-backend` |
| Frontend tests | `just test-frontend` |
| E2E tests | `just test-e2e` |
| Lint | `just lint` |
| Typecheck | `just typecheck` |
| Cut a release | `just release patch` |
| Update CHANGELOG | `just changelog` |
| Build container image(s) | `just build-image [tag]` |
| Install dependencies | `just setup` |
| Health check | `uv run .project-kit/scripts/doctor.py` |

### Subsystem status

- preview: disabled
- release: enabled
- test: enabled
- deploy: disabled
- build: enabled
- db: disabled
- setup: enabled
- docs: disabled
- clean: enabled

### Where things live

- `.project-kit/*.just` — recipe definitions (10 files)
- `.project-kit/scripts/` — uv-scripts for non-trivial recipes
- `.project-kit/cliff.toml` — git-cliff config (centralized; passed via `--config`, no root copy)
- `.project-kit/hooks/` — git hooks (pre-commit guard + pre-push secrets/audit scan); `just setup-hooks` points `core.hooksPath` here
- `justfile` (root) — imports the 10 `.just` files plus repo-specific recipes

### How to refresh

Re-run the project-kit wizard in chat: ask Claude to "refresh project-kit"
or "audit project-kit in this repo".
<!-- END PROJECT-KIT -->
