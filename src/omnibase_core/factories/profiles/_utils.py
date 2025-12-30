"""
Shared utilities for contract profile factories.

This module contains internal utility functions used by the profile factory
modules. These functions are implementation details and should not be
imported directly by external code.

Thread Safety:
    All functions in this module are stateless and thread-safe.
"""

from omnibase_core.models.primitives.model_semver import ModelSemVer


def _parse_version(version: str) -> ModelSemVer:
    """
    Parse a version string into a ModelSemVer instance.

    Args:
        version: A version string in "major.minor.patch" format.
                 Missing components default to 0 (except major defaults to 1).

    Returns:
        A ModelSemVer instance with parsed major, minor, patch values.

    Example:
        >>> _parse_version("1.2.3")
        ModelSemVer(major=1, minor=2, patch=3)
        >>> _parse_version("2.0")
        ModelSemVer(major=2, minor=0, patch=0)
    """
    parts = version.split(".")
    return ModelSemVer(
        major=int(parts[0]) if len(parts) > 0 else 1,
        minor=int(parts[1]) if len(parts) > 1 else 0,
        patch=int(parts[2]) if len(parts) > 2 else 0,
    )
