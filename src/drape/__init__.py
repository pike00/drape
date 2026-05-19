"""drape: Mask secrets in .env / SOPS / YAML / JSON / TOML files for safe LLM inspection."""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("drape")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__author__ = "Will Pike"
__license__ = "MIT"

from .masker import mask_value, parse_env_file, shannon_entropy
from .patterns import classify_secret

__all__ = ["mask_value", "parse_env_file", "shannon_entropy", "classify_secret"]
