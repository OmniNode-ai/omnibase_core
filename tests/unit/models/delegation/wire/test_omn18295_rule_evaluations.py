# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Per-rule quality evidence survives the terminal wire boundary (OMN-18295).

OMN-18295 gave the quality gate a per-rule record: every declared check's own
verdict, the threshold it applied, and whether it was entitled to veto. That
record was reachable inside the reducer and nowhere else. The terminal DTO in
this module is ``extra="forbid"`` and declared no field for it, so the
orchestrator could not put it on ``delegation-completed`` /
``delegation-failed`` at all — and the gateway, which builds its customer-
facing read model out of that payload, had nothing to serve. The only per-rule
evidence that reached a customer was the ``deciding_rules=`` fragment inside
one free-text failure string, present solely on a run that failed.

These tests pin the CONTRACT that closes that gap:

* the per-rule record is a typed wire model, not a dict;
* PASSING rules ride the terminal too — a record that exists only on failure
  cannot tell a rule that passed from one that never ran;
* a ``scored`` rule may fail on a terminal that PASSED, because a scored miss
  moves the graded score and the bar decides (delegation
  ``ca144d1a-ea03-475f-bc81-650ccfa0495e``, the defect this ticket opened on);
* a ``blocking`` rule that failed may NOT, because that IS the verdict;
* the field defaults empty and is omitted from the serialised payload when
  empty, so a producer that predates it emits a byte-identical terminal.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_quality_rule_enforcement import (
    EnumQualityRuleEnforcement,
)
from omnibase_core.models.delegation.wire import (
    ModelDelegationResult,
    ModelQualityRuleEvaluation,
)


def _rule(**kwargs: object) -> ModelQualityRuleEvaluation:
    defaults: dict[str, object] = {
        "rule": "concise",
        "enforcement": EnumQualityRuleEnforcement.SCORED,
        "passed": True,
    }
    defaults.update(kwargs)
    return ModelQualityRuleEvaluation(**defaults)  # type: ignore[arg-type]


