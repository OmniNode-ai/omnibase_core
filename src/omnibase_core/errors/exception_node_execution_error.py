"""
Node Execution Error (OMN-177).

Error class for runtime execution failures in declarative node validation.

Design Principles:
- Inherit from RuntimeHostError for consistency
- Minimal boilerplate (leverage base class features)
- Type-safe with mypy strict mode compliance
- Serializable for event bus and logging
- No circular dependencies

Usage:
    from omnibase_core.errors.exception_node_execution_error import (
        NodeExecutionError,
    )

    raise NodeExecutionError(
        "Execution failed during compute phase",
        node_id="node-compute-abc",
        execution_phase="compute",
    )
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.errors.error_runtime import RuntimeHostError


class NodeExecutionError(RuntimeHostError):
    """
    Node execution errors.

    Raised when a declarative node fails during runtime execution.
    Includes node_id and execution_phase for debugging.

    Example:
        raise NodeExecutionError(
            "Execution failed during compute phase",
            node_id="node-compute-abc",
            execution_phase="compute",
        )
    """

    # NOTE: **context: Any is intentional - accepts arbitrary structured context
    # fields for logging, debugging, and observability (e.g., retry_count, etc.)
    def __init__(
        self,
        message: str,
        error_code: EnumCoreErrorCode | str | None = None,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        correlation_id: UUID | None = None,
        timestamp: datetime | None = None,
        operation: str | None = None,
        node_id: str | None = None,
        execution_phase: str | None = None,
        **context: Any,
    ) -> None:
        """
        Initialize NodeExecutionError with execution context.

        Args:
            message: Human-readable error message
            error_code: Optional error code (defaults to NODE_EXECUTION_ERROR)
            status: Error status (default: ERROR)
            correlation_id: Optional correlation ID for tracking
            timestamp: Optional timestamp (auto-generated if None)
            operation: Optional operation name
            node_id: ID of the node that failed
            execution_phase: Phase where execution failed (e.g., "compute", "reduce")
            **context: Additional structured context
        """
        # Use NODE_EXECUTION_ERROR as default code
        final_error_code = error_code or EnumCoreErrorCode.NODE_EXECUTION_ERROR

        # Add special fields to context if provided
        if node_id is not None:
            context["node_id"] = node_id
        if execution_phase is not None:
            context["execution_phase"] = execution_phase

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
        self.execution_phase = execution_phase


__all__ = [
    "NodeExecutionError",
]
