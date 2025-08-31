# === OmniNode:Metadata ===
# metadata_version: 0.1.0
# protocol_version: 1.1.0
# owner: OmniNode Team
# copyright: OmniNode Team
# schema_version: 1.1.0
# name: error_codes.py
# version: 1.0.0
# uuid: 4dbf1549-9218-47b6-9188-3589104a38f5
# author: OmniNode Team
# created_at: 2025-05-25T16:50:14.043960
# last_modified_at: 2025-05-25T22:11:50.165848
# description: Stamped by ToolPython
# state_contract: state_contract://default
# lifecycle: active
# hash: 2169ab95a8612c7ab87a2015a94c9d110046d8d9d45d76142fe96ae4a00c114a
# entrypoint: python@error_codes.py
# runtime_language_hint: python>=3.11
# namespace: onex.stamped.error_codes
# meta_type: tool
# === /OmniNode:Metadata ===


"""
Shared error codes and exit code mapping for all ONEX nodes.

This module provides the foundation for consistent error handling and CLI exit
code mapping across the entire ONEX ecosystem. All nodes should use these
patterns for error handling and CLI integration.

Exit Code Conventions:
- 0: Success (EnumOnexStatus.SUCCESS)
- 1: General error (EnumOnexStatus.ERROR, EnumOnexStatus.UNKNOWN)
- 2: Warning (EnumOnexStatus.WARNING)
- 3: Partial success (EnumOnexStatus.PARTIAL)
- 4: Skipped (EnumOnexStatus.SKIPPED)
- 5: Fixed (EnumOnexStatus.FIXED)
- 6: Info (EnumOnexStatus.INFO)

Error Code Format: ONEX_<COMPONENT>_<NUMBER>_<DESCRIPTION>
"""

import re
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.core.core_uuid_service import UUIDService
from omnibase_core.enums.enum_onex_status import EnumOnexStatus


class CLIExitCode(int, Enum):
    """Standard CLI exit codes for ONEX operations."""

    SUCCESS = 0
    ERROR = 1
    WARNING = 2
    PARTIAL = 3
    SKIPPED = 4
    FIXED = 5
    INFO = 6


# Global mapping from EnumOnexStatus to CLI exit codes
STATUS_TO_EXIT_CODE: dict[EnumOnexStatus, CLIExitCode] = {
    EnumOnexStatus.SUCCESS: CLIExitCode.SUCCESS,
    EnumOnexStatus.ERROR: CLIExitCode.ERROR,
    EnumOnexStatus.WARNING: CLIExitCode.WARNING,
    EnumOnexStatus.PARTIAL: CLIExitCode.PARTIAL,
    EnumOnexStatus.SKIPPED: CLIExitCode.SKIPPED,
    EnumOnexStatus.FIXED: CLIExitCode.FIXED,
    EnumOnexStatus.INFO: CLIExitCode.INFO,
    EnumOnexStatus.UNKNOWN: CLIExitCode.ERROR,  # Treat unknown as error
}


def get_exit_code_for_status(status: EnumOnexStatus) -> int:
    """
    Get the appropriate CLI exit code for an EnumOnexStatus.

    This is the canonical function for mapping EnumOnexStatus values to CLI exit codes
    across all ONEX nodes and tools.

    Args:
        status: The EnumOnexStatus to map

    Returns:
        The corresponding CLI exit code (integer)

    Example:
        >>> get_exit_code_for_status(EnumOnexStatus.SUCCESS)
        0
        >>> get_exit_code_for_status(EnumOnexStatus.ERROR)
        1
        >>> get_exit_code_for_status(EnumOnexStatus.WARNING)
        2
    """
    return STATUS_TO_EXIT_CODE.get(status, CLIExitCode.ERROR).value


class OnexErrorCode(str, Enum):
    """
    Base class for ONEX error codes.

    All node-specific error code enums should inherit from this class
    to ensure consistent behavior and interface.

    Subclasses should implement the abstract methods to provide
    component-specific information.
    """

    def get_component(self) -> str:
        """Get the component identifier for this error code."""
        msg = "Subclasses must implement get_component()"
        raise NotImplementedError(msg)

    def get_number(self) -> int:
        """Get the numeric identifier for this error code."""
        msg = "Subclasses must implement get_number()"
        raise NotImplementedError(msg)

    def get_description(self) -> str:
        """Get a human-readable description for this error code."""
        msg = "Subclasses must implement get_description()"
        raise NotImplementedError(msg)

    def get_exit_code(self) -> int:
        """
        Get the appropriate CLI exit code for this error.

        Default implementation returns ERROR (1). Subclasses can override
        for more specific mapping.
        """
        return CLIExitCode.ERROR.value


