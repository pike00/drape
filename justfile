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

# Cut a release: bump version, draft notes via LLM, review, tag, push, GitHub release. Delegates to release-kit.
release LEVEL:
    @command -v release-kit >/dev/null || { \
        echo "error: 'release-kit' not on PATH; install with 'uv tool install ~/projects/release-kit'" >&2; \
        exit 1; \
    }
    release-kit cut {{ LEVEL }}
