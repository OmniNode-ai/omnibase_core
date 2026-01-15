"""
Purity Violation Error (OMN-177).

Error class for purity constraint violations in declarative node validation.

Design Principles:
- Inherit from RuntimeHostError for consistency
- Minimal boilerplate (leverage base class features)
- Type-safe with mypy strict mode compliance
- Serializable for event bus and logging
- No circular dependencies

Usage:
    from omnibase_core.errors.exception_purity_violation_error import (
        PurityViolationError,
    )

    raise PurityViolationError(
        "COMPUTE node accessed external state",
        node_id="node-compute-123",
        violation_type="external_state_access",
    )
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.errors.error_runtime import RuntimeHostError


class PurityViolationError(RuntimeHostError):
    """
    Purity violation errors.

    Raised when a declarative node violates purity constraints,
    such as accessing external state or performing I/O operations.
    Includes node_id and violation_type for debugging.

    Example:
        raise PurityViolationError(
            "COMPUTE node accessed external state",
            node_id="node-compute-123",
            violation_type="external_state_access",
        )
    """

    # NOTE: **context: Any is intentional - accepts arbitrary structured context
    # fields for logging, debugging, and observability (e.g., detected_at, etc.)
    def __init__(
        self,
        message: str,
        error_code: EnumCoreErrorCode | str | None = None,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        correlation_id: UUID | None = None,
        timestamp: datetime | None = None,
        operation: str | None = None,
        node_id: str | None = None,
        violation_type: str | None = None,
        **context: Any,
    ) -> None:
        """
        Initialize PurityViolationError with purity context.

        Args:
            message: Human-readable error message
            error_code: Optional error code (defaults to PURITY_VIOLATION_ERROR)
            status: Error status (default: ERROR)
            correlation_id: Optional correlation ID for tracking
            timestamp: Optional timestamp (auto-generated if None)
            operation: Optional operation name
            node_id: ID of the node that violated purity
            violation_type: Type of purity violation (e.g., "external_state_access")
            **context: Additional structured context
        """
        # Use PURITY_VIOLATION_ERROR as default code
        final_error_code = error_code or EnumCoreErrorCode.PURITY_VIOLATION_ERROR

        # Add special fields to context if provided
        if node_id is not None:
            context["node_id"] = node_id
        if violation_type is not None:
            context["violation_type"] = violation_type

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

        # Store special fields as attributes for direct access
        self.node_id = node_id
        self.violation_type = violation_type


__all__ = [
    "PurityViolationError",
]
