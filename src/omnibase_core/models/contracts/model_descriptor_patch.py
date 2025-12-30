# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Descriptor Patch Model.

Partial descriptor overrides within a contract patch.
Part of the contract patching system for OMN-1126.

Related:
    - OMN-1126: ModelContractPatch & Patch Validation
    - OMN-1086: ModelHandlerDescriptor
    - models/runtime/model_handler_descriptor.py: Full descriptor model

.. versionadded:: 0.4.0
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.runtime.model_descriptor_circuit_breaker import (
    ModelDescriptorCircuitBreaker,
)
from omnibase_core.models.runtime.model_descriptor_retry_policy import (
    ModelDescriptorRetryPolicy,
)

__all__ = [
    "ModelDescriptorPatch",
]


class ModelDescriptorPatch(BaseModel):
    """Partial descriptor overrides within a contract patch.

    Descriptor patches allow selective override of handler behavior settings
    without specifying a complete descriptor. Only the fields that need to
    change are included; unspecified fields retain their values from the
    base contract's descriptor.

    All fields are optional since patches only specify overrides.

    Attributes:
        purity: Override purity (pure vs side-effecting).
        idempotent: Override idempotency flag.
        timeout_ms: Override handler timeout in milliseconds.
        retry_policy: Override retry configuration.
        circuit_breaker: Override circuit breaker configuration.
        concurrency_policy: Override concurrency handling.
        isolation_policy: Override process/container isolation.
        observability_level: Override telemetry verbosity.

    Example:
        >>> # Override just timeout and retry for an effect handler
        >>> patch = ModelDescriptorPatch(
        ...     timeout_ms=30000,
        ...     retry_policy=ModelDescriptorRetryPolicy(
        ...         enabled=True,
        ...         max_retries=5,
        ...     ),
        ... )

        >>> # Override concurrency for a compute handler
        >>> patch = ModelDescriptorPatch(
        ...     concurrency_policy="parallel_ok",
        ...     observability_level="verbose",
        ... )

    See Also:
        - ModelContractPatch: Parent patch model that contains this
        - ModelHandlerDescriptor (runtime): Full descriptor this patches
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # All fields optional - only override what's needed

    purity: Literal["pure", "side_effecting"] | None = Field(
        default=None,
        description="Override whether handler is pure (no side effects) or side-effecting.",
    )

    idempotent: bool | None = Field(
        default=None,
        description="Override whether handler is idempotent (safe to retry with same input).",
    )

    timeout_ms: int | None = Field(
        default=None,
        ge=0,
        description="Override handler timeout in milliseconds.",
    )

    retry_policy: ModelDescriptorRetryPolicy | None = Field(
        default=None,
        description="Override retry configuration for handling transient failures.",
    )

    circuit_breaker: ModelDescriptorCircuitBreaker | None = Field(
        default=None,
        description="Override circuit breaker configuration for fault tolerance.",
    )

    concurrency_policy: Literal["parallel_ok", "serialized", "singleflight"] | None = (
        Field(
            default=None,
            description="Override how concurrent handler invocations are managed.",
        )
    )

    isolation_policy: Literal["none", "process", "container", "vm"] | None = Field(
        default=None,
        description="Override process/container isolation level for handler execution.",
    )

    observability_level: Literal["minimal", "standard", "verbose"] | None = Field(
        default=None,
        description="Override telemetry and logging verbosity for the handler.",
    )

    def has_overrides(self) -> bool:
        """Check if this patch contains any overrides.

        Returns:
            True if at least one field is set to a non-None value.
        """
        return any(getattr(self, field) is not None for field in self.model_fields)

    def get_override_fields(self) -> list[str]:
        """Get list of field names that have overrides.

        Returns:
            List of field names with non-None values.
        """
        return [
            field for field in self.model_fields if getattr(self, field) is not None
        ]

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        overrides = self.get_override_fields()
        if not overrides:
            return "ModelDescriptorPatch(empty)"
        return f"ModelDescriptorPatch(overrides={overrides})"