class CoreErrorCode(OnexErrorCode):
    """
    Core error codes that can be reused across all ONEX components.

    These provide common error patterns that don't need to be redefined
    in each node's error_codes.py module.
    """

    # Generic validation errors (001-020)
    INVALID_PARAMETER = "ONEX_CORE_001_INVALID_PARAMETER"
    MISSING_REQUIRED_PARAMETER = "ONEX_CORE_002_MISSING_REQUIRED_PARAMETER"
    PARAMETER_TYPE_MISMATCH = "ONEX_CORE_003_PARAMETER_TYPE_MISMATCH"
    PARAMETER_OUT_OF_RANGE = "ONEX_CORE_004_PARAMETER_OUT_OF_RANGE"
    VALIDATION_FAILED = "ONEX_CORE_005_VALIDATION_FAILED"
    VALIDATION_ERROR = "ONEX_CORE_006_VALIDATION_ERROR"
    INVALID_INPUT = "ONEX_CORE_007_INVALID_INPUT"
    INVALID_OPERATION = "ONEX_CORE_008_INVALID_OPERATION"

    # File system errors (021-040)
    FILE_NOT_FOUND = "ONEX_CORE_021_FILE_NOT_FOUND"
    FILE_READ_ERROR = "ONEX_CORE_022_FILE_READ_ERROR"
    FILE_WRITE_ERROR = "ONEX_CORE_023_FILE_WRITE_ERROR"
    DIRECTORY_NOT_FOUND = "ONEX_CORE_024_DIRECTORY_NOT_FOUND"
    PERMISSION_DENIED = "ONEX_CORE_025_PERMISSION_DENIED"
    FILE_OPERATION_ERROR = "ONEX_CORE_026_FILE_OPERATION_ERROR"

    # Configuration errors (041-060)
    INVALID_CONFIGURATION = "ONEX_CORE_041_INVALID_CONFIGURATION"
    CONFIGURATION_NOT_FOUND = "ONEX_CORE_042_CONFIGURATION_NOT_FOUND"
    CONFIGURATION_PARSE_ERROR = "ONEX_CORE_043_CONFIGURATION_PARSE_ERROR"

    # Registry errors (061-080)
    REGISTRY_NOT_FOUND = "ONEX_CORE_061_REGISTRY_NOT_FOUND"
    REGISTRY_INITIALIZATION_FAILED = "ONEX_CORE_062_REGISTRY_INITIALIZATION_FAILED"
    ITEM_NOT_REGISTERED = "ONEX_CORE_063_ITEM_NOT_REGISTERED"
    DUPLICATE_REGISTRATION = "ONEX_CORE_064_DUPLICATE_REGISTRATION"
    REGISTRY_VALIDATION_FAILED = "ONEX_CORE_065_REGISTRY_VALIDATION_FAILED"
    REGISTRY_RESOLUTION_FAILED = "ONEX_CORE_066_REGISTRY_RESOLUTION_FAILED"

    # Runtime errors (081-100)
    OPERATION_FAILED = "ONEX_CORE_081_OPERATION_FAILED"
    TIMEOUT_EXCEEDED = "ONEX_CORE_082_TIMEOUT_EXCEEDED"
    RESOURCE_UNAVAILABLE = "ONEX_CORE_083_RESOURCE_UNAVAILABLE"
    UNSUPPORTED_OPERATION = "ONEX_CORE_084_UNSUPPORTED_OPERATION"
    RESOURCE_NOT_FOUND = "ONEX_CORE_085_RESOURCE_NOT_FOUND"
    INVALID_STATE = "ONEX_CORE_086_INVALID_STATE"
    INITIALIZATION_FAILED = "ONEX_CORE_087_INITIALIZATION_FAILED"
    TIMEOUT = "ONEX_CORE_088_TIMEOUT"  # Add TIMEOUT as alias

    # Test and development errors (101-120)
    TEST_SETUP_FAILED = "ONEX_CORE_101_TEST_SETUP_FAILED"
    TEST_ASSERTION_FAILED = "ONEX_CORE_102_TEST_ASSERTION_FAILED"
    MOCK_CONFIGURATION_ERROR = "ONEX_CORE_103_MOCK_CONFIGURATION_ERROR"
    TEST_DATA_INVALID = "ONEX_CORE_104_TEST_DATA_INVALID"

    # Import and dependency errors (121-140)
    MODULE_NOT_FOUND = "ONEX_CORE_121_MODULE_NOT_FOUND"
    DEPENDENCY_UNAVAILABLE = "ONEX_CORE_122_DEPENDENCY_UNAVAILABLE"
    VERSION_INCOMPATIBLE = "ONEX_CORE_123_VERSION_INCOMPATIBLE"

    # Database errors (131-140)
    DATABASE_CONNECTION_ERROR = "ONEX_CORE_131_DATABASE_CONNECTION_ERROR"
    DATABASE_OPERATION_ERROR = "ONEX_CORE_132_DATABASE_OPERATION_ERROR"
    DATABASE_QUERY_ERROR = "ONEX_CORE_133_DATABASE_QUERY_ERROR"

    # Abstract method and implementation errors (141-160)
    METHOD_NOT_IMPLEMENTED = "ONEX_CORE_141_METHOD_NOT_IMPLEMENTED"
    ABSTRACT_METHOD_CALLED = "ONEX_CORE_142_ABSTRACT_METHOD_CALLED"

    # LLM provider errors (161-180)
    NO_SUITABLE_PROVIDER = "ONEX_CORE_161_NO_SUITABLE_PROVIDER"
    RATE_LIMIT_ERROR = "ONEX_CORE_162_RATE_LIMIT_ERROR"
    AUTHENTICATION_ERROR = "ONEX_CORE_163_AUTHENTICATION_ERROR"
    QUOTA_EXCEEDED = "ONEX_CORE_164_QUOTA_EXCEEDED"
    PROCESSING_ERROR = "ONEX_CORE_165_PROCESSING_ERROR"

    def get_component(self) -> str:
        """Get the component identifier for this error code."""
        return "CORE"

    def get_number(self) -> int:
        """Get the numeric identifier for this error code."""
        # Extract number from error code string (e.g., "ONEX_CORE_001_..." -> 1)
        match = re.search(r"ONEX_CORE_(\d+)_", self.value)
        return int(match.group(1)) if match else 0

    def get_description(self) -> str:
        """Get a human-readable description for this error code."""
        return get_core_error_description(self)

    def get_exit_code(self) -> int:
        """Get the appropriate CLI exit code for this error."""
        return get_exit_code_for_core_error(self)


