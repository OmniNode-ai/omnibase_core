# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Pipeline hook model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory


# Canonical phase type
PipelinePhase = Literal["preflight", "before", "execute", "after", "emit", "finalize"]


class ModelPipelineHook(BaseModel):
    """
    Represents a registered hook in the pipeline execution system.

    Hooks are registered for specific phases and ordered by dependencies
    and priority within each phase.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    hook_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this hook",
    )
    phase: PipelinePhase = Field(
        ...,
        description="Pipeline phase where this hook executes",
    )
    handler_type_category: EnumHandlerTypeCategory | None = Field(
        default=None,
        description="Optional type category for validation. None = generic hook (allowed everywhere)",
    )
    priority: int = Field(
        default=100,
        ge=0,
        description="Execution priority within phase. Lower = earlier. Default 100.",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of hook IDs that must execute before this hook",
    )
    callable_ref: str = Field(
        ...,
        min_length=1,
        description="Module path or registry key for the hook callable (NOT raw callable)",
    )
    timeout_seconds: float | None = Field(
        default=None,
        gt=0,
        description="Optional timeout for hook execution in seconds",
    )

    @field_validator("hook_id")
    @classmethod
    def validate_hook_id(cls, v: str) -> str:
        """Ensure hook_id is a valid identifier."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                f"hook_id must be alphanumeric with underscores/hyphens: {v}"
            )
        return v

    @field_validator("dependencies")
    @classmethod
    def validate_dependencies(cls, v: list[str]) -> list[str]:
        """Ensure no duplicate dependencies."""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate dependencies not allowed")
        return v


__all__ = [
    "ModelPipelineHook",
    "PipelinePhase",
]
