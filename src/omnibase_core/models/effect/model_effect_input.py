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

See Also:
    - omnibase_core.models.effect.model_effect_output: Corresponding output model
    - omnibase_core.nodes.node_effect: NodeEffect implementation
    - docs/guides/node-building/04_EFFECT_NODE_TUTORIAL.md: Effect node tutorial
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_effect_types import EnumEffectType
from omnibase_core.models.common.model_effect_metadata import ModelEffectMetadata
from omnibase_core.utils.util_decorators import allow_dict_str_any


@allow_dict_str_any(
    "Effect operations require flexible operation_data for various external I/O types "
    "(database queries, API payloads, file operations, etc.) and metadata for tracking."
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
        operation_data: Payload data for the operation. Structure depends on
            effect_type (e.g., SQL query for database, URL for API).
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
            Operations exceeding this timeout are cancelled. Defaults to 30000 (30 seconds).
        metadata: Typed metadata for tracking, tracing, correlation, and operation context.
            Includes fields like trace_id, correlation_id, environment, tags, and priority.
        timestamp: When this input was created. Auto-generated to current time.

    Example:
        >>> # File operation with timeout
        >>> input_data = ModelEffectInput(
        ...     effect_type=EnumEffectType.FILE_OPERATION,
        ...     operation_data={"path": "/data/output.json", "action": "write"},
        ...     timeout_ms=10000,
        ...     transaction_enabled=False,
        ... )
    """

    effect_type: EnumEffectType
    operation_data: dict[str, Any]
    operation_id: UUID = Field(default_factory=uuid4)
    transaction_enabled: bool = True
    retry_enabled: bool = True
    max_retries: int = 3
    retry_delay_ms: int = 1000
    circuit_breaker_enabled: bool = False
    timeout_ms: int = 30000
    metadata: ModelEffectMetadata = Field(default_factory=ModelEffectMetadata)
    timestamp: datetime = Field(default_factory=datetime.now)


__all__ = ["ModelEffectInput"]
