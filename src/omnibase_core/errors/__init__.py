"""Core error handling for ONEX framework."""

# Core error system - comprehensive implementation
from omnibase_core.errors.error_codes import (
    CLIAdapter,
    CLIExitCode,
    CoreErrorCode,
    ModelOnexError,
    ModelOnexWarning,
    ModelRegistryError,
    OnexError,
    OnexErrorCode,
    RegistryErrorCode,
    get_core_error_description,
    get_error_codes_for_component,
    get_exit_code_for_core_error,
    get_exit_code_for_status,
    list_registered_components,
    register_error_codes,
)

# Document freshness errors
from omnibase_core.errors.error_document_freshness import (
    DocumentFreshnessAIError,
    DocumentFreshnessAnalysisError,
    DocumentFreshnessChangeDetectionError,
    DocumentFreshnessDependencyError,
    DocumentFreshnessError,
    DocumentFreshnessPathError,
    DocumentFreshnessSystemError,
    DocumentFreshnessValidationError,
    ModelDocumentFreshnessDatabaseError,
)

__all__ = [
    # Base error classes
    "OnexError",
    "ModelOnexError",
    "ModelOnexWarning",
    # Error codes and enums
    "OnexErrorCode",
    "CoreErrorCode",
    "CLIExitCode",
    "RegistryErrorCode",
    # CLI adapter and utilities
    "CLIAdapter",
    "get_exit_code_for_status",
    "get_exit_code_for_core_error",
    "get_core_error_description",
    # Error code registration
    "register_error_codes",
    "get_error_codes_for_component",
    "list_registered_components",
    # Registry errors
    "ModelRegistryError",
    # Document freshness errors
    "DocumentFreshnessError",
    "DocumentFreshnessPathError",
    "ModelDocumentFreshnessDatabaseError",
    "DocumentFreshnessAnalysisError",
    "DocumentFreshnessAIError",
    "DocumentFreshnessDependencyError",
    "DocumentFreshnessChangeDetectionError",
    "DocumentFreshnessValidationError",
    "DocumentFreshnessSystemError",
]
