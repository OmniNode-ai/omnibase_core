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

Example:
    >>> from omnibase_core.models.effect import ModelEffectInput
    >>> from omnibase_core.enums.enum_effect_types import EnumEffectType
    >>>
    >>> # Database operation with transaction and retry
    >>> input_data = ModelEffectInput(
    ...     effect_type=EnumEffectType.DATABASE_OPERATION,
    ...     operation_data={"table": "users", "data": {"name": "Alice"}},
    ...     transaction_enabled=True,
    ...     retry_enabled=True,
    ...     max_retries=3,
    ... )
    >>>
    >>> # API call with circuit breaker
    >>> api_input = ModelEffectInput(
    ...     effect_type=EnumEffectType.API_CALL,
    ...     operation_data={"url": "https://api.example.com", "method": "POST"},
    ...     circuit_breaker_enabled=True,
    ...     timeout_ms=5000,
    ... )
    >>>
    >>> # Typed operation data using ModelEffectInputData (recommended for new code)
    >>> from omnibase_core.models.context import ModelEffectInputData
    >>> typed_input = ModelEffectInput(
    ...     effect_type=EnumEffectType.API_CALL,
    ...     operation_data=ModelEffectInputData(
    ...         effect_type=EnumEffectType.API_CALL,
    ...         resource_path="https://api.example.com/users",
    ...         target_system="user-service",
    ...         operation_name="create_user",
    ...     ),
    ... )

See Also:
    - omnibase_core.models.effect.model_effect_output: Corresponding output model
    - omnibase_core.nodes.node_effect: NodeEffect implementation
    - docs/guides/node-building/04_EFFECT_NODE_TUTORIAL.md: Effect node tutorial
"""

from datetime import UTC, datetime
from typing import Any, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from omnibase_core.constants import TIMEOUT_DEFAULT_MS
from omnibase_core.enums.enum_effect_types import EnumEffectType
from omnibase_core.models.context import ModelEffectInputData
from omnibase_core.models.effect.model_effect_metadata import ModelEffectMetadata
from omnibase_core.utils.util_decorators import allow_dict_str_any

__all__ = ["ModelEffectInput"]


@allow_dict_str_any(
    "Effect operations support typed operation_data (ModelEffectInputData) and "
    "dict[str, Any] for flexible payloads with various external I/O types "
    "(database queries, API payloads, file operations, message queue bodies)."
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
        operation_data: Payload data for the operation. Accepts ModelEffectInputData
            for typed effect operations or dict[str, Any] for flexible payloads.
            Structure depends on effect_type (e.g., SQL query for database, URL for API).
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

    Example:
        Untyped usage (backwards compatible)::

            input_data = ModelEffectInput(
                effect_type=EnumEffectType.FILE_OPERATION,
                operation_data={"path": "/data/output.json", "action": "write"},
                timeout_ms=10000,
                transaction_enabled=False,
            )

        Using ModelEffectInputData (recommended for new code)::

            from omnibase_core.models.context import ModelEffectInputData

            typed_input = ModelEffectInput(
                effect_type=EnumEffectType.FILE_OPERATION,
                operation_data=ModelEffectInputData(
                    effect_type=EnumEffectType.FILE_OPERATION,
                    resource_path="/data/output.json",
                    target_system="local-fs",
                    operation_name="write_output",
                ),
                timeout_ms=10000,
            )

    See Also:
        - omnibase_core.models.effect.model_effect_output: Corresponding output model
        - omnibase_core.nodes.node_effect: NodeEffect implementation
        - docs/guides/node-building/04_EFFECT_NODE_TUTORIAL.md: Effect node tutorial
    """

    effect_type: EnumEffectType
    operation_data: ModelEffectInputData | dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Operation payload data. Accepts ModelEffectInputData for typed effect "
            "operations or dict[str, Any] for flexible payloads. Structure depends "
            "on effect_type (e.g., SQL query for database, URL for API)."
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
        """Validate effect_type consistency between parent and operation_data.

        When operation_data is a typed ModelEffectInputData (not a dict), its
        effect_type must match the parent effect_type. This prevents confusing
        bugs where routing decisions (based on parent effect_type) conflict with
        the actual data structure (based on nested effect_type).

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If operation_data.effect_type differs from parent effect_type.

        Example:
            # Valid - both effect_types match:
            ModelEffectInput(
                effect_type=EnumEffectType.API_CALL,
                operation_data=ModelEffectInputData(
                    effect_type=EnumEffectType.API_CALL,  # Matches parent
                    resource_path="https://api.example.com",
                ),
            )

            # Invalid - mismatched effect_types raise ValueError:
            ModelEffectInput(
                effect_type=EnumEffectType.API_CALL,
                operation_data=ModelEffectInputData(
                    effect_type=EnumEffectType.DATABASE_OPERATION,  # Mismatch!
                ),
            )
        """
        if isinstance(self.operation_data, ModelEffectInputData):
            if self.operation_data.effect_type != self.effect_type:
                raise ValueError(
                    f"effect_type mismatch: parent effect_type is "
                    f"{self.effect_type.value!r} but operation_data.effect_type is "
                    f"{self.operation_data.effect_type.value!r}. When using typed "
                    f"ModelEffectInputData, both effect_type fields must match to "
                    f"ensure consistent routing and data handling."
                )
        return self
