"""
Input model for NodeEffect operations.

This module provides the ModelEffectInput model that wraps side effect
operations with comprehensive transaction, retry, and circuit breaker
configuration. Effect nodes handle all external I/O in the ONEX architecture.

Thread Safety:
    ModelEffectInput is mutable by default. If thread-safety is needed,
    create the instance with all required values and treat as read-only
    after creation.

Key Features:
    - Transaction support with automatic rollback
    - Configurable retry with exponential backoff
    - Circuit breaker pattern for fault tolerance
    - Timeout configuration for external operations
    - Metadata for operation tracking and correlation

Design: Contract vs Template Context
    The operation_data field accepts two distinct types:

    1. ModelEffectInputData (strict contract):
       - Validated, audited, type-safe
       - effect_type must match parent effect_type
       - Use for production effect inputs

    2. dict[str, Any] (template context):
       - Flexible, untyped, for template resolution
       - Allows arbitrary keys (user_id, operations, etc.)
       - Use for template placeholders like ${input.user_id}

    These are intentionally separate concepts - don't try to coerce one to the other.

Example:
    Strict contract (production)::

        >>> from omnibase_core.models.effect import ModelEffectInput
        >>> from omnibase_core.models.context import ModelEffectInputData
        >>> from omnibase_core.enums.enum_effect_types import EnumEffectType
        >>>
        >>> input_data = ModelEffectInput(
        ...     effect_type=EnumEffectType.API_CALL,
        ...     operation_data=ModelEffectInputData(
        ...         effect_type=EnumEffectType.API_CALL,
        ...         resource_path="https://api.example.com/users",
        ...         target_system="user-service",
        ...         operation_name="create_user",
        ...     ),
        ...     timeout_ms=5000,
        ... )

    Template context (testing/dynamic)::

        >>> input_data = ModelEffectInput(
        ...     effect_type=EnumEffectType.API_CALL,
        ...     operation_data={"user_id": "123", "action": "fetch"},
        ... )

See Also:
    - omnibase_core.models.effect.model_effect_output: Corresponding output model
    - omnibase_core.models.context.ModelTemplateContext: Explicit template context
    - omnibase_core.nodes.node_effect: NodeEffect implementation
"""

from datetime import UTC, datetime
from typing import Any, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from omnibase_core.constants import TIMEOUT_DEFAULT_MS
from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any
from omnibase_core.enums.enum_effect_types import EnumEffectType
from omnibase_core.models.context import ModelEffectInputData
from omnibase_core.models.effect.model_effect_metadata import ModelEffectMetadata

__all__ = ["ModelEffectInput"]


@allow_dict_any(
    reason="operation_data intentionally accepts both strict contracts "
    "(ModelEffectInputData) and template contexts (dict) for different use cases. "
    "See module docstring for the design rationale."
)
class ModelEffectInput(BaseModel):
    """
    Input model for NodeEffect operations.

    Strongly typed input wrapper for side effect operations with comprehensive
    configuration for transactions, retries, circuit breakers, and timeouts.
    Used by NodeEffect to execute external I/O operations safely.

    Attributes:
        effect_type: Type of side effect operation (DATABASE_OPERATION, API_CALL, etc.).
            Determines which handler processes the operation.
        operation_data: Either a strict ModelEffectInputData contract or a dict for
            template context. See module docstring for the design rationale.
        operation_id: Unique identifier for tracking this operation. Auto-generated
            UUID by default. Used for correlation and idempotency.
        transaction_enabled: Whether to wrap the operation in a transaction.
            When True, operations are atomic with automatic rollback on failure.
            Defaults to True.
        retry_enabled: Whether to retry failed operations. When True, the effect
            node will retry based on max_retries and retry_delay_ms. Defaults to True.
        max_retries: Maximum number of retry attempts. Only used when retry_enabled
            is True. Defaults to 3.
        retry_delay_ms: Delay between retries in milliseconds. Actual delay may
            use exponential backoff. Defaults to 1000 (1 second).
        circuit_breaker_enabled: Whether to use circuit breaker pattern. When True,
            repeated failures will trip the breaker and fast-fail subsequent requests.
            Defaults to False.
        timeout_ms: Maximum time to wait for operation completion in milliseconds.
            Operations exceeding this timeout are cancelled. Defaults to TIMEOUT_DEFAULT_MS (30 seconds).
            See omnibase_core.constants for timeout constant values.
        metadata: Typed metadata for tracking, tracing, correlation, and operation context.
            Includes fields like trace_id, correlation_id, environment, tags, and priority.
        timestamp: When this input was created. Auto-generated to current UTC time.
    """

    effect_type: EnumEffectType
    operation_data: ModelEffectInputData | dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Operation payload. Either ModelEffectInputData (strict contract with "
            "effect_type validation) or dict (template context for dynamic resolution). "
            "Dicts are NOT coerced to ModelEffectInputData - they remain as template contexts."
        ),
    )
    operation_id: UUID = Field(
        default_factory=uuid4,
        description=(
            "Unique identifier for tracking this operation. Auto-generated UUID "
            "by default. Used for correlation and idempotency."
        ),
    )
    transaction_enabled: bool = True
    retry_enabled: bool = True
    max_retries: int = 3
    retry_delay_ms: int = 1000
    circuit_breaker_enabled: bool = False
    timeout_ms: int = TIMEOUT_DEFAULT_MS
    metadata: ModelEffectMetadata = Field(
        default_factory=ModelEffectMetadata,
        description=(
            "Typed metadata for tracking, tracing, correlation, and operation "
            "context. Includes fields like trace_id, correlation_id, environment, "
            "tags, and priority."
        ),
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this input was created. Auto-generated to current UTC time.",
    )

    @model_validator(mode="after")
    def _validate_effect_type_consistency(self) -> Self:
        """Validate effect_type consistency when operation_data is a strict contract.

        Only validates when operation_data is a ModelEffectInputData (strict contract).
        Dict operation_data (template context) is not validated - it's for dynamic use.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If operation_data is ModelEffectInputData and effect_type differs.
        """
        # Only validate strict contracts, not template contexts
        if isinstance(self.operation_data, ModelEffectInputData):
            if self.operation_data.effect_type != self.effect_type:
                raise ValueError(
                    f"effect_type mismatch: parent effect_type is "
                    f"{self.effect_type.value!r} but operation_data.effect_type is "
                    f"{self.operation_data.effect_type.value!r}. Both effect_type "
                    f"fields must match to ensure consistent routing and data handling."
                )
        return self
