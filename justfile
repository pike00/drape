set shell := ["bash", "-uc"]
# `release` / `version` / changelog recipes come from release.just (shared).
# drape publishes to PyPI via GitHub Actions OIDC (release.yml). `just release`
# tags + pushes; the tag push triggers the workflow that uploads to PyPI.

default:
    @just --list

# BEGIN PROJECT-KIT — generated, do not edit by hand
import '.project-kit/_lib.just'
import '.project-kit/release.just'
# END PROJECT-KIT

# --- repo-specific ---

# Run linters + type checks
check:
    uv run ruff check .
    uv run black --check .
    uv run mypy src/drape

# Auto-format
fmt:
    uv run ruff check --fix .
    uv run black .

# Cut a release. Build and PyPI publish happen automatically via GitHub Actions
# OIDC after the tag push (release.yml). Alias: `just tag LEVEL`.
ship level:
    @just release {{level}}

# Run tests
test:
    uv run pytest
