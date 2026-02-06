"""Exclusion utilities for cross-repo validation rules.

Provides shared logic for determining whether files should be excluded
from validation based on glob patterns and relative path matching.

Related ticket: OMN-1906
"""

from __future__ import annotations

import fnmatch
from pathlib import Path


def _normalize_to_posix(path: Path) -> str:
    """Normalize a path to POSIX format for cross-platform pattern matching.

    Converts Windows-style backslashes to forward slashes to ensure
    consistent behavior across platforms.

    Args:
        path: Path to normalize.

    Returns:
        POSIX-style path string with forward slashes.
    """
    return str(path).replace("\\", "/")


def get_relative_path_safe(file_path: Path, root_directory: Path | None) -> Path:
    """Calculate relative path from root directory.

    Args:
        file_path: Absolute or relative path to process.
        root_directory: Root directory for relative path calculation.
            If None or if file_path is not under root_directory,
            returns file_path unchanged.

    Returns:
        Relative path if file is under root_directory, otherwise file_path as-is.
    """
    if root_directory is None:
        return file_path

    try:
        return file_path.relative_to(root_directory)
    except ValueError:
        # File is not under root_directory, use as-is
        return file_path


def _matches_exclusion_patterns(
    path_str: str,
    relative_path: Path,
    exclude_patterns: list[str],
) -> bool:
    """Check if path matches any exclusion pattern.

    Args:
        path_str: POSIX-normalized path string.
        relative_path: Path object for parent directory traversal.
        exclude_patterns: Glob patterns for paths to exclude.

    Returns:
        True if any pattern matches.
    """
    for pattern in exclude_patterns:
        # Direct pattern match
        if fnmatch.fnmatch(path_str, pattern):
            return True

        # Also check if any parent directory matches
        # This handles patterns like "tests/**" matching "tests/unit/test_foo.py"
        for parent in relative_path.parents:
            parent_str = _normalize_to_posix(parent)
            if fnmatch.fnmatch(parent_str, pattern.removesuffix("/**")):
                return True

    return False


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
    relative_path = get_relative_path_safe(file_path, root_directory)
    path_str = _normalize_to_posix(relative_path)
    return _matches_exclusion_patterns(path_str, relative_path, exclude_patterns)


def _matches_module_segments(path_str: str, module: str) -> bool:
    """Check if module segments appear as contiguous segments in path.

    Uses segment-based matching to avoid false positives (e.g., "cli"
    won't match "public_client.py").

    Args:
        path_str: POSIX-normalized path string.
        module: Module name with dot separators (e.g., "omnibase_core.bootstrap").

    Returns:
        True if module segments appear contiguously in path segments.
    """
    module_path = module.replace(".", "/")
    module_segments = module_path.split("/")
    path_segments = path_str.split("/")

    # Check if module segments appear as contiguous segments anywhere in the path
    for i in range(len(path_segments) - len(module_segments) + 1):
        if path_segments[i : i + len(module_segments)] == module_segments:
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
    # Calculate path once, reuse for both pattern and module matching
    relative_path = get_relative_path_safe(file_path, root_directory)
    path_str = _normalize_to_posix(relative_path)

    # Check standard exclusion patterns
    if _matches_exclusion_patterns(path_str, relative_path, exclude_patterns):
        return True

    # Check allowlist modules using segment matching
    for allowlist_module in allowlist_modules:
        if _matches_module_segments(path_str, allowlist_module):
            return True

    return False


__all__ = [
    "get_relative_path_safe",
    "should_exclude_path",
    "should_exclude_path_with_modules",
]
