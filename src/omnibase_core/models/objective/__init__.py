# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Objective function data models for the OmniNode reward architecture.

Implements the core Pydantic model layer from the objective functions and
reward architecture design document (OMN-2537, Section 12).

Foundation models:
- ModelObjectiveSpec: The versioned objective contract
- ModelGateSpec: Hard gate specification
- ModelShapedTermSpec: Shaped reward term specification
- ModelScoreRange: Score bounds declaration
- ModelScoreVector: Multi-dimensional score (no single scalar reward)
- ModelEvidenceBundle: Tamper-evident structured evidence collection
- ModelEvidenceItem: Single typed evidence item (free-text disallowed)
- ModelEvaluationResult: Output of the ScoringReducer
- ModelRewardAssignedEvent: Canonical cross-repo reward event (OMN-2928)
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.objective.model_evaluation_result import (
        ModelEvaluationResult,
    )
    from omnibase_core.models.objective.model_evidence_bundle import ModelEvidenceBundle
    from omnibase_core.models.objective.model_evidence_item import ModelEvidenceItem
    from omnibase_core.models.objective.model_gate_spec import ModelGateSpec
    from omnibase_core.models.objective.model_objective_spec import ModelObjectiveSpec
    from omnibase_core.models.objective.model_reward_assigned_event import (
        ModelRewardAssignedEvent,
    )
    from omnibase_core.models.objective.model_score_range import ModelScoreRange
    from omnibase_core.models.objective.model_score_vector import ModelScoreVector
    from omnibase_core.models.objective.model_shaped_term_spec import (
        ModelShapedTermSpec,
    )

__all__ = [
    "ModelEvaluationResult",
    "ModelEvidenceBundle",
    "ModelEvidenceItem",
    "ModelGateSpec",
    "ModelObjectiveSpec",
    "ModelRewardAssignedEvent",
    "ModelScoreRange",
    "ModelScoreVector",
    "ModelShapedTermSpec",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelEvaluationResult": (
        "omnibase_core.models.objective.model_evaluation_result",
        "ModelEvaluationResult",
    ),
    "ModelEvidenceBundle": (
        "omnibase_core.models.objective.model_evidence_bundle",
        "ModelEvidenceBundle",
    ),
    "ModelEvidenceItem": (
        "omnibase_core.models.objective.model_evidence_item",
        "ModelEvidenceItem",
    ),
    "ModelGateSpec": (
        "omnibase_core.models.objective.model_gate_spec",
        "ModelGateSpec",
    ),
    "ModelObjectiveSpec": (
        "omnibase_core.models.objective.model_objective_spec",
        "ModelObjectiveSpec",
    ),
    "ModelRewardAssignedEvent": (
        "omnibase_core.models.objective.model_reward_assigned_event",
        "ModelRewardAssignedEvent",
    ),
    "ModelScoreRange": (
        "omnibase_core.models.objective.model_score_range",
        "ModelScoreRange",
    ),
    "ModelScoreVector": (
        "omnibase_core.models.objective.model_score_vector",
        "ModelScoreVector",
    ),
    "ModelShapedTermSpec": (
        "omnibase_core.models.objective.model_shaped_term_spec",
        "ModelShapedTermSpec",
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
