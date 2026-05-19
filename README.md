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

A real-shaped `.env` (slightly bigger than a hello-world):

```bash
$ cat .env
DATABASE_URL=postgres://app:Y4nKee_Doodle@db.prod.internal:5432/orders
REDIS_URL=redis://default:Sk1pper-Jack@cache.prod.internal:6379
AWS_ACCESS_KEY_ID=AKIAQRSTUVWXYZ234567
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
GITHUB_TOKEN=ghp_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8
OPENAI_API_KEY=sk-proj-aB3cD4eF5gH6iJ7kL8mN9oP0qR1sT2uV3wX4yZ5aB6cD7eF8gH9iJ0
SLACK_WEBHOOK=https://hooks.slack.com/services/T0123ABCD/B4567EFGH/abcdefghij1234567890
JWT_SIGNING_KEY=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.dozjgNryP4J3jVmNHl0w5N_XgL0JtMTPbqlSEqg7yfQ
SESSION_SECRET=k8jHs2pQrL5mN9wXcVbZyT3fG7hJ4dE6
COOKIE_SALT=correct horse battery staple
NODE_ENV=production
PORT=8080
LOG_LEVEL=info
AWS_REGION=us-east-1

$ drape .env
DATABASE_URL=<basic-auth>
REDIS_URL=<basic-auth>
AWS_ACCESS_KEY_ID=<aws-access-key>
AWS_SECRET_ACCESS_KEY=wJa...
GITHUB_TOKEN=<github-token>
OPENAI_API_KEY=sk-...
SLACK_WEBHOOK=<slack-token>
JWT_SIGNING_KEY=<jwt>
SESSION_SECRET=k8j...
COOKIE_SALT=cor...
NODE_ENV=pr...
PORT=<low-entropy-secret>
LOG_LEVEL=<low-entropy-secret>
AWS_REGION=<low-entropy-secret>
```

Three buckets of behavior, all visible above:

