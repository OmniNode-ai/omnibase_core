"""Exclusion utilities for cross-repo validation rules.

Provides shared logic for determining whether files should be excluded
from validation based on glob patterns and relative path matching.

Related ticket: OMN-1906
"""

from __future__ import annotations

import fnmatch
from pathlib import Path


def should_exclude_path(
    file_path: Path,
    root_directory: Path | None,
    exclude_patterns: list[str],
) -> bool:
    """Check if a file should be excluded from validation.

    Handles relative path calculation and pattern matching against
    both the file path and its parent directories.

    Args:
        file_path: Absolute or relative path to check.
        root_directory: Root directory for relative path calculation.
            If provided, the file path will be made relative to this.
        exclude_patterns: Glob patterns for paths to exclude.
            Supports patterns like "tests/**", "examples/**", etc.
            Parent directories are also checked against patterns
            with trailing "/**" removed.

    Returns:
        True if the file should be excluded, False otherwise.

    Example:
        >>> should_exclude_path(
        ...     file_path=Path("/repo/tests/unit/test_foo.py"),
        ...     root_directory=Path("/repo"),
        ...     exclude_patterns=["tests/**"],
        ... )
        True

        >>> should_exclude_path(
        ...     file_path=Path("/repo/src/module.py"),
        ...     root_directory=Path("/repo"),
        ...     exclude_patterns=["tests/**"],
        ... )
        False
    """
    # Get relative path for pattern matching
    if root_directory:
        try:
            relative_path = file_path.relative_to(root_directory)
        except ValueError:
            # File is not under root_directory, use as-is
            relative_path = file_path
    else:
        relative_path = file_path

    # Normalize to POSIX format for consistent pattern matching across platforms
    path_str = str(relative_path).replace("\\", "/")

    for pattern in exclude_patterns:
        # Direct pattern match
        if fnmatch.fnmatch(path_str, pattern):
            return True

        # Also check if any parent directory matches
        # This handles patterns like "tests/**" matching "tests/unit/test_foo.py"
        for parent in relative_path.parents:
            parent_str = str(parent).replace("\\", "/")
            if fnmatch.fnmatch(parent_str, pattern.removesuffix("/**")):
                return True

    return False


def should_exclude_path_with_modules(
    file_path: Path,
    root_directory: Path | None,
    exclude_patterns: list[str],
    allowlist_modules: list[str],
) -> bool:
    """Check if a file should be excluded, including module allowlist.

    Extends should_exclude_path with additional module-based exclusions.
    Used by rules that have both pattern-based and module-based exclusions.

    Args:
        file_path: Absolute or relative path to check.
        root_directory: Root directory for relative path calculation.
        exclude_patterns: Glob patterns for paths to exclude.
        allowlist_modules: Module prefixes where certain patterns are permitted.
            Uses segment-based matching to avoid false positives (e.g., "cli"
            won't match "public_client.py").

    Returns:
        True if the file should be excluded, False otherwise.

    Example:
        >>> should_exclude_path_with_modules(
        ...     file_path=Path("/repo/src/omnibase_core/bootstrap/init.py"),
        ...     root_directory=Path("/repo"),
        ...     exclude_patterns=["tests/**"],
        ...     allowlist_modules=["omnibase_core.bootstrap"],
        ... )
        True
    """
    # First check standard exclusion patterns
    if should_exclude_path(file_path, root_directory, exclude_patterns):
        return True

    # Get the path string for module matching
    if root_directory:
        try:
            relative_path = file_path.relative_to(root_directory)
        except ValueError:
            relative_path = file_path
    else:
        relative_path = file_path

    # Normalize to POSIX format for consistent pattern matching across platforms
    path_str = str(relative_path).replace("\\", "/")

    # Check allowlist modules using segment matching to avoid false positives.
    # Substring matching would cause "cli" to match "public_client.py".
    for allowlist_module in allowlist_modules:
        module_path = allowlist_module.replace(".", "/")
        module_segments = module_path.split("/")
        path_segments = path_str.split("/")
        # Check if module segments appear as contiguous segments anywhere in the path
        for i in range(len(path_segments) - len(module_segments) + 1):
            if path_segments[i : i + len(module_segments)] == module_segments:
                return True

    return False


__all__ = [
    "should_exclude_path",
    "should_exclude_path_with_modules",
]
