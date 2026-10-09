# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pipeline models."""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.pipeline.model_chain_diff import ModelChainDiff
    from omnibase_core.models.pipeline.model_closeout_result import ModelCloseoutResult
    from omnibase_core.models.pipeline.model_evidence_artifact import (
        ModelEvidenceArtifact,
    )
    from omnibase_core.models.pipeline.model_golden_chain_entry import (
        ModelGoldenChainEntry,
    )
    from omnibase_core.models.pipeline.model_hook_error import ModelHookError
    from omnibase_core.models.pipeline.model_phase_execution_plan import (
        ModelPhaseExecutionPlan,
    )
    from omnibase_core.models.pipeline.model_phase_record import ModelPhaseRecord
    from omnibase_core.models.pipeline.model_pipeline_context import (
        ModelPipelineContext,
    )
    from omnibase_core.models.pipeline.model_pipeline_execution_plan import (
        ModelPipelineExecutionPlan,
    )
    from omnibase_core.models.pipeline.model_pipeline_hook import (
        ModelPipelineHook,
        PipelinePhase,
    )
    from omnibase_core.models.pipeline.model_pipeline_result import ModelPipelineResult
    from omnibase_core.models.pipeline.model_pipeline_state import (
        ModelPipelineState,
        PipelineState,
    )
    from omnibase_core.models.pipeline.model_readiness_result import (
        ModelReadinessResult,
    )
    from omnibase_core.models.pipeline.model_validation_warning import (
        ModelValidationWarning,
    )

__all__ = [
    "ModelChainDiff",
    "ModelCloseoutResult",
    "ModelEvidenceArtifact",
    "ModelGoldenChainEntry",
    "ModelHookError",
    "ModelPhaseExecutionPlan",
    "ModelPhaseRecord",
    "ModelPipelineContext",
    "ModelPipelineExecutionPlan",
    "ModelPipelineHook",
    "ModelPipelineResult",
    "ModelPipelineState",
    "ModelReadinessResult",
    "ModelValidationWarning",
    "PipelinePhase",
    "PipelineState",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelChainDiff": (
        "omnibase_core.models.pipeline.model_chain_diff",
        "ModelChainDiff",
    ),
    "ModelCloseoutResult": (
        "omnibase_core.models.pipeline.model_closeout_result",
        "ModelCloseoutResult",
    ),
    "ModelEvidenceArtifact": (
        "omnibase_core.models.pipeline.model_evidence_artifact",
        "ModelEvidenceArtifact",
    ),
    "ModelGoldenChainEntry": (
        "omnibase_core.models.pipeline.model_golden_chain_entry",
        "ModelGoldenChainEntry",
    ),
    "ModelHookError": (
        "omnibase_core.models.pipeline.model_hook_error",
        "ModelHookError",
    ),
    "ModelPhaseExecutionPlan": (
        "omnibase_core.models.pipeline.model_phase_execution_plan",
        "ModelPhaseExecutionPlan",
    ),
    "ModelPhaseRecord": (
        "omnibase_core.models.pipeline.model_phase_record",
        "ModelPhaseRecord",
    ),
    "ModelPipelineContext": (
        "omnibase_core.models.pipeline.model_pipeline_context",
        "ModelPipelineContext",
    ),
    "ModelPipelineExecutionPlan": (
        "omnibase_core.models.pipeline.model_pipeline_execution_plan",
        "ModelPipelineExecutionPlan",
    ),
    "ModelPipelineHook": (
        "omnibase_core.models.pipeline.model_pipeline_hook",
        "ModelPipelineHook",
    ),
    "PipelinePhase": (
        "omnibase_core.models.pipeline.model_pipeline_hook",
        "PipelinePhase",
    ),
    "ModelPipelineResult": (
        "omnibase_core.models.pipeline.model_pipeline_result",
        "ModelPipelineResult",
    ),
    "ModelPipelineState": (
        "omnibase_core.models.pipeline.model_pipeline_state",
        "ModelPipelineState",
    ),
    "PipelineState": (
        "omnibase_core.models.pipeline.model_pipeline_state",
        "PipelineState",
    ),
    "ModelReadinessResult": (
        "omnibase_core.models.pipeline.model_readiness_result",
        "ModelReadinessResult",
    ),
    "ModelValidationWarning": (
        "omnibase_core.models.pipeline.model_validation_warning",
        "ModelValidationWarning",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
