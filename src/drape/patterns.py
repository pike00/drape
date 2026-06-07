"""Pattern-aware secret classification using detect-secrets plugins.

Given a candidate value, return a short type label (``<aws-access-key>``,
``<github-token>``, ``<slack-token>``, ...) if any built-in plugin recognizes
it. Otherwise return ``None`` and let the caller fall back to entropy + prefix
masking.

Identifying the type leaks strictly less than the prefix-reveal: the LLM
learns *what* kind of credential is at this key, but no characters of it.
"""

from __future__ import annotations

import logging  # noqa: F401  # used to silence third-party detect-secrets logger
from functools import lru_cache
from typing import Optional

from loguru import logger

# Map detect-secrets plugin classnames to short labels we render.
# Order matters: more-specific detectors run first so e.g. an AWS key is
# labeled `aws-access-key` rather than just `high-entropy-base64`.
_PLUGIN_LABELS: list[tuple[str, str]] = [
    ("AWSKeyDetector", "<aws-access-key>"),
    ("AzureStorageKeyDetector", "<azure-storage-key>"),
    ("GitHubTokenDetector", "<github-token>"),
    ("GitLabTokenDetector", "<gitlab-token>"),
    ("SlackDetector", "<slack-token>"),
    ("StripeDetector", "<stripe-key>"),
    ("SquareOAuthDetector", "<square-oauth-token>"),
    ("TwilioKeyDetector", "<twilio-key>"),
    ("DiscordBotTokenDetector", "<discord-bot-token>"),
    ("MailchimpDetector", "<mailchimp-key>"),
    ("SendGridDetector", "<sendgrid-key>"),
    ("NpmDetector", "<npm-token>"),
    ("JwtTokenDetector", "<jwt>"),
    ("PrivateKeyDetector", "<private-key>"),
    ("BasicAuthDetector", "<basic-auth>"),
    ("ArtifactoryDetector", "<artifactory-token>"),
    ("CloudantDetector", "<cloudant-credentials>"),
    ("IbmCloudIamDetector", "<ibm-cloud-iam-key>"),
    ("IbmCosHmacDetector", "<ibm-cos-hmac-key>"),
    ("MailgunDetector", "<mailgun-key>"),
    ("OpenAIDetector", "<openai-key>"),  # added in newer detect-secrets versions
    ("AnthropicKeyDetector", "<anthropic-key>"),  # ditto
]


@lru_cache(maxsize=1)
def _load_plugins() -> list[tuple[object, str]]:
    """Instantiate each known plugin once. Silently skip any that don't exist
    in the installed detect-secrets version.
    """
    try:
        from detect_secrets.core.plugins import initialize  # type: ignore[import-untyped]
    except ImportError:
        logger.debug("detect-secrets not installed; pattern classification disabled")
        return []

    # detect-secrets uses a "detect-secrets" logger that writes directly to
    # stderr and isn't fully muted by setLevel alone (it also prints unhandled
    # error tags via its own machinery). Silence both the logger and stderr
    # for the brief plugin-probe phase.
    import contextlib
    import io as _io

    ds_logger = logging.getLogger("detect-secrets")
    prev_level = ds_logger.level
    ds_logger.setLevel(logging.CRITICAL)
    try:
        with contextlib.redirect_stderr(_io.StringIO()):
            loaded: list[tuple[object, str]] = []
            for classname, label in _PLUGIN_LABELS:
                try:
                    plugin: object = initialize.from_plugin_classname(classname)
                except Exception:
                    continue
                loaded.append((plugin, label))
    finally:
        ds_logger.setLevel(prev_level)

    logger.debug("Loaded {} detect-secrets plugins", len(loaded))
    return loaded


def classify_secret(value: str) -> Optional[str]:
    """Return a ``<type>`` label if ``value`` matches a known credential pattern.

    Returns ``None`` if no plugin matches. Never raises — pattern classification
    is best-effort; a failure here just falls back to length+entropy masking.
    """
    if not value:
        return None

    plugins = _load_plugins()
    for plugin, label in plugins:
        # Prefer analyze_string when available (newer detect-secrets); fall
        # back to analyze_line for older versions. Either returns an iterable
        # of PotentialSecret on hit, empty/None on miss.
        try:
            analyzer = getattr(plugin, "analyze_string", None) or getattr(
                plugin, "analyze_line", None
            )
            if analyzer is None:
                continue
            secrets = list(analyzer(value, line_number=1, filename="drape"))
        except TypeError:
            try:
                secrets = list(analyzer(value))  # type: ignore[misc]
            except Exception:
                continue
        except Exception:
            continue
        if secrets:
            return label
    return None
