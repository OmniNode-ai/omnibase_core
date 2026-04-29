# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Red/Green import tests for omnibase_core.enums.governance namespace (OMN-10243)."""

import pytest


@pytest.mark.unit
def test_enum_autopilot_step_status_importable() -> None:
    from omnibase_core.enums.governance.enum_autopilot_step_status import (
        EnumAutopilotStepStatus,
    )

    assert EnumAutopilotStepStatus is not None
    assert EnumAutopilotStepStatus.COMPLETED == "completed"


@pytest.mark.unit
def test_enum_autopilot_cycle_status_importable() -> None:
    from omnibase_core.enums.governance.enum_autopilot_cycle_status import (
        EnumAutopilotCycleStatus,
    )

    assert EnumAutopilotCycleStatus is not None
    assert EnumAutopilotCycleStatus.COMPLETE == "complete"


@pytest.mark.unit
def test_enum_compliance_verdict_importable() -> None:
    from omnibase_core.enums.governance.enum_compliance_verdict import (
        EnumComplianceVerdict,
    )

    assert EnumComplianceVerdict is not None
    assert EnumComplianceVerdict.COMPLIANT == "compliant"


@pytest.mark.unit
def test_enum_compliance_violation_importable() -> None:
    from omnibase_core.enums.governance.enum_compliance_violation import (
        EnumComplianceViolation,
    )

    assert EnumComplianceViolation is not None
    assert EnumComplianceViolation.HARDCODED_TOPIC == "hardcoded_topic"


@pytest.mark.unit
def test_enum_db_boundary_importable() -> None:
    from omnibase_core.enums.governance.enum_db_boundary import (
        EnumDbBoundaryExceptionStatus,
        EnumDbBoundaryReasonCategory,
    )

    assert EnumDbBoundaryReasonCategory is not None
    assert EnumDbBoundaryReasonCategory.READ_MODEL == "READ_MODEL"
    assert EnumDbBoundaryExceptionStatus is not None
    assert EnumDbBoundaryExceptionStatus.APPROVED == "APPROVED"


@pytest.mark.unit
def test_enum_doc_reference_type_importable() -> None:
    from omnibase_core.enums.governance.enum_doc_reference_type import (
        EnumDocReferenceType,
    )

    assert EnumDocReferenceType is not None
    assert EnumDocReferenceType.FILE_PATH == "FILE_PATH"


@pytest.mark.unit
def test_enum_doc_staleness_verdict_importable() -> None:
    from omnibase_core.enums.governance.enum_doc_staleness_verdict import (
        EnumDocStalenessVerdict,
    )

    assert EnumDocStalenessVerdict is not None
    assert EnumDocStalenessVerdict.FRESH == "FRESH"


@pytest.mark.unit
def test_enum_dod_sweep_check_importable() -> None:
    from omnibase_core.enums.governance.enum_dod_sweep_check import EnumDodSweepCheck

    assert EnumDodSweepCheck is not None
    assert EnumDodSweepCheck.CONTRACT_EXISTS == "contract_exists"


@pytest.mark.unit
def test_enum_dogfood_status_importable() -> None:
    from omnibase_core.enums.governance.enum_dogfood_status import (
        EnumDogfoodStatus,
        EnumRegressionSeverity,
    )

    assert EnumDogfoodStatus is not None
    assert EnumDogfoodStatus.PASS == "pass"
    assert EnumRegressionSeverity is not None
    assert EnumRegressionSeverity.CRITICAL == "critical"


@pytest.mark.unit
def test_enum_drift_category_importable() -> None:
    from omnibase_core.enums.governance.enum_drift_category import EnumDriftCategory

    assert EnumDriftCategory is not None
    assert EnumDriftCategory.SCOPE == "scope"


@pytest.mark.unit
def test_enum_drift_sensitivity_importable() -> None:
    from omnibase_core.enums.governance.enum_drift_sensitivity import (
        EnumDriftSensitivity,
    )

    assert EnumDriftSensitivity is not None
    assert EnumDriftSensitivity.STRICT == "STRICT"


@pytest.mark.unit
def test_enum_drift_severity_importable() -> None:
    from omnibase_core.enums.governance.enum_drift_severity import EnumDriftSeverity

    assert EnumDriftSeverity is not None
    assert EnumDriftSeverity.BREAKING == "BREAKING"


@pytest.mark.unit
def test_enum_eval_metric_type_importable() -> None:
    from omnibase_core.enums.governance.enum_eval_metric_type import EnumEvalMetricType

    assert EnumEvalMetricType is not None
    assert EnumEvalMetricType.LATENCY_MS == "latency_ms"


@pytest.mark.unit
def test_enum_eval_mode_importable() -> None:
    from omnibase_core.enums.governance.enum_eval_mode import EnumEvalMode

    assert EnumEvalMode is not None
    assert EnumEvalMode.ONEX_ON == "onex_on"


