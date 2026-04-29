# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Import-assertion tests for governance model Batch D (OMN-10248)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError


@pytest.mark.unit
class TestGovernanceBatchDImports:
    """Assert all Batch D governance models importable from omnibase_core.models.governance.*"""

    # model_day_close.py — 8 classes
    def test_model_day_close_process_change_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_day_close import (
            ModelDayCloseProcessChange,
        )

        assert issubclass(ModelDayCloseProcessChange, BaseModel)

    def test_model_day_close_plan_item_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_day_close import (
            ModelDayClosePlanItem,
        )

        assert issubclass(ModelDayClosePlanItem, BaseModel)

    def test_model_day_close_pr_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_day_close import (
            ModelDayClosePR,
        )

        assert issubclass(ModelDayClosePR, BaseModel)

    def test_model_day_close_actual_repo_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_day_close import (
            ModelDayCloseActualRepo,
        )

        assert issubclass(ModelDayCloseActualRepo, BaseModel)

    def test_model_day_close_drift_detected_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_day_close import (
            ModelDayCloseDriftDetected,
        )

        assert issubclass(ModelDayCloseDriftDetected, BaseModel)

    def test_model_day_close_invariants_checked_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_day_close import (
            ModelDayCloseInvariantsChecked,
        )

        assert issubclass(ModelDayCloseInvariantsChecked, BaseModel)

    def test_model_day_close_risk_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_day_close import (
            ModelDayCloseRisk,
        )

        assert issubclass(ModelDayCloseRisk, BaseModel)

    def test_model_day_close_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_day_close import (
            ModelDayClose,
        )

        assert issubclass(ModelDayClose, BaseModel)

    # model_day_open.py — 5 classes
    def test_model_day_open_repo_sync_entry_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_day_open import (
            ModelDayOpenRepoSyncEntry,
        )

        assert issubclass(ModelDayOpenRepoSyncEntry, BaseModel)

    def test_model_day_open_infra_service_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_day_open import (
            ModelDayOpenInfraService,
        )

        assert issubclass(ModelDayOpenInfraService, BaseModel)

    def test_model_day_open_probe_result_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_day_open import (
            ModelDayOpenProbeResult,
        )

        assert issubclass(ModelDayOpenProbeResult, BaseModel)

    def test_model_day_open_finding_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_day_open import (
            ModelDayOpenFinding,
        )

        assert issubclass(ModelDayOpenFinding, BaseModel)

    def test_model_day_open_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_day_open import (
            ModelDayOpen,
        )

        assert issubclass(ModelDayOpen, BaseModel)

    # model_dogfood_scorecard.py — 7 classes
    def test_model_readiness_dimension_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_dogfood_scorecard import (
            ModelReadinessDimension,
        )

        assert issubclass(ModelReadinessDimension, BaseModel)

    def test_model_golden_chain_health_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_dogfood_scorecard import (
            ModelGoldenChainHealth,
        )

        assert issubclass(ModelGoldenChainHealth, BaseModel)

    def test_model_endpoint_health_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_dogfood_scorecard import (
            ModelEndpointHealth,
        )

        assert issubclass(ModelEndpointHealth, BaseModel)

    def test_model_delegation_health_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_dogfood_scorecard import (
            ModelDelegationHealth,
        )

        assert issubclass(ModelDelegationHealth, BaseModel)

    def test_model_infrastructure_health_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_dogfood_scorecard import (
            ModelInfrastructureHealth,
        )

        assert issubclass(ModelInfrastructureHealth, BaseModel)

    def test_model_dogfood_regression_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_dogfood_scorecard import (
            ModelDogfoodRegression,
        )

        assert issubclass(ModelDogfoodRegression, BaseModel)

    def test_model_dogfood_scorecard_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_dogfood_scorecard import (
            ModelDogfoodScorecard,
        )

        assert issubclass(ModelDogfoodScorecard, BaseModel)

    # model_doc_freshness_result.py — 1 class
    def test_model_doc_freshness_result_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_doc_freshness_result import (
            ModelDocFreshnessResult,
        )

        assert issubclass(ModelDocFreshnessResult, BaseModel)

    # model_doc_freshness_sweep_report.py — 2 classes
    def test_model_repo_doc_summary_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_doc_freshness_sweep_report import (
            ModelRepoDocSummary,
        )

        assert issubclass(ModelRepoDocSummary, BaseModel)

    def test_model_doc_freshness_sweep_report_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_doc_freshness_sweep_report import (
            ModelDocFreshnessSweepReport,
        )

        assert issubclass(ModelDocFreshnessSweepReport, BaseModel)

    # model_dod_sweep.py — 3 classes
    def test_model_dod_sweep_check_result_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_dod_sweep import (
            ModelDodSweepCheckResult,
        )

        assert issubclass(ModelDodSweepCheckResult, BaseModel)

    def test_model_dod_sweep_ticket_result_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_dod_sweep import (
            ModelDodSweepTicketResult,
        )

        assert issubclass(ModelDodSweepTicketResult, BaseModel)

    def test_model_dod_sweep_result_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_dod_sweep import (
            ModelDodSweepResult,
        )

        assert issubclass(ModelDodSweepResult, BaseModel)

    # model_integration_record.py — 2 classes
    def test_model_integration_probe_result_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_integration_record import (
            ModelIntegrationProbeResult,
        )

        assert issubclass(ModelIntegrationProbeResult, BaseModel)

    def test_model_integration_record_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_integration_record import (
            ModelIntegrationRecord,
        )

        assert issubclass(ModelIntegrationRecord, BaseModel)


