# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Execution plan model for pipeline hooks."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.pipeline.models.model_pipeline_hook import (
    ModelPipelineHook,
    PipelinePhase,
)


class ModelPhaseExecutionPlan(BaseModel):
    """Execution plan for a single phase."""

    # TODO(pydantic-v3): Re-evaluate from_attributes=True when Pydantic v3 is released.
    # Workaround for pytest-xdist class identity issues. See model_pipeline_hook.py
    # module docstring for detailed explanation.
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    phase: PipelinePhase = Field(
        ...,
        description="The phase this plan is for",
    )
    hooks: list[ModelPipelineHook] = Field(
        default_factory=list,
        description="Hooks in topologically sorted execution order",
    )
    fail_fast: bool = Field(
        default=True,
        description="Whether to abort on first error in this phase",
    )


class ModelExecutionPlan(BaseModel):
    """
    Complete execution plan for a pipeline run.

    Contains hooks organized by phase in topologically sorted order,
    ready for execution by the PipelineRunner.
    """

    # TODO(pydantic-v3): Re-evaluate from_attributes=True when Pydantic v3 is released.
    # Workaround for pytest-xdist class identity issues. See model_pipeline_hook.py
    # module docstring for detailed explanation.
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    phases: dict[PipelinePhase, ModelPhaseExecutionPlan] = Field(
        default_factory=dict,
        description="Execution plans keyed by phase",
    )
    contract_category: str | None = Field(
        default=None,
        description="The handler type category from the contract (for validation)",
    )
    metadata: dict[str, object] = Field(
        default_factory=dict,
        description="Additional metadata about the plan",
    )

    def get_phase_hooks(self, phase: PipelinePhase) -> list[ModelPipelineHook]:
        """
        Get hooks for a specific phase in execution order.

        Returns:
            A copy of the hooks list (safe to modify without affecting
            internal state).
        """
        if phase not in self.phases:
            return []
        return list(self.phases[phase].hooks)

    def is_phase_fail_fast(self, phase: PipelinePhase) -> bool:
        """Check if a phase should fail fast on error."""
        if phase not in self.phases:
            # Default fail-fast behavior per phase
            return phase in ("preflight", "before", "execute")
        return self.phases[phase].fail_fast

    @property
    def total_hooks(self) -> int:
        """Total number of hooks across all phases."""
        return sum(len(plan.hooks) for plan in self.phases.values())

    @classmethod
    def empty(cls) -> "ModelExecutionPlan":
        """Create an empty execution plan."""
        return cls()


__all__ = [
    "ModelExecutionPlan",
    "ModelPhaseExecutionPlan",
]
