# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Execution plan model for pipeline hooks.

Note: This module was moved from omnibase_core.pipeline.models to
omnibase_core.models.pipeline to comply with ONEX repository structure
validation that requires all models in src/omnibase_core/models/.

The class was renamed from ModelExecutionPlan to ModelPipelineExecutionPlan
to avoid naming conflicts with omnibase_core.models.execution.ModelExecutionPlan
which serves a different purpose (runtime execution sequencing).
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.pipeline.model_pipeline_hook import (
    ModelPipelineHook,
    PipelinePhase,
)
from omnibase_core.models.pipeline.model_pipeline_phase_execution_plan import (
    ModelPhaseExecutionPlan,
    ModelPipelinePhaseExecutionPlan,
)


class ModelPipelineExecutionPlan(BaseModel):
    """
    Complete execution plan for a pipeline run.

    Contains hooks organized by phase in topologically sorted order,
    ready for execution by the PipelineRunner.

    Thread Safety: This class is thread-safe. Instances are immutable
    (frozen=True) and can be safely shared across threads. The same
    execution plan can be used by multiple ``RunnerPipeline`` instances.

    Note: This class was renamed from ModelExecutionPlan to
    ModelPipelineExecutionPlan to avoid naming conflicts with
    omnibase_core.models.execution.ModelExecutionPlan.
    """

    # TODO(pydantic-v3): Re-evaluate from_attributes=True when Pydantic v3 is released.
    # Workaround for pytest-xdist class identity issues. See model_pipeline_hook.py
    # module docstring for detailed explanation.
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    phases: dict[PipelinePhase, ModelPipelinePhaseExecutionPlan] = Field(
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
    def empty(cls) -> "ModelPipelineExecutionPlan":
        """Create an empty execution plan."""
        return cls()


# Legacy alias for migration
ModelExecutionPlan = ModelPipelineExecutionPlan


__all__ = [
    "ModelPipelineExecutionPlan",
    # Re-export for convenience
    "ModelPipelinePhaseExecutionPlan",
    # Legacy aliases
    "ModelExecutionPlan",
    "ModelPhaseExecutionPlan",
]
