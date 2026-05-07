# Pre-Release Checklist

Use this checklist before publishing to PyPI and GitHub.

## Code Quality

- [ ] Run full test suite: `uv run pytest tests/ -v`
- [ ] Check code style: `uv run ruff check src/ tests/`
- [ ] Format code: `uv run black --check src/ tests/`
- [ ] Type check: `uv run mypy src/` (optional, for additional safety)
- [ ] All tests pass with no errors

## Build & Distribution

- [ ] Update version in `pyproject.toml` and `src/drape/__init__.py`
- [ ] Refresh lockfile: `uv lock`
- [ ] Update `CHANGELOG.md` with release notes
- [ ] Commit changes: `git add -A && git commit -m "Release vX.Y.Z"`
- [ ] Build distribution: `uv build`
- [ ] Verify wheel: `unzip -l dist/drape-*.whl | grep -E '(masker|cli|hook)'`
- [ ] Verify source: `tar tzf dist/drape-*.tar.gz | grep -E '(masker|cli|hook)'`

## Installation Testing

- [ ] Install from wheel into an isolated tool env: `uv tool install --force --from dist/drape-*.whl drape`
- [ ] Test CLI: `drape --version` (should show correct version)
- [ ] Test CLI help: `drape --help`
- [ ] Test module: `uv tool run --from drape python -c "from drape import mask_value; print(mask_value('test'))"` (should print `tes...`)
- [ ] Test hook: `echo '{"tool_input":{"file_path":".env"}}' | drape-hook` (should output JSON)

## GitHub Release

- [ ] Tag version: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
- [ ] Push tag: `git push origin vX.Y.Z`
- [ ] Go to GitHub Releases page
- [ ] Create release from tag `vX.Y.Z`
- [ ] Add release notes from `CHANGELOG.md`
- [ ] Upload wheel and source distributions (or let GitHub Actions handle it)
- [ ] Mark as "Latest release"

## PyPI Publishing

### Option A: Automated (Recommended)
- [ ] Ensure GitHub Actions workflow is set up (`.github/workflows/publish.yml`)
- [ ] Push tag to trigger workflow
- [ ] Verify workflow succeeded
- [ ] Check PyPI: https://pypi.org/project/drape/

### Option B: Manual
- [ ] Upload with uv: `uv publish` (set `UV_PUBLISH_TOKEN=<pypi-token>` or use `--token`)
- [ ] Check PyPI: https://pypi.org/project/drape/

## Post-Release Verification

- [ ] Install from PyPI: `uv tool install drape==X.Y.Z`
- [ ] Verify CLI works: `drape --version`
- [ ] Verify hook works: `echo '{"tool_input":{"file_path":".env"}}' | drape-hook`
- [ ] Check package stats: https://pypi.org/project/drape/#history

## Documentation

- [ ] README is up-to-date
- [ ] CHANGELOG is complete
- [ ] Architecture docs are accurate
- [ ] Installation instructions match current version
- [ ] Contributing guide references correct Python version (3.9+)

## Sign-Off

- [ ] All checks passed
- [ ] No critical warnings or errors
- [ ] Release notes are clear and complete
- [ ] Ready to announce on GitHub/social media

**Released by:** _______________  
**Release date:** _______________  
**Version:** _______________  
