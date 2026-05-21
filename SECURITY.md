# Security Policy

`drape` masks secrets in Claude Code hook output. A failure of that masking,
or a path by which `drape` itself leaks the values it is meant to hide, is a
security vulnerability. Please report it.

## Supported Versions

`drape` is pre-1.0 and ships from a single line of development. Only the
latest released version receives security fixes; there are no maintained
backport branches.

| Version        | Supported          |
| -------------- | ------------------ |
| Latest release | :white_check_mark: |
| Older releases | :x:                |

Always upgrade to the newest release on PyPI (`uv tool install --upgrade
drape` or `pip install --upgrade drape`) before reporting an issue, in case it
is already fixed.

## What Counts as a Vulnerability

In addition to the usual categories (arbitrary code execution, path traversal,
dependency CVEs), the following are treated as security issues specific to
`drape`:

- A secret value that should have been masked appearing unmasked in hook
  output, logs, or the audit trail.
- A pattern, file format, or input shape that causes the masker to fail open
  (pass the original content through) instead of failing closed.
- Secret values written verbatim to the audit log (the audit log must record
  metadata only — file, key count, timestamp — never values).
- A way to make `drape` exfiltrate or persist secret material outside the
  intended masking flow.

## Reporting a Vulnerability

Report privately through GitHub's vulnerability reporting:

**https://github.com/pike00/drape/security/advisories/new**

Do not open a public issue, pull request, or discussion for a suspected
vulnerability until a fix has been released.

Please include:

- The version of `drape` and how it was installed.
- A minimal reproduction — a sanitized input file or pattern that triggers the
  leak or bypass. **Do not include real secrets**; use obviously fake values.
- The expected masked output versus what `drape` actually produced.

## What to Expect

This is a solo-maintained project; timelines are best-effort, not contractual.

- **Acknowledgement** within 5 business days.
- **Initial assessment** (accepted / needs-info / declined, with reasoning)
  within 14 days.
- If accepted, a fix is released to PyPI and a GitHub Security Advisory is
  published crediting the reporter, unless they ask to remain anonymous.
- If declined, you will get an explanation of why it is considered out of
  scope, and you are free to disclose publicly after that.

Thank you for helping keep `drape` and the secrets it guards safe.
