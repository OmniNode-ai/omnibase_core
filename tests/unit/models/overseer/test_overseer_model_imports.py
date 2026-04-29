# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for overseer models namespace (OMN-10251)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.models.ticket.model_evidence_requirement import (
    ModelEvidenceRequirement,
)

pytestmark = pytest.mark.unit


@pytest.mark.unit
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

        assert id(ModelWorkerEvidenceRequirement) != id(ModelEvidenceRequirement)
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
        assert id(ModelWorkerEvidenceRequirement) != id(ModelEvidenceRequirement)

    def test_enum_task_status_values(self) -> None:
        from omnibase_core.enums.overseer.enum_task_status import EnumTaskStatus

        assert EnumTaskStatus.PENDING.value == "pending"
        assert EnumTaskStatus.COMPLETED.value == "completed"
        assert EnumTaskStatus.FAILED.value == "failed"

    def test_enum_completion_outcome_values(self) -> None:
        from omnibase_core.enums.overseer.enum_completion_outcome import (
            EnumCompletionOutcome,
        )

        assert EnumCompletionOutcome.SUCCESS.value == "success"
        assert EnumCompletionOutcome.FAILURE.value == "failure"

    def test_context_bundle_l2_freezes_sequence_fields(self) -> None:
        from omnibase_core.models.overseer.model_context_bundle_l2 import (
            ModelContextBundleL2,
        )

        bundle = ModelContextBundleL2(
            run_id="run-1",
            task_id="task-1",
            role="worker",
            fsm_state="running",
            ticket_id="OMN-10251",
            summary="summary",
            entrypoints=("src/a.py",),
            file_scope=("src/a.py", "tests/a.py"),
        )

        assert bundle.entrypoints == ("src/a.py",)
        assert bundle.file_scope == ("src/a.py", "tests/a.py")

    def test_overnight_contract_requires_at_least_one_phase(self) -> None:
        from datetime import UTC, datetime

        from omnibase_core.models.overseer.model_overnight_contract import (
            ModelOvernightContract,
        )

        with pytest.raises(ValidationError):
            ModelOvernightContract(
                session_id="session-1",
                created_at=datetime.now(UTC),
                phases=(),
            )

    def test_overnight_phase_required_outcomes_are_enums(self) -> None:
        from omnibase_core.enums.overseer.enum_completion_outcome import (
            EnumCompletionOutcome,
        )
        from omnibase_core.models.overseer.model_overnight_phase_spec import (
            ModelOvernightPhaseSpec,
        )

        phase = ModelOvernightPhaseSpec.model_validate(
            {
                "phase_name": "merge",
                "required_outcomes": ["success"],
            }
        )

        assert phase.required_outcomes == (EnumCompletionOutcome.SUCCESS,)

    def test_session_contract_default_cost_halt_uses_max_cost(self) -> None:
        from datetime import UTC, datetime

        from omnibase_core.models.overseer.model_session_contract import (
            ModelSessionContract,
        )
        from omnibase_core.models.overseer.model_session_phase_spec import (
            ModelSessionPhaseSpec,
        )

        contract = ModelSessionContract(
            session_id="session-1",
            created_at=datetime.now(UTC),
            max_cost_usd=12.5,
            phases=(ModelSessionPhaseSpec(phase_name="merge"),),
        )

        cost_condition = contract.halt_conditions[0]
        assert cost_condition.condition_id == "cost_ceiling"
        assert cost_condition.threshold == 12.5

    def test_session_phase_rejects_non_positive_timeout(self) -> None:
        from omnibase_core.models.overseer.model_session_phase_spec import (
            ModelSessionPhaseSpec,
        )

        with pytest.raises(ValidationError):
            ModelSessionPhaseSpec(phase_name="merge", timeout_seconds=0)

    def test_task_payloads_are_immutable_and_validate_as_value_errors(self) -> None:
        from omnibase_core.enums.overseer.enum_task_status import EnumTaskStatus
        from omnibase_core.models.overseer.model_task_delta_envelope import (
            ModelTaskDeltaEnvelope,
        )
        from omnibase_core.models.overseer.model_task_state_envelope import (
            ModelTaskStateEnvelope,
        )

        delta = ModelTaskDeltaEnvelope(task_id="task-1", payload={"a": 1})
        state = ModelTaskStateEnvelope(
            task_id="task-1",
            status=EnumTaskStatus.PENDING,
            domain="test",
            node_id="node-1",
            payload={"a": 1},
        )

        def mutate_payload(payload: Any) -> None:
            payload["b"] = 2

        with pytest.raises(TypeError):
            mutate_payload(delta.payload)
        with pytest.raises(TypeError):
            mutate_payload(state.payload)
        bad_payload: Any = object()
        with pytest.raises(ValidationError):
            ModelTaskDeltaEnvelope(task_id="task-1", payload=bad_payload)
        with pytest.raises(ValidationError):
            ModelTaskStateEnvelope(
                task_id="task-1",
                status=EnumTaskStatus.PENDING,
                domain="test",
                node_id="node-1",
                payload=bad_payload,
            )

    def test_worker_contract_boundary_validation_uses_value_errors(self) -> None:
        from omnibase_core.models.overseer.model_worker_contract import (
            ModelWorkerContract,
            load_worker_contract,
        )

        with pytest.raises(ValueError, match="worker contract data must be a mapping"):
            load_worker_contract("not-a-mapping")
        with pytest.raises(ValidationError):
            ModelWorkerContract.model_validate(
                {"worker_name": "worker", "required_evidence": "bad"}
            )
