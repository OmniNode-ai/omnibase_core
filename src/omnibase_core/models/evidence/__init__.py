# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Evidence models for corpus replay aggregation.

These models support corpus replay evidence aggregation and decision-making (OMN-1195).
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.evidence.model_cost_statistics import ModelCostStatistics
    from omnibase_core.models.evidence.model_decision_recommendation import (
        ModelDecisionRecommendation,
    )
    from omnibase_core.models.evidence.model_evidence_filter import ModelEvidenceFilter
    from omnibase_core.models.evidence.model_evidence_summary import (
        ModelEvidenceSummary,
    )
    from omnibase_core.models.evidence.model_export_options import ModelExportOptions
    from omnibase_core.models.evidence.model_invariant_violation_breakdown import (
        ModelInvariantViolationBreakdown,
    )
    from omnibase_core.models.evidence.model_latency_statistics import (
        ModelLatencyStatistics,
    )

__all__ = [
    "ModelCostStatistics",
    "ModelDecisionRecommendation",
    "ModelEvidenceFilter",
    "ModelEvidenceSummary",
    "ModelExportOptions",
    "ModelInvariantViolationBreakdown",
    "ModelLatencyStatistics",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelCostStatistics": (
        "omnibase_core.models.evidence.model_cost_statistics",
        "ModelCostStatistics",
    ),
    "ModelDecisionRecommendation": (
        "omnibase_core.models.evidence.model_decision_recommendation",
        "ModelDecisionRecommendation",
    ),
    "ModelEvidenceFilter": (
        "omnibase_core.models.evidence.model_evidence_filter",
        "ModelEvidenceFilter",
    ),
    "ModelEvidenceSummary": (
        "omnibase_core.models.evidence.model_evidence_summary",
        "ModelEvidenceSummary",
    ),
    "ModelExportOptions": (
        "omnibase_core.models.evidence.model_export_options",
        "ModelExportOptions",
    ),
    "ModelInvariantViolationBreakdown": (
        "omnibase_core.models.evidence.model_invariant_violation_breakdown",
        "ModelInvariantViolationBreakdown",
    ),
    "ModelLatencyStatistics": (
        "omnibase_core.models.evidence.model_latency_statistics",
        "ModelLatencyStatistics",
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
