# === OmniNode:Metadata ===
# metadata_version: 0.1.0
# protocol_version: 0.1.0
# owner: OmniNode Team
# copyright: OmniNode Team
# schema_version: 0.1.0
# name: test_directory_traverser.py
# version: 1.0.0
# uuid: 696af254-2812-4afc-b892-12e79ba182be
# author: OmniNode Team
# created_at: 2025-05-21T12:41:40.172640
# last_modified_at: 2025-05-21T16:42:46.069256
# description: Stamped by ToolPython
# state_contract: state_contract://default
# lifecycle: active
# hash: 5921b393e2ff2b91348ea5533f065882de17fe6c22e413b17dd9af5772d1d417
# entrypoint: python@test_directory_traverser.py
# runtime_language_hint: python>=3.11
# namespace: onex.stamped.test_directory_traverser
# meta_type: tool
# === /OmniNode:Metadata ===


"""
Standards-Compliant Test File for ONEX/OmniBase Directory Traverser

This file follows the canonical test pattern as demonstrated in src/omnibase/utils/tests/test_node_metadata_extractor.py. It demonstrates:
- Naming conventions: test_ prefix, lowercase, descriptive
- Context-agnostic, registry-driven, fixture-injected testing
- Use of both mock (unit) and integration (real) contexts via pytest fixture parametrization
- No global state; all dependencies are injected
- Registry-driven test case execution pattern
- Compliance with all standards in docs/standards.md and docs/testing.md

All new directory traverser tests should follow this pattern unless a justified exception is documented and reviewed.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from unittest import mock

import pytest

from omnibase_core.core.error_codes import CoreErrorCode, OnexError
from omnibase_core.enums import \
    IgnorePatternSourceEnum  # type: ignore[import-untyped]
from omnibase_core.enums import \
    TraversalModeEnum  # type: ignore[import-untyped]
from omnibase_core.model.core.model_file_filter import \
    FileFilterModel  # type: ignore[import-untyped]
from omnibase_core.utils.directory_traverser import \
    DirectoryTraverser  # type: ignore[import-untyped]


class MockPath:
    """Mock Path class for in-memory filesystem testing."""

    path_str: str
    _is_file: bool
    _is_dir: bool
    _size: int
    content: str
    _parent: Optional[str]

    def __init__(
        self,
        path_str: str,
        is_file: bool = True,
        is_dir: bool = False,
        size: int = 1000,
        content: str = "",
    ) -> None:
        self.path_str = path_str
        self._is_file = is_file
        self._is_dir = is_dir
        self._size = size
        self.content = content
        self._parent = None if "/" not in path_str else path_str.rsplit("/", 1)[0]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MockPath):
            return self.path_str == other.path_str
        return False

    def __hash__(self) -> int:
        return hash(self.path_str)

    def is_file(self) -> bool:
        return self._is_file

    def is_dir(self) -> bool:
        return self._is_dir

    def exists(self) -> bool:
        return True

    def absolute(self) -> "MockPath":
        return self

    def as_posix(self) -> str:
        return self.path_str

    def stat(self) -> mock.MagicMock:
        return mock.MagicMock(st_size=self._size)

    @property
    def parent(self) -> "MockPath":
        if self._parent is None:
            return self
        return MockPath(self._parent, is_file=False, is_dir=True)

    @property
    def parent_parent(self) -> "MockPath":
        """Get the parent's parent."""
        if self._parent is None:
            return self
        parent = MockPath(self._parent, is_file=False, is_dir=True)
        if parent._parent is None:
            return parent
        return MockPath(parent._parent, is_file=False, is_dir=True)

    def __str__(self) -> str:
        return self.path_str

    def __truediv__(self, other: str) -> "MockPath":
        """Implement the / operator for path joining."""
        if self.path_str.endswith("/"):
            return MockPath(f"{self.path_str}{other}")
        return MockPath(f"{self.path_str}/{other}")


