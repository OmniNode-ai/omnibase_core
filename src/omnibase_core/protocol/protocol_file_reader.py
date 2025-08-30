"""
Protocol for file reading operations.

This protocol enables dependency injection for file I/O operations,
allowing for easy mocking in tests and alternative implementations.
"""

from pathlib import Path
from typing import Protocol, Type, TypeVar, Union

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ProtocolFileReader(Protocol):
    """
    Protocol for reading file contents.

    This abstraction allows for different implementations:
    - FileSystemFileReader: Reads from actual filesystem
    - MockFileReader: Returns predefined content for testing
    - RemoteFileReader: Could read from S3, HTTP, etc.
    """

    def read_text(self, path: Union[str, Path]) -> str:
        """
        Read text content from a file.

        Args:
            path: Path to the file to read

        Returns:
            str: The text content of the file

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there's an error reading the file
        """
        ...

    def read_yaml(self, path: Union[str, Path], model_class: Type[T]) -> T:
        """
        Read and parse YAML content from a file into a Pydantic model.

        Args:
            path: Path to the YAML file to read
            model_class: Pydantic model class to validate and parse into

        Returns:
            Instance of the specified Pydantic model

        Raises:
            OnexError: If the file doesn't exist (FILE_NOT_FOUND)
            OnexError: If there's an error reading the file (FILE_READ_ERROR)
            OnexError: If the YAML is malformed (YAML_PARSE_ERROR)
            OnexError: If the YAML doesn't match the model schema (VALIDATION_ERROR)
        """
        ...

    def exists(self, path: Union[str, Path]) -> bool:
        """
        Check if a file exists.

        Args:
            path: Path to check

        Returns:
            bool: True if the file exists, False otherwise
        """
        ...
