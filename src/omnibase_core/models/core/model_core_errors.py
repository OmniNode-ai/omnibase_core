import uuid
from datetime import datetime
from typing import Dict, List
from uuid import UUID

from pydantic import Field

from omnibase_core.errors.error_codes import EnumCoreErrorCode

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
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.core.core_uuid_service import UUIDService
from omnibase_core.enums.enum_onex_status import EnumOnexStatus

# Import ModelOnexError from canonical location to avoid duplication
# Note: EnumOnexErrorCode is defined in this file and in error_codes.py
# This file appears to be a legacy/duplicate file that's not imported anywhere
# TODO: Consider removing this file entirely in favor of error_codes.py
from omnibase_core.errors.model_onex_error import ModelOnexError


class EnumCLIExitCode(int, Enum):
    """Standard CLI exit codes for ONEX operations."""

    SUCCESS = 0
    ERROR = 1
    WARNING = 2
    PARTIAL = 3
    SKIPPED = 4
    FIXED = 5
    INFO = 6


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


class EnumOnexErrorCode(str, Enum):
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
        raise NotImplementedError(msg)  # stub-ok: abstract method

    def get_number(self) -> int:
        """Get the numeric identifier for this error code."""
        msg = "Subclasses must implement get_number()"
        raise NotImplementedError(msg)  # stub-ok: abstract method

    def get_description(self) -> str:
        """Get a human-readable description for this error code."""
        msg = "Subclasses must implement get_description()"
        raise NotImplementedError(msg)  # stub-ok: abstract method

    def get_exit_code(self) -> int:
        """
        Get the appropriate CLI exit code for this error.

        Default implementation returns ERROR (1). Subclasses can override
        for more specific mapping.
        """
        return EnumCLIExitCode.ERROR.value


class EnumCoreErrorCode(EnumOnexErrorCode):
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

    # Intelligence processing errors (161-180)
    NO_SUITABLE_PROVIDER = "ONEX_CORE_161_NO_SUITABLE_PROVIDER"
    RATE_LIMIT_ERROR = "ONEX_CORE_162_RATE_LIMIT_ERROR"
    AUTHENTICATION_ERROR = "ONEX_CORE_163_AUTHENTICATION_ERROR"
    QUOTA_EXCEEDED = "ONEX_CORE_164_QUOTA_EXCEEDED"
    PROCESSING_ERROR = "ONEX_CORE_165_PROCESSING_ERROR"
    INTELLIGENCE_PROCESSING_FAILED = "ONEX_CORE_166_INTELLIGENCE_PROCESSING_FAILED"
    PATTERN_RECOGNITION_FAILED = "ONEX_CORE_167_PATTERN_RECOGNITION_FAILED"
    CONTEXT_ANALYSIS_FAILED = "ONEX_CORE_168_CONTEXT_ANALYSIS_FAILED"
    LEARNING_ENGINE_FAILED = "ONEX_CORE_169_LEARNING_ENGINE_FAILED"
    INTELLIGENCE_COORDINATION_FAILED = "ONEX_CORE_170_INTELLIGENCE_COORDINATION_FAILED"

    # System health errors (181-200)
    SYSTEM_HEALTH_DEGRADED = "ONEX_CORE_181_SYSTEM_HEALTH_DEGRADED"
    SERVICE_START_FAILED = "ONEX_CORE_182_SERVICE_START_FAILED"
    SERVICE_STOP_FAILED = "ONEX_CORE_183_SERVICE_STOP_FAILED"
    SECURITY_REPORT_FAILED = "ONEX_CORE_184_SECURITY_REPORT_FAILED"
    SECURITY_VIOLATION = "ONEX_CORE_185_SECURITY_VIOLATION"
    EVENT_PROCESSING_FAILED = "ONEX_CORE_186_EVENT_PROCESSING_FAILED"

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


# ModelOnexError is now defined in omnibase_core.errors.error_codes
# Import from there instead of duplicating the definition


# Import extracted classes instead of duplicating definitions
from omnibase_core.models.common.model_onex_warning import ModelOnexWarning
from omnibase_core.models.core.model_cli_adapter import ModelCLIAdapter

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


class EnumRegistryErrorCode(EnumOnexErrorCode):
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
        return EnumCLIExitCode.ERROR.value


# ModelRegistryErrorModel has been extracted to model_registry_error_model.py
