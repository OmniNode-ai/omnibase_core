"""
ONEX Pipeline Module.

This module provides pipeline execution infrastructure and observability:

**Execution Infrastructure:**

- **RegistryHook**: Hook registration and management
- **ComposerMiddleware**: Middleware composition
- **BuilderExecutionPlan**: Execution plan building
- **RunnerPipeline**: Pipeline execution

**Observability (OMN-1113):**

- **ManifestGenerator**: Accumulates observations during pipeline execution
  and builds immutable execution manifests.
- **ManifestObserver**: Attaches to pipeline context for non-invasive
  instrumentation.
- **ManifestLogger**: Outputs manifests in various formats (JSON, YAML,
  Markdown, text).

Example:
    >>> from omnibase_core.pipeline import ManifestGenerator, ManifestObserver
    >>> from omnibase_core.models.manifest import ModelNodeIdentity, ModelContractIdentity
    >>> from omnibase_core.enums.enum_node_kind import EnumNodeKind
    >>> from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
    >>> from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
    >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
    >>>
    >>> # Create generator
    >>> generator = ManifestGenerator(
    ...     node_identity=ModelNodeIdentity(
    ...         node_id="compute-001",
    ...         node_kind=EnumNodeKind.COMPUTE,
    ...         node_version=ModelSemVer(major=1, minor=0, patch=0),
    ...     ),
    ...     contract_identity=ModelContractIdentity(contract_id="contract-001"),
    ... )
    >>>
    >>> # Record execution events
    >>> generator.start_hook("hook-1", "handler-1", EnumHandlerExecutionPhase.EXECUTE)
    >>> generator.complete_hook("hook-1", EnumExecutionStatus.SUCCESS)
    >>>
    >>> # Build final manifest
    >>> manifest = generator.build()

See Also:
    - :mod:`omnibase_core.models.manifest`: Manifest model definitions

.. versionadded:: 0.4.0
    Added Manifest Generation & Observability (OMN-1113)
"""

from omnibase_core.models.pipeline import (
    ModelHookError,
    ModelPhaseExecutionPlan,
    ModelPipelineContext,
    ModelPipelineExecutionPlan,
    ModelPipelineHook,
    ModelPipelineResult,
    ModelValidationWarning,
    PipelinePhase,
)
from omnibase_core.pipeline.builder_execution_plan import (
    FAIL_FAST_PHASES,
    BuilderExecutionPlan,
)
from omnibase_core.pipeline.composer_middleware import (
    ComposerMiddleware,
    Middleware,
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
from omnibase_core.pipeline.manifest_generator import ManifestGenerator
from omnibase_core.pipeline.manifest_logger import ManifestLogger
from omnibase_core.pipeline.manifest_observer import ManifestObserver
from omnibase_core.pipeline.registry_hook import RegistryHook
from omnibase_core.pipeline.runner_pipeline import (
    CANONICAL_PHASE_ORDER,
    HookCallable,
    RunnerPipeline,
)
from omnibase_core.services.replay.service_rng_injector import ServiceRNGInjector

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
    # Registry
    "RegistryHook",
    # Middleware
    "ComposerMiddleware",
    "Middleware",
    # Builder
    "BuilderExecutionPlan",
    "FAIL_FAST_PHASES",
    # Runner
    "RunnerPipeline",
    "CANONICAL_PHASE_ORDER",
    "HookCallable",
    "ModelHookError",
    "ModelPipelineContext",
    "ModelPipelineResult",
    # Models
    "ModelPhaseExecutionPlan",
    "ModelPipelineExecutionPlan",
    "ModelPipelineHook",
    "ModelValidationWarning",
    "PipelinePhase",
    # Manifest Generation & Observability (OMN-1113)
    "ManifestGenerator",
    "ManifestObserver",
    "ManifestLogger",
    # Replay Infrastructure (OMN-1116)
    "ServiceRNGInjector",
]
