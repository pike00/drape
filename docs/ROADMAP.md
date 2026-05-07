# drape Roadmap

This document outlines planned features and improvements for future versions of drape.

## Version 0.1.0 (Current)

**Released:** 2026-04-09

### Features
- Core masking utility (first 3 characters + ellipsis)
- Python CLI and API
- Claude Code integration via PreToolUse hook
- Support for `.env` and `*.env` file patterns
- Comprehensive test suite (14+ tests)
- Complete documentation and architecture guide

### Known Limitations
- Single-line values only (multiline JSON not supported)
- No quote handling (outputs raw)
- KEY=VALUE format only (no YAML/JSON)
- Fixed masking pattern (not customizable)

---

## Version 0.2.0 (Planned - Minor Release)

**Target:** Q3 2026

### Features

**File Format Support**
- [ ] Support for `.env.local`, `.env.production`, `.env.staging` variants
- [ ] Better handling of variant files in hook pattern matching
- [ ] Configuration file for custom file patterns

**Customization**
- [ ] Custom masking patterns via config file (e.g., `mask_chars: 5` or `mask_pattern: "***"`)
- [ ] Configurable file patterns (which files to mask)
- [ ] Hook configuration via environment variables

**Improved Logging**
- [ ] Debug mode with `--debug` flag
- [ ] Better error messages for common issues
- [ ] Optional audit logging (log masked operations)

**Testing & Quality**
- [ ] 100% type hint coverage
- [ ] GitHub Actions CI/CD pipeline
- [ ] Automated PyPI publishing on GitHub releases
- [ ] Code coverage reports

### Breaking Changes
None

---

## Version 0.3.0 (Planned - Minor Release)

**Target:** Q4 2026

### Features

**Extended Format Support**
- [ ] YAML configuration file masking (mask keys matching patterns)
- [ ] JSON file masking (mask specific keys like `"password"`, `"api_key"`, `"token"`)
- [ ] Toml file support (for Python projects)
- [ ] Docker Compose file support (mask environment variables)

**Hook Enhancements**
- [ ] Support for multiple hook configurations (different patterns for different files)
- [ ] Performance optimization (caching, lazy loading)
- [ ] Better error recovery

**Documentation**
- [ ] Video tutorial for Claude Code setup
- [ ] Integration guide for CI/CD pipelines
- [ ] Best practices guide for secret management

### Breaking Changes
None expected

---

## Version 1.0.0 (Planned - Major Release)

**Target:** 2027 Q1

### Features

**Secret Manager Integration**
- [ ] Integration with 1Password CLI
- [ ] Integration with HashiCorp Vault
- [ ] Integration with AWS Secrets Manager
- [ ] On-demand unmasking with credential prompt

**Plugin System**
- [ ] Claude Code plugin with auto-discovery
- [ ] Settings UI for configuration
- [ ] Plugin marketplace compatibility

**Audit & Compliance**
- [ ] Audit logging (log all masking operations)
- [ ] User identification in logs
- [ ] Compliance reports (SOC 2, etc.)

**Advanced Features**
- [ ] Batch unmasking with re-authentication (MFA/2FA)
- [ ] Differential masking (different patterns for different secret types)
- [ ] Secret strength validation
- [ ] Integration with Secret Scanner tools (detect accidental leaks)

### Stability Commitment
- Stable API (no breaking changes without major version bump)
- Long-term support for Python 3.9+
- Performance SLAs

### Breaking Changes
None expected during alpha/beta phases

---

## Future Considerations (1.1.0+)

### Ideas Under Discussion
- GitHub Actions integration (auto-masking in CI/CD)
- IDE extensions (VS Code, JetBrains)
- Kubernetes secret masking
- ORM integration (Django, SQLAlchemy)
- Testing library integration (pytest plugin)

### Research Areas
- Entropy-based masking (show less for high-entropy secrets)
- ML-based secret detection
- Supply chain security integration
- Compliance automation

---

## Release Schedule

| Version | Status | Target | Features |
|---------|--------|--------|----------|
| 0.1.0 | ✅ Released | 2026-04-09 | MVP + Claude integration |
| 0.2.0 | 📅 Planned | 2026-09 | File variants, customization, CI/CD |
| 0.3.0 | 📅 Planned | 2026-12 | Extended formats, plugin enhancements |
| 1.0.0 | 📅 Planned | 2027-03 | Secret managers, stable API, audit logging |

---

## How to Contribute

Have ideas for features? Please open an issue:
https://github.com/pike00/drape/issues

For security-related suggestions, email will@khanpikehome.com

---

## Version Numbering

drape follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for new features (backwards compatible)
- **PATCH** version for bug fixes

### Pre-Release Versions
- `0.x.y` = Alpha (experimental, API may change)
- `1.0.0+` = Stable (API frozen, long-term support)
