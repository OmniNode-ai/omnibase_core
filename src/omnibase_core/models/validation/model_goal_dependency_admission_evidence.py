# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Complete protected evidence returned for one goal dependency pin."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_goal_admission_observation import (
    ModelGoalAdmissionObservation,
)
from omnibase_core.models.validation.model_goal_attempt_allocation_snapshot import (
    ModelGoalAttemptAllocationSnapshot,
)
from omnibase_core.models.validation.model_goal_evaluation_observation import (
    ModelGoalEvaluationObservation,
)
from omnibase_core.models.validation.model_goal_supervisor_attestation import (
    ModelGoalSupervisorAttestation,
)
from omnibase_core.models.validation.model_goal_supervisor_execution_receipt import (
    ModelGoalSupervisorExecutionReceipt,
)
from omnibase_core.models.validation.model_goal_verifier_policy import (
    ModelGoalVerifierPolicy,
)


class ModelGoalDependencyAdmissionEvidence(BaseModel):
    """A dependency's signed run, protected policy and both trusted observations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    attempts: ModelGoalAttemptAllocationSnapshot
    policy: ModelGoalVerifierPolicy
    initial_observation: ModelGoalEvaluationObservation
    execution_receipt: ModelGoalSupervisorExecutionReceipt
    attestation: ModelGoalSupervisorAttestation
    admission_observation: ModelGoalAdmissionObservation


__all__ = ["ModelGoalDependencyAdmissionEvidence"]
