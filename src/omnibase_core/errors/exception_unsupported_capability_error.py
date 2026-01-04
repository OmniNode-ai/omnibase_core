"""
Unsupported Capability Error (OMN-177).

Error class for missing capability errors in declarative node validation.

Design Principles:
- Inherit from RuntimeHostError for consistency
- Minimal boilerplate (leverage base class features)
- Type-safe with mypy strict mode compliance
- Serializable for event bus and logging
- No circular dependencies

Usage:
    from omnibase_core.errors.exception_unsupported_capability_error import (
        UnsupportedCapabilityError,
    )

    raise UnsupportedCapabilityError(
        "Node does not support streaming",
        capability="streaming",
        node_type="COMPUTE",
    )
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.errors.error_runtime import RuntimeHostError


class UnsupportedCapabilityError(RuntimeHostError):
    """
    Unsupported capability errors.

    Raised when a contract demands a capability that the node does not support.
    Includes capability and node_type for debugging.

    Example:
        raise UnsupportedCapabilityError(
            "Node does not support streaming",
            capability="streaming",
            node_type="COMPUTE",
        )
    """

    # NOTE: **context: Any is intentional - accepts arbitrary structured context
    # fields for logging, debugging, and observability (e.g., available_capabilities, etc.)
    def __init__(
        self,
        message: str,
        error_code: EnumCoreErrorCode | str | None = None,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        correlation_id: UUID | None = None,
        timestamp: datetime | None = None,
        operation: str | None = None,
        capability: str | None = None,
        node_type: str | None = None,
        **context: Any,
    ) -> None:
        """
        Initialize UnsupportedCapabilityError with capability context.

        Args:
            message: Human-readable error message
            error_code: Optional error code (defaults to UNSUPPORTED_CAPABILITY_ERROR)
            status: Error status (default: ERROR)
            correlation_id: Optional correlation ID for tracking
            timestamp: Optional timestamp (auto-generated if None)
            operation: Optional operation name
            capability: The capability that is not supported
            node_type: Type of node that lacks the capability
            **context: Additional structured context
        """
        # Use UNSUPPORTED_CAPABILITY_ERROR as default code
        final_error_code = error_code or EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR

        # Add special fields to context if provided
        if capability is not None:
            context["capability"] = capability
        if node_type is not None:
            context["node_type"] = node_type

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
        self.capability = capability
        self.node_type = node_type


__all__ = [
    "UnsupportedCapabilityError",
]
