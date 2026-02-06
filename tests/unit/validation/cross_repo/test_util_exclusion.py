"""Tests for util_exclusion module.

Verifies the shared exclusion logic used by multiple validation rules.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validation.cross_repo.util_exclusion import (
    should_exclude_path,
    should_exclude_path_with_modules,
)


@pytest.mark.unit
class TestShouldExcludePath:
    """Tests for should_exclude_path function."""

    def test_excludes_matching_pattern(self) -> None:
        """File matching pattern should be excluded."""
        file_path = Path("/repo/tests/unit/test_foo.py")
        root_directory = Path("/repo")
        exclude_patterns = ["tests/**"]

        result = should_exclude_path(file_path, root_directory, exclude_patterns)

        assert result is True

    def test_excludes_parent_directory_match(self) -> None:
        """File in excluded directory should be excluded."""
        file_path = Path("/repo/tests/integration/test_bar.py")
        root_directory = Path("/repo")
        exclude_patterns = ["tests/**"]

        result = should_exclude_path(file_path, root_directory, exclude_patterns)

        assert result is True

    def test_does_not_exclude_non_matching_path(self) -> None:
        """File not matching any pattern should not be excluded."""
        file_path = Path("/repo/src/module.py")
        root_directory = Path("/repo")
        exclude_patterns = ["tests/**"]

        result = should_exclude_path(file_path, root_directory, exclude_patterns)

        assert result is False

    def test_handles_multiple_patterns(self) -> None:
        """Should check all patterns."""
        file_path = Path("/repo/examples/demo.py")
        root_directory = Path("/repo")
        exclude_patterns = ["tests/**", "examples/**", "deprecated/**"]

        result = should_exclude_path(file_path, root_directory, exclude_patterns)

        assert result is True

    def test_handles_none_root_directory(self) -> None:
        """Should work without root directory."""
        file_path = Path("tests/test_foo.py")
        exclude_patterns = ["tests/**"]

        result = should_exclude_path(file_path, None, exclude_patterns)

        assert result is True

    def test_handles_file_outside_root(self) -> None:
        """Should handle file outside root directory."""
        file_path = Path("/other/path/file.py")
        root_directory = Path("/repo")
        exclude_patterns = ["tests/**"]

        # File is outside root, so should use the full path
        result = should_exclude_path(file_path, root_directory, exclude_patterns)

        assert result is False

    def test_empty_exclude_patterns(self) -> None:
        """Empty patterns should not exclude anything."""
        file_path = Path("/repo/tests/test_foo.py")
        root_directory = Path("/repo")
        exclude_patterns: list[str] = []

        result = should_exclude_path(file_path, root_directory, exclude_patterns)

        assert result is False

    def test_exact_file_pattern_match(self) -> None:
        """Should match exact file patterns."""
        file_path = Path("/repo/conftest.py")
        root_directory = Path("/repo")
        exclude_patterns = ["conftest.py"]

        result = should_exclude_path(file_path, root_directory, exclude_patterns)

        assert result is True


@pytest.mark.unit
class TestShouldExcludePathWithModules:
    """Tests for should_exclude_path_with_modules function."""

    def test_excludes_by_pattern(self) -> None:
        """Should exclude based on glob patterns."""
        file_path = Path("/repo/tests/test_foo.py")
        root_directory = Path("/repo")
        exclude_patterns = ["tests/**"]
        allowlist_modules: list[str] = []

        result = should_exclude_path_with_modules(
            file_path, root_directory, exclude_patterns, allowlist_modules
        )

        assert result is True

    def test_excludes_by_allowlist_module(self) -> None:
        """Should exclude based on allowlist modules."""
        file_path = Path("/repo/src/omnibase_core/bootstrap/init.py")
        root_directory = Path("/repo")
        exclude_patterns: list[str] = []
        allowlist_modules = ["omnibase_core.bootstrap"]

        result = should_exclude_path_with_modules(
            file_path, root_directory, exclude_patterns, allowlist_modules
        )

        assert result is True

    def test_module_segment_matching_prevents_false_positives(self) -> None:
        """Should use segment matching to avoid false positives.

        "cli" should not match "public_client.py".
        """
        file_path = Path("/repo/src/public_client.py")
        root_directory = Path("/repo")
        exclude_patterns: list[str] = []
        allowlist_modules = ["cli"]

        result = should_exclude_path_with_modules(
            file_path, root_directory, exclude_patterns, allowlist_modules
        )

        assert result is False

    def test_module_segment_matching_matches_exact_segment(self) -> None:
        """Should match when module appears as exact segment."""
        file_path = Path("/repo/src/cli/commands.py")
        root_directory = Path("/repo")
        exclude_patterns: list[str] = []
        allowlist_modules = ["cli"]

        result = should_exclude_path_with_modules(
            file_path, root_directory, exclude_patterns, allowlist_modules
        )

        assert result is True

    def test_multi_segment_module_matching(self) -> None:
        """Should match multi-segment module paths."""
        file_path = Path("/repo/src/omnibase_core/logging/structured.py")
        root_directory = Path("/repo")
        exclude_patterns: list[str] = []
        allowlist_modules = ["omnibase_core.logging"]

        result = should_exclude_path_with_modules(
            file_path, root_directory, exclude_patterns, allowlist_modules
        )

        assert result is True

    def test_does_not_exclude_non_matching_module(self) -> None:
        """Should not exclude when module doesn't match."""
        file_path = Path("/repo/src/omnibase_core/services/handler.py")
        root_directory = Path("/repo")
        exclude_patterns: list[str] = []
        allowlist_modules = ["omnibase_core.logging"]

        result = should_exclude_path_with_modules(
            file_path, root_directory, exclude_patterns, allowlist_modules
        )

        assert result is False

    def test_empty_allowlist_modules(self) -> None:
        """Empty allowlist should not exclude anything."""
        file_path = Path("/repo/src/omnibase_core/bootstrap/init.py")
        root_directory = Path("/repo")
        exclude_patterns: list[str] = []
        allowlist_modules: list[str] = []

        result = should_exclude_path_with_modules(
            file_path, root_directory, exclude_patterns, allowlist_modules
        )

        assert result is False

    def test_handles_none_root_directory(self) -> None:
        """Should work without root directory."""
        file_path = Path("omnibase_core/bootstrap/init.py")
        exclude_patterns: list[str] = []
        allowlist_modules = ["omnibase_core.bootstrap"]

        result = should_exclude_path_with_modules(
            file_path, None, exclude_patterns, allowlist_modules
        )

        assert result is True
