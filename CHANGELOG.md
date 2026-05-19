# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.2] - 2026-05-19

### Added
- Feat: add ship recipe (release triggers PyPI publish via GHA OIDC) (868481b)

### Documentation
- Docs(README): release section explaining cliff + release-kit cut flow (84d90df)

### Fixed
- Fix: resolve __version__ from package metadata, not hardcoded string (22ade22)

### Other
- Just: standardize header to canonical Tier 2 block (a4dccee)
- Release-kit: wire pypi prod resolver for published drape package (0f23ae8)
- Release-kit: symlink cliff.toml + release.just to shared template (672748f)
- Release: adopt git-cliff CHANGELOG + shared release.just (5cbca6b)
- Release: migrate to release-kit (74ce5a7)
- Projects: housekeeping roadmap-followup (6114108)

## [Unreleased]

### Other
- Release: migrate to release-kit (74ce5a7)
- Projects: housekeeping roadmap-followup (6114108)
- Release: editor fallback chain ($VISUAL → $EDITOR → nano → vim → vi) (8f5ca14)
- Release: bump from latest tag (not pyproject.toml) + LLM progress meter (5d1c460)
- Release: route notes drafting through homelab LiteLLM proxy (7216b19)
- Release: fix Claude auth + sync tags both ways (3c49fba)
- Release: add 'just release {patch|minor|major}' with Claude-drafted notes (6a7b503)

## [0.3.0] - 2026-05-07

### Other
- Release: derive version from git tag, not pyproject.toml (22ba74a)
- Deps: bump min Python to 3.12 to clear Dependabot alerts (4948d2b)
- Release: use pypi-public@wpike.com for project contact email (cd0b842)
- Release: switch to PyPI trusted publishing via OIDC (a30ef3d)

## [0.2.0] - 2026-05-07

### Changed
- Refactor: type config surface with pydantic + pydantic-settings (4633572)
- Refactor: rename package from envguard to envmask (586e0ca)

### Documentation
- Docs: switch install/dev/publish surfaces to uv exclusively (af7a407)

### Other
- Cleanup: remove unused MANIFEST.in and setup.py files (58ab874)
- Release: v0.2.0 with envmask → drape rename (fd17490)
- Projects: scaffold roadmap-followup tracking (3bc206b)
- Gitignore: exclude local SOPS and direnv config (61f41de)
- Initial commit: envguard environment variable masking tool (23b40d2)


