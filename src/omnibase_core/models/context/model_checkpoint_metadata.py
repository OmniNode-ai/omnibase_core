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

from pydantic import BaseModel, ConfigDict, Field

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

    checkpoint_type: str | None = Field(
        default=None,
        description="Type of checkpoint",
    )
    source_node: str | None = Field(
        default=None,
        description="Source node identifier",
    )
    trigger_event: str | None = Field(
        default=None,
        description="Event that triggered checkpoint",
    )
    workflow_stage: str | None = Field(
        default=None,
        description="Current workflow stage",
    )
    parent_checkpoint_id: str | None = Field(
        default=None,
        description="Parent checkpoint ID",
    )