# Mapping from core error codes to exit codes
CORE_ERROR_CODE_TO_EXIT_CODE: dict[CoreErrorCode, CLIExitCode] = {
    # Validation errors -> ERROR
    CoreErrorCode.INVALID_PARAMETER: CLIExitCode.ERROR,
    CoreErrorCode.MISSING_REQUIRED_PARAMETER: CLIExitCode.ERROR,
    CoreErrorCode.PARAMETER_TYPE_MISMATCH: CLIExitCode.ERROR,
    CoreErrorCode.PARAMETER_OUT_OF_RANGE: CLIExitCode.ERROR,
    CoreErrorCode.VALIDATION_FAILED: CLIExitCode.ERROR,
    CoreErrorCode.VALIDATION_ERROR: CLIExitCode.ERROR,
    CoreErrorCode.INVALID_INPUT: CLIExitCode.ERROR,
    CoreErrorCode.INVALID_OPERATION: CLIExitCode.ERROR,
    # File system errors -> ERROR
    CoreErrorCode.FILE_NOT_FOUND: CLIExitCode.ERROR,
    CoreErrorCode.FILE_READ_ERROR: CLIExitCode.ERROR,
    CoreErrorCode.FILE_WRITE_ERROR: CLIExitCode.ERROR,
    CoreErrorCode.DIRECTORY_NOT_FOUND: CLIExitCode.ERROR,
    CoreErrorCode.PERMISSION_DENIED: CLIExitCode.ERROR,
    CoreErrorCode.FILE_OPERATION_ERROR: CLIExitCode.ERROR,
    # Configuration errors -> ERROR
    CoreErrorCode.INVALID_CONFIGURATION: CLIExitCode.ERROR,
    CoreErrorCode.CONFIGURATION_NOT_FOUND: CLIExitCode.ERROR,
    CoreErrorCode.CONFIGURATION_PARSE_ERROR: CLIExitCode.ERROR,
    # Registry errors -> ERROR
    CoreErrorCode.REGISTRY_NOT_FOUND: CLIExitCode.ERROR,
    CoreErrorCode.REGISTRY_INITIALIZATION_FAILED: CLIExitCode.ERROR,
    CoreErrorCode.ITEM_NOT_REGISTERED: CLIExitCode.ERROR,
    CoreErrorCode.DUPLICATE_REGISTRATION: CLIExitCode.WARNING,
    # Runtime errors -> ERROR
    CoreErrorCode.OPERATION_FAILED: CLIExitCode.ERROR,
    CoreErrorCode.TIMEOUT_EXCEEDED: CLIExitCode.ERROR,
    CoreErrorCode.RESOURCE_UNAVAILABLE: CLIExitCode.ERROR,
    CoreErrorCode.UNSUPPORTED_OPERATION: CLIExitCode.ERROR,
    CoreErrorCode.RESOURCE_NOT_FOUND: CLIExitCode.ERROR,
    CoreErrorCode.INVALID_STATE: CLIExitCode.ERROR,
    CoreErrorCode.INITIALIZATION_FAILED: CLIExitCode.ERROR,
    CoreErrorCode.TIMEOUT: CLIExitCode.ERROR,
    # Database errors -> ERROR
    CoreErrorCode.DATABASE_CONNECTION_ERROR: CLIExitCode.ERROR,
    CoreErrorCode.DATABASE_OPERATION_ERROR: CLIExitCode.ERROR,
    CoreErrorCode.DATABASE_QUERY_ERROR: CLIExitCode.ERROR,
    # LLM provider errors -> ERROR
    CoreErrorCode.NO_SUITABLE_PROVIDER: CLIExitCode.ERROR,
    CoreErrorCode.RATE_LIMIT_ERROR: CLIExitCode.ERROR,
    CoreErrorCode.AUTHENTICATION_ERROR: CLIExitCode.ERROR,
    CoreErrorCode.QUOTA_EXCEEDED: CLIExitCode.ERROR,
    CoreErrorCode.PROCESSING_ERROR: CLIExitCode.ERROR,
}


