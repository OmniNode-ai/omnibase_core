# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.117773'
# description: Stamped by ToolPython
# entrypoint: python://protocol_directory_traverser
# hash: 774dc0903eac6c14d4cd9a2aefb2642124debaed178d33f5e784de8bc43484b5
# last_modified_at: '2025-05-29T14:14:00.213326+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_directory_traverser.py
# namespace: python://omnibase.protocol.protocol_directory_traverser
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: c5431a51-699a-4674-abd7-431b5ed0046a
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
Protocol for directory traversal operations.
Defines a standardized interface for discovering and filtering files in directories.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Protocol, TypeVar

from omnibase_core.model.core.model_directory_processing_result import (
    ModelDirectoryProcessingResult,
)

T = TypeVar("T")  # Generic type variable for processor result


class ProtocolDirectoryTraverser(Protocol):
    """
    Protocol for directory traversal with filtering capabilities.

    This protocol defines a standard interface for directory traversal operations,
    including file discovery, filtering, and processing. It is designed to be
    reusable across multiple tools that need to walk directory trees.

    Example implementation:
    ```python
    class DirectoryTraverser:
        def find_files(self, directory: Path, include_patterns: List[str],
                      exclude_patterns: List[str], recursive: bool) -> Set[Path]:
            # Implementation
            ...
    ```
    """

    def find_files(
        self,
        directory: Path,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        recursive: bool = True,
        ignore_file: Path | None = None,
    ) -> set[Path]:
        """
        Find all files matching the given patterns in the directory.

        Args:
            directory: Directory to search
            include_patterns: List of glob patterns to include (e.g., ['**/*.yaml'])
            exclude_patterns: List of glob patterns to exclude (e.g., ['**/.git/**'])
            recursive: Whether to recursively traverse subdirectories
            ignore_file: Path to ignore file (e.g., .onexignore)

        Returns:
            Set of Path objects for matching files
        """
        ...

    def load_ignore_patterns(self, ignore_file: Path | None = None) -> list[str]:
        """
        Load ignore patterns from a file.

        Args:
            ignore_file: Path to ignore file. If None, will try to find in standard locations.

        Returns:
            List of ignore patterns as strings
        """
        ...

    def should_ignore(self, path: Path, ignore_patterns: list[str]) -> bool:
        """
        Check if a file should be ignored based on patterns.

        Args:
            path: Path to check
            ignore_patterns: List of ignore patterns

        Returns:
            True if the file should be ignored, False otherwise
        """
        ...

    def process_directory(
        self,
        directory: Path,
        processor: Callable[[Path], T],
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        recursive: bool = True,
        ignore_file: Path | None = None,
        dry_run: bool = False,
        max_file_size: int | None = None,
    ) -> ModelDirectoryProcessingResult:
        """
        Process all eligible files in a directory using the provided processor function.

        Args:
            directory: Directory to process
            processor: Callable that processes each file and returns a result
            include_patterns: List of glob patterns to include
            exclude_patterns: List of glob patterns to exclude
            recursive: Whether to recursively traverse subdirectories
            ignore_file: Path to ignore file (e.g., .onexignore)
            dry_run: Whether to perform a dry run (don't modify files)
            max_file_size: Maximum file size in bytes to process

        Returns:
            ModelDirectoryProcessingResult with aggregate results and file stats
        """
        ...
