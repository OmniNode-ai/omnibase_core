# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Field-by-field check of the remaining Task 13 models (OMN-22001).

The first test is the proposal check: every field section 4 of the orchestration
plan names exists on the manifest as a typed field. It fails on any missing field.
The rest hold the invariants of each model, each rule with a planted violation
beside a control, so a test that cannot refuse proves nothing.
"""

from __future__ import annotations

import types
import typing
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, get_args, get_origin
from uuid import UUID

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_champion_decision import EnumChampionDecision
from omnibase_core.enums.enum_experiment_estimator import EnumExperimentEstimator
from omnibase_core.enums.enum_experiment_lifecycle_state import (
    EnumExperimentLifecycleState,
)
from omnibase_core.enums.enum_experiment_refusal import EnumExperimentRefusal
from omnibase_core.enums.enum_experiment_slot import EnumExperimentSlot
from omnibase_core.enums.enum_experiment_subject_kind import EnumExperimentSubjectKind
from omnibase_core.enums.enum_guardrail_direction import EnumGuardrailDirection
from omnibase_core.enums.enum_retrospective_reason_code import (
    EnumRetrospectiveReasonCode,
)
from omnibase_core.enums.enum_retrospective_verdict import EnumRetrospectiveVerdict
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.experiment.model_champion_decision import (
    ModelChampionDecision,
)
from omnibase_core.models.experiment.model_evidence_cost import ModelEvidenceCost
from omnibase_core.models.experiment.model_evidence_cost_estimate import (
    ModelEvidenceCostEstimate,
)
from omnibase_core.models.experiment.model_evidence_snapshot import (
    ModelEvidenceSnapshot,
)
from omnibase_core.models.experiment.model_experiment_evidence_ref import (
    ModelExperimentEvidenceRef,
)
from omnibase_core.models.experiment.model_experiment_manifest import (
    ModelExperimentManifest,
)
from omnibase_core.models.experiment.model_experiment_refusal import (
    ModelExperimentRefusal,
)
from omnibase_core.models.experiment.model_experiment_run_state import (
    ModelExperimentRunState,
)
from omnibase_core.models.experiment.model_experiment_verdict import (
    ModelExperimentVerdict,
)
from omnibase_core.models.experiment.model_judgment_disagreement_row import (
    ModelJudgmentDisagreementRow,
)
from omnibase_core.models.experiment.model_judgment_record import ModelJudgmentRecord
from omnibase_core.models.experiment.model_judgment_stored_input import (
    ModelJudgmentStoredInput,
)
from omnibase_core.models.experiment.model_manifest_evidence_source import (
    ModelManifestEvidenceSource,
)
from omnibase_core.models.experiment.model_manifest_guardrail import (
    ModelManifestGuardrail,
)
from omnibase_core.models.experiment.model_manifest_metric_formula import (
    ModelManifestMetricFormula,
)
from omnibase_core.models.experiment.model_manifest_safety_condition import (
    ModelManifestSafetyCondition,
)
from omnibase_core.models.experiment.model_manifest_transition import (
    ModelManifestTransition,
)
from omnibase_core.models.experiment.model_retrospective_evaluator_section import (
    ModelRetrospectiveEvaluatorSection,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

pytestmark = pytest.mark.unit

_T0 = datetime(2026, 10, 26, tzinfo=UTC)
_T1 = datetime(2026, 10, 27, tzinfo=UTC)
_T2 = datetime(2026, 11, 3, tzinfo=UTC)
_EXP = UUID(int=21)
_RUN = UUID(int=1)
_CORR = UUID(int=2)
_HASH = "a" * 64
_V1 = ModelSemVer(major=1, minor=0, patch=0)

# Section 4 of the plan, phrase by phrase -> the manifest field that carries it.
PROPOSAL_FIELDS: dict[str, str] = {
    "eligible cohort": "eligible_cohort_rule",
    "independent intake source": "intake_source_ref",
    "identity": "experiment_id",
    "identity: subject kind": "subject_kind",
    "enrollment cutoff": "enrollment_cutoff",
    "due cutoff": "due_cutoff",
    "maturity cutoff": "maturity_cutoff",
    "exclusions": "exclusions",
    "changed-scope handling": "changed_scope_rule",
    "evidence schemas, source snapshots and hashes": "evidence_sources",
    "provenance": "provenance_rule",
    "coverage floor": "coverage_floor",
    "sample floor": "cohort_floor",
    "freshness": "freshness_max_age_hours",
    "baseline snapshot": "baseline_snapshot_ref",
    "baseline rate": "baseline_rate",
    "metric formulas": "metric_formulas",
    "comparison rule": "comparison_rule",
    "rounding rule": "rounding_rule",
    "target": "target_rate",
    "guardrails": "guardrails",
    "safety-fail conditions": "safety_fail_conditions",
    "missing rule": "missing_rule",
    "late rule": "late_rule",
    "duplicate rule": "duplicate_rule",
    "evaluator version": "evaluator_version",
    "permitted transitions": "permitted_transitions",
    "rule_sha": "rule_sha",
    "estimator": "estimator",
}

_NEW_MODELS: tuple[type[BaseModel], ...] = (
    ModelExperimentManifest,
    ModelManifestEvidenceSource,
    ModelManifestMetricFormula,
    ModelManifestGuardrail,
    ModelManifestSafetyCondition,
    ModelManifestTransition,
    ModelEvidenceCost,
    ModelEvidenceCostEstimate,
    ModelEvidenceSnapshot,
    ModelJudgmentRecord,
    ModelJudgmentStoredInput,
    ModelJudgmentDisagreementRow,
    ModelExperimentRefusal,
    ModelChampionDecision,
    ModelExperimentRunState,
    ModelRetrospectiveEvaluatorSection,
)


def _annotation_atoms(annotation: object) -> list[object]:
    """Flatten an annotation into its leaf types."""
    origin = get_origin(annotation)
    if origin is None:
        return [annotation]
    if origin is typing.Annotated:
        return _annotation_atoms(get_args(annotation)[0])
    atoms: list[object] = []
    for arg in get_args(annotation):
        if arg is Ellipsis:
            continue
        atoms.extend(_annotation_atoms(arg))
    if origin not in (tuple, types.UnionType, typing.Union):
        atoms.append(origin)
    return atoms


def _sample_manifest_values(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "experiment_id": _EXP,
        "subject_kind": EnumExperimentSubjectKind.RETROSPECTIVE,
        "estimator": EnumExperimentEstimator.BASELINE_THRESHOLD,
        "slot": EnumExperimentSlot.R1,
        "manifest_version": _V1,
        "evaluator_version": _V1,
        "frozen_at": _T0,
        "eligible_cohort_rule": "every due follow-up in the window",
        "intake_source_ref": "intake:ledger-rows",
        "enrollment_cutoff": _T0,
        "due_cutoff": _T1,
        "maturity_cutoff": _T2,
        "exclusions": (),
        "changed_scope_rule": "a changed scope is a new experiment",
        "evidence_sources": (
            ModelManifestEvidenceSource(
                schema_ref="schema:follow-up-evidence/1",
                snapshot_ref="snapshot:2026-10-26",
                content_hash=_HASH,
            ),
        ),
        "provenance_rule": "every record names its source result",
        "coverage_floor": 0.8,
        "cohort_floor": 10,
        "freshness_max_age_hours": 24,
        "baseline_snapshot_ref": "baseline:2026-10-19",
        "baseline_rate": 0.4,
        "metric_formulas": (
            ModelManifestMetricFormula(
                metric="open_rate", formula="open_units / due_units"
            ),
        ),
        "comparison_rule": "treatment rate against target rate",
        "rounding_rule": "round half even to 3 places",
        "target_rate": 0.3,
        "guardrails": (
            ModelManifestGuardrail(
                metric="coverage", bound=0.9, direction=EnumGuardrailDirection.AT_LEAST
            ),
        ),
        "safety_fail_conditions": (
            ModelManifestSafetyCondition(
                code=EnumRetrospectiveReasonCode.DUPLICATE_EFFECT,
                condition="an external effect ran twice",
            ),
        ),
        "missing_rule": "missing evidence is unknown, never zero",
        "late_rule": "late evidence makes a new revision",
        "duplicate_rule": "the first record per record_id wins; a conflict blocks",
        "permitted_transitions": (
            ModelManifestTransition(
                from_state=EnumExperimentLifecycleState.ADMITTED,
                to_state=EnumExperimentLifecycleState.ENROLLING,
            ),
        ),
        "rule_sha": _HASH,
    }
    values.update(overrides)
    return values


def _manifest(**overrides: object) -> ModelExperimentManifest:
    values = _sample_manifest_values(**overrides)
    values["rule_sha"] = ModelExperimentManifest.model_validate(
        {**values, "rule_sha": _HASH}
    ).computed_rule_sha()
    return ModelExperimentManifest.model_validate(values)


def _verdict(
    verdict: EnumRetrospectiveVerdict = EnumRetrospectiveVerdict.PASS,
    experiment_id: UUID = _EXP,
) -> ModelExperimentVerdict:
    codes: tuple[EnumRetrospectiveReasonCode, ...] = (
        ()
        if verdict is EnumRetrospectiveVerdict.PASS
        else (EnumRetrospectiveReasonCode.PRIMARY_TARGET_MISSED,)
    )
    return ModelExperimentVerdict(
        experiment_id=experiment_id,
        slot=EnumExperimentSlot.R1,
        verdict=verdict,
        reason_codes=codes,
        contract_version=_V1,
        evaluator_version=_V1,
        input_hash=_HASH,
    )


def _judgment(
    answer: EnumRetrospectiveVerdict = EnumRetrospectiveVerdict.PASS,
    rule_result: EnumRetrospectiveVerdict = EnumRetrospectiveVerdict.PASS,
    disagreement: bool | None = None,
) -> ModelJudgmentRecord:
    flag = answer is not rule_result if disagreement is None else disagreement
    return ModelJudgmentRecord(
        judgment_id=UUID(int=31),
        experiment_id=_EXP,
        model_name="judge-model-a",
        model_revision="2026-10",
        rubric_name="rubric:retro-followup",
        rubric_version=_V1,
        input_digest=_HASH,
        stored_inputs=(
            ModelJudgmentStoredInput(input_ref="evidence:1", content="unit closed"),
        ),
        cited_evidence=(ModelExperimentEvidenceRef(evidence_id=UUID(int=41)),),
        answer=answer,
        rule_result=rule_result,
        disagreement=flag,
        judged_at=_T1,
    )


# --------------------------------------------------------------- proposal check


def test_every_proposal_field_exists_on_the_manifest() -> None:
    missing = {
        phrase: field
        for phrase, field in PROPOSAL_FIELDS.items()
        if field not in ModelExperimentManifest.model_fields
    }
    assert missing == {}, f"proposal fields missing from the manifest: {missing}"


def test_the_manifest_carries_no_field_the_proposal_does_not_name() -> None:
    extra = (
        set(ModelExperimentManifest.model_fields)
        - set(PROPOSAL_FIELDS.values())
        - {"slot", "manifest_version", "frozen_at"}
    )
    assert extra == set(), f"undeclared manifest fields: {extra}"


@pytest.mark.parametrize("model", _NEW_MODELS, ids=lambda m: m.__name__)
def test_no_untyped_dict_and_no_any_in_any_field(model: type[BaseModel]) -> None:
    for name, info in model.model_fields.items():
        for atom in _annotation_atoms(info.annotation):
            assert atom is not Any, f"{model.__name__}.{name} is Any"
            assert atom not in (dict, object, list, set), (
                f"{model.__name__}.{name} is untyped: {atom}"
            )


# ---------------------------------------------- frozen, extra forbid, round trip


def _instances() -> list[BaseModel]:
    verdict = _verdict()
    judgment = _judgment()
    return [
        _manifest(),
        ModelManifestEvidenceSource(
            schema_ref="s", snapshot_ref="n", content_hash=_HASH
        ),
        ModelManifestMetricFormula(metric="m", formula="a / b"),
        ModelManifestGuardrail(
            metric="m", bound=1.0, direction=EnumGuardrailDirection.AT_MOST
        ),
        ModelManifestSafetyCondition(
            code=EnumRetrospectiveReasonCode.FALSE_COMPLETION, condition="c"
        ),
        ModelManifestTransition(
            from_state=EnumExperimentLifecycleState.SEALED,
            to_state=EnumExperimentLifecycleState.COLLECTING,
        ),
        ModelEvidenceCost(),
        ModelEvidenceCostEstimate(
            amount=Decimal("1.5"), unit="usd", price_date=date(2026, 10, 1)
        ),
        ModelJudgmentStoredInput(input_ref="r", content="c"),
        judgment,
        ModelJudgmentDisagreementRow.from_judgment(
            _judgment(EnumRetrospectiveVerdict.FAIL), recorded_at=_T1
        ),
        ModelExperimentRefusal(
            experiment_id=_EXP,
            refusal=EnumExperimentRefusal.MISSING_EVIDENCE,
            refused_at=_T1,
        ),
        ModelChampionDecision(
            experiment_id=_EXP,
            decision=EnumChampionDecision.PROMOTE,
            verdict=EnumRetrospectiveVerdict.PASS,
            evaluator_version=_V1,
            input_hash=_HASH,
            decided_at=_T2,
        ),
        ModelExperimentRunState(
            experiment_id=_EXP,
            correlation_id=_CORR,
            subject_kind=EnumExperimentSubjectKind.RETROSPECTIVE,
            state=EnumExperimentLifecycleState.ADMITTED,
            revision=1,
        ),
        ModelRetrospectiveEvaluatorSection(
            run_id=_RUN,
            correlation_id=_CORR,
            revision=1,
            evaluator_version=_V1,
            input_hash=_HASH,
            verdicts=(verdict,),
        ),
    ]


@pytest.mark.parametrize("instance", _instances(), ids=lambda i: type(i).__name__)
class TestEveryModel:
    def test_round_trips_through_json(self, instance: BaseModel) -> None:
        again = type(instance).model_validate_json(instance.model_dump_json())
        assert again == instance

    def test_is_frozen(self, instance: BaseModel) -> None:
        name = next(iter(type(instance).model_fields))
        with pytest.raises(ValidationError):
            setattr(instance, name, getattr(instance, name))

    def test_unknown_field_is_refused(self, instance: BaseModel) -> None:
        data = instance.model_dump()
        data["grants_adoption"] = True
        with pytest.raises(ValidationError):
            type(instance).model_validate(data)


# ------------------------------------------------------------- unresolved values


def test_unresolved_manifest_validates_and_names_every_unset_value() -> None:
    manifest = ModelExperimentManifest.model_validate(
        {
            "experiment_id": _EXP,
            "subject_kind": EnumExperimentSubjectKind.RETROSPECTIVE,
            "estimator": EnumExperimentEstimator.BASELINE_THRESHOLD,
            "manifest_version": _V1,
            "evaluator_version": _V1,
            "frozen_at": _T0,
            "rule_sha": _HASH,
        }
    )
    unresolved = manifest.unresolved_fields()
    assert "cohort_floor" in unresolved
    assert "baseline_rate" in unresolved
    assert "permitted_transitions" in unresolved
    assert manifest.is_resolved is False
    with pytest.raises(ModelOnexError, match="cohort_floor"):
        manifest.require_resolved()


def test_every_optional_manifest_field_is_tracked_as_resolvable() -> None:
    optional = {
        name
        for name, info in ModelExperimentManifest.model_fields.items()
        if type(None) in _annotation_atoms(info.annotation)
    }
    assert optional - {"slot"} == set(ModelExperimentManifest.resolvable_fields())


def test_a_complete_manifest_is_resolved() -> None:
    manifest = _manifest()
    assert manifest.unresolved_fields() == ()
    assert manifest.is_resolved is True
    manifest.require_resolved()


def test_an_empty_declared_list_is_resolved_but_none_is_not() -> None:
    assert "exclusions" not in _manifest(exclusions=()).unresolved_fields()
    assert "exclusions" in _manifest(exclusions=None).unresolved_fields()


def test_a_single_unresolved_value_blocks_resolution() -> None:
    manifest = _manifest(coverage_floor=None)
    assert manifest.unresolved_fields() == ("coverage_floor",)
    assert manifest.is_resolved is False


# ----------------------------------------------------------------------- rule_sha


def test_rule_sha_matches_its_values_and_changes_with_any_value() -> None:
    manifest = _manifest()
    assert manifest.rule_sha_matches() is True
    changed = manifest.model_copy(update={"target_rate": 0.31})
    assert changed.rule_sha_matches() is False
    assert changed.computed_rule_sha() != manifest.rule_sha


def test_rule_sha_ignores_nothing_but_itself() -> None:
    manifest = _manifest()
    other_sha = manifest.model_copy(update={"rule_sha": "b" * 64})
    assert other_sha.computed_rule_sha() == manifest.computed_rule_sha()


def test_rule_sha_must_be_64_lowercase_hex() -> None:
    with pytest.raises(ValidationError):
        ModelExperimentManifest.model_validate(_sample_manifest_values(rule_sha="XYZ"))


# --------------------------------------------------------------- manifest parts


def test_safety_condition_accepts_only_safety_codes() -> None:
    ModelManifestSafetyCondition(
        code=EnumRetrospectiveReasonCode.UNAUTHORIZED_EFFECT, condition="c"
    )
    with pytest.raises(ValidationError, match="safety"):
        ModelManifestSafetyCondition(
            code=EnumRetrospectiveReasonCode.PRIMARY_TARGET_MISSED, condition="c"
        )


def test_a_terminal_state_has_no_permitted_exit() -> None:
    ModelManifestTransition(
        from_state=EnumExperimentLifecycleState.SEALED,
        to_state=EnumExperimentLifecycleState.DECIDED,
    )
    with pytest.raises(ValidationError, match="terminal"):
        ModelManifestTransition(
            from_state=EnumExperimentLifecycleState.DECIDED,
            to_state=EnumExperimentLifecycleState.SEALED,
        )


# --------------------------------------------------------------------------- cost


def test_default_cost_is_unknown_never_zero() -> None:
    cost = ModelEvidenceCost()
    assert cost.unknown is True
    assert cost.measured_amount is None
    assert ModelEvidenceSnapshot.model_fields["cost"].default_factory is not None


def test_measured_cost_needs_its_source_and_unit() -> None:
    ModelEvidenceCost(
        measured_amount=Decimal("0.42"),
        measurement_source="provider-invoice",
        unit="usd",
        unknown=False,
    )
    with pytest.raises(ValidationError, match="source"):
        ModelEvidenceCost(measured_amount=Decimal("0.42"), unit="usd", unknown=False)
    with pytest.raises(ValidationError, match="unit"):
        ModelEvidenceCost(
            measured_amount=Decimal("0.42"),
            measurement_source="provider-invoice",
            unknown=False,
        )


def test_unknown_flag_and_measured_amount_cannot_disagree() -> None:
    with pytest.raises(ValidationError, match="unknown"):
        ModelEvidenceCost(
            measured_amount=Decimal("1"),
            measurement_source="s",
            unit="usd",
            unknown=True,
        )
    with pytest.raises(ValidationError, match="unknown"):
        ModelEvidenceCost(unknown=False)


def test_an_estimate_never_stands_in_for_a_measurement() -> None:
    cost = ModelEvidenceCost(
        estimate=ModelEvidenceCostEstimate(
            amount=Decimal("2"), unit="usd", price_date=date(2026, 10, 1)
        )
    )
    assert cost.unknown is True
    assert cost.measured_amount is None
    assert cost.estimate is not None
    assert "price_date" in ModelEvidenceCostEstimate.model_fields


def test_negative_cost_is_refused() -> None:
    with pytest.raises(ValidationError):
        ModelEvidenceCost(
            measured_amount=Decimal("-1"),
            measurement_source="s",
            unit="usd",
            unknown=False,
        )


def test_snapshot_without_cost_still_validates_with_unknown_cost() -> None:
    snapshot = ModelEvidenceSnapshot(
        run_id=_RUN,
        correlation_id=_CORR,
        cohort_cutoff=_T0,
        ingestion_watermark=_T1,
        input_hash=_HASH,
    )
    assert snapshot.cost.unknown is True


# ----------------------------------------------------------------------- judgment


def test_judgment_has_every_field_the_plan_names() -> None:
    fields = set(ModelJudgmentRecord.model_fields)
    assert {
        "model_name",
        "model_revision",
        "rubric_name",
        "input_digest",
        "stored_inputs",
        "cited_evidence",
        "answer",
        "rule_result",
        "disagreement",
    } <= fields


def test_disagreement_flag_must_follow_answer_versus_rule_result() -> None:
    _judgment(EnumRetrospectiveVerdict.PASS, EnumRetrospectiveVerdict.PASS)
    _judgment(EnumRetrospectiveVerdict.PASS, EnumRetrospectiveVerdict.FAIL)
    with pytest.raises(ValidationError, match="disagreement"):
        _judgment(
            EnumRetrospectiveVerdict.PASS,
            EnumRetrospectiveVerdict.FAIL,
            disagreement=False,
        )
    with pytest.raises(ValidationError, match="disagreement"):
        _judgment(
            EnumRetrospectiveVerdict.PASS,
            EnumRetrospectiveVerdict.PASS,
            disagreement=True,
        )


def test_disagreement_row_only_comes_from_a_disagreeing_judgment() -> None:
    row = ModelJudgmentDisagreementRow.from_judgment(
        _judgment(EnumRetrospectiveVerdict.FAIL), recorded_at=_T1
    )
    assert row.answer is EnumRetrospectiveVerdict.FAIL
    assert row.rule_result is EnumRetrospectiveVerdict.PASS
    with pytest.raises(ModelOnexError, match="disagree"):
        ModelJudgmentDisagreementRow.from_judgment(_judgment(), recorded_at=_T1)
    with pytest.raises(ValidationError, match="disagree"):
        ModelJudgmentDisagreementRow(
            judgment_id=UUID(int=31),
            experiment_id=_EXP,
            model_name="m",
            rubric_name="r",
            answer=EnumRetrospectiveVerdict.PASS,
            rule_result=EnumRetrospectiveVerdict.PASS,
            recorded_at=_T1,
        )


# ------------------------------------------------------------ enums and decisions


def test_refusal_enum_names_the_plan_refusals_with_rule_hash_mismatch() -> None:
    names = {member.name for member in EnumExperimentRefusal}
    assert {
        "MISSING_EVIDENCE",
        "TASK_MISMATCH",
        "REFUSED_UNMEASURED",
        "REFUSED_NO_CONFIG_PIN",
        "AA_CONTROL_FAILED",
        "HELD_OUT_SPENT",
        "STALE_DECISION",
        "VOID",
        "RULE_HASH_MISMATCH",
    } == names


def test_refusal_vocabulary_is_kept_apart_from_the_reason_codes() -> None:
    refusal_values = {member.value for member in EnumExperimentRefusal}
    reason_values = {member.value for member in EnumRetrospectiveReasonCode}
    assert refusal_values & reason_values == set()


def test_champion_decision_values() -> None:
    assert {m.name for m in EnumChampionDecision} == {"PROMOTE", "RETAIN", "REJECT"}


def test_estimator_values_name_the_three_dispatch_targets() -> None:
    assert {m.value for m in EnumExperimentEstimator} == {
        "paired_bootstrap",
        "cluster_stratified",
        "baseline_threshold",
    }


def test_promote_needs_a_pass_verdict() -> None:
    def build(
        decision: EnumChampionDecision, verdict: EnumRetrospectiveVerdict
    ) -> ModelChampionDecision:
        return ModelChampionDecision(
            experiment_id=_EXP,
            decision=decision,
            verdict=verdict,
            evaluator_version=_V1,
            input_hash=_HASH,
            decided_at=_T2,
        )

    build(EnumChampionDecision.PROMOTE, EnumRetrospectiveVerdict.PASS)
    build(EnumChampionDecision.RETAIN, EnumRetrospectiveVerdict.INSUFFICIENT_EVIDENCE)
    build(EnumChampionDecision.REJECT, EnumRetrospectiveVerdict.FAIL)
    with pytest.raises(ValidationError, match="PROMOTE"):
        build(EnumChampionDecision.PROMOTE, EnumRetrospectiveVerdict.FAIL)


def test_verdict_and_decision_authorize_nothing() -> None:
    forbidden = ("adopt", "deploy", "permission", "grant", "authoriz", "approve")
    for model in (ModelExperimentVerdict, ModelChampionDecision):
        for name in model.model_fields:
            assert not any(word in name for word in forbidden), (model, name)


# --------------------------------------------------------------------- run state


def _state(**overrides: object) -> ModelExperimentRunState:
    values: dict[str, object] = {
        "experiment_id": _EXP,
        "correlation_id": _CORR,
        "subject_kind": EnumExperimentSubjectKind.RETROSPECTIVE,
        "state": EnumExperimentLifecycleState.ADMITTED,
        "revision": 1,
    }
    values.update(overrides)
    return ModelExperimentRunState.model_validate(values)


def test_lifecycle_has_fourteen_states_and_five_terminals() -> None:
    assert len(EnumExperimentLifecycleState) == 14
    assert {s.name for s in EnumExperimentLifecycleState if s.is_terminal} == {
        "DECIDED",
        "VOID",
        "CANCELLED",
        "BUDGET_EXHAUSTED",
        "REFUSED",
    }


def test_a_sealed_experiment_must_carry_its_rule_sha() -> None:
    _state(state=EnumExperimentLifecycleState.SEALED, rule_sha=_HASH)
    with pytest.raises(ValidationError, match="rule_sha"):
        _state(state=EnumExperimentLifecycleState.SEALED)
    _state(state=EnumExperimentLifecycleState.ENROLLING)


def test_a_refused_experiment_names_its_refusal_and_only_then() -> None:
    refusal = ModelExperimentRefusal(
        experiment_id=_EXP,
        refusal=EnumExperimentRefusal.AA_CONTROL_FAILED,
        refused_at=_T1,
    )
    _state(state=EnumExperimentLifecycleState.REFUSED, refusal=refusal)
    with pytest.raises(ValidationError, match="refusal"):
        _state(state=EnumExperimentLifecycleState.REFUSED)
    with pytest.raises(ValidationError, match="refusal"):
        _state(state=EnumExperimentLifecycleState.ENROLLING, refusal=refusal)


def test_evaluated_needs_a_verdict_and_decided_needs_a_decision() -> None:
    verdict = _verdict()
    decision = ModelChampionDecision(
        experiment_id=_EXP,
        decision=EnumChampionDecision.PROMOTE,
        verdict=EnumRetrospectiveVerdict.PASS,
        evaluator_version=_V1,
        input_hash=_HASH,
        decided_at=_T2,
    )
    sealed = {"rule_sha": _HASH}
    _state(state=EnumExperimentLifecycleState.EVALUATED, verdict=verdict, **sealed)
    with pytest.raises(ValidationError, match="verdict"):
        _state(state=EnumExperimentLifecycleState.EVALUATED, **sealed)
    _state(
        state=EnumExperimentLifecycleState.DECIDED,
        verdict=verdict,
        decision=decision,
        **sealed,
    )
    with pytest.raises(ValidationError, match="decision"):
        _state(state=EnumExperimentLifecycleState.DECIDED, verdict=verdict, **sealed)
    with pytest.raises(ValidationError, match="decision"):
        _state(
            state=EnumExperimentLifecycleState.EVALUATED,
            verdict=verdict,
            decision=decision,
            **sealed,
        )


def test_a_decision_must_belong_to_the_same_experiment() -> None:
    other = ModelChampionDecision(
        experiment_id=UUID(int=99),
        decision=EnumChampionDecision.RETAIN,
        verdict=EnumRetrospectiveVerdict.FAIL,
        evaluator_version=_V1,
        input_hash=_HASH,
        decided_at=_T2,
    )
    with pytest.raises(ValidationError, match="experiment"):
        _state(
            state=EnumExperimentLifecycleState.DECIDED,
            rule_sha=_HASH,
            verdict=_verdict(),
            decision=other,
        )


def test_revision_starts_at_one() -> None:
    with pytest.raises(ValidationError):
        _state(revision=0)


# ---------------------------------------------------------------- evaluator section


def test_section_decisions_and_disagreements_must_match_the_run() -> None:
    verdict = _verdict()
    decision = ModelChampionDecision(
        experiment_id=_EXP,
        decision=EnumChampionDecision.PROMOTE,
        verdict=EnumRetrospectiveVerdict.PASS,
        evaluator_version=_V1,
        input_hash=_HASH,
        decided_at=_T2,
    )
    disagreeing = _judgment(EnumRetrospectiveVerdict.FAIL)
    row = ModelJudgmentDisagreementRow.from_judgment(disagreeing, recorded_at=_T1)
    base = {
        "run_id": _RUN,
        "correlation_id": _CORR,
        "revision": 1,
        "evaluator_version": _V1,
        "input_hash": _HASH,
    }
    ModelRetrospectiveEvaluatorSection(
        **base,
        verdicts=(verdict,),
        decisions=(decision,),
        judgments=(disagreeing,),
        disagreements=(row,),
    )
    with pytest.raises(ValidationError, match="decision"):
        ModelRetrospectiveEvaluatorSection(**base, decisions=(decision,))
    with pytest.raises(ValidationError, match="disagreement"):
        ModelRetrospectiveEvaluatorSection(
            **base, verdicts=(verdict,), disagreements=(row,)
        )
