"""Pipeline execution infrastructure for ONEX."""

from omnibase_core.pipeline.exceptions import (
    DependencyCycleError,
    DuplicateHookError,
    HookRegistryFrozenError,
    HookTypeMismatchError,
    PipelineError,
    UnknownDependencyError,
)
from omnibase_core.pipeline.hook_registry import HookRegistry
from omnibase_core.pipeline.middleware_composer import Middleware, MiddlewareComposer
from omnibase_core.pipeline.models import (
    ModelExecutionPlan,
    ModelPhaseExecutionPlan,
    ModelPipelineHook,
    ModelValidationWarning,
    PipelinePhase,
)
from omnibase_core.pipeline.pipeline_runner import (
    CANONICAL_PHASE_ORDER,
    HookCallable,
    ModelHookError,
    PipelineContext,
    PipelineResult,
    PipelineRunner,
)
from omnibase_core.pipeline.runtime_plan_builder import RuntimePlanBuilder

__all__ = [
    # Exceptions
    "DependencyCycleError",
    "DuplicateHookError",
    "HookRegistryFrozenError",
    "HookTypeMismatchError",
    "PipelineError",
    "UnknownDependencyError",
    # Registry
    "HookRegistry",
    # Middleware
    "Middleware",
    "MiddlewareComposer",
    # Builder
    "RuntimePlanBuilder",
    # Runner
    "CANONICAL_PHASE_ORDER",
    "HookCallable",
    "ModelHookError",
    "PipelineContext",
    "PipelineResult",
    "PipelineRunner",
    # Models
    "ModelExecutionPlan",
    "ModelPhaseExecutionPlan",
    "ModelPipelineHook",
    "ModelValidationWarning",
    "PipelinePhase",
]
