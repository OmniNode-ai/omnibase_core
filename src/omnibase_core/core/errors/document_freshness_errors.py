"""
Document Freshness Error Classes

Structured error classes for document freshness monitoring operations.
Extends OmniBaseError with specific error codes and contexts.
"""

from omnibase_core.core.errors.onex_error import CoreErrorCode, OnexError
from omnibase_core.enums.enum_document_freshness_errors import (
    EnumDocumentFreshnessErrorCodes,
)
from omnibase_core.model.docs.model_error_details import ModelErrorDetails


class DocumentFreshnessError(OnexError):
    """
    Base error class for all document freshness monitoring errors.

    Provides structured error handling with standardized error codes,
    context information, and correlation IDs for tracing.
    """

    def __init__(
        self,
        error_code: EnumDocumentFreshnessErrorCodes,
        message: str,
        details: ModelErrorDetails | None = None,
        correlation_id: str | None = None,
        file_path: str | None = None,
    ):
        """
        Initialize a document freshness error.

        Args:
            error_code: Standardized error code from enum
            message: Human-readable error message
            details: Additional context information
            correlation_id: Correlation ID for request tracing
            file_path: File path related to the error
        """
        # Build the message
        full_message = message
        if file_path:
            full_message += f" (file: {file_path})"

        # Convert to appropriate core error code based on document freshness error type
        core_error_code = self._map_to_core_error_code(error_code)

        # Build details dict
        error_details = {}
        if details:
            error_details.update(details.model_dump())
        if correlation_id:
            error_details["correlation_id"] = correlation_id
        if file_path:
            error_details["file_path"] = file_path

        # Initialize the base OnexError with proper parameters
        super().__init__(
            code=core_error_code,
            message=full_message,
            details=error_details,
        )

        # Store additional attributes specific to document freshness errors
        self._error_code_enum = error_code
        self.correlation_id = correlation_id
        self.file_path = file_path

    @property
    def error_code(self) -> EnumDocumentFreshnessErrorCodes:
        """Get the error code enum."""
        return self._error_code_enum

    @staticmethod
    def _map_to_core_error_code(
        error_code: EnumDocumentFreshnessErrorCodes,
    ) -> CoreErrorCode:
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
            return CoreErrorCode.NOT_FOUND

        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_INVALID,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_TOO_LONG,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_FORBIDDEN_PATTERN,
        }:
            return CoreErrorCode.VALIDATION_ERROR

        # Permission and access errors -> PERMISSION_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_ACCESS_DENIED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PERMISSION_DENIED,
        }:
            return CoreErrorCode.PERMISSION_ERROR

        # Database errors -> INTERNAL_ERROR or CONFIGURATION_ERROR or DEPENDENCY_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_INIT_FAILED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_CONNECTION_FAILED,
        }:
            return CoreErrorCode.CONFIGURATION_ERROR

        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_QUERY_FAILED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_WRITE_FAILED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_SCHEMA_INVALID,
        }:
            return CoreErrorCode.INTERNAL_ERROR

        # Analysis timeout and resource errors -> TIMEOUT_ERROR or RESOURCE_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_TIMEOUT,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_OPERATION_CANCELLED,
        }:
            return CoreErrorCode.TIMEOUT_ERROR

        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_MEMORY_EXCEEDED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_FILE_TOO_LARGE,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_RESOURCE_EXHAUSTED,
        }:
            return CoreErrorCode.RESOURCE_ERROR

        # Configuration and validation errors -> CONFIGURATION_ERROR or VALIDATION_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_CONFIG_INVALID,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_INVALID_CONFIG,
        }:
            return CoreErrorCode.CONFIGURATION_ERROR

        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_VALIDATION_FAILED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_INPUT_INVALID,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_OUTPUT_VALIDATION_FAILED,
        }:
            return CoreErrorCode.VALIDATION_ERROR

        # AI service errors -> NETWORK_ERROR or DEPENDENCY_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_SERVICE_UNAVAILABLE,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_SERVICE_ERROR,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_RATE_LIMIT_EXCEEDED,
        }:
            return CoreErrorCode.NETWORK_ERROR

        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_CONTENT_TOO_LARGE,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_QUALITY_THRESHOLD_NOT_MET,
        }:
            return CoreErrorCode.DEPENDENCY_ERROR

        # Git and change detection errors -> DEPENDENCY_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_GIT_UNAVAILABLE,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_GIT_OPERATION_FAILED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_CHANGE_HISTORY_CORRUPTED,
        }:
            return CoreErrorCode.DEPENDENCY_ERROR

        # Dependency analysis errors -> DEPENDENCY_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DEPENDENCY_ANALYSIS_FAILED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DEPENDENCY_CIRCULAR_DETECTED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DEPENDENCY_DEPTH_EXCEEDED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DEPENDENCY_PARSING_FAILED,
        }:
            return CoreErrorCode.DEPENDENCY_ERROR

        # General analysis and change detection failures -> OPERATION_FAILED
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_FAILED,
            EnumDocumentFreshnessErrorCodes.FRESHNESS_CHANGE_DETECTION_FAILED,
        }:
            return CoreErrorCode.OPERATION_FAILED

        # System errors -> INTERNAL_ERROR
        if error_code in {
            EnumDocumentFreshnessErrorCodes.FRESHNESS_SYSTEM_ERROR,
        }:
            return CoreErrorCode.INTERNAL_ERROR

        # Default fallback for any unmapped errors
        return CoreErrorCode.OPERATION_FAILED

    def to_dict(self) -> dict[str, str | int | bool | None]:
        """Convert error to dictionary for serialization."""
        # Custom error serialization with correlation and file path
        return {
            "error_code": self.error_code.value,
            "core_error_code": self.code.value,  # Include core error code for better categorization
            "message": str(self),
            "correlation_id": self.correlation_id,
            "file_path": self.file_path,
        }


class DocumentFreshnessPathError(DocumentFreshnessError):
    """Error related to file path operations."""


class DocumentFreshnessDatabaseError(DocumentFreshnessError):
    """Error related to database operations."""


class DocumentFreshnessAnalysisError(DocumentFreshnessError):
    """Error related to document analysis operations."""


class DocumentFreshnessAIServiceError(DocumentFreshnessError):
    """Error related to AI service operations."""


class DocumentFreshnessDependencyError(DocumentFreshnessError):
    """Error related to dependency analysis."""


class DocumentFreshnessChangeDetectionError(DocumentFreshnessError):
    """Error related to change detection."""


class DocumentFreshnessValidationError(DocumentFreshnessError):
    """Error related to input/output validation."""


class DocumentFreshnessSystemError(DocumentFreshnessError):
    """Error related to system-level operations."""
