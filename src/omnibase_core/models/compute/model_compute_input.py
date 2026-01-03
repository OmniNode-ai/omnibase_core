"""
Strongly typed input model for NodeCompute operations.

This module provides the ModelComputeInput generic model that wraps computation
input data with metadata for operation tracking, caching configuration, and
parallel execution control.

Thread Safety:
    ModelComputeInput is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

Key Features:
    - Generic type parameter T_Input for type-safe input data
    - Automatic operation_id generation for tracking
    - Configurable caching and parallel execution
    - Timestamp tracking for audit and debugging

Example:
    >>> from omnibase_core.models import ModelComputeInput
    >>>
    >>> # Simple input with caching enabled
    >>> input_data = ModelComputeInput(
    ...     data={"text": "hello world"},
    ...     computation_type="text_transform",
    ...     cache_enabled=True,
    ... )
    >>>
    >>> # Typed input for specific data structure
    >>> from pydantic import BaseModel
    >>> class UserData(BaseModel):
    ...     name: str
    ...     age: int
    >>>
    >>> typed_input: ModelComputeInput[UserData] = ModelComputeInput(
    ...     data=UserData(name="Alice", age=30),
    ...     computation_type="user_validation",
    ...     parallel_enabled=True,
    ... )

See Also:
    - omnibase_core.models.model_compute_output: Corresponding output model
    - omnibase_core.nodes.node_compute: NodeCompute.process() uses this model
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_serializable_value import SerializedDict

__all__ = [
    "ModelComputeInput",
]


class ModelComputeInput[T_Input](BaseModel):
    """
    Input model for NodeCompute operations.

    Strongly typed input wrapper that ensures type safety and provides metadata
    for computation tracking, caching control, and parallel execution configuration.

    Type Parameters:
        T_Input: The type of the data being processed. Can be any type including
            primitives, dictionaries, lists, or Pydantic models.

    Attributes:
        data: The actual input data to process. Type is determined by the
            generic parameter T_Input.
        operation_id: Unique identifier for this operation instance. Auto-generated
            UUID by default. Used for logging, tracing, and correlation.
        computation_type: String identifier for the type of computation to perform.
            Used to select the appropriate computation function from the registry.
            Defaults to "default".
        cache_enabled: Whether to use cached results if available. When True,
            the compute node will check its cache before executing and store
            results for future use. Defaults to True.
        parallel_enabled: Whether to allow parallel execution for batch operations.
            When True and the data supports it (e.g., list input), the compute
            node may process items in parallel. Defaults to False.
        metadata: Additional context metadata as key-value pairs. Can be used
            for custom tracking, feature flags, or computation parameters.
        timestamp: When this input was created. Auto-generated to current time.
            Useful for audit trails and timeout calculations.

    Example:
        >>> # Basic usage with default settings
        >>> input_data = ModelComputeInput(
        ...     data="hello world",
        ...     computation_type="string_uppercase",
        ... )
        >>>
        >>> # With all options configured
        >>> input_data = ModelComputeInput(
        ...     data=[1, 2, 3, 4, 5],
        ...     computation_type="sum_numbers",
        ...     cache_enabled=False,  # Always recompute
        ...     parallel_enabled=True,  # Allow parallel processing
        ...     metadata={"source": "user_input", "priority": "high"},
        ... )
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,  # pytest-xdist compatibility
    )

    data: T_Input
    operation_id: UUID = Field(default_factory=uuid4)
    computation_type: str = "default"
    cache_enabled: bool = True
    parallel_enabled: bool = False
    metadata: SerializedDict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
