# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Compute pipeline models for contract-driven NodeCompute v1.0.

The core models for compute pipeline execution as defined
in the CONTRACT_DRIVEN_NODECOMPUTE_V1_0 specification. These models support
deterministic, traceable data transformation pipelines with abort-on-first-failure
semantics.

Key Components:
    ModelComputeExecutionContext:
        Typed execution context carrying operation IDs, correlation IDs, and
        node identification for distributed tracing and observability.

    ModelComputeStepMetadata:
        Execution metadata for individual steps including timing information
        and transformation type for performance analysis.

    ModelComputeStepResult:
        Complete result of a single pipeline step including output data,
        success status, metadata, and error details.

    ModelComputePipelineResult:
        Aggregated result of entire pipeline execution with overall status,
        final output, timing, and per-step results.

Thread Safety:
    All models in this module are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.

Example:
    >>> from uuid import uuid4
    >>> from omnibase_core.models.compute import (
    ...     ModelComputeExecutionContext,
    ...     ModelComputePipelineResult,
    ... )
    >>> from omnibase_core.utils.util_compute_executor import execute_compute_pipeline
    >>>
    >>> # Create execution context
    >>> context = ModelComputeExecutionContext(
    ...     operation_id=uuid4(),
    ...     correlation_id=request_correlation_id,
    ... )
    >>>
    >>> # Execute pipeline and get result
    >>> result: ModelComputePipelineResult = execute_compute_pipeline(
    ...     contract, input_data, context
    ... )
    >>> if result.success:
    ...     print(f"Output: {result.output}")
    ... else:
    ...     print(f"Error at '{result.error_step}': {result.error_message}")

See Also:
    - omnibase_core.utils.util_compute_executor: Pipeline execution logic
    - omnibase_core.utils.util_compute_transformations: Transformation functions
    - omnibase_core.models.contracts.subcontracts: Contract definitions
    - docs/guides/node-building/03_COMPUTE_NODE_TUTORIAL.md: Compute node tutorial
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.compute.model_compute_context import ModelComputeContext
    from omnibase_core.models.compute.model_compute_execution_context import (
        ModelComputeExecutionContext,
    )
    from omnibase_core.models.compute.model_compute_input import ModelComputeInput
    from omnibase_core.models.compute.model_compute_output import ModelComputeOutput
    from omnibase_core.models.compute.model_compute_pipeline_result import (
        ModelComputePipelineResult,
    )
    from omnibase_core.models.compute.model_compute_step_metadata import (
        ModelComputeStepMetadata,
    )
    from omnibase_core.models.compute.model_compute_step_result import (
        ModelComputeStepResult,
    )

__all__ = [
    "ModelComputeContext",
    "ModelComputeExecutionContext",
    "ModelComputeInput",
    "ModelComputeOutput",
    "ModelComputeStepMetadata",
    "ModelComputeStepResult",
    "ModelComputePipelineResult",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelComputeContext": (
        "omnibase_core.models.compute.model_compute_context",
        "ModelComputeContext",
    ),
    "ModelComputeExecutionContext": (
        "omnibase_core.models.compute.model_compute_execution_context",
        "ModelComputeExecutionContext",
    ),
    "ModelComputeInput": (
        "omnibase_core.models.compute.model_compute_input",
        "ModelComputeInput",
    ),
    "ModelComputeOutput": (
        "omnibase_core.models.compute.model_compute_output",
        "ModelComputeOutput",
    ),
    "ModelComputePipelineResult": (
        "omnibase_core.models.compute.model_compute_pipeline_result",
        "ModelComputePipelineResult",
    ),
    "ModelComputeStepMetadata": (
        "omnibase_core.models.compute.model_compute_step_metadata",
        "ModelComputeStepMetadata",
    ),
    "ModelComputeStepResult": (
        "omnibase_core.models.compute.model_compute_step_result",
        "ModelComputeStepResult",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
