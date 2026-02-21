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
