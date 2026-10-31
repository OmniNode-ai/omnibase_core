# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The retrospective crossing models hold their invariants (OMN-21627).

Each model is one crossing of the retrospective graph. Each rule below has a
planted violation beside a control, so a test that cannot refuse proves nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_evidence_unit_outcome import EnumEvidenceUnitOutcome
from omnibase_core.enums.enum_experiment_slot import EnumExperimentSlot
from omnibase_core.enums.enum_retrospective_reason_code import (
    EnumRetrospectiveReasonCode,
)
from omnibase_core.enums.enum_retrospective_run_phase import EnumRetrospectiveRunPhase
from omnibase_core.enums.enum_retrospective_verdict import EnumRetrospectiveVerdict
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.retrospective.model_evidence_snapshot import (
    ModelEvidenceSnapshot,
)
from omnibase_core.models.retrospective.model_experiment_card import ModelExperimentCard
from omnibase_core.models.retrospective.model_experiment_evidence_record import (
    ModelExperimentEvidenceRecord,
)
from omnibase_core.models.retrospective.model_experiment_skill_run_result import (
    ModelExperimentSkillRunResult,
)
from omnibase_core.models.retrospective.model_experiment_verdict import (
    ModelExperimentVerdict,
)
from omnibase_core.models.retrospective.model_retrospective_collect_request import (
    ModelRetrospectiveCollectRequest,
)
from omnibase_core.models.retrospective.model_retrospective_digest import (
    ModelRetrospectiveDigest,
)
from omnibase_core.models.retrospective.model_retrospective_digest_request import (
    ModelRetrospectiveDigestRequest,
)
from omnibase_core.models.retrospective.model_retrospective_run_open import (
    ModelRetrospectiveRunOpen,
)
from omnibase_core.models.retrospective.model_retrospective_run_projected import (
    ModelRetrospectiveRunProjected,
)
from omnibase_core.models.retrospective.model_retrospective_run_state import (
    ModelRetrospectiveRunState,
)
from omnibase_core.models.retrospective.model_retrospective_verdict_set import (
    ModelRetrospectiveVerdictSet,
)
from omnibase_core.models.retrospective.model_success_contract import (
    ModelSuccessContract,
)

pytestmark = pytest.mark.unit

_T0 = datetime(2026, 10, 26, tzinfo=UTC)
_RUN = UUID(int=1)
_CORR = UUID(int=2)
_HASH = "a" * 64
_V1 = ModelSemVer(major=1, minor=0, patch=0)
_R1 = UUID(int=11)
_R2 = UUID(int=12)
_R3 = UUID(int=13)


def _contract(**values: object) -> ModelSuccessContract:
    return ModelSuccessContract.model_validate(
        {
            "experiment_id": _R1,
            "slot": EnumExperimentSlot.R1,
            "contract_version": _V1,
            "evaluator_version": _V1,
            "frozen_at": _T0,
            **values,
        }
    )


def _verdict(
    verdict: EnumRetrospectiveVerdict,
    *codes: EnumRetrospectiveReasonCode,
) -> ModelExperimentVerdict:
    return ModelExperimentVerdict(
        experiment_id=_R1,
        slot=EnumExperimentSlot.R1,
        verdict=verdict,
        reason_codes=codes,
        contract_version=_V1,
        evaluator_version=_V1,
        input_hash=_HASH,
    )


def _record() -> ModelExperimentEvidenceRecord:
    return ModelExperimentEvidenceRecord(
        record_id=UUID(int=3),
        slot=EnumExperimentSlot.R2,
        experiment_id=_R2,
        unit_ref="claim-1",
        outcome=EnumEvidenceUnitOutcome.UNASSESSED,
        source_ref="results/claim-1.json",
        source_hash=_HASH,
        assessor_version=_V1,
        recorded_at=_T0,
        correlation_id=_CORR,
    )


