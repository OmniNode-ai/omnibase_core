"""
Behavior Patch Model.

Partial behavior overrides within a contract patch.
Part of the contract patching system for OMN-1126.

Related:
    - OMN-1126: ModelContractPatch & Patch Validation
    - OMN-1086: ModelHandlerBehavior
    - models/runtime/model_handler_behavior.py: Full behavior model

.. versionadded:: 0.4.0
"""

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    """Partial behavior overrides within a contract patch.

    Behavior patches allow selective override of handler behavior settings
    without specifying a complete behavior configuration. Only the fields
    that need to change are included; unspecified fields retain their values
    from the base contract's behavior.

    This model is used in the `descriptor` field of ModelContractPatch.
    The field name is 'descriptor' for historical reasons, but the concept
    is handler behavior configuration.

    All fields are optional since patches only specify overrides.

    Attributes:
        purity: Override purity (pure vs side-effecting). Pure handlers
            have no side effects and are safe to cache/parallelize.
        idempotent: Override idempotency flag. Idempotent handlers can be
            safely retried without causing duplicate effects.
        timeout_ms: Override handler timeout in milliseconds. Maximum
            allowed value is 3,600,000 (1 hour).
        retry_policy: Override retry configuration for transient failures.
        circuit_breaker: Override circuit breaker for fault tolerance.
        concurrency_policy: Override how concurrent invocations are handled
            (parallel_ok, serialized, or singleflight).
        isolation_policy: Override process/container isolation level.
        observability_level: Override telemetry and logging verbosity.

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

        >>> # Check if patch has any overrides
        >>> if patch.has_overrides():
        ...     print(f"Overriding: {patch.get_override_fields()}")

    See Also:
        - ModelContractPatch: Parent patch model that contains this
        - ModelHandlerBehavior (runtime): Full behavior model this patches
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

    # Maximum timeout: 1 hour (3,600,000 ms) to prevent unreasonable values
    # that could cause resource exhaustion or effectively disable timeouts
    MAX_TIMEOUT_MS: ClassVar[int] = 3_600_000

    # Note: le= must use literal value because Pydantic Field() evaluates at class
    # definition time before ClassVar is available. Keep in sync with MAX_TIMEOUT_MS.
    timeout_ms: int | None = Field(
        default=None,
        ge=0,
        le=3_600_000,
        description=(
            "Override handler timeout in milliseconds. "
            "Maximum allowed value is 3,600,000 (1 hour). See MAX_TIMEOUT_MS."
        ),
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

    # =========================================================================
    # Validators
    # =========================================================================

    @model_validator(mode="after")
    def validate_settings_consistency(self) -> "ModelDescriptorPatch":
        """Validate that behavior patch settings are internally consistent.

        Catches conflicting configurations that, while individually valid,
        would produce nonsensical runtime behavior when combined.

        Validates:
            - timeout_ms=0 (no timeout) with retry_policy.enabled=True is invalid
              because retries without a timeout could wait forever per attempt.
            - idempotent=False with retry_policy.enabled=True is invalid because
              retrying non-idempotent operations could cause duplicate side effects.

        Returns:
            Self if validation passes.

        Raises:
            ValueError: If conflicting settings are detected.

        Note:
            This validator only checks fields that are explicitly set in the patch.
            Fields that are None are not validated since they will retain values
            from the base contract.
        """
        # Early return: skip validation if no overrides are set
        # This is an optimization for empty patches
        if not self.has_overrides():
            return self

        # Early return: skip conflict checks if retry_policy is not set
        # Both conflict checks require retry_policy to be present
        if self.retry_policy is None:
            return self

        # Check: timeout_ms=0 with retry enabled
        # Type narrowing: retry_policy is guaranteed non-None after above check
        if self.timeout_ms == 0:
            if self.retry_policy.enabled and self.retry_policy.max_retries > 0:
                raise ValueError(
                    "Conflicting settings: cannot enable retry_policy with "
                    "timeout_ms=0. With no timeout, each retry attempt could wait "
                    "forever. Either set a positive timeout_ms or disable retries."
                )

        # Check: non-idempotent with retry enabled
        # Type narrowing: retry_policy is guaranteed non-None after early return
        if self.idempotent is False:
            if self.retry_policy.enabled and self.retry_policy.max_retries > 0:
                raise ValueError(
                    "Conflicting settings: cannot enable retry_policy when "
                    "idempotent=False. Retrying non-idempotent operations could "
                    "cause duplicate side effects. Either mark the handler as "
                    "idempotent=True or disable retries."
                )

        return self

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def has_overrides(self) -> bool:
        """Check if this behavior patch contains any overrides.

        Returns:
            True if at least one behavior field is set to a non-None value.
            Returns False if the patch is empty (no-op).

        Example:
            >>> empty_patch = ModelDescriptorPatch()
            >>> assert not empty_patch.has_overrides()
            >>> timeout_patch = ModelDescriptorPatch(timeout_ms=5000)
            >>> assert timeout_patch.has_overrides()
        """
        return any(getattr(self, field) is not None for field in self.model_fields)

    def get_override_fields(self) -> list[str]:
        """Get list of behavior field names that have overrides.

        Returns:
            List of field names with non-None values. Empty list if no
            overrides are set.

        Example:
            >>> patch = ModelDescriptorPatch(timeout_ms=5000, idempotent=True)
            >>> patch.get_override_fields()
            ['idempotent', 'timeout_ms']  # Order may vary
        """
        return [
            field for field in self.model_fields if getattr(self, field) is not None
        ]

    def __repr__(self) -> str:
        """Return a concise representation for debugging.

        Returns:
            String representation showing either 'empty' or the list of
            overridden field names.

        Example:
            >>> str(ModelDescriptorPatch())
            'ModelDescriptorPatch(empty)'
            >>> str(ModelDescriptorPatch(timeout_ms=5000))
            "ModelDescriptorPatch(overrides=['timeout_ms'])"
        """
        overrides = self.get_override_fields()
        if not overrides:
            return "ModelDescriptorPatch(empty)"
        return f"ModelDescriptorPatch(overrides={overrides})"
