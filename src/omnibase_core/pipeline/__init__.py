# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Pipeline execution infrastructure for ONEX."""

from omnibase_core.models.pipeline import (
    ModelExecutionPlan,
    ModelHookError,
    ModelPhaseExecutionPlan,
    ModelPipelineExecutionPlan,
    ModelPipelineHook,
    ModelPipelinePhaseExecutionPlan,
    ModelValidationWarning,
    PipelineContext,
    PipelinePhase,
    PipelineResult,
)
from omnibase_core.pipeline.builder_execution_plan import (
    FAIL_FAST_PHASES,
    BuilderExecutionPlan,
    RuntimePlanBuilder,
)
from omnibase_core.pipeline.composer_middleware import (
    ComposerMiddleware,
    Middleware,
    MiddlewareComposer,
)
from omnibase_core.pipeline.exceptions import (
    CallableNotFoundError,
    DependencyCycleError,
    DuplicateHookError,
    HookRegistryFrozenError,
    HookTimeoutError,
    HookTypeMismatchError,
    PipelineError,
    UnknownDependencyError,
)
from omnibase_core.pipeline.registry_hook import HookRegistry, RegistryHook
from omnibase_core.pipeline.runner_pipeline import (
    CANONICAL_PHASE_ORDER,
    HookCallable,
    PipelineRunner,
    RunnerPipeline,
)

__all__ = [
    # Exceptions
    "CallableNotFoundError",
    "DependencyCycleError",
    "DuplicateHookError",
    "HookRegistryFrozenError",
    "HookTimeoutError",
    "HookTypeMismatchError",
    "PipelineError",
    "UnknownDependencyError",
    # Registry (new name first, then backwards compat)
    "RegistryHook",
    "HookRegistry",
    # Middleware (new name first, then backwards compat)
    "ComposerMiddleware",
    "Middleware",
    "MiddlewareComposer",
    # Builder (new name first, then backwards compat)
    "BuilderExecutionPlan",
    "FAIL_FAST_PHASES",
    "RuntimePlanBuilder",
    # Runner (new name first, then backwards compat)
    "RunnerPipeline",
    "CANONICAL_PHASE_ORDER",
    "HookCallable",
    "ModelHookError",
    "PipelineContext",
    "PipelineResult",
    "PipelineRunner",
    # Models (new canonical names first, then backwards compat)
    "ModelPipelineExecutionPlan",
    "ModelPipelinePhaseExecutionPlan",
    "ModelPipelineHook",
    "ModelValidationWarning",
    "PipelinePhase",
    # Legacy aliases
    "ModelExecutionPlan",
    "ModelPhaseExecutionPlan",
]