def _every_crossing() -> list[BaseModel]:
    verdict = _verdict(
        EnumRetrospectiveVerdict.INSUFFICIENT_EVIDENCE,
        EnumRetrospectiveReasonCode.CONTRACT_UNRESOLVED,
    )
    return [
        ModelRetrospectiveRunOpen(
            run_id=_RUN,
            correlation_id=_CORR,
            idempotency_key="2026-W44:config-1",
            cohort_start=_T0,
            cohort_cutoff=_T0 + timedelta(days=7),
            configuration_version=_V1,
        ),
        ModelRetrospectiveCollectRequest(
            run_id=_RUN,
            correlation_id=_CORR,
            cohort_start=_T0,
            cohort_cutoff=_T0 + timedelta(days=7),
        ),
        ModelExperimentSkillRunResult(
            slot=EnumExperimentSlot.R3,
            experiment_id=_R3,
            skill_name="plan-writes",
            skill_version=_V1,
            unit_ref="intent-1",
            result_ref="results/intent-1.json",
            result_hash=_HASH,
            completed_at=_T0,
            correlation_id=_CORR,
        ),
        _record(),
        ModelEvidenceSnapshot(
            run_id=_RUN,
            correlation_id=_CORR,
            cohort_cutoff=_T0,
            ingestion_watermark=_T0,
            input_hash=_HASH,
            contracts=(_contract(),),
            records=(_record(),),
        ),
        ModelRetrospectiveVerdictSet(
            run_id=_RUN,
            correlation_id=_CORR,
            input_hash=_HASH,
            evaluator_version=_V1,
            verdicts=(verdict,),
        ),
        ModelRetrospectiveRunState(
            run_id=_RUN,
            correlation_id=_CORR,
            phase=EnumRetrospectiveRunPhase.EVALUATED,
            revision=3,
            input_hash=_HASH,
            verdicts=(verdict,),
        ),
        ModelRetrospectiveRunProjected(
            run_id=_RUN,
            correlation_id=_CORR,
            phase=EnumRetrospectiveRunPhase.EVALUATED,
            revision=3,
        ),
        ModelRetrospectiveDigestRequest(run_id=_RUN, correlation_id=_CORR, revision=3),
        ModelRetrospectiveDigest(
            run_id=_RUN,
            correlation_id=_CORR,
            revision=3,
            verdicts=(verdict,),
            degraded=True,
        ),
    ]


@pytest.mark.parametrize("model", _every_crossing(), ids=lambda m: type(m).__name__)
def test_every_crossing_round_trips_through_json(model: BaseModel) -> None:
    assert type(model).model_validate_json(model.model_dump_json()) == model


@pytest.mark.parametrize("model", _every_crossing(), ids=lambda m: type(m).__name__)
def test_every_crossing_refuses_an_unknown_field(model: BaseModel) -> None:
    with pytest.raises(ValidationError):
        type(model).model_validate({**model.model_dump(), "unexpected": 1})


def test_a_naive_timestamp_is_refused() -> None:
    with pytest.raises(ValidationError):
        ModelRetrospectiveCollectRequest(
            run_id=_RUN,
            correlation_id=_CORR,
            cohort_start=datetime(2026, 10, 26),
            cohort_cutoff=_T0,
        )


def test_a_hash_that_is_not_lowercase_hex_is_refused() -> None:
    with pytest.raises(ValidationError):
        ModelRetrospectiveVerdictSet(
            run_id=_RUN,
            correlation_id=_CORR,
            input_hash="A" * 64,
            evaluator_version=_V1,
        )


def test_a_pass_with_a_reason_code_is_refused() -> None:
    _verdict(EnumRetrospectiveVerdict.PASS)
    with pytest.raises(ValidationError, match="carries no reason code"):
        _verdict(
            EnumRetrospectiveVerdict.PASS,
            EnumRetrospectiveReasonCode.PRIMARY_TARGET_MISSED,
        )


@pytest.mark.parametrize(
    "verdict",
    [EnumRetrospectiveVerdict.FAIL, EnumRetrospectiveVerdict.INSUFFICIENT_EVIDENCE],
)
def test_a_non_pass_without_a_reason_code_is_refused(
    verdict: EnumRetrospectiveVerdict,
) -> None:
    with pytest.raises(ValidationError, match="needs a reason code"):
        _verdict(verdict)


def test_an_unset_contract_names_every_unresolved_value() -> None:
    assert _contract().unresolved_fields() == (
        "cohort_floor",
        "coverage_floor",
        "baseline_rate",
        "target_rate",
        "coverage_target",
        "maturity_hours",
    )
    resolved = _contract(
        cohort_floor=10,
        coverage_floor=1.0,
        baseline_rate=0.4,
        target_rate=0.2,
        coverage_target=0.9,
        maturity_hours=72,
    )
    assert resolved.unresolved_fields() == ()


def test_a_digest_holds_at_most_three_candidate_cards() -> None:
    card = ModelExperimentCard(
        slot=EnumExperimentSlot.R1,
        experiment_id=_R1,
        hypothesis="independent claim checking reduces material corrections",
        skill_name="team-status-evidence",
        eligible_cohort="team-status drafts",
        primary_endpoint="material corrections per eligible draft",
    )
    base: dict[str, object] = {
        "run_id": _RUN,
        "correlation_id": _CORR,
        "revision": 1,
        "degraded": False,
    }
    ModelRetrospectiveDigest.model_validate({**base, "candidate_cards": (card,) * 3})
    with pytest.raises(ValidationError):
        ModelRetrospectiveDigest.model_validate(
            {**base, "candidate_cards": (card,) * 4}
        )
