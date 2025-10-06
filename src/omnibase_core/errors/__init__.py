from typing import Any

"""Core error handling for ONEX framework."""

# Core error system - comprehensive implementation
from omnibase_core.errors.error_codes import (
    EnumCLIExitCode,
    ModelCoreErrorCode,
    ModelOnexError,
    ModelRegistryErrorCode,
    get_core_error_description,
    get_error_codes_for_component,
    get_exit_code_for_core_error,
    get_exit_code_for_status,
    list_registered_components,
    register_error_codes,
)

# Document freshness errors
from omnibase_core.errors.error_document_freshness import DocumentFreshnessError
from omnibase_core.errors.error_document_freshness_ai import DocumentFreshnessAIError
from omnibase_core.errors.error_document_freshness_analysis import (
    DocumentFreshnessAnalysisError,
)
from omnibase_core.errors.error_document_freshness_change_detection import (
    DocumentFreshnessChangeDetectionError,
)
from omnibase_core.errors.error_document_freshness_database import (
    ModelDocumentFreshnessDatabaseError,
)
from omnibase_core.errors.error_document_freshness_dependency import (
    DocumentFreshnessDependencyError,
)
from omnibase_core.errors.error_document_freshness_path import (
    DocumentFreshnessPathError,
)
from omnibase_core.errors.error_document_freshness_system import (
    DocumentFreshnessSystemError,
)
from omnibase_core.errors.error_document_freshness_validation import (
    DocumentFreshnessValidationError,
)
from omnibase_core.models.common.model_onex_warning import ModelOnexWarning
from omnibase_core.models.common.model_registry_error import ModelRegistryError

# Import extracted classes
from omnibase_core.models.core.model_cli_adapter import ModelCLIAdapter

__all__ = [
    # Base error classes
    "ModelOnexError",
    "ModelOnexWarning",
    # Error codes and enums
    "ModelCoreErrorCode",
    "EnumCLIExitCode",
    "ModelRegistryErrorCode",
    # CLI adapter and utilities
    "ModelCLIAdapter",
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