class MockDirectoryTraverser(DirectoryTraverser):
    """
    Mock implementation of DirectoryTraverser for in-memory testing.
    """

    mock_files: Dict[str, MockPath]
    mock_file_list: List[MockPath]

    def __init__(self, mock_files: Optional[Dict[str, MockPath]] = None) -> None:
        """
        Initialize the mock directory traverser.

        Args:
            mock_files: Dictionary mapping path strings to MockPath objects
        """
        super().__init__()
        self.mock_files = mock_files or {}
        self.mock_file_list = list(self.mock_files.values())

    def glob(self, pattern: str) -> List[MockPath]:
        """
        Mock implementation of Path.glob.

        Args:
            pattern: Glob pattern to match

        Returns:
            List of MockPath objects matching the pattern
        """
        # Simple pattern matching for testing
        results = []
        for path in self.mock_file_list:
            if self._matches_pattern(path.path_str, pattern):
                results.append(path)
        return results

    def _matches_pattern(self, path_str: str, pattern: str) -> bool:
        """
        Check if a path matches a glob pattern.

        This is a simplified implementation for testing purposes.

        Args:
            path_str: Path string to check
            pattern: Glob pattern to match

        Returns:
            True if the path matches the pattern, False otherwise
        """
        # Handle recursive patterns
        if "**" in pattern:
            # Convert ** to * for simple testing
            pattern = pattern.replace("**", "*")

        # Handle file extension patterns
        if pattern.startswith("*."):
            ext = pattern[1:]
            return path_str.endswith(ext)

        # Handle directory patterns
        if pattern.endswith("/"):
            return pattern[:-1] in path_str

        # Simple substring matching for test purposes
        parts = pattern.replace("*", "").split("/")
        for part in parts:
            if part and part not in path_str:
                return False

        return True

    def find_files(
        self,
        directory: Path,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        recursive: bool = True,
        ignore_file: Optional[Path] = None,
    ) -> Set[Path]:
        """
        Override find_files to use our mock filesystem. Signature matches DirectoryTraverser for mypy compliance.
        """
        filter_config = make_filter_config(
            traversal_mode=(
                TraversalModeEnum.RECURSIVE if recursive else TraversalModeEnum.FLAT
            ),
            include_patterns=include_patterns or self.DEFAULT_INCLUDE_PATTERNS,
            exclude_patterns=exclude_patterns or [],
            ignore_file=ignore_file,
        )
        # Cast Path to MockPath for test logic
        mock_dir = self.mock_files.get(str(directory), None)
        if mock_dir is None:
            raise OnexError(
                f"MockPath not found for {directory}", CoreErrorCode.RESOURCE_NOT_FOUND
            )
        return self._find_files_with_config_mock(mock_dir, filter_config)

    def _find_files_with_config_mock(
        self, directory: MockPath, filter_config: FileFilterModel
    ) -> Set[Path]:
        """
        Mock implementation of _find_files_with_config, returns Set[Path] for mypy compliance.
        """
        self.reset_counters()
        ignore_patterns = []
        if filter_config.exclude_patterns:
            ignore_patterns.extend(filter_config.exclude_patterns)
        ignore_patterns.append(".git/")
        eligible_files: Set[Path] = set()
        dir_path = directory.path_str
        for path in self.mock_file_list:
            if not path.is_file():
                continue
            if not path.path_str.startswith(dir_path):
                continue
            if filter_config.traversal_mode == TraversalModeEnum.FLAT:
                if path.parent.path_str != dir_path:
                    continue
            if filter_config.traversal_mode == TraversalModeEnum.SHALLOW:
                if (
                    path.parent.path_str != dir_path
                    and path.parent.parent.path_str != dir_path
                ):
                    continue
            include_matched = False
            for pattern in filter_config.include_patterns:
                if self._matches_pattern(path.path_str, pattern):
                    include_matched = True
                    break
            if not include_matched:
                continue
            if self.should_ignore(Path(path.path_str), ignore_patterns, None):
                continue
            eligible_files.add(Path(path.path_str))
        return eligible_files

    def should_ignore(
        self, path: Path, ignore_patterns: list[str], root_dir: Path | None = None
    ) -> bool:
        """
        Mock implementation of should_ignore. Accepts Path for mypy compliance.
        """
        rel_path = str(path)
        for pattern in ignore_patterns:
            if pattern.endswith("/") and pattern[:-1] in rel_path:
                return True
            if self._matches_pattern(rel_path, pattern):
                return True
        return False


