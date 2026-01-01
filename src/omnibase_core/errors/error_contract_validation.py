"""
Contract Validation Error.

Contract/schema validation error for Runtime Host operations.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.errors.error_runtime_host import RuntimeHostError


class ContractValidationError(RuntimeHostError):
    """
    Contract/schema validation errors.

    Raised when contract or schema validation fails during node registration,
    configuration loading, or runtime validation.

    Example:
        raise ContractValidationError(
            "Missing required field 'handler_type'",
            operation="validate_contract",
            field="handler_type",
            expected_type="string",
        )
    """

    # NOTE: **context: Any is intentional - accepts arbitrary structured context
    # fields for logging, debugging, and observability (e.g., field, expected_type, etc.)
    def __init__(
        self,
        message: str,
        error_code: EnumCoreErrorCode | str | None = None,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        correlation_id: UUID | None = None,
        timestamp: datetime | None = None,
        operation: str | None = None,
        **context: Any,
    ) -> None:
        """
        Initialize ContractValidationError with validation context.

        Args:
            message: Human-readable error message
            error_code: Optional error code (defaults to CONTRACT_VALIDATION_ERROR)
            status: Error status (default: ERROR)
            correlation_id: Optional correlation ID for tracking
            timestamp: Optional timestamp (auto-generated if None)
            operation: Optional operation name (e.g., "validate_schema")
            **context: Additional structured context (e.g., field, expected_type)
        """
        # Use CONTRACT_VALIDATION_ERROR as default code
        final_error_code = error_code or EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR

        # Call parent with all structured fields
        super().__init__(
            message=message,
            error_code=final_error_code,
            status=status,
            correlation_id=correlation_id,
            timestamp=timestamp,
            operation=operation,
            **context,
        )


__all__ = ["ContractValidationError"]
