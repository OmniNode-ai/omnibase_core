import uuid
from typing import Any

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Document Freshness Error Classes

Structured error classes for document freshness monitoring operations.
Extends OmniBaseError with specific error codes and contexts.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is imported by errors/__init__.py, which is imported when error_codes is imported.
Therefore, this module MUST NOT import from models at runtime to avoid circular dependencies.

Import Chain:
1. errors.error_codes (safe - only imports types.core_types)
2. errors/__init__.py → imports error_codes AND this module
3. THIS MODULE → MUST NOT import models.* at runtime (use TYPE_CHECKING)
4. models.common.model_schema_value → imports errors.error_codes

Breaking this chain (adding runtime import from models) will cause circular import!
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from omnibase_core.enums.enum_document_freshness_errors import (
    EnumDocumentFreshnessErrorCodes,
)
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

# Type-only imports - MUST stay under TYPE_CHECKING to prevent circular imports
if TYPE_CHECKING:
    from omnibase_core.models.common.model_error_context import ModelErrorContext
    from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class DocumentFreshnessError(ModelOnexError):
    """
    Base error class for all document freshness monitoring errors.

    Provides structured error handling with standardized error codes,
    context information, and correlation IDs for tracing.
    """

    def __init__(
        self,
        error_code: EnumDocumentFreshnessErrorCodes,
        message: str,
        details: "ModelErrorContext | None" = None,
        correlation_id: UUID | None = None,
        file_path: str | None = None,
    ):
        """
        Initialize a document freshness error.

        Args:
            error_code: Standardized error code from enum
            message: Human-readable error message
            details: Additional context information (ModelErrorContext)
            correlation_id: Correlation ID for request tracing
            file_path: File path related to the error
        """
        # Build the message
        full_message = message
        if file_path:
            full_message += f" (file: {file_path})"

        # Convert to appropriate core error code based on document freshness error type
        core_error_code = self._map_to_core_error_code(error_code)

        # Build details dict[str, Any]using duck typing to avoid importing ModelErrorContext
        error_details: dict[str, Any] = {}
        if details:
            # Use duck typing - if it has model_dump(), call it
            if hasattr(details, "model_dump"):
                error_details.update(details.model_dump())
            else:
                # Otherwise assume it's dict[str, Any]-like and update directly
                error_details.update(details)  # type: ignore[arg-type]
        if correlation_id:
            error_details["correlation_id"] = str(correlation_id)
        if file_path:
            error_details["file_path"] = file_path

        # Initialize the base ModelOnexError with proper parameters
        super().__init__(
            code=core_error_code,
            message=full_message,
            details=error_details,
        )

        # Store additional attributes specific to document freshness errors
        self._error_code_enum = error_code
        # correlation_id is already set by parent __init__
        self.file_path = file_path

    @property
    def error_code(self) -> EnumDocumentFreshnessErrorCodes:
        """Get the error code enum."""
        return self._error_code_enum

    @staticmethod
    def _map_to_core_error_code(
        error_code: EnumDocumentFreshnessErrorCodes,
    ) -> EnumCoreErrorCode:
        """
        Map document freshness error codes to appropriate core error codes.

        Args:
            error_code: Document freshness specific error code

        Returns:
            Corresponding core error code for proper categorization
        """
        # Path validation errors -> NOT_FOUND or VALIDATION_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_NOT_FOUND,
        }:
            return EnumCoreErrorCode.NOT_FOUND

        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_INVALID,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_TOO_LONG,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_FORBIDDEN_PATTERN,
        }:
            return EnumCoreErrorCode.VALIDATION_ERROR

        # Permission and access errors -> PERMISSION_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_ACCESS_DENIED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PERMISSION_DENIED,
        }:
            return EnumCoreErrorCode.PERMISSION_ERROR

        # Database errors -> INTERNAL_ERROR or CONFIGURATION_ERROR or DEPENDENCY_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_INIT_FAILED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_CONNECTION_FAILED,
        }:
            return EnumCoreErrorCode.CONFIGURATION_ERROR

        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_QUERY_FAILED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_WRITE_FAILED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_SCHEMA_INVALID,
        }:
            return EnumCoreErrorCode.INTERNAL_ERROR

        # Analysis timeout and resource errors -> TIMEOUT_ERROR or RESOURCE_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_TIMEOUT,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_OPERATION_CANCELLED,
        }:
            return EnumCoreErrorCode.TIMEOUT_ERROR

        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_MEMORY_EXCEEDED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_FILE_TOO_LARGE,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_RESOURCE_EXHAUSTED,
        }:
            return EnumCoreErrorCode.RESOURCE_ERROR

        # Configuration and validation errors -> CONFIGURATION_ERROR or VALIDATION_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_CONFIG_INVALID,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_INVALID_CONFIG,
        }:
            return EnumCoreErrorCode.CONFIGURATION_ERROR

        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_VALIDATION_FAILED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_INPUT_INVALID,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_OUTPUT_VALIDATION_FAILED,
        }:
            return EnumCoreErrorCode.VALIDATION_ERROR

        # AI service errors -> NETWORK_ERROR or DEPENDENCY_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_SERVICE_UNAVAILABLE,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_SERVICE_ERROR,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_RATE_LIMIT_EXCEEDED,
        }:
            return EnumCoreErrorCode.NETWORK_ERROR

        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_CONTENT_TOO_LARGE,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_QUALITY_THRESHOLD_NOT_MET,
        }:
            return EnumCoreErrorCode.DEPENDENCY_ERROR

        # Git and change detection errors -> DEPENDENCY_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_GIT_UNAVAILABLE,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_GIT_OPERATION_FAILED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_CHANGE_HISTORY_CORRUPTED,
        }:
            return EnumCoreErrorCode.DEPENDENCY_ERROR

        # Dependency analysis errors -> DEPENDENCY_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DEPENDENCY_ANALYSIS_FAILED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DEPENDENCY_CIRCULAR_DETECTED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DEPENDENCY_DEPTH_EXCEEDED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DEPENDENCY_PARSING_FAILED,
        }:
            return EnumCoreErrorCode.DEPENDENCY_ERROR

        # General analysis and change detection failures -> OPERATION_FAILED
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_FAILED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_CHANGE_DETECTION_FAILED,
        }:
            return EnumCoreErrorCode.OPERATION_FAILED

        # System errors -> INTERNAL_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_SYSTEM_ERROR,
        }:
            return EnumCoreErrorCode.INTERNAL_ERROR

        # Default fallback for any unmapped errors
        return EnumCoreErrorCode.OPERATION_FAILED

    def to_dict(self) -> dict[str, "ModelSchemaValue"]:
        """
        Convert error to dict[str, Any]ionary for serialization.

        Uses lazy import of ModelSchemaValue to avoid circular dependencies.
        This import is only triggered when the method is called, not at module load time.
        """
        # LAZY IMPORT: Only load ModelSchemaValue when this method is called
        # This prevents circular dependency at module import time

        # Custom error serialization with correlation and file path
        core_code = self.model.error_code
        core_code_str = (
            core_code.value
            if core_code and hasattr(core_code, "value")
            else (str(core_code) if core_code else "UNKNOWN")
        )
        return {
            "error_code": ModelSchemaValue.from_value(self._error_code_enum.value),
            "core_error_code": ModelSchemaValue.from_value(core_code_str),
            "message": ModelSchemaValue.from_value(str(self)),
            "correlation_id": ModelSchemaValue.from_value(
                str(self.correlation_id) if self.correlation_id else None
            ),
            "file_path": ModelSchemaValue.from_value(self.file_path),
        }
