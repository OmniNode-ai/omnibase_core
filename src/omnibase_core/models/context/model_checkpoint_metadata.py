# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
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

    checkpoint_type: EnumCheckpointType | None = Field(
        default=None,
        description=(
            "Type of checkpoint (e.g., automatic, manual, recovery). "
            "Must be a valid EnumCheckpointType value."
        ),
    )
    source_node: str | None = Field(
        default=None,
        description="Source node identifier",
    )
    trigger_event: EnumTriggerEvent | None = Field(
        default=None,
        description=(
            "Event that triggered checkpoint (e.g., stage_complete, error, timeout). "
            "Must be a valid EnumTriggerEvent value."
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

    @field_validator("checkpoint_type", mode="before")
    @classmethod
    def normalize_checkpoint_type(
        cls, v: EnumCheckpointType | str | None
    ) -> EnumCheckpointType | None:
        """Normalize and validate checkpoint type to EnumCheckpointType.

        Accepts enum values directly or string representations. Strings are
        normalized via case-insensitive matching to valid enum values.

        Args:
            v: The checkpoint type value, either as EnumCheckpointType,
               string, or None.

        Returns:
            The EnumCheckpointType value, or None if input is None.

        Raises:
            ValueError: If the string value is not a valid EnumCheckpointType.
            TypeError: If the value is neither EnumCheckpointType, str, nor None.
        """
        if v is None:
            return None
        if isinstance(v, EnumCheckpointType):
            return v
        if isinstance(v, str):
            try:
                return EnumCheckpointType(v.lower())
            except ValueError:
                valid_values = [e.value for e in EnumCheckpointType]
                raise ValueError(
                    f"Invalid checkpoint_type '{v}'. Must be one of: {valid_values}"
                ) from None
        raise TypeError(  # error-ok: Pydantic validator requires TypeError for type checks
            f"checkpoint_type must be EnumCheckpointType or str, got {type(v).__name__}"
        )

    @field_validator("trigger_event", mode="before")
    @classmethod
    def normalize_trigger_event(
        cls, v: EnumTriggerEvent | str | None
    ) -> EnumTriggerEvent | None:
        """Normalize and validate trigger event to EnumTriggerEvent.

        Accepts enum values directly or string representations. Strings are
        normalized via case-insensitive matching to valid enum values.

        Args:
            v: The trigger event value, either as EnumTriggerEvent,
               string, or None.

        Returns:
            The EnumTriggerEvent value, or None if input is None.

        Raises:
            ValueError: If the string value is not a valid EnumTriggerEvent.
            TypeError: If the value is neither EnumTriggerEvent, str, nor None.
        """
        if v is None:
            return None
        if isinstance(v, EnumTriggerEvent):
            return v
        if isinstance(v, str):
            try:
                return EnumTriggerEvent(v.lower())
            except ValueError:
                valid_values = [e.value for e in EnumTriggerEvent]
                raise ValueError(
                    f"Invalid trigger_event '{v}'. Must be one of: {valid_values}"
                ) from None
        raise TypeError(  # error-ok: Pydantic validator requires TypeError for type checks
            f"trigger_event must be EnumTriggerEvent or str, got {type(v).__name__}"
        )
