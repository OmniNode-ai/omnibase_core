# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:25.416682'
# description: Stamped by ToolPython
# entrypoint: python://core_error_codes
# hash: 458401b2a864609be1f0d1a144b8d68e7183caafc603bf90a6fa2d5a9877196f
# last_modified_at: '2025-05-29T14:13:58.411741+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: core_error_codes.py
# namespace: python://omnibase.core.core_error_codes
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: e5028d69-3575-43b8-8691-6ce5b343b43b
# version: 1.0.0
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
from collections.abc import Mapping
from enum import Enum
from pathlib import Path

from omnibase_core.enums.enum_onex_status import EnumOnexStatus

# Model imports moved to be local to avoid circular dependencies


# Component identifier for logging
_COMPONENT_NAME = Path(__file__).stem


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
STATUS_TO_EXIT_CODE: Mapping[EnumOnexStatus, CLIExitCode] = {
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

    This is the canonical function for mapping OnexStatus values to CLI exit codes
    across all ONEX nodes and tools.

    Args:
        status: The OnexStatus to map

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
        # Parse component from the enum value format: ONEX_<COMPONENT>_<NUMBER>_<DESCRIPTION>
        parts = str(self.value).split("_")
        if len(parts) >= 3 and parts[0] == "ONEX":
            return str(parts[1])
        return "UNKNOWN"

    def get_number(self) -> int:
        """Get the numeric identifier for this error code."""
        # Parse number from the enum value format: ONEX_<COMPONENT>_<NUMBER>_<DESCRIPTION>
        parts = self.value.split("_")
        if len(parts) >= 3 and parts[0] == "ONEX":
            try:
                return int(parts[2])
            except ValueError:
                return 0
        return 0

    def get_description(self) -> str:
        """Get a human-readable description for this error code."""
        # Parse description from the enum value format: ONEX_<COMPONENT>_<NUMBER>_<DESCRIPTION>
        parts = self.value.split("_")
        if len(parts) >= 4 and parts[0] == "ONEX":
            # Join the remaining parts as the description
            return str("_".join(parts[3:]).replace("_", " ").title())
        return str(self.value)

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

    # File system errors (021-040)
    FILE_NOT_FOUND = "ONEX_CORE_021_FILE_NOT_FOUND"
    FILE_READ_ERROR = "ONEX_CORE_022_FILE_READ_ERROR"
    FILE_WRITE_ERROR = "ONEX_CORE_023_FILE_WRITE_ERROR"
    DIRECTORY_NOT_FOUND = "ONEX_CORE_024_DIRECTORY_NOT_FOUND"
    PERMISSION_DENIED = "ONEX_CORE_025_PERMISSION_DENIED"

    # Configuration errors (041-060)
    INVALID_CONFIGURATION = "ONEX_CORE_041_INVALID_CONFIGURATION"
    CONFIGURATION_NOT_FOUND = "ONEX_CORE_042_CONFIGURATION_NOT_FOUND"
    CONFIGURATION_PARSE_ERROR = "ONEX_CORE_043_CONFIGURATION_PARSE_ERROR"

    # Registry errors (061-080)
    REGISTRY_NOT_FOUND = "ONEX_CORE_061_REGISTRY_NOT_FOUND"
    REGISTRY_INITIALIZATION_FAILED = "ONEX_CORE_062_REGISTRY_INITIALIZATION_FAILED"
    ITEM_NOT_REGISTERED = "ONEX_CORE_063_ITEM_NOT_REGISTERED"
    DUPLICATE_REGISTRATION = "ONEX_CORE_064_DUPLICATE_REGISTRATION"

    # Runtime errors (081-100)
    OPERATION_FAILED = "ONEX_CORE_081_OPERATION_FAILED"
    TIMEOUT_EXCEEDED = "ONEX_CORE_082_TIMEOUT_EXCEEDED"
    RESOURCE_UNAVAILABLE = "ONEX_CORE_083_RESOURCE_UNAVAILABLE"
    UNSUPPORTED_OPERATION = "ONEX_CORE_084_UNSUPPORTED_OPERATION"
    RESOURCE_NOT_FOUND = "ONEX_CORE_085_RESOURCE_NOT_FOUND"
    INVALID_STATE = "ONEX_CORE_086_INVALID_STATE"
    RESOURCE_EXHAUSTED = "ONEX_CORE_087_RESOURCE_EXHAUSTED"
    DATABASE_CONNECTION_FAILED = "ONEX_CORE_088_DATABASE_CONNECTION_FAILED"
    DATABASE_OPERATION_FAILED = "ONEX_CORE_089_DATABASE_OPERATION_FAILED"
    SERVICE_INITIALIZATION_FAILED = "ONEX_CORE_090_SERVICE_INITIALIZATION_FAILED"
    SERVICE_RESOLUTION_FAILED = "ONEX_CORE_091_SERVICE_RESOLUTION_FAILED"

    # Test and development errors (101-120)
    TEST_SETUP_FAILED = "ONEX_CORE_101_TEST_SETUP_FAILED"
    TEST_ASSERTION_FAILED = "ONEX_CORE_102_TEST_ASSERTION_FAILED"
    MOCK_CONFIGURATION_ERROR = "ONEX_CORE_103_MOCK_CONFIGURATION_ERROR"
    TEST_DATA_INVALID = "ONEX_CORE_104_TEST_DATA_INVALID"

    # Import and dependency errors (121-140)
    MODULE_NOT_FOUND = "ONEX_CORE_121_MODULE_NOT_FOUND"
    DEPENDENCY_UNAVAILABLE = "ONEX_CORE_122_DEPENDENCY_UNAVAILABLE"
    VERSION_INCOMPATIBLE = "ONEX_CORE_123_VERSION_INCOMPATIBLE"

    # Abstract method and implementation errors (141-160)
    METHOD_NOT_IMPLEMENTED = "ONEX_CORE_141_METHOD_NOT_IMPLEMENTED"
    ABSTRACT_METHOD_CALLED = "ONEX_CORE_142_ABSTRACT_METHOD_CALLED"

    # Intelligence processing errors (161-180)
    INTELLIGENCE_PROCESSING_FAILED = "ONEX_CORE_161_INTELLIGENCE_PROCESSING_FAILED"
    PATTERN_RECOGNITION_FAILED = "ONEX_CORE_162_PATTERN_RECOGNITION_FAILED"
    CONTEXT_ANALYSIS_FAILED = "ONEX_CORE_163_CONTEXT_ANALYSIS_FAILED"
    LEARNING_ENGINE_FAILED = "ONEX_CORE_164_LEARNING_ENGINE_FAILED"
    INTELLIGENCE_COORDINATION_FAILED = "ONEX_CORE_165_INTELLIGENCE_COORDINATION_FAILED"

    # System health errors (181-200)
    SYSTEM_HEALTH_DEGRADED = "ONEX_CORE_181_SYSTEM_HEALTH_DEGRADED"
    SERVICE_START_FAILED = "ONEX_CORE_182_SERVICE_START_FAILED"
    SERVICE_STOP_FAILED = "ONEX_CORE_183_SERVICE_STOP_FAILED"
    INITIALIZATION_FAILED = "ONEX_CORE_184_INITIALIZATION_FAILED"
    SECURITY_REPORT_FAILED = "ONEX_CORE_185_SECURITY_REPORT_FAILED"
    SECURITY_VIOLATION = "ONEX_CORE_186_SECURITY_VIOLATION"
    EVENT_PROCESSING_FAILED = "ONEX_CORE_187_EVENT_PROCESSING_FAILED"

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

    @property
    def exit_code(self) -> int:
        """Get the CLI exit code for this error code (enum property)."""
        return get_exit_code_for_core_error(self)


# Mapping from core error codes to exit codes
CORE_ERROR_CODE_TO_EXIT_CODE: Mapping[CoreErrorCode, CLIExitCode] = {
    # Validation errors -> ERROR
    CoreErrorCode.INVALID_PARAMETER: CLIExitCode.ERROR,
    CoreErrorCode.MISSING_REQUIRED_PARAMETER: CLIExitCode.ERROR,
    CoreErrorCode.PARAMETER_TYPE_MISMATCH: CLIExitCode.ERROR,
    CoreErrorCode.PARAMETER_OUT_OF_RANGE: CLIExitCode.ERROR,
    CoreErrorCode.VALIDATION_FAILED: CLIExitCode.ERROR,
    # File system errors -> ERROR
    CoreErrorCode.FILE_NOT_FOUND: CLIExitCode.ERROR,
    CoreErrorCode.FILE_READ_ERROR: CLIExitCode.ERROR,
    CoreErrorCode.FILE_WRITE_ERROR: CLIExitCode.ERROR,
    CoreErrorCode.DIRECTORY_NOT_FOUND: CLIExitCode.ERROR,
    CoreErrorCode.PERMISSION_DENIED: CLIExitCode.ERROR,
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
}


def get_exit_code_for_core_error(error_code: CoreErrorCode) -> int:
    """
    Get the appropriate CLI exit code for a core error code.
    Uses the .exit_code property on the enum.
    """
    return error_code.exit_code


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
        CoreErrorCode.FILE_NOT_FOUND: "File not found",
        CoreErrorCode.FILE_READ_ERROR: "Cannot read file",
        CoreErrorCode.FILE_WRITE_ERROR: "Cannot write file",
        CoreErrorCode.DIRECTORY_NOT_FOUND: "Directory not found",
        CoreErrorCode.PERMISSION_DENIED: "Permission denied",
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
        CoreErrorCode.DATABASE_CONNECTION_FAILED: "Database connection failed",
        CoreErrorCode.DATABASE_OPERATION_FAILED: "Database operation failed",
        CoreErrorCode.SERVICE_INITIALIZATION_FAILED: "Service initialization failed",
        CoreErrorCode.SERVICE_RESOLUTION_FAILED: "Service resolution failed",
        CoreErrorCode.INTELLIGENCE_PROCESSING_FAILED: "Intelligence processing failed",
        CoreErrorCode.PATTERN_RECOGNITION_FAILED: "Pattern recognition failed",
        CoreErrorCode.CONTEXT_ANALYSIS_FAILED: "Context analysis failed",
        CoreErrorCode.LEARNING_ENGINE_FAILED: "Learning engine failed",
        CoreErrorCode.INTELLIGENCE_COORDINATION_FAILED: "Intelligence coordination failed",
        CoreErrorCode.SYSTEM_HEALTH_DEGRADED: "System health degraded",
        CoreErrorCode.SERVICE_START_FAILED: "Service start failed",
        CoreErrorCode.SERVICE_STOP_FAILED: "Service stop failed",
        CoreErrorCode.INITIALIZATION_FAILED: "Initialization failed",
        CoreErrorCode.SECURITY_REPORT_FAILED: "Security report failed",
        CoreErrorCode.SECURITY_VIOLATION: "Security violation",
        CoreErrorCode.EVENT_PROCESSING_FAILED: "Event processing failed",
    }
    return descriptions.get(error_code, "Unknown error")


# === Current Standards Imports ===
# Removed imports that were causing circular dependencies
# Users should import these directly from omnibase_core.exceptions or omnibase_core.core.errors.core_errors

# Re-export for current standards
__all__ = [
    "CLIExitCode",
    "CoreErrorCode",
    "OnexErrorCode",
    "get_core_error_description",
    "get_exit_code_for_core_error",
    "get_exit_code_for_status",
]
