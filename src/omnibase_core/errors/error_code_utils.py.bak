"""Error Code Utilities.

Utility functions for error code and exit code mapping.
"""

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.enums.enum_registry_error_code import EnumOnexErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Global mapping from EnumOnexStatus to CLI exit codes
STATUS_TO_EXIT_CODE: dict[EnumOnexStatus, EnumCLIExitCode] = {
    EnumOnexStatus.SUCCESS: EnumCLIExitCode.SUCCESS,
    EnumOnexStatus.ERROR: EnumCLIExitCode.ERROR,
    EnumOnexStatus.WARNING: EnumCLIExitCode.WARNING,
    EnumOnexStatus.PARTIAL: EnumCLIExitCode.PARTIAL,
    EnumOnexStatus.SKIPPED: EnumCLIExitCode.SKIPPED,
    EnumOnexStatus.FIXED: EnumCLIExitCode.FIXED,
    EnumOnexStatus.INFO: EnumCLIExitCode.INFO,
    EnumOnexStatus.UNKNOWN: EnumCLIExitCode.ERROR,  # Treat unknown as error
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
    return STATUS_TO_EXIT_CODE.get(status, EnumCLIExitCode.ERROR).value


# Mapping from core error codes to exit codes
CORE_ERROR_CODE_TO_EXIT_CODE: dict[EnumCoreErrorCode, EnumCLIExitCode] = {
    # Validation errors -> ERROR
    EnumCoreErrorCode.INVALID_PARAMETER: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.MISSING_REQUIRED_PARAMETER: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.PARAMETER_OUT_OF_RANGE: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.VALIDATION_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.VALIDATION_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.INVALID_INPUT: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.INVALID_OPERATION: EnumCLIExitCode.ERROR,
    # File system errors -> ERROR
    EnumCoreErrorCode.FILE_NOT_FOUND: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.FILE_READ_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.FILE_WRITE_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.DIRECTORY_NOT_FOUND: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.PERMISSION_DENIED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.FILE_OPERATION_ERROR: EnumCLIExitCode.ERROR,
    # Configuration errors -> ERROR
    EnumCoreErrorCode.INVALID_CONFIGURATION: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.CONFIGURATION_NOT_FOUND: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR: EnumCLIExitCode.ERROR,
    # Registry errors -> ERROR
    EnumCoreErrorCode.REGISTRY_NOT_FOUND: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.REGISTRY_INITIALIZATION_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.ITEM_NOT_REGISTERED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.DUPLICATE_REGISTRATION: EnumCLIExitCode.WARNING,
    # Runtime errors -> ERROR
    EnumCoreErrorCode.OPERATION_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.TIMEOUT_EXCEEDED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.RESOURCE_UNAVAILABLE: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.UNSUPPORTED_OPERATION: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.RESOURCE_NOT_FOUND: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.INVALID_STATE: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.INITIALIZATION_FAILED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.TIMEOUT: EnumCLIExitCode.ERROR,
    # Database errors -> ERROR
    EnumCoreErrorCode.DATABASE_CONNECTION_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.DATABASE_OPERATION_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.DATABASE_QUERY_ERROR: EnumCLIExitCode.ERROR,
    # LLM provider errors -> ERROR
    EnumCoreErrorCode.NO_SUITABLE_PROVIDER: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.RATE_LIMIT_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.AUTHENTICATION_ERROR: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.QUOTA_EXCEEDED: EnumCLIExitCode.ERROR,
    EnumCoreErrorCode.PROCESSING_ERROR: EnumCLIExitCode.ERROR,
}


def get_exit_code_for_core_error(error_code: EnumCoreErrorCode) -> int:
    """
    Get the appropriate CLI exit code for a core error code.

    Args:
        error_code: The EnumCoreErrorCode to map

    Returns:
        The corresponding CLI exit code (integer)
    """
    return CORE_ERROR_CODE_TO_EXIT_CODE.get(error_code, EnumCLIExitCode.ERROR).value


def get_core_error_description(error_code: EnumCoreErrorCode) -> str:
    """
    Get a human-readable description for a core error code.

    Args:
        error_code: The EnumCoreErrorCode to describe

    Returns:
        A human-readable description of the error
    """
    descriptions = {
        EnumCoreErrorCode.INVALID_PARAMETER: "Invalid parameter value",
        EnumCoreErrorCode.MISSING_REQUIRED_PARAMETER: "Required parameter missing",
        EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH: "Parameter type mismatch",
        EnumCoreErrorCode.PARAMETER_OUT_OF_RANGE: "Parameter value out of range",
        EnumCoreErrorCode.VALIDATION_FAILED: "Validation failed",
        EnumCoreErrorCode.VALIDATION_ERROR: "Validation error occurred",
        EnumCoreErrorCode.INVALID_INPUT: "Invalid input provided",
        EnumCoreErrorCode.INVALID_OPERATION: "Invalid operation requested",
        EnumCoreErrorCode.FILE_NOT_FOUND: "File not found",
        EnumCoreErrorCode.FILE_READ_ERROR: "Cannot read file",
        EnumCoreErrorCode.FILE_WRITE_ERROR: "Cannot write file",
        EnumCoreErrorCode.DIRECTORY_NOT_FOUND: "Directory not found",
        EnumCoreErrorCode.PERMISSION_DENIED: "Permission denied",
        EnumCoreErrorCode.FILE_OPERATION_ERROR: "File operation failed",
        EnumCoreErrorCode.INVALID_CONFIGURATION: "Invalid configuration",
        EnumCoreErrorCode.CONFIGURATION_NOT_FOUND: "Configuration not found",
        EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR: "Configuration parse error",
        EnumCoreErrorCode.REGISTRY_NOT_FOUND: "Registry not found",
        EnumCoreErrorCode.REGISTRY_INITIALIZATION_FAILED: "Registry initialization failed",
        EnumCoreErrorCode.ITEM_NOT_REGISTERED: "Item not registered",
        EnumCoreErrorCode.DUPLICATE_REGISTRATION: "Duplicate registration",
        EnumCoreErrorCode.OPERATION_FAILED: "Operation failed",
        EnumCoreErrorCode.TIMEOUT_EXCEEDED: "Timeout exceeded",
        EnumCoreErrorCode.RESOURCE_UNAVAILABLE: "Resource unavailable",
        EnumCoreErrorCode.UNSUPPORTED_OPERATION: "Unsupported operation",
        EnumCoreErrorCode.RESOURCE_NOT_FOUND: "Resource not found",
        EnumCoreErrorCode.INVALID_STATE: "Invalid state",
        EnumCoreErrorCode.INITIALIZATION_FAILED: "Initialization failed",
        EnumCoreErrorCode.TIMEOUT: "Operation timed out",
        EnumCoreErrorCode.DATABASE_CONNECTION_ERROR: "Database connection failed",
        EnumCoreErrorCode.DATABASE_OPERATION_ERROR: "Database operation failed",
        EnumCoreErrorCode.DATABASE_QUERY_ERROR: "Database query failed",
        EnumCoreErrorCode.NO_SUITABLE_PROVIDER: "No suitable provider available",
        EnumCoreErrorCode.RATE_LIMIT_ERROR: "Rate limit exceeded",
        EnumCoreErrorCode.AUTHENTICATION_ERROR: "Authentication failed",
        EnumCoreErrorCode.QUOTA_EXCEEDED: "Quota exceeded",
        EnumCoreErrorCode.PROCESSING_ERROR: "Processing error",
        EnumCoreErrorCode.INTELLIGENCE_PROCESSING_FAILED: "Intelligence processing failed",
        EnumCoreErrorCode.PATTERN_RECOGNITION_FAILED: "Pattern recognition failed",
        EnumCoreErrorCode.CONTEXT_ANALYSIS_FAILED: "Context analysis failed",
        EnumCoreErrorCode.LEARNING_ENGINE_FAILED: "Learning engine failed",
        EnumCoreErrorCode.INTELLIGENCE_COORDINATION_FAILED: "Intelligence coordination failed",
        EnumCoreErrorCode.SYSTEM_HEALTH_DEGRADED: "System health degraded",
        EnumCoreErrorCode.SERVICE_START_FAILED: "Service start failed",
        EnumCoreErrorCode.SERVICE_STOP_FAILED: "Service stop failed",
        EnumCoreErrorCode.SECURITY_REPORT_FAILED: "Security report failed",
        EnumCoreErrorCode.SECURITY_VIOLATION: "Security violation",
        EnumCoreErrorCode.EVENT_PROCESSING_FAILED: "Event processing failed",
    }
    return descriptions.get(error_code, "Unknown error")


# Registry for component-specific error code mappings
_ERROR_CODE_REGISTRIES: dict[str, type[EnumOnexErrorCode]] = {}


def register_error_codes(
    component: str, error_code_enum: type[EnumOnexErrorCode]
) -> None:
    """
    Register error codes for a specific component.

    Args:
        component: Component identifier (e.g., "stamper", "validator")
        error_code_enum: Error code enum class for the component
    """
    _ERROR_CODE_REGISTRIES[component] = error_code_enum


def get_error_codes_for_component(component: str) -> type[EnumOnexErrorCode]:
    """
    Get the error code enum for a specific component.

    Args:
        component: Component identifier

    Returns:
        The error code enum class for the component

    Raises:
        ModelOnexError: If component is not registered
    """
    if component not in _ERROR_CODE_REGISTRIES:
        msg = f"No error codes registered for component: {component}"
        raise ModelOnexError(
            message=msg,
            error_code=EnumCoreErrorCode.ITEM_NOT_REGISTERED,
        )
    return _ERROR_CODE_REGISTRIES[component]


def list_registered_components() -> list[str]:
    """
    List all registered component identifiers.

    Returns:
        List of component identifiers that have registered error codes
    """
    return list(_ERROR_CODE_REGISTRIES.keys())


__all__ = [
    "STATUS_TO_EXIT_CODE",
    "CORE_ERROR_CODE_TO_EXIT_CODE",
    "get_exit_code_for_status",
    "get_exit_code_for_core_error",
    "get_core_error_description",
    "register_error_codes",
    "get_error_codes_for_component",
    "list_registered_components",
]