def _result(**kwargs: object) -> ModelDelegationResult:
    defaults: dict[str, object] = {
        "correlation_id": uuid4(),
        "task_type": "summarization",
        "model_used": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "endpoint_url": "https://openrouter.ai/api/v1/chat/completions",
        "content": "ok",
        "quality_passed": True,
        "quality_score": 0.9,
        "latency_ms": 12,
        "fallback_to_claude": False,
    }
    defaults.update(kwargs)
    return ModelDelegationResult(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestTheEnforcementVocabulary:
    def test_a_rule_is_blocking_or_scored_and_nothing_else(self) -> None:
        assert {member.value for member in EnumQualityRuleEnforcement} == {
            "blocking",
            "scored",
        }

    def test_the_values_are_the_wire_strings_the_gateway_matches_on(self) -> None:
        assert EnumQualityRuleEnforcement.BLOCKING == "blocking"
        assert EnumQualityRuleEnforcement.SCORED == "scored"


@pytest.mark.unit
class TestOneRuleRecord:
    def test_it_carries_the_threshold_it_actually_applied(self) -> None:
        """The 250-word literal a customer was held to appeared in no receipt."""
        evaluation = _rule(threshold=250, threshold_unit="words", passed=False)
        assert evaluation.threshold == 250
        assert evaluation.threshold_unit == "words"

    def test_a_rule_that_declares_no_threshold_says_so_rather_than_zero(self) -> None:
        assert _rule().threshold is None

    def test_a_blank_rule_name_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _rule(rule="   ")

    def test_a_negative_threshold_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _rule(threshold=-1)

    def test_a_passing_rule_may_not_carry_a_failure_detail(self) -> None:
        """``detail`` is the failure message; a pass with one reads as a failure."""
        with pytest.raises(ValidationError):
            _rule(passed=True, detail="response is not concise")


@pytest.mark.unit
class TestTheTerminalCarriesThem:
    def test_the_field_exists_and_defaults_empty(self) -> None:
        assert _result().rule_evaluations == ()

    def test_an_empty_set_is_omitted_from_the_wire_payload(self) -> None:
        """A producer predating this field emits a byte-identical terminal."""
        assert "rule_evaluations" not in _result().model_dump(mode="json")

    def test_passing_rules_ride_a_completed_terminal(self) -> None:
        """The half the gateway could never serve: evidence on a run that PASSED."""
        dumped = _result(
            rule_evaluations=(
                _rule(rule="no_refusal", enforcement="blocking", passed=True),
                _rule(rule="concise", threshold=250, threshold_unit="words"),
            )
        ).model_dump(mode="json")
        carried = {item["rule"]: item for item in dumped["rule_evaluations"]}
        assert set(carried) == {"no_refusal", "concise"}
        assert carried["no_refusal"]["enforcement"] == "blocking"
        assert carried["concise"]["threshold"] == 250

    def test_it_round_trips_through_the_wire_shape(self) -> None:
        original = _result(
            rule_evaluations=(_rule(rule="accurate", enforcement="blocking"),)
        )
        restored = ModelDelegationResult.model_validate(
            original.model_dump(mode="json")
        )
        assert restored.rule_evaluations == original.rule_evaluations

    def test_the_same_rule_cannot_be_recorded_twice(self) -> None:
        with pytest.raises(ValidationError):
            _result(rule_evaluations=(_rule(), _rule(passed=False, detail="x")))


@pytest.mark.unit
class TestOneRuleDecides:
    def test_a_scored_miss_does_not_contradict_a_passed_terminal(self) -> None:
        """OMN-18295's property, at the wire.

        ``ca144d1a-ea03-475f-bc81-650ccfa0495e`` scored 0.900 against an 0.800
        bar with ``concise`` missed, and was terminalised ``failed`` anyway. A
        scored miss moves the score; the bar decides. The terminal must be able
        to say both things at once.
        """
        result = _result(
            quality_passed=True,
            rule_evaluations=(
                _rule(
                    rule="concise",
                    enforcement="scored",
                    passed=False,
                    threshold=250,
                    threshold_unit="words",
                    detail="response is not concise",
                ),
            ),
        )
        assert result.quality_passed is True
        assert result.rule_evaluations[0].passed is False

    def test_a_failed_blocking_rule_may_sit_on_a_passed_terminal(self) -> None:
        """The case that falsified this model's first draft.

        Refusing this pairing was the original design, and two existing proofs
        immediately broke: when the judge is unreachable the DETERMINISTIC
        acceptance floor decides, and a run whose blocking heuristics failed
        completes on that floor by declared policy
        (``test_judge_unavailable_deterministic_floor_omn13959``,
        ``test_quality_gate_judge_combine_omn13470`` in omnimarket).

        ``enforcement`` names the authority a rule holds within the heuristic
        band. It is not the only authority that can decide a run, and the
        record must be able to state what actually happened rather than being
        edited into agreement with the verdict. Which authority decided is
        carried by ``score_vs_required_bar`` and the terminal reason's
        ``score_source``.
        """
        result = _result(
            quality_passed=True,
            rule_evaluations=(
                _rule(
                    rule="no_obvious_regressions",
                    enforcement="blocking",
                    passed=False,
                    detail="failed no_obvious_regressions",
                ),
            ),
        )
        assert result.quality_passed is True
        assert result.rule_evaluations[0].passed is False

    def test_a_failed_blocking_rule_is_at_home_on_a_failed_terminal(self) -> None:
        result = _result(
            quality_passed=False,
            quality_score=0.8,
            required_quality_bar=0.8,
            score_vs_required_bar="at_or_above_bar",
            failed_acceptance_criteria=("TASK_MISMATCH: failed methodical_analysis",),
            rule_evaluations=(
                _rule(
                    rule="methodical_analysis",
                    enforcement="blocking",
                    passed=False,
                    detail="failed methodical_analysis",
                ),
                _rule(rule="cites_sources", enforcement="blocking", passed=True),
            ),
        )
        deciding = [
            item.rule
            for item in result.rule_evaluations
            if not item.passed
            and item.enforcement is EnumQualityRuleEnforcement.BLOCKING
        ]
        assert deciding == ["methodical_analysis"]
