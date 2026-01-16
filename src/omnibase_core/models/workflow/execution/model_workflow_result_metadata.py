"""
Typed metadata model for workflow execution results.

This module provides ModelWorkflowResultMetadata which replaces the
untyped dict[str, ModelSchemaValue] pattern in ModelDeclarativeWorkflowResult
with strongly-typed fields for full type safety and IDE support.

Thread Safety:
    ModelWorkflowResultMetadata is immutable (frozen=True) after creation.
    Once constructed, instances are safe to share across threads without
    synchronization since no mutation is possible.

Key Features:
    - Full type safety for all metadata fields
    - IDE autocomplete and type checking support
    - No dict-based escape hatches - all fields are explicitly typed
    - Based on actual usage audit of workflow_executor.py
    - Immutable after creation (frozen=True) for thread safety

Example:
    >>> from omnibase_core.models.workflow.execution import (
    ...     ModelWorkflowResultMetadata,
    ... )
    >>>
    >>> # Create metadata for a completed workflow
    >>> metadata = ModelWorkflowResultMetadata(
    ...     execution_mode="sequential",
    ...     workflow_name="data_pipeline",
    ...     workflow_hash="a1b2c3d4e5f6...",
    ... )
    >>>
    >>> # For batch workflows, include batch_size
    >>> batch_metadata = ModelWorkflowResultMetadata(
    ...     execution_mode="batch",
    ...     workflow_name="bulk_processor",
    ...     workflow_hash="f6e5d4c3b2a1...",
    ...     batch_size=100,
    ... )

See Also:
    - omnibase_core.models.workflow.execution.model_declarative_workflow_result:
        Parent model that uses this metadata
    - omnibase_core.utils.util_workflow_executor: Source of field requirements
    - docs/guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md: Tutorial
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelWorkflowResultMetadata(BaseModel):
    """Typed metadata for declarative workflow execution results.

    Replaces dict[str, ModelSchemaValue] with strongly-typed fields.
    All fields are based on actual usage audit of workflow_executor.py.

    This model is frozen (immutable) after creation, making it safe to
    share across threads without synchronization.

    Attributes:
        execution_mode: Workflow execution mode - one of "sequential",
            "parallel", or "batch". Required field with no default.
        workflow_name: Name of the executed workflow from the workflow
            definition. Required field with no default.
        workflow_hash: SHA-256 hash of the workflow definition for integrity
            verification. 64-character hexadecimal string. Defaults to "".
        batch_size: Number of workflow steps. Only set for batch execution
            mode. Defaults to None.

    Example:
        >>> metadata = ModelWorkflowResultMetadata(
        ...     execution_mode="sequential",
        ...     workflow_name="data_pipeline",
        ...     workflow_hash="a1b2c3d4...",
        ... )
        >>> metadata.execution_mode
        'sequential'
        >>> metadata.workflow_name
        'data_pipeline'

    Note:
        Once created, instances cannot be modified (frozen=True). Create a
        new instance if different values are needed.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    execution_mode: Literal["sequential", "parallel", "batch"] = Field(
        ...,
        description="Workflow execution mode",
    )

    workflow_name: str = Field(
        ...,
        description="Name of the executed workflow from workflow definition",
    )

    workflow_hash: str = Field(
        default="",
        pattern=r"^$|^[a-fA-F0-9]{64}$",
        description=(
            "SHA-256 hash of workflow definition for integrity verification. "
            "Must be empty string or exactly 64 hexadecimal characters (0-9, a-f, A-F)."
        ),
    )

    batch_size: int | None = Field(
        default=None,
        description="Number of workflow steps (only set for batch execution mode)",
    )


__all__ = ["ModelWorkflowResultMetadata"]