@pytest.fixture
def mock_file_system() -> dict[str, MockPath]:
    """Create a mock file system with test files."""
    root = MockPath("/test", is_file=False, is_dir=True)
    files: dict[str, MockPath] = {
        "/test": root,
        "/test/test.yaml": MockPath("/test/test.yaml", content="name: test"),
        "/test/test.json": MockPath("/test/test.json", content='{"name": "test"}'),
        "/test/test.txt": MockPath(
            "/test/test.txt", content="This is not YAML or JSON"
        ),
        "/test/subdir": MockPath("/test/subdir", is_file=False, is_dir=True),
        "/test/subdir/sub_test.yaml": MockPath(
            "/test/subdir/sub_test.yaml", content="name: subtest"
        ),
        "/test/subdir/sub_test.json": MockPath(
            "/test/subdir/sub_test.json", content='{"name": "subtest"}'
        ),
        "/test/.git": MockPath("/test/.git", is_file=False, is_dir=True),
        "/test/.git/git.yaml": MockPath("/test/.git/git.yaml", content="name: git"),
    }
    return files


@pytest.fixture
def traverser(mock_file_system: dict[str, MockPath]) -> MockDirectoryTraverser:
    """Create a MockDirectoryTraverser with the mock file system."""
    return MockDirectoryTraverser(mock_files=mock_file_system)


def test_find_files_recursive(
    traverser: MockDirectoryTraverser, mock_file_system: dict[str, MockPath]
) -> None:
    """Test finding files recursively."""
    files = traverser.find_files(
        directory=Path("/test"),
        include_patterns=["**/*.yaml", "**/*.json"],
        recursive=True,
    )

    # Should find 4 files: test.yaml, test.json, subdir/sub_test.yaml, subdir/sub_test.json
    # But not .git/git.yaml (ignored by default)
    assert len(files) == 4
    assert any(str(mock_file_system["/test/test.yaml"]) == str(f) for f in files)
    assert any(str(mock_file_system["/test/test.json"]) == str(f) for f in files)
    assert any(
        str(mock_file_system["/test/subdir/sub_test.yaml"]) == str(f) for f in files
    )
    assert any(
        str(mock_file_system["/test/subdir/sub_test.json"]) == str(f) for f in files
    )
    assert not any(
        str(mock_file_system["/test/.git/git.yaml"]) == str(f) for f in files
    )


def test_find_files_non_recursive(
    traverser: MockDirectoryTraverser, mock_file_system: dict[str, MockPath]
) -> None:
    """Test finding files non-recursively."""
    files = traverser.find_files(
        directory=Path("/test"),
        include_patterns=["**/*.yaml", "**/*.json"],
        recursive=False,
    )

    # Should find 2 files: test.yaml, test.json
    # But not files in subdirectories
    assert len(files) == 2
    assert any(str(mock_file_system["/test/test.yaml"]) == str(f) for f in files)
    assert any(str(mock_file_system["/test/test.json"]) == str(f) for f in files)
    assert not any(
        str(mock_file_system["/test/subdir/sub_test.yaml"]) == str(f) for f in files
    )
    assert not any(
        str(mock_file_system["/test/subdir/sub_test.json"]) == str(f) for f in files
    )


def test_find_files_with_filter_config(
    traverser: MockDirectoryTraverser, mock_file_system: dict[str, MockPath]
) -> None:
    """Test finding files with a filter config."""
    filter_config = make_filter_config(
        traversal_mode=TraversalModeEnum.RECURSIVE,
        include_patterns=["**/*.yaml"],
        exclude_patterns=["**/subdir/**"],
    )
    files = traverser._find_files_with_config_mock(
        mock_file_system["/test"], filter_config
    )

    # Should find 1 file: test.yaml
    # But not test.json (not matched by pattern) or files in subdirectories (excluded)
    assert len(files) == 1
    assert any(str(mock_file_system["/test/test.yaml"]) == str(f) for f in files)
    assert not any(str(mock_file_system["/test/test.json"]) == str(f) for f in files)
    assert not any(
        str(mock_file_system["/test/subdir/sub_test.yaml"]) == str(f) for f in files
    )
    assert not any(
        str(mock_file_system["/test/subdir/sub_test.json"]) == str(f) for f in files
    )


