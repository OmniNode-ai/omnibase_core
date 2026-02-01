"""File discovery scanner using glob patterns.

Discovers files to validate based on include/exclude patterns
from the discovery configuration.

Related ticket: OMN-1771
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

from omnibase_core.models.validation.model_validation_discovery_config import (
    ModelValidationDiscoveryConfig,
)


class ScannerFileDiscovery:
    """Discovers files for validation using glob patterns.

    Uses the discovery configuration to find files matching include
    patterns while excluding those matching exclude patterns.
    """

    def __init__(self, config: ModelValidationDiscoveryConfig) -> None:
        """Initialize the scanner with discovery configuration.

        Args:
            config: Discovery configuration with include/exclude patterns.
        """
        self.config = config

    def discover(self, root: Path) -> list[Path]:
        """Discover files to validate under the given root.

        Args:
            root: Root directory to scan.

        Returns:
            List of file paths to validate (sorted for determinism).
        """
        discovered: set[Path] = set()

        # Expand include patterns
        for pattern in self.config.include_globs:
            for match in root.glob(pattern):
                if match.is_file():
                    discovered.add(match.resolve())

        # Filter by exclusions (resolve root to match resolved file paths)
        resolved_root = root.resolve()
        filtered = [f for f in discovered if not self._is_excluded(f, resolved_root)]

        # Filter generated files if configured
        if self.config.skip_generated:
            filtered = [f for f in filtered if not self._is_generated(f)]

        return sorted(filtered)

    def _is_excluded(self, path: Path, root: Path) -> bool:
        """Check if a path matches any exclusion pattern.

        Args:
            path: File path to check.
            root: Root directory for relative path calculation.

        Returns:
            True if the path should be excluded.
        """
        # Get path relative to root for pattern matching
        try:
            relative = path.relative_to(root)
        except ValueError:
            relative = path

        path_str = str(relative)
        posix_str = relative.as_posix()

        for pattern in self.config.exclude_globs:
            # Match against both native and POSIX paths
            if fnmatch.fnmatch(path_str, pattern):
                return True
            if fnmatch.fnmatch(posix_str, pattern):
                return True

            # Also check path components for patterns like **/__pycache__/**
            if "**" in pattern:
                core_pattern = pattern.replace("**", "").strip("/")
                if core_pattern:
                    for part in path.parts:
                        if fnmatch.fnmatch(part, core_pattern):
                            return True

        return False

    def _is_generated(self, path: Path) -> bool:
        """Check if a file is marked as generated.

        Args:
            path: File path to check.

        Returns:
            True if the file contains a generated code marker.
        """
        try:
            # Read first few lines to check for markers
            content = path.read_text(encoding="utf-8", errors="ignore")
            first_lines = content[:1000]  # Check first ~1000 chars

            for marker in self.config.generated_markers:
                if marker in first_lines:
                    return True

            return False
        except OSError:
            return False
