"""
FileRegistry for loading YAML contract files.

Provides fail-fast loading of RuntimeHostContract files from YAML,
with comprehensive error handling and validation.

OMN-229: FileRegistry implementation for contract loading.

Related:
    - ModelRuntimeHostContract: The contract model being loaded
    - ModelOnexError: Structured error class for all failures
    - EnumHandlerType: Valid handler types for validation
"""

from __future__ import annotations

from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.models.contracts.model_runtime_host_contract import (
    ModelRuntimeHostContract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class FileRegistry:
    """
    Registry for loading YAML contract files.

    Provides methods to load single files or all files from a directory,
    with fail-fast error handling and comprehensive validation.

    All errors are raised as ModelOnexError with appropriate error codes
    and context information including file paths.

    Example:
        >>> registry = FileRegistry()
        >>> contract = registry.load(Path("config/runtime_host.yaml"))
        >>> contracts = registry.load_all(Path("config/contracts/"))
    """

    def load(self, path: Path) -> ModelRuntimeHostContract:
        """
        Load a single YAML contract file.

        Parses and validates a YAML contract file, returning a fully
        validated ModelRuntimeHostContract instance. Delegates core YAML
        loading to ModelRuntimeHostContract.from_yaml() and adds
        FileRegistry-specific validations.

        Args:
            path: Path to the YAML contract file

        Returns:
            ModelRuntimeHostContract: Validated contract instance

        Raises:
            ModelOnexError: If file not found, invalid YAML, or validation fails.
                Error codes:
                - FILE_NOT_FOUND: Contract file does not exist
                - FILE_READ_ERROR: Cannot read file (permission denied, is a directory, etc.)
                - CONFIGURATION_PARSE_ERROR: Invalid YAML syntax
                - CONTRACT_VALIDATION_ERROR: Schema validation failure
                    (unknown fields, invalid enum values, missing required fields)
                - VALIDATION_ERROR: YAML parsed to non-dict type
                - DUPLICATE_REGISTRATION: Duplicate handler types detected

        Example:
            >>> registry = FileRegistry()
            >>> contract = registry.load(Path("config/runtime_host.yaml"))
            >>> contract.event_bus.kind
            'kafka'
        """
        # Delegate core YAML loading to ModelRuntimeHostContract.from_yaml()
        # This handles: file existence check, OSError handling, YAML parsing
        # (with line numbers), empty file detection, type validation, and
        # Pydantic model validation
        contract = ModelRuntimeHostContract.from_yaml(path)

        # FileRegistry-specific validation: no duplicate handler types
        self._validate_unique_handler_types(contract, path)

        return contract

    def _validate_unique_handler_types(
        self, contract: ModelRuntimeHostContract, path: Path
    ) -> None:
        """
        Validate that handler types are unique within a contract.

        Ensures that no duplicate handler types exist in the contract's handlers list.
        This is a FileRegistry-specific validation that complements the schema-level
        validation performed by ModelRuntimeHostContract.

        Args:
            contract: The validated contract to check for duplicate handler types
            path: Path to the contract file (used for error context and debugging)

        Raises:
            ModelOnexError: If duplicate handler types are detected.
                Error code: DUPLICATE_REGISTRATION
                Context includes the path and duplicate handler type value
        """
        seen_types: set[EnumHandlerType] = set()
        for handler in contract.handlers:
            if handler.handler_type in seen_types:
                raise ModelOnexError(
                    message=f"Duplicate handler type '{handler.handler_type.value}' in contract: {path}",
                    error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
                    file_path=str(path),
                    duplicate_handler_type=handler.handler_type.value,
                )
            seen_types.add(handler.handler_type)

    def load_all(self, directory: Path) -> list[ModelRuntimeHostContract]:
        """
        Load all YAML contracts from a directory.

        Scans the directory for .yaml and .yml files (non-recursive)
        and loads each one. Uses fail-fast behavior - stops at first error.

        Args:
            directory: Path to directory containing YAML contract files

        Returns:
            list[ModelRuntimeHostContract]: List of validated contracts.
                Empty list if directory contains no YAML files.

        Raises:
            ModelOnexError: If directory not found, or any file fails to load.
                Error codes:
                - DIRECTORY_NOT_FOUND: Directory does not exist or is not a directory
                - FILE_OPERATION_ERROR: Cannot scan directory (permission denied, etc.)
                - FILE_NOT_FOUND: Contract file does not exist
                - FILE_READ_ERROR: Cannot read file (permission denied, is a directory, etc.)
                - CONFIGURATION_PARSE_ERROR: Invalid YAML syntax
                - CONTRACT_VALIDATION_ERROR: Schema validation failure
                - VALIDATION_ERROR: YAML parsed to non-dict type
                - DUPLICATE_REGISTRATION: Duplicate handler types detected

        Example:
            >>> registry = FileRegistry()
            >>> contracts = registry.load_all(Path("config/contracts/"))
            >>> len(contracts)
            3
        """
        # Check directory exists and is a directory
        if not directory.exists():
            raise ModelOnexError(
                message=f"Directory not found: {directory}",
                error_code=EnumCoreErrorCode.DIRECTORY_NOT_FOUND,
                file_path=str(directory),
            )

        if not directory.is_dir():
            raise ModelOnexError(
                message=f"Path is not a directory: {directory}",
                error_code=EnumCoreErrorCode.DIRECTORY_NOT_FOUND,
                file_path=str(directory),
            )

        # Find all YAML files (non-recursive)
        try:
            yaml_files: list[Path] = []
            for pattern in ("*.yaml", "*.yml"):
                yaml_files.extend(directory.glob(pattern))
        except OSError as e:
            # Handle directory scanning errors (permission denied, etc.)
            raise ModelOnexError(
                message=f"Cannot scan directory for contract files: {directory}: {e}",
                error_code=EnumCoreErrorCode.FILE_OPERATION_ERROR,
                file_path=str(directory),
                os_error=str(e),
            ) from e

        # Sort for deterministic ordering
        yaml_files.sort()

        # Load each file with fail-fast behavior
        contracts: list[ModelRuntimeHostContract] = []
        for yaml_file in yaml_files:
            contract = self.load(yaml_file)
            contracts.append(contract)

        return contracts