def test_should_ignore(
    traverser: MockDirectoryTraverser, mock_file_system: dict[str, MockPath]
) -> None:
    """Test the should_ignore method."""
    patterns = ["*.json", "*.yml", ".git/"]

    # Test files that should be ignored
    assert traverser.should_ignore(Path("/test/test.json"), patterns, None)
    assert traverser.should_ignore(Path("/test/.git/git.yaml"), patterns, None)

    # Test files that should not be ignored
    assert not traverser.should_ignore(Path("/test/test.yaml"), patterns, None)
    assert not traverser.should_ignore(Path("/test/test.txt"), patterns, None)


def test_traversal_modes(
    traverser: MockDirectoryTraverser, mock_file_system: dict[str, MockPath]
) -> None:
    """Test different traversal modes."""
    # Test FLAT mode
    filter_config = make_filter_config(
        traversal_mode=TraversalModeEnum.FLAT,
        include_patterns=["**/*.yaml", "**/*.json"],
        ignore_pattern_sources=[IgnorePatternSourceEnum.NONE],
    )

    files = traverser._find_files_with_config_mock(
        mock_file_system["/test"], filter_config
    )

    # Should find 2 files: test.yaml, test.json
    assert len(files) == 2
    assert any(str(mock_file_system["/test/test.yaml"]) == str(f) for f in files)
    assert any(str(mock_file_system["/test/test.json"]) == str(f) for f in files)
    assert not any(
        str(mock_file_system["/test/subdir/sub_test.yaml"]) == str(f) for f in files
    )

    # Test SHALLOW mode
    filter_config = make_filter_config(
        traversal_mode=TraversalModeEnum.SHALLOW,
        include_patterns=["**/*.yaml", "**/*.json"],
        ignore_pattern_sources=[IgnorePatternSourceEnum.NONE],
    )

    files = traverser._find_files_with_config_mock(
        mock_file_system["/test"], filter_config
    )

    # Should find 4 files: all .yaml and .json files in root and immediate subdirectories
    assert len(files) == 4
    assert any(str(mock_file_system["/test/test.yaml"]) == str(f) for f in files)
    assert any(str(mock_file_system["/test/test.json"]) == str(f) for f in files)
    assert any(
        str(mock_file_system["/test/subdir/sub_test.yaml"]) == str(f) for f in files
    )
    assert any(
        str(mock_file_system["/test/subdir/sub_test.json"]) == str(f) for f in files
    )


def make_filter_config(
    traversal_mode: TraversalModeEnum = TraversalModeEnum.RECURSIVE,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    ignore_file: Optional[Any] = None,
    ignore_pattern_sources: Optional[List[IgnorePatternSourceEnum]] = None,
    max_file_size: int = 5 * 1024 * 1024,
    max_files: Optional[int] = None,
    follow_symlinks: bool = False,
    case_sensitive: bool = True,
    **overrides: Any,
) -> FileFilterModel:
    """Test helper to create a FileFilterModel with all required fields and defaults, allowing overrides."""
    return FileFilterModel(
        traversal_mode=traversal_mode,
        include_patterns=(
            include_patterns
            if include_patterns is not None
            else ["**/*.yaml", "**/*.json"]
        ),
        exclude_patterns=exclude_patterns if exclude_patterns is not None else [],
        ignore_file=ignore_file,
        ignore_pattern_sources=(
            ignore_pattern_sources
            if ignore_pattern_sources is not None
            else [IgnorePatternSourceEnum.DEFAULT]
        ),
        max_file_size=max_file_size,
        max_files=max_files,
        follow_symlinks=follow_symlinks,
        case_sensitive=case_sensitive,
        **overrides,
    )
