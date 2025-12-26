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
        >>>
        >>> checkpoint = ModelCheckpointMetadata(
        ...     checkpoint_type="automatic",
        ...     source_node="node_compute_transform",
        ...     trigger_event="stage_complete",
        ...     workflow_stage="processing",
        ...     parent_checkpoint_id="chk_parent_123",
        ... )
        >>> checkpoint.checkpoint_type
        'automatic'
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    checkpoint_type: EnumCheckpointType | str | None = Field(
        default=None,
        description=(
            "Type of checkpoint (e.g., automatic, manual, recovery). "
            "Accepts EnumCheckpointType or string."
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
            "Accepts EnumTriggerEvent or string."
        ),
    )
    workflow_stage: str | None = Field(
        default=None,
        description="Current workflow stage",
    )
    parent_checkpoint_id: str | None = Field(
        default=None,
        description="Parent checkpoint ID",
    )

    @field_validator("checkpoint_type", mode="before")
    @classmethod
    def normalize_checkpoint_type(
        cls, v: EnumCheckpointType | str | None
    ) -> EnumCheckpointType | str | None:
        """Accept both enum and string values for backward compatibility.

        Args:
            v: The checkpoint type value, either as EnumCheckpointType,
               string, or None.

        Returns:
            The normalized value - EnumCheckpointType if valid enum value,
            else the original string for backward compatibility.
        """
        if v is None:
            return None
        if isinstance(v, EnumCheckpointType):
            return v
        # Try to convert string to enum (v must be str at this point)
        try:
            return EnumCheckpointType(v.lower())
        except ValueError:
            # Keep as string if not a valid enum value (backward compat)
            return v

    @field_validator("trigger_event", mode="before")
    @classmethod
    def normalize_trigger_event(
        cls, v: EnumTriggerEvent | str | None
    ) -> EnumTriggerEvent | str | None:
        """Accept both enum and string values for backward compatibility.

        Args:
            v: The trigger event value, either as EnumTriggerEvent,
               string, or None.

        Returns:
            The normalized value - EnumTriggerEvent if valid enum value,
            else the original string for backward compatibility.
        """
        if v is None:
            return None
        if isinstance(v, EnumTriggerEvent):
            return v
        # Try to convert string to enum (v must be str at this point)
        try:
            return EnumTriggerEvent(v.lower())
        except ValueError:
            # Keep as string if not a valid enum value (backward compat)
            return v
