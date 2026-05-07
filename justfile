set shell := ["bash", "-cu"]

# List recipes
default:
    @just --list

# Run tests
test:
    uv run pytest

# Run linters + type checks
check:
    uv run ruff check .
    uv run black --check .
    uv run mypy src/drape

# Auto-format
fmt:
    uv run ruff check --fix .
    uv run black .

# Cut a release: bump {patch|minor|major}, draft notes via Claude, review, tag, push, GitHub release
release LEVEL:
    ./scripts/release.sh {{ LEVEL }}
