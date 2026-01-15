"""
Runtime Host Error Hierarchy ().

Minimal MVP error classes for Runtime Host operations with structured error handling.

MVP Classes:
- RuntimeHostError: Base error for all runtime host operations
- HandlerExecutionError: Handler-specific execution errors
- EventBusError: Event bus operation errors
- InvalidOperationError: Invalid state or operation errors
- ContractValidationError: Contract/schema validation errors

Error Invariants (MVP Requirements):
- All errors MUST include correlation_id for tracking
- Handler errors MUST include handler_type when applicable
- All errors SHOULD include operation when applicable
- Raw stack traces MUST NOT appear in error envelopes
- Structured fields for logging and observability

Design Principles:
- Inherit from ModelOnexError for consistency
- Minimal boilerplate (leverage base class features)
- Type-safe with mypy strict mode compliance
- Serializable for event bus and logging
- No circular dependencies

Usage:
    from omnibase_core.errors.error_runtime import (
        RuntimeHostError,
        HandlerExecutionError,
        EventBusError,
    )

    # Base runtime error
    raise RuntimeHostError(
        "Node initialization failed",
        operation="initialize",
    )

    # Handler-specific error
    raise HandlerExecutionError(
        "Kafka connection timeout",
        handler_type="Kafka",
        operation="publish_message",
    )

    # Event bus error with correlation tracking
    raise EventBusError(
        "Failed to deliver event",
        operation="publish",
        correlation_id=corr_id,
    )
"""

# Re-export from split modules
from omnibase_core.errors.error_contract_validation import ContractValidationError
from omnibase_core.errors.error_event_bus import EventBusError
from omnibase_core.errors.error_handler_execution import HandlerExecutionError
from omnibase_core.errors.error_invalid_operation import InvalidOperationError
from omnibase_core.errors.error_runtime_host import RuntimeHostError

__all__ = [
    "ContractValidationError",
    "EventBusError",
    "HandlerExecutionError",
    "InvalidOperationError",
    "RuntimeHostError",
]