def get_exit_code_for_core_error(error_code: CoreErrorCode) -> int:
    """
    Get the appropriate CLI exit code for a core error code.

    Args:
        error_code: The CoreErrorCode to map

    Returns:
        The corresponding CLI exit code (integer)
    """
    return CORE_ERROR_CODE_TO_EXIT_CODE.get(error_code, CLIExitCode.ERROR).value


def get_core_error_description(error_code: CoreErrorCode) -> str:
    """
    Get a human-readable description for a core error code.

    Args:
        error_code: The CoreErrorCode to describe

    Returns:
        A human-readable description of the error
    """
    descriptions = {
        CoreErrorCode.INVALID_PARAMETER: "Invalid parameter value",
        CoreErrorCode.MISSING_REQUIRED_PARAMETER: "Required parameter missing",
        CoreErrorCode.PARAMETER_TYPE_MISMATCH: "Parameter type mismatch",
        CoreErrorCode.PARAMETER_OUT_OF_RANGE: "Parameter value out of range",
        CoreErrorCode.VALIDATION_FAILED: "Validation failed",
        CoreErrorCode.VALIDATION_ERROR: "Validation error occurred",
        CoreErrorCode.INVALID_INPUT: "Invalid input provided",
        CoreErrorCode.INVALID_OPERATION: "Invalid operation requested",
        CoreErrorCode.FILE_NOT_FOUND: "File not found",
        CoreErrorCode.FILE_READ_ERROR: "Cannot read file",
        CoreErrorCode.FILE_WRITE_ERROR: "Cannot write file",
        CoreErrorCode.DIRECTORY_NOT_FOUND: "Directory not found",
        CoreErrorCode.PERMISSION_DENIED: "Permission denied",
        CoreErrorCode.FILE_OPERATION_ERROR: "File operation failed",
        CoreErrorCode.INVALID_CONFIGURATION: "Invalid configuration",
        CoreErrorCode.CONFIGURATION_NOT_FOUND: "Configuration not found",
        CoreErrorCode.CONFIGURATION_PARSE_ERROR: "Configuration parse error",
        CoreErrorCode.REGISTRY_NOT_FOUND: "Registry not found",
        CoreErrorCode.REGISTRY_INITIALIZATION_FAILED: "Registry initialization failed",
        CoreErrorCode.ITEM_NOT_REGISTERED: "Item not registered",
        CoreErrorCode.DUPLICATE_REGISTRATION: "Duplicate registration",
        CoreErrorCode.OPERATION_FAILED: "Operation failed",
        CoreErrorCode.TIMEOUT_EXCEEDED: "Timeout exceeded",
        CoreErrorCode.RESOURCE_UNAVAILABLE: "Resource unavailable",
        CoreErrorCode.UNSUPPORTED_OPERATION: "Unsupported operation",
        CoreErrorCode.RESOURCE_NOT_FOUND: "Resource not found",
        CoreErrorCode.INVALID_STATE: "Invalid state",
        CoreErrorCode.INITIALIZATION_FAILED: "Initialization failed",
        CoreErrorCode.TIMEOUT: "Operation timed out",
        CoreErrorCode.DATABASE_CONNECTION_ERROR: "Database connection failed",
        CoreErrorCode.DATABASE_OPERATION_ERROR: "Database operation failed",
        CoreErrorCode.DATABASE_QUERY_ERROR: "Database query failed",
        CoreErrorCode.NO_SUITABLE_PROVIDER: "No suitable provider available",
        CoreErrorCode.RATE_LIMIT_ERROR: "Rate limit exceeded",
        CoreErrorCode.AUTHENTICATION_ERROR: "Authentication failed",
        CoreErrorCode.QUOTA_EXCEEDED: "Quota exceeded",
        CoreErrorCode.PROCESSING_ERROR: "Processing error",
    }
    return descriptions.get(error_code, "Unknown error")


