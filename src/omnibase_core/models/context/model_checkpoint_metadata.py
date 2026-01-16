"""
Checkpoint metadata model for state persistence.

This module provides ModelCheckpointMetadata, a typed model for checkpoint
state metadata that replaces untyped dict[str, str] fields. It captures
checkpoint type, source, trigger events, and workflow state information.

Thread Safety:
    ModelCheckpointMetadata is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

See Also:
    - omnibase_core.models.context.model_audit_metadata: Audit metadata
    - omnibase_core.models.workflow: Workflow state models
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums import EnumCheckpointType, EnumTriggerEvent
from omnibase_core.utils import create_enum_normalizer

__all__ = ["ModelCheckpointMetadata"]


class ModelCheckpointMetadata(BaseModel):
    """Checkpoint state metadata.

    Provides typed checkpoint information for state persistence, recovery,
    and workflow resumption. Supports hierarchical checkpoints and event
    tracing through workflow stages.

    Attributes:
        checkpoint_type: Type of checkpoint for filtering and processing
            (e.g., "automatic", "manual", "recovery", "snapshot").
        source_node: Identifier of the node that created the checkpoint.
            Used for debugging and workflow visualization.
        trigger_event: Event or condition that triggered the checkpoint
            creation (e.g., "stage_complete", "error", "timeout", "manual").
        workflow_stage: Current workflow stage at checkpoint time
            (e.g., "validation", "processing", "completion").
        parent_checkpoint_id: ID of the parent checkpoint for hierarchical
            checkpoint trees. Enables checkpoint ancestry tracking.

    Thread Safety:
        This model is frozen and immutable after creation.
        Safe for concurrent read access across threads.

    Example:
        >>> from omnibase_core.models.context import ModelCheckpointMetadata
        >>> from omnibase_core.enums import EnumCheckpointType
        >>>
        >>> checkpoint = ModelCheckpointMetadata(
        ...     checkpoint_type="automatic",
        ...     source_node="node_compute_transform",
        ...     trigger_event="stage_complete",
        ...     workflow_stage="processing",
        ...     parent_checkpoint_id="chk_parent_123",
        ... )
        >>> checkpoint.checkpoint_type == EnumCheckpointType.AUTOMATIC
        True
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    checkpoint_type: EnumCheckpointType | str | None = Field(
        default=None,
        description=(
            "Type of checkpoint (e.g., automatic, manual, recovery). "
            "Accepts EnumCheckpointType values or strings."
        ),
    )
    source_node: str | None = Field(
        default=None,
        description="Source node identifier",
    )
    trigger_event: EnumTriggerEvent | str | None = Field(
        default=None,
        description=(
            "Event that triggered checkpoint (e.g., stage_complete, error, timeout). "
            "Accepts EnumTriggerEvent values or strings."
        ),
    )
    workflow_stage: str | None = Field(
        default=None,
        description="Current workflow stage",
    )
    parent_checkpoint_id: UUID | None = Field(
        default=None,
        description="Parent checkpoint ID",
    )

    @field_validator("parent_checkpoint_id", mode="before")
    @classmethod
    def coerce_parent_checkpoint_id(cls, v: UUID | str | None) -> UUID | None:
        """Coerce string UUID values to UUID type.

        Accepts UUID objects directly or valid UUID string representations.

        Args:
            v: The parent checkpoint ID value, either as UUID, string, or None.

        Returns:
            The UUID value, or None if input is None.

        Raises:
            ValueError: If the string value is not a valid UUID format.
        """
        if v is None:
            return None
        if isinstance(v, UUID):
            return v
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                # error-ok: Pydantic field_validator requires ValueError
                raise ValueError(
                    f"Invalid UUID string for parent_checkpoint_id: '{v}'. "
                    f"Must be a valid UUID format (e.g., '550e8400-e29b-41d4-a716-446655440000')"
                ) from None
        # error-ok: Pydantic field_validator requires ValueError
        raise ValueError(
            f"parent_checkpoint_id must be UUID or str, got {type(v).__name__}"
        )

    @field_validator("checkpoint_type", mode="before")
    @classmethod
    def normalize_checkpoint_type(
        cls, v: EnumCheckpointType | str | None
    ) -> EnumCheckpointType | str | None:
        """Normalize checkpoint type from string or enum input.

        Args:
            v: The checkpoint type value, either as EnumCheckpointType,
               string, or None.

        Returns:
            The normalized value - EnumCheckpointType if valid enum value,
            otherwise the original string for extensibility.
        """
        return create_enum_normalizer(EnumCheckpointType)(v)

    @field_validator("trigger_event", mode="before")
    @classmethod
    def normalize_trigger_event(
        cls, v: EnumTriggerEvent | str | None
    ) -> EnumTriggerEvent | str | None:
        """Normalize trigger event from string or enum input.

        Args:
            v: The trigger event value, either as EnumTriggerEvent,
               string, or None.

        Returns:
            The normalized value - EnumTriggerEvent if valid enum value,
            otherwise the original string for extensibility.
        """
        return create_enum_normalizer(EnumTriggerEvent)(v)
