"""
Action Model.

Orchestrator-issued Action with lease semantics for single-writer guarantees.
Converted from NamedTuple to Pydantic BaseModel for better validation.

Thread Safety:
    ModelAction is immutable (frozen=True) after creation, making it thread-safe
    for concurrent read access from multiple threads or async tasks. This follows
    ONEX thread safety guidelines where action models are frozen to ensure lease
    semantics and epoch tracking remain consistent during distributed coordination.
    Note that this provides shallow immutability - while the model's fields cannot
    be reassigned, mutable field values (like dict/list contents) can still be
    modified. For full thread safety with mutable nested data, use
    model_copy(deep=True) to create independent copies.

    To create a modified copy (e.g., for retry with incremented retry_count):
        new_action = action.model_copy(update={"retry_count": action.retry_count + 1})

Extracted from node_orchestrator.py to eliminate embedded class anti-pattern.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_workflow_execution import EnumActionType
from omnibase_core.models.core.model_action_metadata import ModelActionMetadata
from omnibase_core.utils.util_decorators import allow_dict_str_any


@allow_dict_str_any(
    "Action model requires flexible payload for arbitrary action data "
    "across different action types and workflow contexts."
)
class ModelAction(BaseModel):
    """
    Orchestrator-issued Action with lease management for single-writer semantics.

    Represents an Action emitted by the Orchestrator to Compute/Reducer nodes
    with single-writer semantics enforced via lease_id and epoch. The lease_id
    proves Orchestrator ownership, while epoch provides optimistic concurrency
    control through monotonically increasing version numbers.

    This model is immutable (frozen=True) after creation, making it thread-safe
    for concurrent read access from multiple threads or async tasks. Unknown
    fields are rejected (extra='forbid') to ensure strict schema compliance.

    To modify a frozen instance, use model_copy():
        >>> modified = action.model_copy(update={"priority": 5, "retry_count": 1})

    Attributes:
        action_id: Unique identifier for this action (auto-generated UUID).
        action_type: Type of action for execution routing (required).
        target_node_type: Target node type for action execution (1-100 chars, required).
        payload: Action payload data (default empty dict).
        dependencies: List of action IDs this action depends on (default empty list).
        priority: Execution priority (1-10, higher = more urgent, default 1).
        timeout_ms: Execution timeout (100-300000 ms, default 30000).
        lease_id: Lease ID proving Orchestrator ownership (required).
        epoch: Monotonically increasing version number (>= 0, required).
        retry_count: Number of retry attempts on failure (0-10, default 0).
        metadata: Action execution metadata with full type safety (default ModelActionMetadata()).
        created_at: Timestamp when action was created (auto-generated).

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.enums.enum_workflow_execution import EnumActionType
        >>> action = ModelAction(
        ...     action_type=EnumActionType.INVOKE,
        ...     target_node_type="compute",
        ...     lease_id=uuid4(),
        ...     epoch=1,
        ...     priority=5,
        ... )

    Converted from NamedTuple to Pydantic BaseModel for:
    - Runtime validation with constraint checking
    - Better type safety via Pydantic's type coercion
    - Serialization support (JSON, dict)
    - Default value handling with factories
    - Lease validation for single-writer semantics
    - Thread safety via immutability (frozen=True)
    """

    action_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this action",
    )

    action_type: EnumActionType = Field(
        default=...,
        description="Type of action for execution routing",
    )

    target_node_type: str = Field(
        default=...,
        description="Target node type for action execution",
        min_length=1,
        max_length=100,
    )

    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Action payload data",
    )

    dependencies: list[UUID] = Field(
        default_factory=list,
        description="List of action IDs this action depends on",
    )

    priority: int = Field(
        default=1,
        description="Execution priority (higher = more urgent)",
        ge=1,
        le=10,
    )

    timeout_ms: int = Field(
        default=30000,
        description="Execution timeout in milliseconds",
        ge=100,
        le=300000,  # Max 5 minutes
    )

    # Lease management fields for single-writer semantics
    lease_id: UUID = Field(
        default=...,
        description="Lease ID proving Orchestrator ownership",
    )

    epoch: int = Field(
        default=...,
        description="Monotonically increasing version number",
        ge=0,
    )

    retry_count: int = Field(
        default=0,
        description="Number of retry attempts on failure",
        ge=0,
        le=10,
    )

    metadata: ModelActionMetadata = Field(
        default_factory=ModelActionMetadata,
        description="Action execution metadata with full type safety",
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when action was created",
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
        from_attributes=True,
    )