@pytest.mark.unit
def test_repo_doc_summary_rejects_impossible_doc_counts() -> None:
    from omnibase_core.models.governance.model_repo_doc_summary import (
        ModelRepoDocSummary,
    )

    with pytest.raises(ValidationError, match="cannot exceed total_docs"):
        ModelRepoDocSummary(
            repo="omnibase_core",
            total_docs=1,
            fresh=1,
            stale=1,
            broken=0,
            broken_references=0,
        )


@pytest.mark.unit
def test_doc_freshness_sweep_report_rejects_contradictory_totals() -> None:
    from datetime import UTC, datetime

    from omnibase_core.models.governance.model_doc_freshness_sweep_report import (
        ModelDocFreshnessSweepReport,
    )

    with pytest.raises(ValidationError, match="must equal total_docs"):
        ModelDocFreshnessSweepReport(
            timestamp=datetime.now(UTC),
            total_docs=1,
            fresh_count=1,
            stale_count=1,
            broken_count=0,
            unknown_count=0,
            total_references=0,
            broken_reference_count=0,
            stale_reference_count=0,
        )

    with pytest.raises(ValidationError, match="cannot exceed total_references"):
        ModelDocFreshnessSweepReport(
            timestamp=datetime.now(UTC),
            total_docs=1,
            fresh_count=1,
            stale_count=0,
            broken_count=0,
            unknown_count=0,
            total_references=1,
            broken_reference_count=1,
            stale_reference_count=1,
        )


@pytest.mark.unit
def test_dod_sweep_check_result_rejects_unknown_subtype_mismatch() -> None:
    from omnibase_core.enums.governance.enum_dod_sweep_check import EnumDodSweepCheck
    from omnibase_core.enums.governance.enum_invariant_status import (
        EnumInvariantStatus,
    )
    from omnibase_core.models.governance.model_dod_sweep_check_result import (
        ModelDodSweepCheckResult,
    )

    with pytest.raises(ValidationError, match="only allowed"):
        ModelDodSweepCheckResult(
            check=EnumDodSweepCheck.CONTRACT_EXISTS,
            status=EnumInvariantStatus.PASS,
            unknown_subtype="exempt",
        )

    with pytest.raises(ValidationError, match="required"):
        ModelDodSweepCheckResult(
            check=EnumDodSweepCheck.CONTRACT_EXISTS,
            status=EnumInvariantStatus.UNKNOWN,
        )


@pytest.mark.unit
def test_dod_sweep_ticket_result_rejects_exemption_reason_mismatch() -> None:
    from omnibase_core.models.governance.model_dod_sweep_ticket_result import (
        ModelDodSweepTicketResult,
    )

    with pytest.raises(ValidationError, match="required"):
        ModelDodSweepTicketResult(
            ticket_id="OMN-10248",
            title="Batch D",
            checks=[],
            exempted=True,
        )

    with pytest.raises(ValidationError, match="only allowed"):
        ModelDodSweepTicketResult(
            ticket_id="OMN-10248",
            title="Batch D",
            checks=[],
            exemption_reason="not exempt",
        )


@pytest.mark.unit
def test_dod_sweep_result_rejects_mode_input_mismatch() -> None:
    from omnibase_core.models.governance.model_dod_sweep import ModelDodSweepResult

    with pytest.raises(ValidationError, match="lookback_days is required"):
        ModelDodSweepResult(
            schema_version="1.0.0",
            date="2026-04-29",
            run_id="run-1",
            mode="batch",
        )

    with pytest.raises(ValidationError, match="target_id is required"):
        ModelDodSweepResult(
            schema_version="1.0.0",
            date="2026-04-29",
            run_id="run-1",
            mode="targeted",
        )


@pytest.mark.unit
def test_dogfood_scorecard_rejects_invalid_wire_formats() -> None:
    from omnibase_core.enums.governance.enum_dogfood_status import EnumDogfoodStatus
    from omnibase_core.models.governance.model_dogfood_scorecard import (
        ModelDogfoodScorecard,
    )

    with pytest.raises(ValidationError, match="Invalid schema_version"):
        ModelDogfoodScorecard(
            schema_version="v1",
            captured_at="2026-04-29T07:00:00Z",
            run_id="run-1",
            overall_status=EnumDogfoodStatus.PASS,
        )

    with pytest.raises(ValidationError, match="Invalid captured_at"):
        ModelDogfoodScorecard(
            schema_version="1.0.0",
            captured_at="not-a-timestamp",
            run_id="run-1",
            overall_status=EnumDogfoodStatus.PASS,
        )


@pytest.mark.unit
def test_integration_probe_result_rejects_reason_status_mismatch() -> None:
    from omnibase_core.enums.governance.enum_integration_surface import (
        EnumIntegrationSurface,
    )
    from omnibase_core.enums.governance.enum_invariant_status import (
        EnumInvariantStatus,
    )
    from omnibase_core.enums.governance.enum_probe_reason import EnumProbeReason
    from omnibase_core.models.governance.model_integration_probe_result import (
        ModelIntegrationProbeResult,
    )

    with pytest.raises(ValidationError, match="only allowed"):
        ModelIntegrationProbeResult(
            surface=EnumIntegrationSurface.CI,
            status=EnumInvariantStatus.PASS,
            reason=EnumProbeReason.INCONCLUSIVE,
        )

    with pytest.raises(ValidationError, match="required"):
        ModelIntegrationProbeResult(
            surface=EnumIntegrationSurface.CI,
            status=EnumInvariantStatus.UNKNOWN,
        )
