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
    """Registry for loading YAML contract files.

    Provides methods to load single files or all files from a directory,
    with fail-fast error handling and comprehensive validation.

    All errors are raised as ModelOnexError with appropriate error codes
    and structured context information for debugging and error recovery.

    Error Handling:
        All methods raise ModelOnexError with structured context. The error
        context always includes 'file_path' and may include additional fields
        depending on the error type:

        - os_error: String representation of the underlying OSError
        - yaml_error: String representation of YAML parsing error
        - line_number: Line number where YAML parsing failed (1-indexed)
        - column_number: Column number where YAML parsing failed (1-indexed)
        - validation_error: String representation of validation failure
        - validation_errors: List of validation error dicts from Pydantic
        - duplicate_handler_type: Handler type value that was duplicated

    Thread Safety:
        FileRegistry instances are stateless and can be safely shared across
        threads. Each call to load() or load_all() is independent.

    Example:
        >>> registry = FileRegistry()
        >>> contract = registry.load(Path("config/runtime_host.yaml"))
        >>> contracts = registry.load_all(Path("config/contracts/"))

    See Also:
        ModelRuntimeHostContract: The contract model being loaded
        ModelRuntimeHostContract.from_yaml: Core YAML loading logic
        ModelOnexError: Structured error class for all failures
    """

    def load(self, path: Path) -> ModelRuntimeHostContract:
        """Load a single YAML contract file.

        Parses and validates a YAML contract file, returning a fully
        validated ModelRuntimeHostContract instance. Delegates core YAML
        loading to ModelRuntimeHostContract.from_yaml() and adds
        FileRegistry-specific validations (e.g., duplicate handler type check).

        Args:
            path: Path to the YAML contract file. Must be an absolute or
                relative path to an existing YAML file.

        Returns:
            Validated ModelRuntimeHostContract instance ready for use.

        Raises:
            ModelOnexError: With one of the following error codes:

                FILE_NOT_FOUND:
                    Contract file does not exist. This includes TOCTOU race
                    conditions where the file is deleted between the existence
                    check and the open() call.
                    Context: file_path, os_error (if TOCTOU race)

                FILE_READ_ERROR:
                    Cannot read file due to OS-level errors such as permission
                    denied, path is a directory, I/O errors, etc.
                    Context: file_path, os_error

                CONFIGURATION_PARSE_ERROR:
                    Invalid YAML syntax in the contract file.
                    Context: file_path, yaml_error, line_number (if available),
                    column_number (if available)

                VALIDATION_ERROR:
                    YAML parsed successfully but resulted in a non-dict type
                    (e.g., a list, string, or None from empty file).
                    Context: file_path

                CONTRACT_VALIDATION_ERROR:
                    Pydantic schema validation failure. This includes unknown
                    fields (due to extra="forbid"), invalid enum values,
                    missing required fields, or type mismatches.
                    Context: file_path, validation_error, validation_errors

                DUPLICATE_REGISTRATION:
                    FileRegistry-specific validation failure. Multiple handlers
                    with the same handler_type were found in the contract.
                    Context: file_path, duplicate_handler_type

        Example:
            >>> registry = FileRegistry()
            >>> contract = registry.load(Path("config/runtime_host.yaml"))
            >>> contract.event_bus.kind
            'kafka'

        See Also:
            ModelRuntimeHostContract.from_yaml: Core YAML loading logic
            _validate_unique_handler_types: Duplicate handler validation
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
        """Validate that handler types are unique within a contract.

        Ensures that no duplicate handler types exist in the contract's handlers
        list. This is a FileRegistry-specific validation that complements the
        schema-level validation performed by ModelRuntimeHostContract.

        This validation exists at the FileRegistry level rather than in the
        Pydantic model because it is a registry-level constraint (preventing
        registration conflicts) rather than a schema-level constraint.

        Args:
            contract: The validated contract to check for duplicate handler types.
                Must be a fully validated ModelRuntimeHostContract instance.
            path: Path to the contract file. Used for error context to help
                identify which file contains the duplicate.

        Raises:
            ModelOnexError: If duplicate handler types are detected.

                DUPLICATE_REGISTRATION:
                    Two or more handlers in the contract have the same
                    handler_type value.
                    Context:
                        - file_path: Path to the contract file
                        - duplicate_handler_type: The handler type value that
                          was found more than once (string representation)

        Note:
            This method uses O(n) time and O(n) space where n is the number
            of handlers. For typical contracts with few handlers, this is
            negligible.
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
        """Load all YAML contracts from a directory.

        Scans the directory for .yaml and .yml files (non-recursive) and loads
        each one. Uses fail-fast behavior - stops at first error encountered.

        Files are processed in sorted order (lexicographic by filename) to
        ensure deterministic behavior across runs.

        Args:
            directory: Path to directory containing YAML contract files. Must
                be an existing directory (not a file).

        Returns:
            List of validated ModelRuntimeHostContract instances, one per YAML
            file found. Returns an empty list if the directory contains no
            .yaml or .yml files.

        Raises:
            ModelOnexError: With one of the following error codes:

                DIRECTORY_NOT_FOUND:
                    The specified path does not exist, or exists but is not
                    a directory (e.g., is a regular file).
                    Context: file_path (the directory path)

                FILE_OPERATION_ERROR:
                    Cannot scan directory contents. This typically occurs due
                    to permission denied errors on the directory itself.
                    Context: file_path, os_error

                FILE_NOT_FOUND:
                    A contract file was deleted after directory scan but before
                    loading (TOCTOU race), or file does not exist.
                    Context: file_path, os_error (if TOCTOU race)

                FILE_READ_ERROR:
                    Cannot read a contract file (permission denied, is a
                    directory, I/O errors, etc.).
                    Context: file_path, os_error

                CONFIGURATION_PARSE_ERROR:
                    Invalid YAML syntax in a contract file.
                    Context: file_path, yaml_error, line_number, column_number

                VALIDATION_ERROR:
                    YAML parsed to non-dict type in a contract file.
                    Context: file_path

                CONTRACT_VALIDATION_ERROR:
                    Pydantic schema validation failure in a contract file.
                    Context: file_path, validation_error, validation_errors

                DUPLICATE_REGISTRATION:
                    Duplicate handler types in a contract file.
                    Context: file_path, duplicate_handler_type

        Example:
            >>> registry = FileRegistry()
            >>> contracts = registry.load_all(Path("config/contracts/"))
            >>> len(contracts)
            3

        Note:
            **Design Decision - Fail-Fast Behavior**:
            This method intentionally stops at the first error rather than collecting
            all errors. Rationale:

            1. **Deployment Safety**: Contracts are typically loaded at startup.
               If ANY contract is invalid, the system should not start with partial
               configuration. Partial loading would mask configuration errors and
               lead to subtle runtime failures.

            2. **Clear Error Context**: A single error with full context is more
               actionable than a list of errors that may have cascading effects.
               Fixing the first error often resolves dependent errors.

            3. **Future Extension**: If batch validation is needed (e.g., for tooling
               that reports "fix these 3 files"), a separate ``validate_all()`` method
               can be added that collects all errors without loading. This would be
               useful for CI/CD pipelines or IDE integrations that want to report
               all issues at once.

            Successfully loaded contracts before the failure are not returned.
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

        # Load each file with fail-fast behavior.
        # DESIGN: Fail-fast is intentional - for deployment, ALL contracts must be
        # valid. If any contract fails, we stop immediately rather than returning
        # partial results that could mask configuration errors.
        contracts: list[ModelRuntimeHostContract] = []
        for yaml_file in yaml_files:
            contract = self.load(yaml_file)
            contracts.append(contract)

        return contracts
