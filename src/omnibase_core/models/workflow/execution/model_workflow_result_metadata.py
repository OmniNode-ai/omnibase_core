"""Typed metadata for workflow execution results.

Replaces dict[str, ModelSchemaValue] with strongly-typed fields
in ModelDeclarativeWorkflowResult.

Follows ONEX one-model-per-file architecture.
Strict typing is enforced - no Any types in implementation.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelWorkflowResultMetadata(BaseModel):
    """Typed metadata for declarative workflow execution results.

    Replaces dict[str, ModelSchemaValue] with strongly-typed fields.
    All fields are based on actual usage audit of workflow_executor.py.
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
        description="SHA-256 hash of workflow definition for integrity verification (64-char hex)",
    )

    batch_size: int | None = Field(
        default=None,
        description="Number of workflow steps (only set for batch execution mode)",
    )


__all__ = ["ModelWorkflowResultMetadata"]
