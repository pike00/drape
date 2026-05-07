# drape

[![PyPI](https://img.shields.io/pypi/v/drape.svg)](https://pypi.org/project/drape/)
[![Python](https://img.shields.io/pypi/pyversions/drape.svg)](https://pypi.org/project/drape/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-64%20passing-brightgreen.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-84%25-brightgreen.svg)](tests/)

**Hide secrets from LLMs when reading config files.**

drape is a defense-in-depth tool for Claude Code and other AI agents. It masks credentials in `.env`, SOPS-encrypted `.env.sops`, and structured (YAML / JSON / TOML) config files so they never appear in LLM conversations, prompt-cache snapshots, or provider logs.

> Your real `.env` is never modified. Plaintext is never written to disk. The masking happens in-process on your machine before the agent sees anything.

## Quick demo

```bash
$ cat .env
DATABASE_URL=postgres://user:hunter2@localhost/db
AWS_ACCESS_KEY_ID=AKIA<example-redacted-for-readme>
GITHUB_TOKEN=ghp_<example-redacted-for-readme>
APP_PASSWORD=correct-horse-battery-staple
JWT=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.<example>
RANDOM_HEX=a8f3c9e7b2d1f4a6c8e0b9d7f2a1c4e6

$ drape .env
DATABASE_URL=<basic-auth>
AWS_ACCESS_KEY_ID=<aws-access-key>
GITHUB_TOKEN=<github-token>
APP_PASSWORD=cor...
JWT=<jwt>
RANDOM_HEX=a8f...
```

Recognized credentials are reduced to a type label. Unknown values reveal at most three characters (capped to 25 % of the value's length).

## How it masks

Three strategies, applied in order — the most-protective hit wins:

1. **Pattern recognition** — known credential shapes are replaced with a type label, e.g. `<aws-access-key>`, `<github-token>`. The LLM learns *what kind* of credential is at this key, but zero characters of it. Powered by [`detect-secrets`](https://github.com/Yelp/detect-secrets); ~21 detectors enabled by default:

   | Detector | Label |
   |---|---|
   | AWS access keys | `<aws-access-key>` |
   | Azure storage keys | `<azure-storage-key>` |
   | GitHub / GitLab tokens | `<github-token>` / `<gitlab-token>` |
   | Slack tokens | `<slack-token>` |
   | Stripe keys | `<stripe-key>` |
   | Square OAuth tokens | `<square-oauth-token>` |
   | Twilio keys | `<twilio-key>` |
   | Discord bot tokens | `<discord-bot-token>` |
   | Mailchimp / Mailgun / SendGrid | `<mailchimp-key>` / `<mailgun-key>` / `<sendgrid-key>` |
   | npm tokens | `<npm-token>` |
   | JWTs | `<jwt>` |
   | Private keys (RSA / EC / OpenSSH / PGP) | `<private-key>` |
   | Basic-auth URIs | `<basic-auth>` |
   | Artifactory tokens | `<artifactory-token>` |
   | IBM Cloud (IAM, COS, Cloudant) | `<ibm-cloud-iam-key>` etc. |
   | OpenAI / Anthropic keys | `<openai-key>` / `<anthropic-key>` |

2. **Entropy-aware reveal** — values whose Shannon entropy is below the threshold (default 3.0 bits/char) get the label `<low-entropy-secret>`. Catches passwords like `hunter2` or `correct horse battery staple` whose 3-char prefix would otherwise leak meaningful information.

3. **Length-bounded prefix** — for high-entropy values that didn't match any pattern, reveal the first N characters (default 3), capped at 25 % of the value length, with a minimum of 1:

   ```
   POSTGRES_PASSWORD=wFw...
   ```

Surrounding quotes are stripped before any of this, so `KEY="abcd"` reveals chars from `abcd`, not `"abcd"`.

## Installation

```bash
pip install drape                 # core (.env + .env.sops)
pip install 'drape[yaml]'         # + YAML support
pip install 'drape[toml]'         # + TOML on Python <3.11
pip install 'drape[all]'          # everything
```

Or from source:

```bash
git clone https://github.com/pike00/drape.git
cd drape
pip install .
```

Requires Python 3.9+. SOPS support requires the [`sops`](https://github.com/getsops/sops) binary on `$PATH`.

## Usage

### Command line

```bash
drape .env                                # plain .env
drape config/.env.production              # variants ok
drape infra/secrets.env.sops              # SOPS-encrypted (decrypts in-process)
drape --format yaml config/secrets.yaml   # YAML key-pattern masking
drape --format json config/secrets.json   # JSON
drape --format toml pyproject.toml        # TOML
drape --prefix-chars 5 .env               # reveal up to 5 chars (still 25%-capped)
drape --no-patterns .env                  # disable type-label detection
drape --entropy-threshold 0 .env          # restore "reveal everything" behavior
```

Format auto-detects from filename for `.env`, `.env.sops`, `.yaml`, `.yml`, `.json`, `.toml`. Override with `--format` when needed.

### Claude Code integration (primary use case)

drape ships a [PreToolUse hook](https://docs.claude.com/en/docs/agents-and-tools/claude-code/hooks) that intercepts file reads before they reach the model. Install once per project:

```bash
pip install drape
bash scripts/install-claude-hook.sh --project-dir /path/to/project
```

The installer adds the right entries to `.claude/settings.json` automatically. After restarting Claude:

```
Claude asks:  What's in .env?
Claude sees:  POSTGRES_PASSWORD=wFw...
              AWS_KEY=<aws-access-key>
              GITHUB_PAT=<github-token>
```

The hook covers three tools, not just `Read`:

- **`Read`** on a secrets file — replaced with the masked rendering
- **`Grep`** on a secrets file — re-greps against the masked rendering, so matches on a key still surface but the value stays hidden
- **`Bash`** commands that try to read a secrets file directly (`cat .env`, `head .env.sops`, `grep PASSWORD .env`, `rg KEY .env.sops`, `awk -F= '...' .env`, …) — the hook returns a denial that redirects the agent to `drape`

For step-by-step setup: [docs/SETUP.md](docs/SETUP.md). For publishing notes: [docs/PUBLISHING.md](docs/PUBLISHING.md).

### Python API

```python
from pathlib import Path
from drape import parse_env_file, mask_value, classify_secret

# Mask a whole file
for line in parse_env_file(Path(".env"), prefix_chars=4):
    print(line)

# Mask a single value
mask_value("AKIAIOSFODNN7EXAMPLE")          # -> "<aws-access-key>"
mask_value("hunter2")                        # -> "<low-entropy-secret>"
mask_value("R8aFq9wKjL2pXmZbT3vH")          # -> "R8a..."

# Just classify (no masking)
classify_secret("ghp_1234567890abcdef...")  # -> "<github-token>"
classify_secret("just a string")             # -> None
```

## Security threat model

**What drape protects against**
- Secrets appearing in LLM conversation transcripts
- Provider logging / prompt-cache snapshots of full secrets
- Accidental copy-paste of credentials into chat
- Third-party access to session history (e.g., shared/exported transcripts)

**What drape does *not* protect against**
- Compromised local machine — if an attacker can read your `.env` directly, drape doesn't help
- Compromised LLM account — anyone with your account can request unmasked files
- File permissions — drape reads whatever your shell can read
- Multiline secrets in `.env` — only single-line `KEY=VALUE` parses correctly (use a structured format for multiline values)

**Threat scenario prevented**
- Attacker gains read-only access to Claude conversation transcripts
- Masked content shows: `AWS_KEY=<aws-access-key>` (zero chars revealed) or `RANDOM=a8f...` (3 chars, ~10^15 brute-force space for a 22-char value)
- Even with full pattern knowledge, the type label is not enough to authenticate

See [docs/architecture.md](docs/architecture.md) for the detailed threat model and design rationale, and [docs/ROADMAP.md](docs/ROADMAP.md) for planned features.

## Configuration

All knobs are settable via CLI flags and/or environment variables. The hook reads only the env vars (CLI flags don't apply when Claude invokes drape).

| Setting | CLI flag | Env var | Default |
|---|---|---|---|
| Max prefix chars revealed | `--prefix-chars N` | `DRAPE_PREFIX_CHARS` | 3 |
| Entropy threshold (bits/char) | `--entropy-threshold F` | `DRAPE_ENTROPY_THRESHOLD` | 3.0 |
| Disable pattern type-labels | `--no-patterns` | (n/a) | enabled |
| Format override | `--format <fmt>` | (n/a) | auto |
| Extra hook glob patterns | (n/a) | `DRAPE_HOOK_PATTERNS` | unset |
| Audit log path (JSONL) | (n/a) | `DRAPE_AUDIT_LOG` | unset |
| Log level | (n/a) | `DRAPE_LOG_LEVEL` | INFO |

### Cap behavior

The 25 % cap is unconditional: asking for 8 chars on a 12-char secret reveals only 3 (`12 // 4 = 3`); asking for 5 on a 4-char secret reveals only 1. Order of precedence:

```
empty                  → ""
matches a pattern      → <credential-type>
entropy < threshold    → <low-entropy-secret>
otherwise              → first min(prefix, len // 4, ≥1) chars + "..."
```

### Audit log

Set `DRAPE_AUDIT_LOG=/path/to/audit.jsonl` to record every masking operation. Each line is a JSON object with `ts`, `event`, `file`, `format`, `key_count`, and `prefix_chars`. **Values are never logged** — only the fact that a file was masked, what shape it was, and how many keys it contained.

```bash
$ DRAPE_AUDIT_LOG=~/.drape-audit.jsonl drape .env > /dev/null
$ tail -1 ~/.drape-audit.jsonl
{"ts":"2026-05-06T19:30:00+00:00","event":"cli_mask","file":".env","format":"env","key_count":12,"prefix_chars":3}
```

The audit writer never raises — if the log path is unwritable, masking still succeeds.

### File patterns

The hook intercepts these file shapes by default:

- `.env`, `*.env` (e.g., `production.env`, `app.env`)
- `.env.sops`, `*.env.sops` — decrypted via the `sops` binary in-process, then masked

It explicitly skips:

- `.env.example`, `.env.sample`, `.env.template`
- `.env.json`, `.env.yaml`, `.env.yml`, `.env.toml` (use `--format` on the CLI for these)

Add extra glob patterns via `DRAPE_HOOK_PATTERNS=*.secrets.yaml,credentials.json`.

### Structured-format key matching

For YAML / JSON / TOML, drape walks the document and masks any leaf value whose key contains a secret-looking substring (case-insensitive):

```
password    passwd        secret       token       api_key      apikey
auth        credential    private_key  access_key  client_secret
session     cookie        salt         signature
```

Output is always rendered as flat `dotted.path=masked` lines so the LLM sees one consistent shape across all formats.

## Development

```bash
git clone https://github.com/pike00/drape.git
cd drape
uv sync --group dev          # install dev deps
.venv/bin/pytest             # 64 tests, ~1s
.venv/bin/pytest --cov       # with coverage report (target: ≥84%)
.venv/bin/ruff check src tests
.venv/bin/black --check src tests
```

The test suite covers: masker logic, all detect-secrets pattern integrations, entropy thresholds, structured-format walkers, SOPS dispatch (with the `sops` binary stubbed), the Claude hook (Read / Grep / Bash variants), audit log emission, and CLI argument parsing.

## Limitations

- **Single-line `.env` values** — multiline values aren't parsed; use YAML / JSON / TOML for those
- **Structured formats use key-name heuristics** — a key not matching the secret-keyword list is rendered in the clear, even if its value looks like a credential. (The CLI's `--format env` mode still runs full pattern + entropy detection on every value.)
- **No on-demand unmasking** — once masked, the model can't ask for the real value (planned for a future release with re-authentication)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE).

## Contact

For security issues, email **will@khanpikehome.com** instead of opening a public issue.

## Related work

- [direnv](https://direnv.net/) — load `.env` files in your shell
- [python-dotenv](https://github.com/theskumar/python-dotenv) — load `.env` in Python apps
- [SOPS](https://github.com/getsops/sops) — encrypt `.env` and YAML / JSON files at rest
- [detect-secrets](https://github.com/Yelp/detect-secrets) — the credential-detection engine drape uses for pattern matching
- [git-secrets](https://github.com/awslabs/git-secrets) — pre-commit-hook approach to keeping secrets out of repos
