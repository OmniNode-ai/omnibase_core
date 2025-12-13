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
from typing import TYPE_CHECKING

import yaml
from pydantic import ValidationError

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
        validated ModelRuntimeHostContract instance.

        Args:
            path: Path to the YAML contract file

        Returns:
            ModelRuntimeHostContract: Validated contract instance

        Raises:
            ModelOnexError: If file not found, invalid YAML, or validation fails.
                Error codes:
                - FILE_NOT_FOUND: Contract file does not exist
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
        # Check file exists
        if not path.exists():
            raise ModelOnexError(
                message=f"Contract file not found: {path}",
                error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
                file_path=str(path),
            )

        # Parse YAML
        try:
            with path.open("r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            # Extract line number if available
            line_info = ""
            if hasattr(e, "problem_mark") and e.problem_mark:
                line_info = f" at line {e.problem_mark.line + 1}"
            raise ModelOnexError(
                message=f"Invalid YAML in contract file: {path}{line_info}",
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
                file_path=str(path),
                yaml_error=str(e),
            ) from e

        # Check YAML parsed to a dict
        if yaml_data is None:
            raise ModelOnexError(
                message=f"Contract file is empty or contains only comments: {path}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                file_path=str(path),
            )

        if not isinstance(yaml_data, dict):
            raise ModelOnexError(
                message=f"Contract file must contain a YAML mapping, got {type(yaml_data).__name__}: {path}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                file_path=str(path),
            )

        # Validate with Pydantic model
        try:
            contract = ModelRuntimeHostContract.model_validate(yaml_data)
        except ValidationError as e:
            # Extract field information from validation error
            error_details = str(e)
            raise ModelOnexError(
                message=f"Contract validation failed for {path}: {error_details}",
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
                file_path=str(path),
                validation_error=error_details,
            ) from e

        # Validate no duplicate handler types
        self._validate_unique_handler_types(contract, path)

        return contract

    def _validate_unique_handler_types(
        self, contract: ModelRuntimeHostContract, path: Path
    ) -> None:
        """
        Validate that handler types are unique within a contract.

        Args:
            contract: The validated contract to check
            path: Path to the contract file (for error context)

        Raises:
            ModelOnexError: If duplicate handler types are found
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
                - FILE_NOT_FOUND: Contract file does not exist
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
        yaml_files: list[Path] = []
        for pattern in ("*.yaml", "*.yml"):
            yaml_files.extend(directory.glob(pattern))

        # Sort for deterministic ordering
        yaml_files.sort()

        # Load each file with fail-fast behavior
        contracts: list[ModelRuntimeHostContract] = []
        for yaml_file in yaml_files:
            contract = self.load(yaml_file)
            contracts.append(contract)

        return contracts