- **Pattern-matched → zero chars revealed.** `DATABASE_URL`, `REDIS_URL`, `AWS_ACCESS_KEY_ID`, `GITHUB_TOKEN`, `SLACK_WEBHOOK`, `JWT_SIGNING_KEY` — detect-secrets recognizes the shape, so the value collapses to a type label. (~21 detectors in total; full list further down.)
- **Pattern miss → prefix reveal.** `AWS_SECRET_ACCESS_KEY` (40-char base64, no fixed prefix), `OPENAI_API_KEY` (the newer `sk-proj-` form isn't in detect-secrets yet), `SESSION_SECRET`, `COOKIE_SALT`, `NODE_ENV` — none matched a pattern and entropy was high enough that the fallback ran. You get at most 3 chars + `...`, capped to 25 % of the value's length.
- **Low-entropy → `<low-entropy-secret>`.** `PORT=8080`, `LOG_LEVEL=info`, `AWS_REGION=us-east-1` — these aren't secrets. They're short, low-variety strings that fall below the entropy threshold, so drape masks them anyway. **Drape is deliberately conservative**: the LLM doesn't need the *value* of `PORT` to help you reason about config, only that the key is set. Over-masking is the right error to make.

Things to notice that the LLM still sees:

- Every key name. So the model can still answer "what services does this app talk to?"
- Whether a key is empty or set.
- The credential *type* for recognized shapes — enough to say "you have an AWS access key here" without ever seeing it.

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

2. **Entropy-aware reveal** — values whose Shannon entropy is below the threshold (default 3.0 bits/char) get the label `<low-entropy-secret>`. Catches short, low-variety passwords like `hunter2`, `password`, `letmein`, and `aaaaaaaa`. **Does not catch passphrases like `correct horse battery staple`** at the default threshold — that one has enough character diversity to land above 3.0 and falls through to prefix reveal. Bump `--entropy-threshold 3.5` if you want passphrases caught too; the tradeoff is more non-secrets get the `<low-entropy-secret>` label.

3. **Length-bounded prefix** — for high-entropy values that didn't match any pattern, reveal the first N characters (default 3), capped at 25 % of the value length, with a minimum of 1:

   ```
   POSTGRES_PASSWORD=wFw...
   ```

Surrounding quotes are stripped before any of this, so `KEY="abcd"` reveals chars from `abcd`, not `"abcd"`.

## Installation

drape is distributed as a [uv](https://docs.astral.sh/uv/) tool — install once, run from anywhere:

```bash
uv tool install drape                 # core (.env + .env.sops)
uv tool install 'drape[yaml]'         # + YAML support
uv tool install 'drape[toml]'         # + TOML on Python <3.11
uv tool install 'drape[all]'          # everything
```

To run without installing:

```bash
uvx drape .env
uvx --from 'drape[all]' drape --format yaml config/secrets.yaml
```

Or from source:

```bash
git clone https://github.com/pike00/drape.git
cd drape
uv tool install .
```

Requires Python 3.9+ (uv manages this automatically). SOPS support requires the [`sops`](https://github.com/getsops/sops) binary on `$PATH`.

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
uv tool install drape
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

For YAML / JSON / TOML, drape walks the document and masks any leaf value whose **leaf key** contains a secret-looking substring (case-insensitive):

```
password    passwd        secret       token       api_key      apikey
auth        credential    private_key  access_key  client_secret
session     cookie        salt         signature
```

Output is always rendered as flat `dotted.path=masked` lines so the LLM sees one consistent shape across all formats:

```bash
$ drape --format yaml secrets.yaml
service.name=orders-api
service.port=8080
database.host=db.prod.internal
database.user=app_user
database.password=Y4n...                        # ← key contains "password" → masked, but
                                                #   prefix path is taken because the value
                                                #   itself didn't match a pattern
auth.jwt_signing_key=eyJhbGciOiJIUzI1NiJ9...    # ← LEAKS: "jwt_signing_key" doesn't
                                                #   contain any of the keywords above
auth.session_secret=k8j...
aws.access_key_id=<aws-access-key>              # ← key matches AND value matches pattern
aws.secret_access_key=wJa...                    # ← key matches; value falls through to prefix
integrations.github_token=<github-token>
integrations.stripe_api_key=<stripe-key>
features[0]=newCheckout
features[1]=asyncEmail
```

The walker checks only the **last segment** of the path, not parent segments. `auth.jwt_signing_key` leaks because `jwt_signing_key` itself doesn't match `password|secret|token|key`-with-a-suffix. Workarounds:

- Rename the key to something the walker catches: `auth.jwt_signing_token` would be masked.
- Use the CLI's `--format env` mode, which runs full pattern + entropy detection on every value and would have caught the JWT shape regardless of key name.
- Add to the keyword list — open an issue if you have a common case that's slipping through.

## Release

```bash
just release patch          # patch | minor | major
```

This runs [release-kit](https://github.com/pike00/release-kit) `cut`, which:
1. Preflights (clean tree on `main`, in sync with `origin`).
2. Updates `CHANGELOG.md` via `git-cliff` (mechanical, commits → grouped sections per `cliff.toml`).
3. Drafts the GitHub release body via LiteLLM (`deepseek-v4-pro-cloud`) and opens it in `$EDITOR`.
4. Commits `CHANGELOG.md`, tags the commit, pushes, and runs `gh release create`.

Pushing the `v*.*.*` tag triggers `.github/workflows/release.yml`, which is the only GitHub Actions workflow drape keeps: it builds the sdist + wheel and publishes to PyPI via OIDC trusted publishing (no API token in source). The PyPI page typically updates within a minute.

Preview what will land without releasing:

```bash
just changelog-preview      # what git-cliff will write into CHANGELOG.md
just notes-dry-run          # what the LLM will draft for the GH release body
```

`CHANGELOG.md` is generated; do not hand-edit it. To regenerate from full history (e.g. after editing `cliff.toml`), run `just changelog-backfill`.

## Development

```bash
git clone https://github.com/pike00/drape.git
cd drape
uv sync --group dev          # install dev deps
uv run pytest                # 64 tests, ~1s
uv run pytest --cov          # with coverage report (target: ≥84%)
uv run ruff check src tests
uv run black --check src tests
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
