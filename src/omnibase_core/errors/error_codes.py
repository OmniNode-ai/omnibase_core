"""
Helper functions for error code mapping and registration.

This module provides utility functions for mapping EnumOnexStatus to CLI exit codes
and for component-specific error code registration.

NOTE: The enum classes (EnumCLIExitCode, EnumOnexErrorCode, EnumCoreErrorCode,
EnumRegistryErrorCode) have been moved to omnibase_core.enums/ as of v0.2.0.
Import them from their new locations:
  - from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
  - from omnibase_core.enums.enum_onex_error_code import EnumOnexErrorCode
  - from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
  - from omnibase_core.enums.enum_registry_error_code import EnumRegistryErrorCode

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is early in the import chain and must remain free of circular dependencies.

Safe Runtime Imports:
- typing (standard library)
- omnibase_core.enums.* (simple enum classes with no dependencies)

Import Chain Position:
1. types.core_types (no external deps)
2. THIS MODULE → enums.* (safe runtime imports)
3. models.common.model_schema_value → THIS MODULE
4. types.constraints → TYPE_CHECKING import of THIS MODULE
5. models.* → types.constraints, THIS MODULE

Critical Rules:
- NEVER import from models.* at module level (creates circular dependencies)
- NEVER import from types.constraints at module level (creates circular dependencies)
- Only import from enums.* which are leaf nodes in the dependency graph
- All enum imports are safe because enums have no dependencies on other omnibase_core modules

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

# Safe runtime imports - no circular dependency risk
from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_onex_error_code import EnumOnexErrorCode
from omnibase_core.enums.enum_onex_status import EnumOnexStatus

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
        KeyError: If component is not registered
    """
    if component not in _ERROR_CODE_REGISTRIES:
        # Use standard Python exception - error_codes.py should not depend on models
        raise KeyError(  # error-ok: avoid circular import with ModelOnexError
            f"No error codes registered for component: {component}"
        )
    return _ERROR_CODE_REGISTRIES[component]


def list_registered_components() -> list[str]:
    """
    List all registered component identifiers.

    Returns:
        List of component identifiers that have registered error codes
    """
    return list(_ERROR_CODE_REGISTRIES.keys())
