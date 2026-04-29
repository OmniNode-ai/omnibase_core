# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for overseer models namespace (OMN-10251)."""

from __future__ import annotations

from pydantic import BaseModel

from omnibase_core.models.ticket.model_evidence_requirement import (
    ModelEvidenceRequirement,
)


class TestOverseerModelImports:
    """Assert all overseer model classes importable from omnibase_core.models.overseer.*."""

    def test_enum_completion_outcome_importable(self) -> None:
        from omnibase_core.enums.overseer.enum_completion_outcome import (
            EnumCompletionOutcome,
        )

        assert issubclass(EnumCompletionOutcome, str)

    def test_enum_task_status_importable(self) -> None:
        from omnibase_core.enums.overseer.enum_task_status import EnumTaskStatus

        assert issubclass(EnumTaskStatus, str)

    def test_model_completion_report_importable(self) -> None:
        from omnibase_core.models.overseer.model_completion_report import (
            ModelCompletionReport,
        )

        assert issubclass(ModelCompletionReport, BaseModel)

    def test_model_context_bundle_importable(self) -> None:
        from omnibase_core.models.overseer.model_context_bundle import (
            ModelContextBundle,
            ModelContextBundleL0,
            ModelContextBundleL1,
            ModelContextBundleL2,
            ModelContextBundleL3,
            ModelContextBundleL4,
            _ContextBundleBase,
        )

        assert issubclass(ModelContextBundleL0, BaseModel)
        assert issubclass(ModelContextBundleL1, BaseModel)
        assert issubclass(ModelContextBundleL2, BaseModel)
        assert issubclass(ModelContextBundleL3, BaseModel)
        assert issubclass(ModelContextBundleL4, BaseModel)
        assert issubclass(_ContextBundleBase, BaseModel)
        assert ModelContextBundle is not None

    def test_model_context_bundle_split_files_importable(self) -> None:
        from omnibase_core.models.overseer.model_context_bundle_base import (
            _ContextBundleBase,
        )
        from omnibase_core.models.overseer.model_context_bundle_l0 import (
            ModelContextBundleL0,
        )
        from omnibase_core.models.overseer.model_context_bundle_l1 import (
            ModelContextBundleL1,
        )
        from omnibase_core.models.overseer.model_context_bundle_l2 import (
            ModelContextBundleL2,
        )
        from omnibase_core.models.overseer.model_context_bundle_l3 import (
            ModelContextBundleL3,
        )
        from omnibase_core.models.overseer.model_context_bundle_l4 import (
            ModelContextBundleL4,
        )

        assert issubclass(_ContextBundleBase, BaseModel)
        assert issubclass(ModelContextBundleL0, BaseModel)
        assert issubclass(ModelContextBundleL1, BaseModel)
        assert issubclass(ModelContextBundleL2, BaseModel)
        assert issubclass(ModelContextBundleL3, BaseModel)
        assert issubclass(ModelContextBundleL4, BaseModel)

    def test_model_contract_allowed_actions_importable(self) -> None:
        from omnibase_core.models.overseer.model_contract_allowed_actions import (
            ModelContractAllowedActions,
        )

        assert issubclass(ModelContractAllowedActions, BaseModel)

    def test_model_dispatch_item_importable(self) -> None:
        from omnibase_core.models.overseer.model_dispatch_item import ModelDispatchItem

        assert issubclass(ModelDispatchItem, BaseModel)

    def test_model_escalation_request_importable(self) -> None:
        from omnibase_core.models.overseer.model_escalation_request import (
            ModelEscalationRequest,
        )

        assert issubclass(ModelEscalationRequest, BaseModel)

    def test_model_overnight_contract_importable(self) -> None:
        from omnibase_core.models.overseer.model_overnight_contract import (
            ModelOvernightContract,
        )
        from omnibase_core.models.overseer.model_overnight_halt_condition import (
            ModelOvernightHaltCondition,
        )
        from omnibase_core.models.overseer.model_overnight_phase_spec import (
            ModelOvernightPhaseSpec,
        )

        assert issubclass(ModelOvernightContract, BaseModel)
        assert issubclass(ModelOvernightHaltCondition, BaseModel)
        assert issubclass(ModelOvernightPhaseSpec, BaseModel)

    def test_model_process_runner_state_transition_importable(self) -> None:
        from omnibase_core.models.overseer.model_process_runner_state_transition import (
            ModelProcessRunnerStateTransition,
        )

        assert issubclass(ModelProcessRunnerStateTransition, BaseModel)

    def test_model_session_contract_importable(self) -> None:
        from omnibase_core.models.overseer.model_session_contract import (
            ModelSessionContract,
        )
        from omnibase_core.models.overseer.model_session_halt_condition import (
            ModelSessionHaltCondition,
        )
        from omnibase_core.models.overseer.model_session_phase_spec import (
            ModelSessionPhaseSpec,
        )

        assert issubclass(ModelSessionContract, BaseModel)
        assert issubclass(ModelSessionHaltCondition, BaseModel)
        assert issubclass(ModelSessionPhaseSpec, BaseModel)

    def test_model_task_delta_envelope_importable(self) -> None:
        from omnibase_core.models.overseer.model_task_delta_envelope import (
            ModelTaskDeltaEnvelope,
        )

        assert issubclass(ModelTaskDeltaEnvelope, BaseModel)

    def test_model_task_shape_features_importable(self) -> None:
        from omnibase_core.models.overseer.model_task_shape_features import (
            ModelTaskShapeFeatures,
        )

        assert issubclass(ModelTaskShapeFeatures, BaseModel)

    def test_model_task_state_envelope_importable(self) -> None:
        from omnibase_core.models.overseer.model_task_state_envelope import (
            ModelTaskStateEnvelope,
        )

        assert issubclass(ModelTaskStateEnvelope, BaseModel)

    def test_model_verifier_output_importable(self) -> None:
        from omnibase_core.models.overseer.model_verifier_output import (
            ModelVerifierOutput,
        )

        assert issubclass(ModelVerifierOutput, BaseModel)

    def test_model_worker_contract_importable(self) -> None:
        from omnibase_core.models.overseer.model_worker_contract import (
            ModelWorkerContract,
            load_worker_contract,
        )

        assert issubclass(ModelWorkerContract, BaseModel)
        assert callable(load_worker_contract)

    def test_model_worker_evidence_requirement_importable(self) -> None:
        from omnibase_core.models.overseer.model_worker_evidence_requirement import (
            ModelWorkerEvidenceRequirement,
        )

        assert issubclass(ModelWorkerEvidenceRequirement, BaseModel)

    def test_namespace_init_exports(self) -> None:
        from omnibase_core.models import overseer

        assert hasattr(overseer, "ModelWorkerEvidenceRequirement")
        assert hasattr(overseer, "ModelWorkerContract")
        assert hasattr(overseer, "ModelVerifierOutput")
        assert hasattr(overseer, "ModelOvernightHaltCondition")
        assert hasattr(overseer, "ModelOvernightPhaseSpec")
        assert hasattr(overseer, "ModelSessionHaltCondition")
        assert hasattr(overseer, "ModelSessionPhaseSpec")
        assert hasattr(overseer, "EnumCompletionOutcome")
        assert hasattr(overseer, "EnumTaskStatus")

    def test_no_shadowing_of_core_evidence_requirement(self) -> None:
        """ModelWorkerEvidenceRequirement must not shadow core's ModelEvidenceRequirement."""
        from omnibase_core.models.overseer.model_worker_evidence_requirement import (
            ModelWorkerEvidenceRequirement,
        )

        assert ModelWorkerEvidenceRequirement is not ModelEvidenceRequirement
        overseer_fields = set(ModelWorkerEvidenceRequirement.model_fields.keys())
        core_fields = set(ModelEvidenceRequirement.model_fields.keys())
        assert overseer_fields != core_fields

    def test_model_worker_evidence_requirement_fields(self) -> None:
        from omnibase_core.models.overseer.model_worker_evidence_requirement import (
            ModelWorkerEvidenceRequirement,
        )

        req = ModelWorkerEvidenceRequirement(
            evidence_id="test-id",
            description="test description",
            kind="contains",
            pattern="expected text",
        )
        assert req.evidence_id == "test-id"
        assert req.description == "test description"
        assert req.kind == "contains"
        assert req.pattern == "expected text"

    def test_model_worker_contract_uses_worker_evidence_requirement(self) -> None:
        from omnibase_core.models.overseer.model_worker_contract import (
            ModelWorkerContract,
        )
        from omnibase_core.models.overseer.model_worker_evidence_requirement import (
            ModelWorkerEvidenceRequirement,
        )

        contract = ModelWorkerContract(worker_name="test-worker")
        assert contract.worker_name == "test-worker"
        assert ModelWorkerEvidenceRequirement is not ModelEvidenceRequirement

    def test_enum_task_status_values(self) -> None:
        from omnibase_core.enums.overseer.enum_task_status import EnumTaskStatus

        assert EnumTaskStatus.PENDING == "pending"
        assert EnumTaskStatus.COMPLETED == "completed"
        assert EnumTaskStatus.FAILED == "failed"

    def test_enum_completion_outcome_values(self) -> None:
        from omnibase_core.enums.overseer.enum_completion_outcome import (
            EnumCompletionOutcome,
        )

        assert EnumCompletionOutcome.SUCCESS == "success"
        assert EnumCompletionOutcome.FAILURE == "failure"
