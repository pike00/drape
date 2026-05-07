#!/usr/bin/env bash
# Cut a new release: bump version, draft notes via the homelab LiteLLM
# proxy (deepseek-v4-pro:cloud by default), review, tag, push, create
# GitHub release.
#
# Usage: scripts/release.sh {patch|minor|major}
#
# Env (all optional, sensible defaults):
#   LITELLM_URL          Proxy base URL (default http://127.0.0.1:4000)
#   LITELLM_MODEL        Model name (default deepseek-v4-pro-cloud)
#   LITELLM_MASTER_KEY   Bearer token. If unset, auto-decrypted from
#                        $HOMELAB_REPO/ai/litellm/.env.sops via 'just secrets'.
#   HOMELAB_REPO         Default ~/Documents/Homelab.
#
# Tag push triggers .github/workflows/release.yml which publishes to PyPI.
# pyproject.toml is NOT mutated locally; the release workflow rewrites the
# version from the tag at build time.

set -euo pipefail

LITELLM_URL="${LITELLM_URL:-http://127.0.0.1:4000}"
LITELLM_MODEL="${LITELLM_MODEL:-deepseek-v4-pro-cloud}"
HOMELAB_REPO="${HOMELAB_REPO:-$HOME/Documents/Homelab}"

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

for tool in gh jq curl; do
    command -v "$tool" >/dev/null || {
        echo "error: '$tool' not found on PATH" >&2
        exit 1
    }
done

# Bootstrap LITELLM_MASTER_KEY from homelab sops if not already exported.
if [ -z "${LITELLM_MASTER_KEY:-}" ]; then
    if [ -f "$HOMELAB_REPO/justfile" ] && [ -f "$HOMELAB_REPO/ai/litellm/.env.sops" ]; then
        echo "==> Decrypting LITELLM_MASTER_KEY from $HOMELAB_REPO/ai/litellm/.env.sops…"
        LITELLM_MASTER_KEY=$(
            cd "$HOMELAB_REPO" && just secrets sopsx ai/litellm/.env.sops -d 2>/dev/null \
                | awk -F= '/^LITELLM_MASTER_KEY=/{ sub(/^LITELLM_MASTER_KEY=/,""); print; exit }'
        )
        export LITELLM_MASTER_KEY
    fi
fi
if [ -z "${LITELLM_MASTER_KEY:-}" ]; then
    echo "error: LITELLM_MASTER_KEY not in env and could not bootstrap" >&2
    echo "  hint: export LITELLM_MASTER_KEY=... or set HOMELAB_REPO=<path>" >&2
    exit 1
fi

# --- Compute versions --------------------------------------------------------
# The git tag is the source of truth (workflow rewrites pyproject.toml from
# the tag at build time). Compute next version by bumping the latest tag,
# NOT by reading pyproject.toml.

last_tag=$(git describe --tags --abbrev=0 2>/dev/null || true)
if [ -n "$last_tag" ]; then
    current="${last_tag#v}"
    log_range="$last_tag..HEAD"
else
    current="0.0.0"
    log_range="HEAD"
fi

if ! [[ "$current" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "error: latest tag '$last_tag' is not semver-shaped (X.Y.Z)" >&2
    exit 1
fi

IFS=. read -r v_major v_minor v_patch <<<"$current"
case "$LEVEL" in
    patch) new="$v_major.$v_minor.$((v_patch + 1))" ;;
    minor) new="$v_major.$((v_minor + 1)).0" ;;
    major) new="$((v_major + 1)).0.0" ;;
esac
new_tag="v$new"

if git rev-parse "$new_tag" >/dev/null 2>&1; then
    echo "error: tag $new_tag already exists" >&2
    exit 1
fi

commits=$(git log --no-merges --pretty=format:'- %s%n%b' "$log_range")
if [ -z "$commits" ]; then
    echo "error: no commits since $last_tag — nothing to release" >&2
    exit 1
fi

echo "==> Bumping $current → $new ($LEVEL)"
echo "==> $(echo "$commits" | grep -c '^- ') commits since ${last_tag:-<root>}"

# --- Draft notes via LiteLLM proxy -------------------------------------------

system_prompt='You are an experienced open-source maintainer writing GitHub
release notes for the Python package "drape" — a CLI and Claude Code hook
that masks secrets in .env / SOPS / YAML / JSON / TOML files for safe LLM
inspection. Audience: developers and security-conscious users running drape
locally or in CI.

