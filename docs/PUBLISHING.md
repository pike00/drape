# Publishing drape to GitHub and PyPI

This document outlines the steps to publish drape.

## Prerequisites

- GitHub account with a new empty repository
- PyPI account (https://pypi.org/account/register/)
- GitHub personal access token with repo + write:packages permissions
- [uv](https://docs.astral.sh/uv/) installed (used for both build and publish)

## Step 1: Initialize Git Repository

```bash
cd drape
git init
git config user.name "Your Name"
git config user.email "your.email@example.com"
git add .
git commit -m "Initial commit: drape v0.1.0"
git branch -M main
```

## Step 2: Add GitHub Remote

```bash
git remote add origin https://github.com/pike00/drape.git
git push -u origin main
```

## Step 3: Create GitHub Release

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

Then on GitHub:
1. Go to https://github.com/pike00/drape/releases
2. Click "Draft a new release"
3. Select tag `v0.1.0`
4. Add release notes from [CHANGELOG.md](../CHANGELOG.md)
5. Check "Set as the latest release"
6. Publish

## Step 4: Publish to PyPI

### Option A: Manual Upload (with uv)

```bash
uv build                          # Creates dist/drape-X.Y.Z-py3-none-any.whl and dist/drape-X.Y.Z.tar.gz
UV_PUBLISH_TOKEN=<pypi-token> uv publish
# or: uv publish --token <pypi-token>
```

### Option B: Automated (GitHub Actions)

Add this to `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv build
      - run: uv publish --token ${{ secrets.PYPI_API_TOKEN }}
```

Then:
1. Create PyPI API token at https://pypi.org/account/manage/
2. Add to GitHub repo settings: Settings → Secrets and variables → Actions
3. New secret: `PYPI_API_TOKEN` = your PyPI token
4. Release a new version on GitHub (triggers workflow)

## Step 5: Verify Installation

After publishing to PyPI:

```bash
uv tool install drape
drape --version
```

## Future Updates

To release a new version (e.g., v0.2.0):

1. Update `version` in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Commit: `git commit -am "Release v0.2.0"`
4. Tag: `git tag -a v0.2.0 -m "Release v0.2.0"`
5. Push: `git push origin main && git push origin v0.2.0`
6. Create release on GitHub (auto-publishes to PyPI if workflow is set up)

## Notes

- First release to PyPI may take 5-10 minutes to appear
- Subsequent releases cache for ~5 minutes
- You can view package stats at https://pypi.org/project/drape/
- Yank old versions if needed: https://pypi.org/project/drape/#history
