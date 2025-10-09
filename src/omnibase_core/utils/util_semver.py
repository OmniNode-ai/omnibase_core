"""
Semantic Version Utility Module.

Re-exports parse_semver_from_string from the core model_semver module.
"""

from omnibase_core.models.core.model_semver import parse_semver_from_string

__all__ = ["parse_semver_from_string"]
