#!/usr/bin/env bash
# Cut a new release: bump version, draft notes via Claude, review, tag, push, create GitHub release.
#
# Usage: scripts/release.sh {patch|minor|major}
#
# Tag push triggers .github/workflows/release.yml which publishes to PyPI.
# pyproject.toml is NOT mutated locally; the release workflow rewrites the
# version from the tag at build time.

set -euo pipefail

LEVEL="${1:-}"
case "$LEVEL" in
    patch | minor | major) ;;
    *)
        echo "Usage: $0 {patch|minor|major}" >&2
        exit 2
        ;;
esac

# --- Preflight ---------------------------------------------------------------

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$branch" != "main" ]; then
    echo "error: must be on main (currently on '$branch')" >&2
    exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "error: working tree is dirty; commit or stash first" >&2
    git status --short >&2
    exit 1
fi

echo "==> Syncing with origin (branch + tags)…"
git fetch --quiet --prune --prune-tags --tags origin main
# Push any local-only tags up; non-fast-forward tag updates are rejected
# without --force, so this is safe.
git push --quiet --tags origin 2>/dev/null || true

local_sha=$(git rev-parse HEAD)
remote_sha=$(git rev-parse origin/main)
if [ "$local_sha" != "$remote_sha" ]; then
    echo "error: local main is not in sync with origin/main" >&2
    echo "  local : $local_sha" >&2
    echo "  origin: $remote_sha" >&2
    echo "  hint  : 'git pull --rebase && git push' first" >&2
    exit 1
fi

command -v claude >/dev/null || {
    echo "error: 'claude' CLI not found" >&2
    exit 1
}
command -v gh >/dev/null || {
    echo "error: 'gh' CLI not found" >&2
    exit 1
}
command -v jq >/dev/null || {
    echo "error: 'jq' not found" >&2
    exit 1
}
command -v uv >/dev/null || {
    echo "error: 'uv' not found" >&2
    exit 1
}

# --- Compute versions --------------------------------------------------------

current=$(uv version --short)
new=$(uv version --bump "$LEVEL" --dry-run --short)
new_tag="v$new"

if git rev-parse "$new_tag" >/dev/null 2>&1; then
    echo "error: tag $new_tag already exists" >&2
    exit 1
fi

last_tag=$(git describe --tags --abbrev=0 2>/dev/null || true)
if [ -n "$last_tag" ]; then
    log_range="$last_tag..HEAD"
else
    log_range="HEAD"
fi

commits=$(git log --no-merges --pretty=format:'- %s%n%b' "$log_range")
if [ -z "$commits" ]; then
    echo "error: no commits since $last_tag — nothing to release" >&2
    exit 1
fi

echo "==> Bumping $current → $new ($LEVEL)"
echo "==> $(echo "$commits" | grep -c '^- ') commits since ${last_tag:-<root>}"

# --- Draft notes via Claude --------------------------------------------------

prompt=$(
    cat <<EOF
You are drafting GitHub release notes for the "drape" Python package — a CLI
and Claude Code hook that masks secrets in .env / SOPS / YAML / JSON / TOML
files for safe LLM inspection.

This is a $LEVEL bump from $current to $new.

Commits since ${last_tag:-<root commit>}:

$commits

Produce JSON with two fields:
  - title: one line, format "vX.Y.Z — <short human summary>" (no markdown, no
    trailing punctuation).
  - body: GitHub-flavored markdown, grouped under "### Added", "### Changed",
    "### Fixed", "### Removed" headers (only include sections that apply).
    Bullet points should describe user-facing impact, not internal refactors.
    Skip purely mechanical commits (deps bumps, formatting) unless they
    materially affect users. End with an "**Install**" line: \`uv tool install
    drape==$new\` (in fenced bash block).

Be concise. No preamble, no marketing language, no emoji.
EOF
)

schema='{
  "type": "object",
  "properties": {
    "title": {"type": "string"},
    "body":  {"type": "string"}
  },
  "required": ["title", "body"],
  "additionalProperties": false
}'

echo "==> Drafting notes with Claude…"
draft_response=$(printf '%s' "$prompt" | claude -p \
    --output-format json \
    --json-schema "$schema")

title=$(printf '%s' "$draft_response" | jq -r '.structured_output.title // empty')
body=$(printf '%s' "$draft_response" | jq -r '.structured_output.body // empty')

if [ -z "$title" ] || [ -z "$body" ]; then
    echo "error: claude returned no structured output" >&2
    printf '%s' "$draft_response" | jq '.' >&2 || printf '%s\n' "$draft_response" >&2
    exit 1
fi

# --- Review ------------------------------------------------------------------

tmp=$(mktemp -t drape-release-XXXXXX.md)
trap 'rm -f "$tmp"' EXIT

cat >"$tmp" <<EOF
$title

---

$body

<!--
The first line above is the release TITLE.
Everything after the '---' separator is the BODY (markdown).
Edit freely, save, and quit. Lines in HTML comments are stripped.
Tag: $new_tag    Commits: ${last_tag:-<root>}..HEAD
-->
EOF

"${EDITOR:-vim}" "$tmp"

# Strip HTML comment blocks, split on first '---' separator line.
cleaned=$(sed '/<!--/,/-->/d' "$tmp")
title=$(printf '%s\n' "$cleaned" | awk 'NF{print; exit}' | sed 's/[[:space:]]*$//')
body=$(printf '%s\n' "$cleaned" | awk '/^---[[:space:]]*$/{flag=1; next} flag' | awk 'NF{p=1} p')

if [ -z "$title" ]; then
    echo "error: title is empty after edit" >&2
    exit 1
fi
if [ -z "$body" ]; then
    echo "error: body is empty after edit" >&2
    exit 1
fi

echo
echo "===== TITLE ====="
echo "$title"
echo
echo "===== BODY ====="
echo "$body"
echo "================="
echo

read -r -p "Publish $new_tag with these notes? [y/N] " confirm
case "$confirm" in
    [yY] | [yY][eE][sS]) ;;
    *)
        echo "aborted"
        exit 1
        ;;
esac

# --- Tag, push, release ------------------------------------------------------

notes_file=$(mktemp -t drape-notes-XXXXXX.md)
trap 'rm -f "$tmp" "$notes_file"' EXIT
printf '%s\n' "$body" >"$notes_file"

echo "==> Creating GitHub release $new_tag"
gh release create "$new_tag" \
    --target main \
    --title "$title" \
    --notes-file "$notes_file" \
    --verify-tag=false

echo "==> Done. Tag pushed; PyPI publish workflow should be running:"
echo "    https://github.com/pike00/drape/actions"
