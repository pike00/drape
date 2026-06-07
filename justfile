set shell := ["bash", "-uc"]
# `release` / `version` / changelog recipes come from release.just (shared).
# drape publishes to PyPI via GitHub Actions OIDC (release.yml). `just release`
# tags + pushes; the tag push triggers the workflow that uploads to PyPI.

default:
    @just --list

# BEGIN PROJECT-KIT — generated, do not edit by hand
import '.project-kit/_lib.just'
import '.project-kit/preview.just'
import '.project-kit/release.just'
import '.project-kit/test.just'
import '.project-kit/deploy.just'
import '.project-kit/build.just'
import '.project-kit/db.just'
import '.project-kit/setup.just'
import '.project-kit/docs.just'
import '.project-kit/clean.just'
# END PROJECT-KIT

# --- repo-specific ---

# Auto-format
fmt:
    uv run ruff check --fix .
    uv run black .