Voice: precise, factual, no marketing language, no emoji, no exclamation
points. Write as if reviewers from a security-minded shop will read it.

Title rules:
  - Format exactly: "vX.Y.Z — <what users notice>"
  - No more than 80 characters total
  - No trailing punctuation
  - Summarize the most important user-visible change, not the bump kind

Body rules (GitHub-flavored markdown):
  - Group bullets under "### Added", "### Changed", "### Fixed", "###
    Removed", "### Security", "### Deprecated". Include ONLY sections that
    apply.
  - Each bullet describes user-visible impact, not commit mechanics. If
    several commits implement one feature, collapse them into a single
    bullet. Skip mechanical commits (deps bumps, lockfile churn, internal
    refactors, CI tweaks) unless they materially affect users.
  - For breaking changes, prefix the bullet with **Breaking:** and include
    a brief migration note inline.
  - Reference user-visible function/CLI flag names in `code` formatting.
  - Do not invent features that are not supported by the commit log.
  - End the body with an "**Install**" heading followed by a single fenced
    bash block: `uv tool install drape=='"$new"'`.

Output: ONLY the JSON object. No preamble, no postscript, no fences around
the JSON.'

user_prompt=$(
    cat <<EOF
Draft release notes for drape $new ($LEVEL bump from $current).

Commits since ${last_tag:-<root commit>}:

$commits
EOF
)

request_body=$(jq -n \
    --arg model "$LITELLM_MODEL" \
    --arg system "$system_prompt" \
    --arg user "$user_prompt" \
    --arg version "$new" \
    '{
      model: $model,
      messages: [
        {role: "system", content: $system},
        {role: "user",   content: $user}
      ],
      max_tokens: 4096,
      temperature: 0.3,
      reasoning_effort: "low",
      response_format: {
        type: "json_schema",
        json_schema: {
          name: "release_notes",
          strict: true,
          schema: {
            type: "object",
            properties: {
              title: {type: "string"},
              body:  {type: "string"}
            },
            required: ["title", "body"],
            additionalProperties: false
          }
        }
      }
    }')

echo "==> Drafting notes via $LITELLM_MODEL → Ollama Cloud (LiteLLM proxy)…"
echo "    deepseek-v4-pro is a reasoning model; expect 30–60s of think time."

resp_file=$(mktemp -t drape-llm-resp-XXXXXX.json)
trap 'rm -f "${resp_file:-} ${tmp:-} ${notes_file:-}"' EXIT

curl -sS -X POST "$LITELLM_URL/v1/chat/completions" \
    -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
    -H "Content-Type: application/json" \
    --max-time 300 \
    -d "$request_body" \
    -o "$resp_file" &
curl_pid=$!

start=$SECONDS
while kill -0 "$curl_pid" 2>/dev/null; do
    sleep 5
    printf '\r    elapsed: %ds…  ' "$((SECONDS - start))" >&2
done
wait "$curl_pid"
curl_status=$?
printf '\r    completed in %ds       \n' "$((SECONDS - start))" >&2

if [ "$curl_status" -ne 0 ]; then
    echo "error: LiteLLM call failed (curl exit $curl_status)" >&2
    cat "$resp_file" >&2
    exit 1
fi

draft_response=$(cat "$resp_file")
content=$(printf '%s' "$draft_response" | jq -r '.choices[0].message.content // empty')
if [ -z "$content" ]; then
    echo "error: empty response from LiteLLM proxy" >&2
    printf '%s' "$draft_response" | jq '.' >&2 || printf '%s\n' "$draft_response" >&2
    exit 1
fi

title=$(printf '%s' "$content" | jq -r '.title // empty')
body=$(printf '%s' "$content" | jq -r '.body // empty')

if [ -z "$title" ] || [ -z "$body" ]; then
    echo "error: model output did not match schema" >&2
    printf '%s\n' "$content" >&2
    exit 1
fi

# --- Review ------------------------------------------------------------------

tmp=$(mktemp -t drape-release-XXXXXX.md)

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
printf '%s\n' "$body" >"$notes_file"

echo "==> Creating GitHub release $new_tag"
gh release create "$new_tag" \
    --target main \
    --title "$title" \
    --notes-file "$notes_file" \
    --verify-tag=false

echo "==> Done. Tag pushed; PyPI publish workflow should be running:"
echo "    https://github.com/pike00/drape/actions"
