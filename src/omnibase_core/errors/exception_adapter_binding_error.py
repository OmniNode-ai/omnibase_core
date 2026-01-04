"""
Adapter Binding Error (OMN-177).

Error class for adapter binding failures in declarative node validation.

Design Principles:
- Inherit from RuntimeHostError for consistency
- Minimal boilerplate (leverage base class features)
- Type-safe with mypy strict mode compliance
- Serializable for event bus and logging
- No circular dependencies

Usage:
    from omnibase_core.errors.exception_adapter_binding_error import (
        AdapterBindingError,
    )

    raise AdapterBindingError(
        "Cannot bind YAML adapter to contract",
        adapter_type="YamlContractAdapter",
        contract_path="nodes/compute/contract.yaml",
    )
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.errors.error_runtime import RuntimeHostError


class AdapterBindingError(RuntimeHostError):
    """
    Adapter binding errors.

    Raised when an adapter cannot bind to a contract structure.
    Includes adapter_type and contract_path for debugging.

    Example:
        raise AdapterBindingError(
            "Cannot bind YAML adapter to contract",
            adapter_type="YamlContractAdapter",
            contract_path="nodes/compute/contract.yaml",
        )
    """

    # NOTE: **context: Any is intentional - accepts arbitrary structured context
    # fields for logging, debugging, and observability (e.g., binding_phase, etc.)
    def __init__(
        self,
        message: str,
        error_code: EnumCoreErrorCode | str | None = None,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        correlation_id: UUID | None = None,
        timestamp: datetime | None = None,
        operation: str | None = None,
        adapter_type: str | None = None,
        contract_path: str | None = None,
        **context: Any,
    ) -> None:
        """
        Initialize AdapterBindingError with adapter context.

        Args:
            message: Human-readable error message
            error_code: Optional error code (defaults to ADAPTER_BINDING_ERROR)
            status: Error status (default: ERROR)
            correlation_id: Optional correlation ID for tracking
            timestamp: Optional timestamp (auto-generated if None)
            operation: Optional operation name
            adapter_type: Type of adapter that failed to bind
            contract_path: Path to the contract file
            **context: Additional structured context
        """
        # Use ADAPTER_BINDING_ERROR as default code
        final_error_code = error_code or EnumCoreErrorCode.ADAPTER_BINDING_ERROR

        # Add special fields to context if provided
        if adapter_type is not None:
            context["adapter_type"] = adapter_type
        if contract_path is not None:
            context["contract_path"] = contract_path

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
        self.adapter_type = adapter_type
        self.contract_path = contract_path


__all__ = [
    "AdapterBindingError",
]
