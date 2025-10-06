import uuid
from datetime import datetime
from typing import Any, Dict, List

from pydantic import Field

from omnibase_core.errors.error_codes import ModelCoreErrorCode, ModelOnexError

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

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- omnibase_core.enums.* (no dependencies on this module)
- omnibase_core.types.core_types (minimal types, no dependencies on this module)
- Standard library modules

Type-Only Imports (MUST use TYPE_CHECKING guard):
- omnibase_core.models.* (imports from types.constraints, which references this module)
- Any module that directly/indirectly imports from types.constraints

Import Chain:
1. types.core_types (minimal types, no external deps)
2. THIS MODULE (errors.error_codes) → imports types.core_types
3. models.common.model_schema_value → imports THIS MODULE
4. types.constraints → TYPE_CHECKING import of THIS MODULE
5. models.* → imports types.constraints

Breaking this chain (e.g., adding runtime import from models.*) will cause circular import!
"""

import re
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

# Safe runtime imports - no circular dependency risk
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.types.core_types import BasicErrorContext

# Type-only imports - protected by TYPE_CHECKING to prevent circular imports
if TYPE_CHECKING:
    from omnibase_core.models.common.model_error_context import ModelErrorContext
    from omnibase_core.models.common.model_schema_value import ModelSchemaValue


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


class ModelCoreErrorCode(EnumOnexErrorCode):
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
    CONVERSION_ERROR = "ONEX_CORE_009_CONVERSION_ERROR"

    # File system errors (021-040)
    FILE_NOT_FOUND = "ONEX_CORE_021_FILE_NOT_FOUND"
    FILE_READ_ERROR = "ONEX_CORE_022_FILE_READ_ERROR"
    FILE_WRITE_ERROR = "ONEX_CORE_023_FILE_WRITE_ERROR"
    DIRECTORY_NOT_FOUND = "ONEX_CORE_024_DIRECTORY_NOT_FOUND"
    PERMISSION_DENIED = "ONEX_CORE_025_PERMISSION_DENIED"
    FILE_OPERATION_ERROR = "ONEX_CORE_026_FILE_OPERATION_ERROR"
    FILE_ACCESS_ERROR = "ONEX_CORE_027_FILE_ACCESS_ERROR"
    NOT_FOUND = "ONEX_CORE_028_NOT_FOUND"
    PERMISSION_ERROR = "ONEX_CORE_029_PERMISSION_ERROR"

    # Configuration errors (041-060)
    INVALID_CONFIGURATION = "ONEX_CORE_041_INVALID_CONFIGURATION"
    CONFIGURATION_NOT_FOUND = "ONEX_CORE_042_CONFIGURATION_NOT_FOUND"
    CONFIGURATION_PARSE_ERROR = "ONEX_CORE_043_CONFIGURATION_PARSE_ERROR"
    CONFIGURATION_ERROR = "ONEX_CORE_044_CONFIGURATION_ERROR"

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
    TIMEOUT = "ONEX_CORE_088_TIMEOUT"
    INTERNAL_ERROR = "ONEX_CORE_089_INTERNAL_ERROR"
    NETWORK_ERROR = "ONEX_CORE_090_NETWORK_ERROR"
    MIGRATION_ERROR = "ONEX_CORE_091_MIGRATION_ERROR"
    TIMEOUT_ERROR = "ONEX_CORE_092_TIMEOUT_ERROR"
    RESOURCE_ERROR = "ONEX_CORE_093_RESOURCE_ERROR"

    # Test and development errors (101-120)
    TEST_SETUP_FAILED = "ONEX_CORE_101_TEST_SETUP_FAILED"
    TEST_ASSERTION_FAILED = "ONEX_CORE_102_TEST_ASSERTION_FAILED"
    MOCK_CONFIGURATION_ERROR = "ONEX_CORE_103_MOCK_CONFIGURATION_ERROR"
    TEST_DATA_INVALID = "ONEX_CORE_104_TEST_DATA_INVALID"

    # Import and dependency errors (121-140)
    MODULE_NOT_FOUND = "ONEX_CORE_121_MODULE_NOT_FOUND"
    DEPENDENCY_UNAVAILABLE = "ONEX_CORE_122_DEPENDENCY_UNAVAILABLE"
    VERSION_INCOMPATIBLE = "ONEX_CORE_123_VERSION_INCOMPATIBLE"
    IMPORT_ERROR = "ONEX_CORE_124_IMPORT_ERROR"
    DEPENDENCY_ERROR = "ONEX_CORE_125_DEPENDENCY_ERROR"

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
CORE_ERROR_CODE_TO_EXIT_CODE: dict[ModelCoreErrorCode, EnumCLIExitCode] = {
    # Validation errors -> ERROR
    ModelCoreErrorCode.INVALID_PARAMETER: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.MISSING_REQUIRED_PARAMETER: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.PARAMETER_TYPE_MISMATCH: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.PARAMETER_OUT_OF_RANGE: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.VALIDATION_FAILED: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.VALIDATION_ERROR: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.INVALID_INPUT: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.INVALID_OPERATION: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.CONVERSION_ERROR: EnumCLIExitCode.ERROR,
    # File system errors -> ERROR
    ModelCoreErrorCode.FILE_NOT_FOUND: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.FILE_READ_ERROR: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.FILE_WRITE_ERROR: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.DIRECTORY_NOT_FOUND: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.PERMISSION_DENIED: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.FILE_OPERATION_ERROR: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.FILE_ACCESS_ERROR: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.NOT_FOUND: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.PERMISSION_ERROR: EnumCLIExitCode.ERROR,
    # Configuration errors -> ERROR
    ModelCoreErrorCode.INVALID_CONFIGURATION: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.CONFIGURATION_NOT_FOUND: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.CONFIGURATION_PARSE_ERROR: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.CONFIGURATION_ERROR: EnumCLIExitCode.ERROR,
    # Registry errors -> ERROR
    ModelCoreErrorCode.REGISTRY_NOT_FOUND: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.REGISTRY_INITIALIZATION_FAILED: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.ITEM_NOT_REGISTERED: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.DUPLICATE_REGISTRATION: EnumCLIExitCode.WARNING,
    # Runtime errors -> ERROR
    ModelCoreErrorCode.OPERATION_FAILED: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.TIMEOUT_EXCEEDED: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.RESOURCE_UNAVAILABLE: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.UNSUPPORTED_OPERATION: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.RESOURCE_NOT_FOUND: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.INVALID_STATE: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.INITIALIZATION_FAILED: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.TIMEOUT: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.INTERNAL_ERROR: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.NETWORK_ERROR: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.MIGRATION_ERROR: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.TIMEOUT_ERROR: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.RESOURCE_ERROR: EnumCLIExitCode.ERROR,
    # Database errors -> ERROR
    ModelCoreErrorCode.DATABASE_CONNECTION_ERROR: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.DATABASE_OPERATION_ERROR: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.DATABASE_QUERY_ERROR: EnumCLIExitCode.ERROR,
    # LLM provider errors -> ERROR
    ModelCoreErrorCode.NO_SUITABLE_PROVIDER: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.RATE_LIMIT_ERROR: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.AUTHENTICATION_ERROR: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.QUOTA_EXCEEDED: EnumCLIExitCode.ERROR,
    ModelCoreErrorCode.PROCESSING_ERROR: EnumCLIExitCode.ERROR,
}


def get_exit_code_for_core_error(error_code: ModelCoreErrorCode) -> int:
    """
    Get the appropriate CLI exit code for a core error code.

    Args:
        error_code: The ModelCoreErrorCode to map

    Returns:
        The corresponding CLI exit code (integer)
    """
    return CORE_ERROR_CODE_TO_EXIT_CODE.get(error_code, EnumCLIExitCode.ERROR).value


def get_core_error_description(error_code: ModelCoreErrorCode) -> str:
    """
    Get a human-readable description for a core error code.

    Args:
        error_code: The ModelCoreErrorCode to describe

    Returns:
        A human-readable description of the error
    """
    descriptions = {
        ModelCoreErrorCode.INVALID_PARAMETER: "Invalid parameter value",
        ModelCoreErrorCode.MISSING_REQUIRED_PARAMETER: "Required parameter missing",
        ModelCoreErrorCode.PARAMETER_TYPE_MISMATCH: "Parameter type mismatch",
        ModelCoreErrorCode.PARAMETER_OUT_OF_RANGE: "Parameter value out of range",
        ModelCoreErrorCode.VALIDATION_FAILED: "Validation failed",
        ModelCoreErrorCode.VALIDATION_ERROR: "Validation error occurred",
        ModelCoreErrorCode.INVALID_INPUT: "Invalid input provided",
        ModelCoreErrorCode.INVALID_OPERATION: "Invalid operation requested",
        ModelCoreErrorCode.CONVERSION_ERROR: "Data conversion error",
        ModelCoreErrorCode.FILE_NOT_FOUND: "File not found",
        ModelCoreErrorCode.FILE_READ_ERROR: "Cannot read file",
        ModelCoreErrorCode.FILE_WRITE_ERROR: "Cannot write file",
        ModelCoreErrorCode.DIRECTORY_NOT_FOUND: "Directory not found",
        ModelCoreErrorCode.PERMISSION_DENIED: "Permission denied",
        ModelCoreErrorCode.FILE_OPERATION_ERROR: "File operation failed",
        ModelCoreErrorCode.FILE_ACCESS_ERROR: "File access error",
        ModelCoreErrorCode.NOT_FOUND: "Resource not found",
        ModelCoreErrorCode.PERMISSION_ERROR: "Permission error",
        ModelCoreErrorCode.INVALID_CONFIGURATION: "Invalid configuration",
        ModelCoreErrorCode.CONFIGURATION_NOT_FOUND: "Configuration not found",
        ModelCoreErrorCode.CONFIGURATION_PARSE_ERROR: "Configuration parse error",
        ModelCoreErrorCode.CONFIGURATION_ERROR: "Configuration error",
        ModelCoreErrorCode.REGISTRY_NOT_FOUND: "Registry not found",
        ModelCoreErrorCode.REGISTRY_INITIALIZATION_FAILED: "Registry initialization failed",
        ModelCoreErrorCode.ITEM_NOT_REGISTERED: "Item not registered",
        ModelCoreErrorCode.DUPLICATE_REGISTRATION: "Duplicate registration",
        ModelCoreErrorCode.OPERATION_FAILED: "Operation failed",
        ModelCoreErrorCode.TIMEOUT_EXCEEDED: "Timeout exceeded",
        ModelCoreErrorCode.RESOURCE_UNAVAILABLE: "Resource unavailable",
        ModelCoreErrorCode.UNSUPPORTED_OPERATION: "Unsupported operation",
        ModelCoreErrorCode.RESOURCE_NOT_FOUND: "Resource not found",
        ModelCoreErrorCode.INVALID_STATE: "Invalid state",
        ModelCoreErrorCode.INITIALIZATION_FAILED: "Initialization failed",
        ModelCoreErrorCode.TIMEOUT: "Operation timed out",
        ModelCoreErrorCode.INTERNAL_ERROR: "Internal error occurred",
        ModelCoreErrorCode.NETWORK_ERROR: "Network error occurred",
        ModelCoreErrorCode.MIGRATION_ERROR: "Migration error occurred",
        ModelCoreErrorCode.TIMEOUT_ERROR: "Timeout error occurred",
        ModelCoreErrorCode.RESOURCE_ERROR: "Resource error occurred",
        ModelCoreErrorCode.DATABASE_CONNECTION_ERROR: "Database connection failed",
        ModelCoreErrorCode.DATABASE_OPERATION_ERROR: "Database operation failed",
        ModelCoreErrorCode.DATABASE_QUERY_ERROR: "Database query failed",
        ModelCoreErrorCode.MODULE_NOT_FOUND: "Module not found",
        ModelCoreErrorCode.DEPENDENCY_UNAVAILABLE: "Dependency unavailable",
        ModelCoreErrorCode.VERSION_INCOMPATIBLE: "Version incompatible",
        ModelCoreErrorCode.IMPORT_ERROR: "Import error occurred",
        ModelCoreErrorCode.DEPENDENCY_ERROR: "Dependency error occurred",
        ModelCoreErrorCode.NO_SUITABLE_PROVIDER: "No suitable provider available",
        ModelCoreErrorCode.RATE_LIMIT_ERROR: "Rate limit exceeded",
        ModelCoreErrorCode.AUTHENTICATION_ERROR: "Authentication failed",
        ModelCoreErrorCode.QUOTA_EXCEEDED: "Quota exceeded",
        ModelCoreErrorCode.PROCESSING_ERROR: "Processing error",
    }
    return descriptions.get(error_code, "Unknown error")


# Import extracted ModelOnexError class
from omnibase_core.errors.model_onex_error import ModelOnexError

# Import extracted models
from omnibase_core.models.common.model_onex_error_data import _ModelOnexErrorData
from omnibase_core.models.common.model_onex_warning import ModelOnexWarning
from omnibase_core.models.common.model_registry_error import ModelRegistryError
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
            msg,
            ModelCoreErrorCode.ITEM_NOT_REGISTERED,
        )
    return _ERROR_CODE_REGISTRIES[component]


def list_registered_components() -> list[str]:
    """
    List all registered component identifiers.

    Returns:
        List of component identifiers that have registered error codes
    """
    return list(_ERROR_CODE_REGISTRIES.keys())


class ModelRegistryErrorCode(EnumOnexErrorCode):
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
