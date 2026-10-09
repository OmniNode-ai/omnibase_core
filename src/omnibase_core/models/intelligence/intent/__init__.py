# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Intent Intelligence Framework models.

This subpackage contains frozen Pydantic models for the Intent Intelligence
Framework (OMN-2486). These are cross-repo canonical data structures used
by classification, drift detection, forecasting, graph, and commit binding
subsystems.

Models:
    ModelTypedIntent: Classified, structured intent object.
    ModelIntentDriftSignal: Drift detection output.
    ModelIntentCostForecast: Cost/latency prediction before execution.
    ModelIntentGraphNode: Intent graph vertex.
    ModelIntentTransition: Intent graph edge with statistics.
    ModelIntentToCommitBinding: Commit-level causal link.
    ModelUserIntentProfile: Per-user intent tendency patterns.
    ModelIntentRollbackTrigger: Signal when to revert based on outcome.

All models use:
    - ``frozen=True``: Immutable after creation (cross-service safety).
    - ``extra="ignore"``: Tolerates additional fields from future schema versions.
    - ``from_attributes=True``: ORM/dataclass interoperability.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.intelligence.intent.model_intent_cost_forecast import (
        ModelIntentCostForecast,
    )
    from omnibase_core.models.intelligence.intent.model_intent_drift_signal import (
        ModelIntentDriftSignal,
    )
    from omnibase_core.models.intelligence.intent.model_intent_graph_node import (
        ModelIntentGraphNode,
    )
    from omnibase_core.models.intelligence.intent.model_intent_rollback_trigger import (
        ModelIntentRollbackTrigger,
    )
    from omnibase_core.models.intelligence.intent.model_intent_to_commit_binding import (
        ModelIntentToCommitBinding,
    )
    from omnibase_core.models.intelligence.intent.model_intent_transition import (
        ModelIntentTransition,
    )
    from omnibase_core.models.intelligence.intent.model_typed_intent import (
        ModelTypedIntent,
    )
    from omnibase_core.models.intelligence.intent.model_user_intent_profile import (
        ModelUserIntentProfile,
    )

__all__ = [
    "ModelIntentCostForecast",
    "ModelIntentDriftSignal",
    "ModelIntentGraphNode",
    "ModelIntentRollbackTrigger",
    "ModelIntentToCommitBinding",
    "ModelIntentTransition",
    "ModelTypedIntent",
    "ModelUserIntentProfile",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelIntentCostForecast": (
        "omnibase_core.models.intelligence.intent.model_intent_cost_forecast",
        "ModelIntentCostForecast",
    ),
    "ModelIntentDriftSignal": (
        "omnibase_core.models.intelligence.intent.model_intent_drift_signal",
        "ModelIntentDriftSignal",
    ),
    "ModelIntentGraphNode": (
        "omnibase_core.models.intelligence.intent.model_intent_graph_node",
        "ModelIntentGraphNode",
    ),
    "ModelIntentRollbackTrigger": (
        "omnibase_core.models.intelligence.intent.model_intent_rollback_trigger",
        "ModelIntentRollbackTrigger",
    ),
    "ModelIntentToCommitBinding": (
        "omnibase_core.models.intelligence.intent.model_intent_to_commit_binding",
        "ModelIntentToCommitBinding",
    ),
    "ModelIntentTransition": (
        "omnibase_core.models.intelligence.intent.model_intent_transition",
        "ModelIntentTransition",
    ),
    "ModelTypedIntent": (
        "omnibase_core.models.intelligence.intent.model_typed_intent",
        "ModelTypedIntent",
    ),
    "ModelUserIntentProfile": (
        "omnibase_core.models.intelligence.intent.model_user_intent_profile",
        "ModelUserIntentProfile",
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