@pytest.mark.unit
def test_enum_eval_verdict_importable() -> None:
    from omnibase_core.enums.governance.enum_eval_verdict import EnumEvalVerdict

    assert EnumEvalVerdict is not None
    assert EnumEvalVerdict.ONEX_BETTER == "onex_better"


@pytest.mark.unit
def test_enum_evidence_kind_importable() -> None:
    from omnibase_core.enums.governance.enum_evidence_kind import EnumEvidenceKind

    assert EnumEvidenceKind is not None
    assert EnumEvidenceKind.TESTS == "tests"


@pytest.mark.unit
def test_enum_finding_severity_importable() -> None:
    from omnibase_core.enums.governance.enum_finding_severity import EnumFindingSeverity

    assert EnumFindingSeverity is not None
    assert EnumFindingSeverity.CRITICAL == "critical"


@pytest.mark.unit
def test_enum_integration_surface_importable() -> None:
    from omnibase_core.enums.governance.enum_integration_surface import (
        EnumIntegrationSurface,
    )

    assert EnumIntegrationSurface is not None
    assert EnumIntegrationSurface.KAFKA == "kafka"


@pytest.mark.unit
def test_enum_interface_surface_importable() -> None:
    from omnibase_core.enums.governance.enum_interface_surface import (
        EnumInterfaceSurface,
    )

    assert EnumInterfaceSurface is not None
    assert EnumInterfaceSurface.EVENTS == "events"


@pytest.mark.unit
def test_enum_invariant_status_importable() -> None:
    from omnibase_core.enums.governance.enum_invariant_status import EnumInvariantStatus

    assert EnumInvariantStatus is not None
    assert EnumInvariantStatus.PASS == "pass"


@pytest.mark.unit
def test_enum_migration_status_importable() -> None:
    from omnibase_core.enums.governance.enum_migration_status import EnumMigrationStatus

    assert EnumMigrationStatus is not None
    assert EnumMigrationStatus.PENDING == "pending"


@pytest.mark.unit
def test_enum_pr_state_importable() -> None:
    from omnibase_core.enums.governance.enum_pr_state import EnumPRState

    assert EnumPRState is not None
    assert EnumPRState.MERGED == "merged"


@pytest.mark.unit
def test_enum_probe_reason_importable() -> None:
    from omnibase_core.enums.governance.enum_probe_reason import EnumProbeReason

    assert EnumProbeReason is not None
    assert EnumProbeReason.NO_CONTRACT == "no_contract"


@pytest.mark.unit
def test_enum_probe_status_importable() -> None:
    from omnibase_core.enums.governance.enum_probe_status import EnumProbeStatus

    assert EnumProbeStatus is not None
    assert EnumProbeStatus.COMPLETED == "completed"


@pytest.mark.unit
def test_enum_wire_field_type_importable() -> None:
    from omnibase_core.enums.governance.enum_wire_field_type import EnumWireFieldType

    assert EnumWireFieldType is not None
    assert EnumWireFieldType.UUID == "uuid"


@pytest.mark.unit
def test_governance_init_reexports_all() -> None:
    """All governance enums are re-exported from the governance __init__."""
    from omnibase_core.enums.governance import (
        EnumAutopilotCycleStatus,
        EnumAutopilotStepStatus,
        EnumComplianceVerdict,
        EnumComplianceViolation,
        EnumDbBoundaryExceptionStatus,
        EnumDbBoundaryReasonCategory,
        EnumDocReferenceType,
        EnumDocStalenessVerdict,
        EnumDodSweepCheck,
        EnumDogfoodStatus,
        EnumDriftCategory,
        EnumDriftSensitivity,
        EnumDriftSeverity,
        EnumEvalMetricType,
        EnumEvalMode,
        EnumEvalVerdict,
        EnumEvidenceKind,
        EnumFindingSeverity,
        EnumIntegrationSurface,
        EnumInterfaceSurface,
        EnumInvariantStatus,
        EnumMigrationStatus,
        EnumProbeReason,
        EnumProbeStatus,
        EnumPRState,
        EnumRegressionSeverity,
        EnumWireFieldType,
    )

    for cls in [
        EnumAutopilotStepStatus,
        EnumAutopilotCycleStatus,
        EnumComplianceVerdict,
        EnumComplianceViolation,
        EnumDbBoundaryReasonCategory,
        EnumDbBoundaryExceptionStatus,
        EnumDocReferenceType,
        EnumDocStalenessVerdict,
        EnumDodSweepCheck,
        EnumDogfoodStatus,
        EnumRegressionSeverity,
        EnumDriftCategory,
        EnumDriftSensitivity,
        EnumDriftSeverity,
        EnumEvalMetricType,
        EnumEvalMode,
        EnumEvalVerdict,
        EnumEvidenceKind,
        EnumFindingSeverity,
        EnumIntegrationSurface,
        EnumInterfaceSurface,
        EnumInvariantStatus,
        EnumMigrationStatus,
        EnumPRState,
        EnumProbeReason,
        EnumProbeStatus,
        EnumWireFieldType,
    ]:
        assert cls is not None
