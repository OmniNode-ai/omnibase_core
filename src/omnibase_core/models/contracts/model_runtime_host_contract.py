"""
Runtime Host Contract Model.

Main contract model for RuntimeHost configuration combining:
- Handler configurations for I/O operations
- Event bus configuration for pub/sub messaging
- Node references for node graph management

MVP implementation - simplified for minimal viable product.
Advanced features (retry policies, rate limits) deferred to Beta.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_node_ref import ModelNodeRef
from omnibase_core.models.contracts.model_runtime_event_bus_config import (
    ModelRuntimeEventBusConfig,
)
from omnibase_core.models.contracts.model_runtime_handler_config import (
    ModelRuntimeHandlerConfig,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelRuntimeHostContract(BaseModel):
    """
    Runtime Host Contract for ONEX RuntimeHostProcess.

    Defines the configuration for a runtime host including:
    - Handler configurations for I/O operations
    - Event bus configuration for pub/sub messaging
    - Node references for node graph management

    MVP implementation - simplified for minimal viable product.
    Advanced features (retry policies, rate limits) deferred to Beta.

    Attributes:
        handlers: List of handler configurations for I/O operations
        event_bus: Event bus configuration for pub/sub messaging
        nodes: List of node references for node graph management

    Example:
        >>> from omnibase_core.enums.enum_handler_type import EnumHandlerType
        >>> contract = ModelRuntimeHostContract(
        ...     handlers=[ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.FILESYSTEM)],
        ...     event_bus=ModelRuntimeEventBusConfig(kind="kafka"),
        ...     nodes=[ModelNodeRef(slug="node-compute-transformer")],
        ... )
        >>> contract.event_bus.kind
        'kafka'
    """

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
    )

    handlers: list[ModelRuntimeHandlerConfig] = Field(
        default_factory=list,
        description="Handler configurations for I/O operations",
    )

    event_bus: ModelRuntimeEventBusConfig = Field(
        ...,
        description="Event bus configuration for pub/sub messaging",
    )

    nodes: list[ModelNodeRef] = Field(
        default_factory=list,
        description="Node references for node graph management",
    )

    @classmethod
    def from_yaml(cls, path: Path) -> "ModelRuntimeHostContract":
        """Load RuntimeHostContract from a YAML file.

        Parses and validates a YAML contract file, returning a fully
        validated ModelRuntimeHostContract instance. This method handles
        all file I/O, YAML parsing, and Pydantic validation in a single call.

        YAML Root Type Requirement:
            The YAML file MUST have a mapping (dict) at its root. This is an
            intentional design constraint for the following reasons:

            1. **Pydantic Compatibility**: ``model_validate()`` requires dict input
               to map YAML keys to model field names.

            2. **Contract Semantics**: RuntimeHostContract has named fields
               (event_bus, handlers, nodes) that naturally map to a YAML mapping.
               A list or scalar at root would be semantically meaningless.

            3. **Fail-Fast Behavior**: Empty files (which parse to None) and
               non-mapping types (lists, scalars) are explicitly rejected with
               clear error messages rather than causing cryptic downstream failures.

            Valid YAML root types that are REJECTED:
                - Empty file (parses to None)
                - List at root: ``- item1\\n- item2``
                - Scalar at root: ``"just a string"`` or ``42``

        TOCTOU Handling:
            This method performs an explicit exists() check before opening the
            file for better error messages. If the file is deleted between the
            exists() check and the open() call (a TOCTOU race condition), the
            resulting FileNotFoundError is caught and mapped to FILE_NOT_FOUND
            with the os_error context field populated.

        Args:
            path: Path to the YAML contract file. Can be absolute or relative.
                The file must exist and be readable.

        Returns:
            Validated ModelRuntimeHostContract instance ready for use.

        Raises:
            ModelOnexError: With one of the following error codes:

                FILE_NOT_FOUND:
                    Contract file does not exist at the specified path. This
                    error is also raised for TOCTOU race conditions where the
                    file is deleted between the exists() check and open() call.
                    Context:
                        - file_path: String path to the missing file
                        - os_error: (only for TOCTOU race) String representation
                          of the FileNotFoundError

                FILE_READ_ERROR:
                    Cannot read the file due to OS-level errors. Common causes
                    include permission denied, path is a directory, disk I/O
                    errors, or file system issues.
                    Context:
                        - file_path: String path to the file
                        - os_error: String representation of the OSError

                CONFIGURATION_PARSE_ERROR:
                    The file contains invalid YAML syntax. The error context
                    includes position information when available from the YAML
                    parser.
                    Context:
                        - file_path: String path to the file
                        - yaml_error: String representation of the YAMLError
                        - line_number: (if available) 1-indexed line number
                          where the parse error occurred
                        - column_number: (if available) 1-indexed column number
                          where the parse error occurred

                VALIDATION_ERROR:
                    The YAML file parsed successfully but the result is not a
                    mapping (dict). This occurs when the file is empty (parsed
                    as None), contains only a scalar value, or contains a list
                    at the root level.
                    Context:
                        - file_path: String path to the file

                CONTRACT_VALIDATION_ERROR:
                    The YAML parsed to a dict but failed Pydantic schema
                    validation. Common causes include:
                    - Unknown fields (due to extra="forbid" configuration)
                    - Invalid enum values for handler_type or other enums
                    - Missing required fields (e.g., event_bus)
                    - Type mismatches (e.g., string where list expected)
                    Context:
                        - file_path: String path to the file
                        - validation_error: String representation of the
                          Pydantic ValidationError
                        - validation_errors: List of error dicts from
                          Pydantic's e.errors(), each containing 'loc',
                          'msg', and 'type' keys

        Example:
            >>> from pathlib import Path
            >>> contract = ModelRuntimeHostContract.from_yaml(
            ...     Path("config/runtime_host.yaml")
            ... )  # doctest: +SKIP
            >>> contract.event_bus.kind  # doctest: +SKIP
            'kafka'

        See Also:
            FileRegistry.load: Wrapper that adds duplicate handler validation
            ModelRuntimeHandlerConfig: Handler configuration model
            ModelRuntimeEventBusConfig: Event bus configuration model
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
        except FileNotFoundError as e:
            # Handle TOCTOU race: file deleted between exists() check and open()
            raise ModelOnexError(
                message=f"Contract file not found: {path}: {e}",
                error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
                file_path=str(path),
                os_error=str(e),
            ) from e
        except OSError as e:
            # Handle other file read errors (permission denied, is a directory, etc.)
            raise ModelOnexError(
                message=f"Cannot read contract file: {path}: {e}",
                error_code=EnumCoreErrorCode.FILE_READ_ERROR,
                file_path=str(path),
                os_error=str(e),
            ) from e
        except yaml.YAMLError as e:
            # Extract line/column info if available for structured error context
            line_info = ""
            line_number: int | None = None
            column_number: int | None = None
            if hasattr(e, "problem_mark") and e.problem_mark:
                line_number = e.problem_mark.line + 1
                column_number = e.problem_mark.column + 1
                line_info = f" at line {line_number}, column {column_number}"
            raise ModelOnexError(
                message=f"Invalid YAML in contract file: {path}{line_info}",
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
                file_path=str(path),
                yaml_error=str(e),
                line_number=line_number,
                column_number=column_number,
            ) from e

        # INTENTIONAL: Contract files MUST have a YAML mapping (dict) at root.
        # This validation is by design for three reasons:
        # 1. Pydantic model_validate() requires dict input for field mapping
        # 2. RuntimeHostContract has named fields (event_bus, handlers, nodes)
        #    which only make semantic sense as a YAML mapping, not list/scalar
        # 3. Fail-fast: reject invalid root types with clear errors rather than
        #    letting them cause cryptic failures in model_validate()
        #
        # See: tests/unit/runtime/test_file_registry.py for explicit test coverage
        # of empty files, lists at root, and scalars at root.
        if yaml_data is None:
            # Empty YAML files parse to None - reject with clear error
            raise ModelOnexError(
                message=f"Contract file must contain a YAML mapping, got NoneType: {path}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                file_path=str(path),
            )

        if not isinstance(yaml_data, dict):
            # Lists, scalars, or other non-mapping types at root - reject
            raise ModelOnexError(
                message=f"Contract file must contain a YAML mapping, got {type(yaml_data).__name__}: {path}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                file_path=str(path),
            )

        # Validate with Pydantic model
        try:
            return cls.model_validate(yaml_data)
        except ValidationError as e:
            # Extract structured field information from validation error
            error_details = str(e)
            validation_errors = e.errors()  # List of dicts with loc, msg, type
            raise ModelOnexError(
                message=f"Contract validation failed for {path}: {error_details}",
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
                file_path=str(path),
                validation_error=error_details,
                validation_errors=validation_errors,
            ) from e
