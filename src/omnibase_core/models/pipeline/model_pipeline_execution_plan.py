"""Execution plan model for pipeline hooks."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.pipeline.model_phase_execution_plan import (
    ModelPhaseExecutionPlan,
)
from omnibase_core.models.pipeline.model_pipeline_hook import (
    ModelPipelineHook,
    PipelinePhase,
)


class ModelPipelineExecutionPlan(BaseModel):
    """
    Complete execution plan for a pipeline run.

    Contains hooks organized by phase in topologically sorted order,
    ready for execution by the RunnerPipeline.

    Thread Safety: This class is thread-safe. Instances are immutable
    (frozen=True) and can be safely shared across threads. The same
    execution plan can be used by multiple ``RunnerPipeline`` instances.
    """

    # TODO(OMN-TBD): [pydantic-v3] Re-evaluate from_attributes=True when Pydantic v3 is released.
    # Workaround for pytest-xdist class identity issues. See model_pipeline_hook.py
    # module docstring for detailed explanation.  [NEEDS TICKET]
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
    def empty(cls) -> "ModelPipelineExecutionPlan":
        """Create an empty execution plan."""
        return cls()


__all__ = [
    "ModelPipelineExecutionPlan",
]
