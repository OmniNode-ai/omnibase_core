"""
Protocol for file writing operations.

This protocol defines the interface for writing files to various storage systems.
Implementations can write to filesystem, S3, memory, etc.
"""

from pathlib import Path
from typing import List, Protocol, Union


class ProtocolFileWriter(Protocol):
    """
    Protocol for writing files to storage.

    Follows ONEX patterns:
    - Protocol-based design for flexibility
    - No implementation details in protocol
    - Type-safe interfaces
    """

    def write_file(self, path: Union[str, Path], content: str) -> Path:
        """
        Write content to a file.

        Args:
            path: Path where to write the file
            content: Content to write

        Returns:
            Path: Actual path where file was written

        Raises:
            IOError: If file cannot be written
        """
        ...

    def write_files(self, files: List[tuple[Union[str, Path], str]]) -> List[Path]:
        """
        Write multiple files atomically.

        Args:
            files: List of (path, content) tuples

        Returns:
            List of paths where files were written

        Raises:
            IOError: If any file cannot be written
        """
        ...

    def ensure_directory(self, path: Union[str, Path]) -> Path:
        """
        Ensure a directory exists, creating it if necessary.

        Args:
            path: Directory path to ensure exists

        Returns:
            Path: The directory path

        Raises:
            IOError: If directory cannot be created
        """
        ...

    def delete_file(self, path: Union[str, Path]) -> bool:
        """
        Delete a file if it exists.

        Args:
            path: Path to file to delete

        Returns:
            bool: True if file was deleted, False if it didn't exist

        Raises:
            IOError: If file exists but cannot be deleted
        """
        ...
