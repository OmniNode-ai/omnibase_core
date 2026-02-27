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

from omnibase_core.models.objective.model_evaluation_result import ModelEvaluationResult
from omnibase_core.models.objective.model_evidence_bundle import ModelEvidenceBundle
from omnibase_core.models.objective.model_evidence_item import ModelEvidenceItem
from omnibase_core.models.objective.model_gate_spec import ModelGateSpec
from omnibase_core.models.objective.model_objective_spec import ModelObjectiveSpec
from omnibase_core.models.objective.model_reward_assigned_event import (
    ModelRewardAssignedEvent,
)
from omnibase_core.models.objective.model_score_range import ModelScoreRange
from omnibase_core.models.objective.model_score_vector import ModelScoreVector
from omnibase_core.models.objective.model_shaped_term_spec import ModelShapedTermSpec

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