class ModelOnexError(BaseModel):
    """
    Pydantic model for ONEX error serialization and validation.

    This model provides structured error information with validation,
    serialization, and schema generation capabilities.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "File not found: config.yaml",
                "error_code": "ONEX_CORE_021_FILE_NOT_FOUND",
                "status": "error",
                "correlation_id": "req-123e4567-e89b-12d3-a456-426614174000",
                "timestamp": "2025-05-25T22:30:00Z",
                "context": {"file_path": "/path/to/config.yaml"},
            },
        },
    )

    message: str = Field(
        ...,
        description="Human-readable error message",
        json_schema_extra={"example": "File not found: config.yaml"},
    )
    error_code: str | OnexErrorCode | None = Field(
        default=None,
        description="Canonical error code for this error",
        json_schema_extra={"example": "ONEX_CORE_021_FILE_NOT_FOUND"},
    )
    status: EnumOnexStatus = Field(
        default=EnumOnexStatus.ERROR,
        description="EnumOnexStatus for this error",
        json_schema_extra={"example": "error"},
    )
    correlation_id: str | None = Field(
        default=None,
        description="Optional correlation ID for request tracking",
        json_schema_extra={"example": "req-123e4567-e89b-12d3-a456-426614174000"},
    )
    timestamp: datetime | None = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the error occurred",
        json_schema_extra={"example": "2025-05-25T22:30:00Z"},
    )
    context: dict[str, str | int | bool | float] = Field(
        default_factory=dict,
        description="Additional context information for the error",
        json_schema_extra={"example": {"file_path": "/path/to/config.yaml"}},
    )


class ModelOnexWarning(BaseModel):
    """
    Pydantic model for ONEX warning serialization and validation.

    This model provides structured warning information with validation,
    serialization, and schema generation capabilities.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "File already exists and will be overwritten: config.yaml",
                "warning_code": "ONEX_CORE_W001_FILE_OVERWRITE",
                "status": "warning",
                "correlation_id": "req-123e4567-e89b-12d3-a456-426614174000",
                "timestamp": "2025-05-25T22:30:00Z",
                "context": {"file_path": "/path/to/config.yaml"},
            },
        },
    )

    message: str = Field(
        ...,
        description="Human-readable warning message",
        json_schema_extra={
            "example": "File already exists and will be overwritten: config.yaml",
        },
    )
    warning_code: str | None = Field(
        default=None,
        description="Canonical warning code for this warning",
        json_schema_extra={"example": "ONEX_CORE_W001_FILE_OVERWRITE"},
    )
    status: EnumOnexStatus = Field(
        default=EnumOnexStatus.WARNING,
        description="EnumOnexStatus for this warning",
        json_schema_extra={"example": "warning"},
    )
    correlation_id: str | None = Field(
        default=None,
        description="Optional correlation ID for request tracking",
        json_schema_extra={"example": "req-123e4567-e89b-12d3-a456-426614174000"},
    )
    timestamp: datetime | None = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the warning occurred",
        json_schema_extra={"example": "2025-05-25T22:30:00Z"},
    )
    context: dict[str, str | int | bool | float] = Field(
        default_factory=dict,
        description="Additional context information for the warning",
        json_schema_extra={"example": {"file_path": "/path/to/config.yaml"}},
    )


