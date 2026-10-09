# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Overseer models namespace (OMN-10251).

20 model files migrated from OCC into omnibase_core.models.overseer.
ModelEvidenceRequirement collision resolved: OCC overseer version is
ModelWorkerEvidenceRequirement; core's ModelEvidenceRequirement is unchanged.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.enums.overseer.enum_completion_outcome import (
        EnumCompletionOutcome,
    )
    from omnibase_core.enums.overseer.enum_task_status import EnumTaskStatus
    from omnibase_core.models.overseer.model_completion_report import (
        ModelCompletionReport,
    )
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
    from omnibase_core.models.overseer.model_phase_exit_condition import (
        ModelPhaseExitCondition,
    )
    from omnibase_core.models.overseer.model_process_runner_state_transition import (
        ModelProcessRunnerStateTransition,
    )
    from omnibase_core.models.overseer.model_session_contract import (
        ModelSessionContract,
    )
    from omnibase_core.models.overseer.model_session_halt_condition import (
        ModelSessionHaltCondition,
    )
    from omnibase_core.models.overseer.model_session_phase_spec import (
        ModelSessionPhaseSpec,
    )
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
    "ModelPhaseExitCondition",
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumCompletionOutcome": (
        "omnibase_core.enums.overseer.enum_completion_outcome",
        "EnumCompletionOutcome",
    ),
    "EnumTaskStatus": (
        "omnibase_core.enums.overseer.enum_task_status",
        "EnumTaskStatus",
    ),
    "ModelCompletionReport": (
        "omnibase_core.models.overseer.model_completion_report",
        "ModelCompletionReport",
    ),
    "ModelContextBundle": (
        "omnibase_core.models.overseer.model_context_bundle",
        "ModelContextBundle",
    ),
    "ModelContextBundleL0": (
        "omnibase_core.models.overseer.model_context_bundle",
        "ModelContextBundleL0",
    ),
    "ModelContextBundleL1": (
        "omnibase_core.models.overseer.model_context_bundle",
        "ModelContextBundleL1",
    ),
    "ModelContextBundleL2": (
        "omnibase_core.models.overseer.model_context_bundle",
        "ModelContextBundleL2",
    ),
    "ModelContextBundleL3": (
        "omnibase_core.models.overseer.model_context_bundle",
        "ModelContextBundleL3",
    ),
    "ModelContextBundleL4": (
        "omnibase_core.models.overseer.model_context_bundle",
        "ModelContextBundleL4",
    ),
    "_ContextBundleBase": (
        "omnibase_core.models.overseer.model_context_bundle",
        "_ContextBundleBase",
    ),
    "ModelContractAllowedActions": (
        "omnibase_core.models.overseer.model_contract_allowed_actions",
        "ModelContractAllowedActions",
    ),
    "ModelDispatchItem": (
        "omnibase_core.models.overseer.model_dispatch_item",
        "ModelDispatchItem",
    ),
    "ModelEscalationRequest": (
        "omnibase_core.models.overseer.model_escalation_request",
        "ModelEscalationRequest",
    ),
    "ModelPhaseExitCondition": (
        "omnibase_core.models.overseer.model_phase_exit_condition",
        "ModelPhaseExitCondition",
    ),
    "ModelProcessRunnerStateTransition": (
        "omnibase_core.models.overseer.model_process_runner_state_transition",
        "ModelProcessRunnerStateTransition",
    ),
    "ModelSessionContract": (
        "omnibase_core.models.overseer.model_session_contract",
        "ModelSessionContract",
    ),
    "ModelSessionHaltCondition": (
        "omnibase_core.models.overseer.model_session_halt_condition",
        "ModelSessionHaltCondition",
    ),
    "ModelSessionPhaseSpec": (
        "omnibase_core.models.overseer.model_session_phase_spec",
        "ModelSessionPhaseSpec",
    ),
    "ModelTaskDeltaEnvelope": (
        "omnibase_core.models.overseer.model_task_delta_envelope",
        "ModelTaskDeltaEnvelope",
    ),
    "ModelTaskShapeFeatures": (
        "omnibase_core.models.overseer.model_task_shape_features",
        "ModelTaskShapeFeatures",
    ),
    "ModelTaskStateEnvelope": (
        "omnibase_core.models.overseer.model_task_state_envelope",
        "ModelTaskStateEnvelope",
    ),
    "ModelVerifierOutput": (
        "omnibase_core.models.overseer.model_verifier_output",
        "ModelVerifierOutput",
    ),
    "ModelWorkerContract": (
        "omnibase_core.models.overseer.model_worker_contract",
        "ModelWorkerContract",
    ),
    "load_worker_contract": (
        "omnibase_core.models.overseer.model_worker_contract",
        "load_worker_contract",
    ),
    "ModelWorkerEvidenceRequirement": (
        "omnibase_core.models.overseer.model_worker_evidence_requirement",
        "ModelWorkerEvidenceRequirement",
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
