# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Overseer models namespace (OMN-10251).

13 model files migrated from OCC into omnibase_core.models.overseer.
ModelEvidenceRequirement collision resolved: OCC overseer version is
ModelWorkerEvidenceRequirement; core's ModelEvidenceRequirement is unchanged.
"""

from __future__ import annotations

from omnibase_core.enums.overseer.enum_completion_outcome import EnumCompletionOutcome
from omnibase_core.enums.overseer.enum_task_status import EnumTaskStatus
from omnibase_core.models.overseer.model_completion_report import ModelCompletionReport
from omnibase_core.models.overseer.model_context_bundle import (
    ModelContextBundle,
    ModelContextBundleL0,
    ModelContextBundleL1,
    ModelContextBundleL2,
    ModelContextBundleL3,
    ModelContextBundleL4,
    _ContextBundleBase,
)
from omnibase_core.models.overseer.model_contract_allowed_actions import (
    ModelContractAllowedActions,
)
from omnibase_core.models.overseer.model_dispatch_item import ModelDispatchItem
from omnibase_core.models.overseer.model_escalation_request import (
    ModelEscalationRequest,
)
from omnibase_core.models.overseer.model_overnight_contract import (
    ModelOvernightContract,
)
from omnibase_core.models.overseer.model_overnight_halt_condition import (
    ModelOvernightHaltCondition,
)
from omnibase_core.models.overseer.model_overnight_phase_spec import (
    ModelOvernightPhaseSpec,
)
from omnibase_core.models.overseer.model_process_runner_state_transition import (
    ModelProcessRunnerStateTransition,
)
from omnibase_core.models.overseer.model_session_contract import ModelSessionContract
from omnibase_core.models.overseer.model_session_halt_condition import (
    ModelSessionHaltCondition,
)
from omnibase_core.models.overseer.model_session_phase_spec import ModelSessionPhaseSpec
from omnibase_core.models.overseer.model_task_delta_envelope import (
    ModelTaskDeltaEnvelope,
)
from omnibase_core.models.overseer.model_task_shape_features import (
    ModelTaskShapeFeatures,
)
from omnibase_core.models.overseer.model_task_state_envelope import (
    ModelTaskStateEnvelope,
)
from omnibase_core.models.overseer.model_verifier_output import ModelVerifierOutput
from omnibase_core.models.overseer.model_worker_contract import (
    ModelWorkerContract,
    load_worker_contract,
)
from omnibase_core.models.overseer.model_worker_evidence_requirement import (
    ModelWorkerEvidenceRequirement,
)

__all__ = [
    "_ContextBundleBase",
    "EnumCompletionOutcome",
    "EnumTaskStatus",
    "ModelCompletionReport",
    "ModelContextBundle",
    "ModelContextBundleL0",
    "ModelContextBundleL1",
    "ModelContextBundleL2",
    "ModelContextBundleL3",
    "ModelContextBundleL4",
    "ModelContractAllowedActions",
    "ModelDispatchItem",
    "ModelEscalationRequest",
    "ModelOvernightContract",
    "ModelOvernightHaltCondition",
    "ModelOvernightPhaseSpec",
    "ModelProcessRunnerStateTransition",
    "ModelSessionContract",
    "ModelSessionHaltCondition",
    "ModelSessionPhaseSpec",
    "ModelTaskDeltaEnvelope",
    "ModelTaskShapeFeatures",
    "ModelTaskStateEnvelope",
    "ModelVerifierOutput",
    "ModelWorkerContract",
    "ModelWorkerEvidenceRequirement",
    "load_worker_contract",
]