class OnexError(Exception):
    """
    Exception class for ONEX errors with Pydantic model integration.

    This class combines standard Python exception behavior with Pydantic
    model features through composition, providing validation, serialization,
    and schema generation while maintaining exception compatibility.

    All ONEX nodes should use this or subclasses for error handling
    to ensure consistent error reporting and CLI exit code mapping.
    """

    def __init__(
        self,
        message: str,
        error_code: OnexErrorCode | str | None = None,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        correlation_id: str | UUID | None = None,
        timestamp: datetime | None = None,
        **context: str | int | bool | float,
    ) -> None:
        """
        Initialize an ONEX error with error code and status.

        Entry point pattern: If correlation_id is not provided, generates a new one.
        Accepts both string and UUID correlation IDs for convenience.

        Args:
            message: Human-readable error message
            error_code: Canonical error code (optional)
            status: EnumOnexStatus for this error (default: ERROR)
            correlation_id: Correlation ID for tracking (auto-generated if not provided)
            timestamp: Optional timestamp (defaults to current time)
            **context: Additional context information
        """
        # Initialize the Exception
        super().__init__(message)

        # Handle correlation ID using UUID architecture pattern
        if correlation_id is None:
            # Entry point pattern: Generate new UUID if not provided
            final_correlation_id = str(UUIDService.generate_correlation_id())
        elif isinstance(correlation_id, UUID):
            final_correlation_id = str(correlation_id)
        elif isinstance(correlation_id, str):
            # Validate string UUIDs
            try:
                # Will raise ValueError if invalid UUID format
                validated_uuid = UUIDService.from_string(correlation_id)
                final_correlation_id = str(validated_uuid)
            except ValueError:
                # If string is not a valid UUID, generate a new one
                final_correlation_id = str(UUIDService.generate_correlation_id())
        else:
            # Invalid type, generate new UUID
            final_correlation_id = str(UUIDService.generate_correlation_id())

        # Create the Pydantic model for structured data
        # Check if ModelOnexError expects ModelErrorContext (newer version) or dict (older version)
        try:
            # Try to import ModelErrorContext to detect if we're using the newer ModelOnexError
            from omnibase_core.model.core.model_error_context import ModelErrorContext

            # Convert dictionary context to ModelErrorContext for new ModelOnexError
            if isinstance(context, dict):
                context_model = ModelErrorContext.from_dict(context)
            else:
                context_model = context or ModelErrorContext()

            # Use newer ModelOnexError from model package
            from omnibase_core.model.core.model_onex_error import (
                ModelOnexError as NewModelOnexError,
            )

            self.model = NewModelOnexError(
                message=message,
                error_code=error_code,
                status=status,
                correlation_id=final_correlation_id,
                timestamp=timestamp or datetime.utcnow(),
                context=context_model,
            )
        except ImportError:
            # Fall back to older ModelOnexError that expects dict context
            self.model = ModelOnexError(
                message=message,
                error_code=error_code,
                status=status,
                correlation_id=final_correlation_id,
                timestamp=timestamp or datetime.utcnow(),
                context=context,
            )

    @classmethod
    def with_correlation_id(
        cls,
        message: str,
        correlation_id: UUID,
        error_code: OnexErrorCode | str | None = None,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        timestamp: datetime | None = None,
        **context: str | int | bool | float,
    ) -> "OnexError":
        """
        Create an OnexError with a guaranteed UUID correlation ID.

        This method follows the UUID architecture pattern for internal processing
        where correlation IDs are already available and guaranteed to be UUIDs.

        Args:
            message: Human-readable error message
            correlation_id: Correlation ID as UUID (required)
            error_code: Canonical error code (optional)
            status: EnumOnexStatus for this error (default: ERROR)
            timestamp: Optional timestamp (defaults to current time)
            **context: Additional context information

        Returns:
            OnexError: New error instance with guaranteed UUID correlation ID
        """
        return cls(
            message=message,
            error_code=error_code,
            status=status,
            correlation_id=correlation_id,
            timestamp=timestamp,
            **context,
        )

    @classmethod
    def with_new_correlation_id(
        cls,
        message: str,
        error_code: OnexErrorCode | str | None = None,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        timestamp: datetime | None = None,
        **context: str | int | bool | float,
    ) -> tuple["OnexError", UUID]:
        """
        Create an OnexError with a new generated correlation ID.

        Convenience method that generates a new correlation ID and returns
        both the error and the generated UUID for use in subsequent operations.

        Args:
            message: Human-readable error message
            error_code: Canonical error code (optional)
            status: EnumOnexStatus for this error (default: ERROR)
            timestamp: Optional timestamp (defaults to current time)
            **context: Additional context information

        Returns:
            tuple[OnexError, UUID]: Error instance and generated correlation ID
        """
        correlation_id = UUIDService.generate_correlation_id()
        error = cls(
            message=message,
            error_code=error_code,
            status=status,
            correlation_id=correlation_id,
            timestamp=timestamp,
            **context,
        )
        return error, correlation_id

    @property
    def message(self) -> str:
        """Get the error message."""
        return self.model.message

    @property
    def error_code(self) -> str | OnexErrorCode | None:
        """Get the error code."""
        return self.model.error_code

    @property
    def status(self) -> EnumOnexStatus:
        """Get the error status."""
        return self.model.status

    @property
    def correlation_id(self) -> str | None:
        """Get the correlation ID."""
        return self.model.correlation_id

    @property
    def timestamp(self) -> datetime | None:
        """Get the timestamp."""
        return self.model.timestamp

    @property
    def context(self) -> dict[str, str | int | bool | float]:
        """Get the context information."""
        # Handle both old dict format and new ModelErrorContext format
        if hasattr(self.model.context, "to_dict"):
            # New ModelErrorContext format
            return self.model.context.to_dict()
        # Old dict format
        return self.model.context

    def get_exit_code(self) -> int:
        """Get the appropriate CLI exit code for this error."""
        if isinstance(self.error_code, OnexErrorCode):
            return self.error_code.get_exit_code()
        return get_exit_code_for_status(self.status)

    def __str__(self) -> str:
        """String representation including error code if available."""
        if self.error_code:
            # Use .value to get the string value for OnexErrorCode enums
            error_code_str = (
                self.error_code.value
                if hasattr(self.error_code, "value")
                else str(self.error_code)
            )
            return f"[{error_code_str}] {self.message}"
        return self.message

    def model_dump(self) -> dict[str, str | int | bool | float]:
        """Convert error to dictionary for serialization."""
        return self.model.model_dump()

    def model_dump_json(self) -> str:
        """Convert error to JSON string for logging/telemetry."""
        return self.model.model_dump_json()

    def to_dict(self) -> dict[str, str | int | bool | float]:
        """Convert error to dictionary for serialization (alias for model_dump)."""
        return self.model_dump()

    def to_json(self) -> str:
        """Convert error to JSON string for logging/telemetry (alias for model_dump_json)."""
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: dict[str, str | int | bool | float]) -> "OnexError":
        """Create OnexError from dictionary."""
        model = ModelOnexError.model_validate(data)
        return cls(
            message=model.message,
            error_code=model.error_code,
            status=model.status,
            correlation_id=model.correlation_id,
            timestamp=model.timestamp,
            **model.context,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "OnexError":
        """Create OnexError from JSON string."""
        model = ModelOnexError.model_validate_json(json_str)
        return cls(
            message=model.message,
            error_code=model.error_code,
            status=model.status,
            correlation_id=model.correlation_id,
            timestamp=model.timestamp,
            **model.context,
        )

    @classmethod
    def model_json_schema(cls) -> dict[str, str | int | bool | float]:
        """Get the JSON schema for OnexError."""
        return ModelOnexError.model_json_schema()


class CLIAdapter:
    """
    Base CLI adapter class that provides consistent exit code handling.

    All CLI adapters should inherit from this class or implement similar
    exit code mapping functionality.
    """

    @staticmethod
    def exit_with_status(status: EnumOnexStatus, message: str = "") -> None:
        """
        Exit the CLI with the appropriate exit code for the given status.

        Args:
            status: The EnumOnexStatus to map to an exit code
            message: Optional message to print before exiting
        """
        import sys

        from omnibase_core.core.core_bootstrap import emit_log_event_sync
        from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

        exit_code = get_exit_code_for_status(status)

        if message:
            if status in (EnumOnexStatus.ERROR, EnumOnexStatus.UNKNOWN):
                emit_log_event_sync(
                    level=LogLevel.ERROR,
                    message=message,
                    event_type="cli_exit_error",
                    data={"status": status.value, "exit_code": exit_code},
                )
            elif status == EnumOnexStatus.WARNING:
                emit_log_event_sync(
                    level=LogLevel.WARNING,
                    message=message,
                    event_type="cli_exit_warning",
                    data={"status": status.value, "exit_code": exit_code},
                )
            else:
                emit_log_event_sync(
                    level=LogLevel.INFO,
                    message=message,
                    event_type="cli_exit_info",
                    data={"status": status.value, "exit_code": exit_code},
                )

        sys.exit(exit_code)

    @staticmethod
    def exit_with_error(error: OnexError) -> None:
        """
        Exit the CLI with the appropriate exit code for the given error.

        Args:
            error: The OnexError to handle
        """
        import sys

        from omnibase_core.core.core_bootstrap import emit_log_event_sync
        from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

        exit_code = error.get_exit_code()
        emit_log_event_sync(
            level=LogLevel.ERROR,
            message=str(error),
            event_type="cli_exit_with_error",
            correlation_id=error.correlation_id,
            data={
                "error_code": str(error.error_code) if error.error_code else None,
                "exit_code": exit_code,
                "context": error.context,
            },
        )
        sys.exit(exit_code)


# Registry for component-specific error code mappings
_ERROR_CODE_REGISTRIES: dict[str, type[OnexErrorCode]] = {}


def register_error_codes(component: str, error_code_enum: type[OnexErrorCode]) -> None:
    """
    Register error codes for a specific component.

    Args:
        component: Component identifier (e.g., "stamper", "validator")
        error_code_enum: Error code enum class for the component
    """
    _ERROR_CODE_REGISTRIES[component] = error_code_enum


def get_error_codes_for_component(component: str) -> type[OnexErrorCode]:
    """
    Get the error code enum for a specific component.

    Args:
        component: Component identifier

    Returns:
        The error code enum class for the component

    Raises:
        OnexError: If component is not registered
    """
    if component not in _ERROR_CODE_REGISTRIES:
        msg = f"No error codes registered for component: {component}"
        raise OnexError(
            msg,
            CoreErrorCode.ITEM_NOT_REGISTERED,
        )
    return _ERROR_CODE_REGISTRIES[component]


def list_registered_components() -> list[str]:
    """
    List all registered component identifiers.

    Returns:
        List of component identifiers that have registered error codes
    """
    return list(_ERROR_CODE_REGISTRIES.keys())


class RegistryErrorCode(OnexErrorCode):
    """
    Canonical error codes for ONEX tool/handler registries.
    Use these for all registry-driven error handling (tool not found, duplicate, etc.).
    """

    TOOL_NOT_FOUND = "ONEX_REGISTRY_001_TOOL_NOT_FOUND"
    DUPLICATE_TOOL = "ONEX_REGISTRY_002_DUPLICATE_TOOL"
    INVALID_MODE = "ONEX_REGISTRY_003_INVALID_MODE"
    REGISTRY_UNAVAILABLE = "ONEX_REGISTRY_004_REGISTRY_UNAVAILABLE"

    def get_component(self) -> str:
        return "REGISTRY"

    def get_number(self) -> int:
        match = re.search(r"ONEX_REGISTRY_(\d+)_", self.value)
        return int(match.group(1)) if match else 0

    def get_description(self) -> str:
        descriptions = {
            self.TOOL_NOT_FOUND: "Requested tool is not registered in the registry.",
            self.DUPLICATE_TOOL: "A tool with this name is already registered.",
            self.INVALID_MODE: "The requested registry mode is invalid or unsupported.",
            self.REGISTRY_UNAVAILABLE: "The registry is unavailable or not initialized.",
        }
        return descriptions.get(self, "Unknown registry error.")

    def get_exit_code(self) -> int:
        return CLIExitCode.ERROR.value


class RegistryErrorModel(ModelOnexError):
    """
    Canonical error model for registry errors (tool/handler registries).
    Use this for all structured registry error reporting.
    """

    error_code: RegistryErrorCode = Field(
        ...,
        description="Canonical registry error code.",
    )
