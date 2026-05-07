"""drape: Mask secrets in .env / SOPS / YAML / JSON / TOML files for safe LLM inspection."""

__version__ = "0.2.0"
__author__ = "Will Pike"
__license__ = "MIT"

from .masker import mask_value, parse_env_file, shannon_entropy
from .patterns import classify_secret

__all__ = ["mask_value", "parse_env_file", "shannon_entropy", "classify_secret"]
