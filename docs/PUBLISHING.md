# Publishing drape

drape is published to [PyPI](https://pypi.org/project/drape/) via GitHub
Actions using **trusted publishing (OIDC)**. There is no long-lived PyPI token
in the repo or in any environment variable — every release exchanges a
short-lived OIDC identity for a one-shot upload token.

## Architecture

```
git push tag v0.x.y
        │
        ▼
.github/workflows/release.yml
   ├── build:   uv build  →  twine check  →  upload artifact
   └── publish: download artifact → pypa/gh-action-pypi-publish
                (job runs in `pypi` environment, requires reviewer approval)
```

Two boundaries protect a release:

1. **PyPI trusted publisher** restricts uploads to the exact
   `pike00/drape` repo + `release.yml` workflow + `pypi` environment.
2. **GitHub `pypi` environment** requires a manual approval click and only
   runs against tags matching `v*.*.*`.

## One-time setup (already done)

These are recorded for posterity / disaster recovery — re-run only if the
publisher or environment is deleted.

### 1. Register the trusted publisher on PyPI

https://pypi.org/manage/project/drape/settings/publishing/ → **Add a new
publisher** → GitHub:

| Field              | Value                          |
| ------------------ | ------------------------------ |
| Owner              | `pike00`                       |
| Repository         | `drape`                        |
| Workflow filename  | `release.yml`                  |
| Environment name   | `pypi`                         |

### 2. Configure the GitHub `pypi` environment

Done via `gh api`; equivalent to repo Settings → Environments → `pypi`:

- Required reviewer: `pike00`
- Deployment branch policy: tags matching `v*.*.*` only

```bash
gh api -X PUT repos/pike00/drape/environments/pypi --input - <<'EOF'
{
  "wait_timer": 0,
  "prevent_self_review": false,
  "reviewers": [{"type": "User", "id": 6687499}],
  "deployment_branch_policy": {
    "protected_branches": false,
    "custom_branch_policies": true
  }
}
EOF

gh api -X POST repos/pike00/drape/environments/pypi/deployment-branch-policies \
  -f name='v*.*.*' -f type='tag'
```

## Cutting a release

1. Bump `version` in `pyproject.toml`.
2. Update `CHANGELOG.md` with the new version's notes.
3. Commit:

   ```bash
   git commit -am "release: vX.Y.Z"
   git push
   ```

4. Tag and push:

   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```

5. The tag push triggers `.github/workflows/release.yml`. The workflow:
   - Verifies the tag matches `pyproject.toml`'s version.
   - Builds `sdist` + `wheel` with `uv build`.
   - Runs `twine check` against the artifacts.
   - Pauses on the `pypi` environment for your approval.
   - Approve the deployment in the GitHub UI (Actions tab → run → "Review
     deployments") to publish.

6. Draft GitHub release notes (optional but recommended):

   ```bash
   gh release create vX.Y.Z --notes-from-tag
   ```

## Verifying a release

```bash
uv tool install drape
drape --version
```

PyPI usually serves new versions within ~30 seconds; the project page caches
for a few minutes:

- Project: https://pypi.org/project/drape/
- Versions: https://pypi.org/project/drape/#history

## Disaster recovery

If trusted publishing is broken (PyPI publisher deleted, repo renamed, etc.)
and you need to push a release manually:

```bash
uv build
UV_PUBLISH_TOKEN='pypi-...' uv publish
```

Generate a temporary token at https://pypi.org/manage/account/token/ scoped
to the `drape` project, **revoke it immediately** after the release, and
re-establish trusted publishing per "One-time setup" above. Long-lived
tokens are not the supported path.

## History

- **v0.1.0 / v0.2.0** — published manually with a project-scoped PyPI API
  token (now revoked). Tag `v0.2.0` predates this workflow.
- **v0.3.0+** — published via OIDC trusted publishing as described here.
