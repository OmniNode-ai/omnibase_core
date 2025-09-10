"""
Filesystem implementation of the file reader protocol.

This is the production implementation that reads from the actual filesystem.
"""

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.exceptions import OnexError
from omnibase_core.model.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.utils.safe_yaml_loader import (
    load_yaml_content_as_model,
)

T = TypeVar("T", bound=BaseModel)


class UtilityFileSystemReader:
    """
    Filesystem implementation of ProtocolFileReader.

    This implementation reads files from the actual filesystem.
    """

    def read_text(self, path: str | Path) -> str:
        """
        Read text content from a file on the filesystem.

        Args:
            path: Path to the file to read

        Returns:
            str: The text content of the file

        Raises:
            OnexError: If the file doesn't exist or can't be read
        """
        path = Path(path)
        if not path.exists():
            raise OnexError(CoreErrorCode.FILE_NOT_FOUND, f"File not found: {path}")

        try:
            return path.read_text()
        except Exception as e:
            raise OnexError(
                CoreErrorCode.FILE_READ_ERROR,
                f"Failed to read file {path}: {e}",
            )

    def read_yaml(self, path: str | Path, model_class: type[T]) -> T:
        """
        Read and parse YAML content from a file into a Pydantic model.

        Args:
            path: Path to the YAML file to read
            model_class: Pydantic model class to validate and parse into

        Returns:
            Instance of the specified Pydantic model

        Raises:
            OnexError: If file operations fail or validation fails
        """
        try:
            content = self.read_text(path)
        except FileNotFoundError:
            raise OnexError(
                CoreErrorCode.FILE_NOT_FOUND,
                f"Contract file not found: {path}",
            )
        except Exception as e:
            raise OnexError(
                CoreErrorCode.FILE_READ_ERROR,
                f"Failed to read file {path}: {e}",
            )

        try:
            # Load and validate YAML using Pydantic model

            yaml_model = load_yaml_content_as_model(content, ModelGenericYaml)

            data = yaml_model.model_dump()
        except yaml.YAMLError as e:
            raise OnexError(
                CoreErrorCode.CONFIGURATION_PARSE_ERROR,
                f"Failed to parse YAML from {path}: {e}",
            )

        try:
            return model_class.model_validate(data)
        except ValidationError as e:
            raise OnexError(
                CoreErrorCode.VALIDATION_ERROR,
                f"Failed to validate {model_class.__name__} from {path}: {e}",
            )

    def exists(self, path: str | Path) -> bool:
        """
        Check if a file exists on the filesystem.

        Args:
            path: Path to check

        Returns:
            bool: True if the file exists, False otherwise
        """
        return Path(path).exists()
