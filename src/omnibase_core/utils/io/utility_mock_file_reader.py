"""
Mock implementation of the file reader protocol for testing.

This implementation returns predefined Pydantic models directly,
without any file I/O simulation.
"""

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.exceptions import OnexError

T = TypeVar("T", bound=BaseModel)


class UtilityMockFileReader:
    """
    Mock implementation of ProtocolFileReader for testing.

    This implementation returns predefined Pydantic models directly,
    without any file I/O simulation.
    """

    def __init__(self, models: dict[str, BaseModel] | None = None):
        """
        Initialize the mock file reader with predefined models.

        Args:
            models: Dictionary mapping file paths to their Pydantic model instances.
        """
        self._models: dict[str, BaseModel] = models or {}

        # Add default test models if not provided
        if not self._models:
            self._setup_default_test_models()

    def _setup_default_test_models(self):
        """Set up default test models for common test scenarios."""
        import yaml

        from omnibase_core.model.generation.model_contract_document import (
            ModelContractDocument,
        )

        # Load the test contract data and create a proper model
        test_data_path = Path(__file__).parent / "test_contract_data.yaml"
        if test_data_path.exists():
            with open(test_data_path) as f:
                contract_data = yaml.safe_load(f)

            contract_model = ModelContractDocument.model_validate(contract_data)

            # Store the model directly - no dict conversion needed
            self._models = {
                "src/omnibase/tools/generation/tool_contract_driven_generator/v1_0_0/contract.yaml": contract_model,
            }

    def add_model(self, path: str, model: BaseModel):
        """
        Add a model to the mock reader.

        Args:
            path: Path where the model should be available
            model: Pydantic model instance
        """
        self._models[str(path)] = model

    def read_text(self, path: str | Path) -> str:
        """
        Read text content from the mock.

        Args:
            path: Path to the file to read

        Returns:
            str: The text content of the file

        Raises:
            OnexError: If the file doesn't exist in the mock
        """
        path_str = str(path)

        if path_str not in self._models:
            raise OnexError(
                CoreErrorCode.FILE_NOT_FOUND,
                f"Mock file not found: {path}",
            )

        model = self._models[path_str]

        # Convert model to YAML string for text reading
        import yaml

        return yaml.dump(model.model_dump(), default_flow_style=False)

    def read_yaml(self, path: str | Path, model_class: type[T]) -> T:
        """
        Read and return a Pydantic model directly from the mock.

        Args:
            path: Path to the file
            model_class: Pydantic model class (must match stored model type)

        Returns:
            Instance of the specified Pydantic model

        Raises:
            OnexError: If file operations fail or model type mismatch
        """
        path_str = str(path)

        # Use test contract data for contract generator
        if path_str not in self._models:
            raise OnexError(
                CoreErrorCode.FILE_NOT_FOUND,
                f"Mock model not found for path: {path}",
            )

        model = self._models[path_str]

        # Verify the model is of the expected type
        if not isinstance(model, model_class):
            raise OnexError(
                CoreErrorCode.VALIDATION_ERROR,
                f"Mock model type mismatch: expected {model_class.__name__}, got {type(model).__name__}",
            )

        return model

    def exists(self, path: str | Path) -> bool:
        """
        Check if a model exists in the mock.

        Args:
            path: Path to check

        Returns:
            bool: True if the model exists in the mock, False otherwise
        """
        return str(path) in self._models
