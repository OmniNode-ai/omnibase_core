# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelDispatchEvalResult."""

from datetime import UTC, datetime
from typing import get_args, get_origin

import pytest
from pydantic import ValidationError

from omnibase_core.enums.cost import EnumUsageSource
from omnibase_core.models.cost import ModelCostProvenance
from omnibase_core.models.dispatch import (
    EnumDispatchVerdict,
    ModelCallRecord,
    ModelDispatchEvalResult,
)


def _call(
    *,
    input_tokens: int = 100,
    output_tokens: int = 20,
    cost_dollars: float = 0.01,
    provenance: ModelCostProvenance | None = None,
) -> ModelCallRecord:
    return ModelCallRecord(
        provider="openai",
        model="gpt-5-mini",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=250,
        cost_dollars=cost_dollars,
        cost_provenance=provenance
        or ModelCostProvenance(
            usage_source=EnumUsageSource.MEASURED,
            source_payload_hash="hash-1",
        ),
    )


def _result(**overrides: object) -> ModelDispatchEvalResult:
    calls = [_call()]
    defaults: dict[str, object] = {
        "task_id": "task-1",
        "dispatch_id": "dispatch-1",
        "ticket_id": "OMN-10381",
        "verdict": EnumDispatchVerdict.PASS,
        "quality_score": 0.95,
        "token_cost": 120,
        "dollars_cost": 0.01,
        "cost_provenance": ModelCostProvenance.rollup(calls),
        "model_calls": calls,
        "evaluated_at": datetime(2026, 4, 30, 12, 0, tzinfo=UTC),
        "eval_latency_ms": 300,
    }
    defaults.update(overrides)
    return ModelDispatchEvalResult(**defaults)


@pytest.mark.unit
def test_dispatch_eval_result_round_trips_with_enum_verdict() -> None:
    result = _result()

    assert result.verdict == EnumDispatchVerdict.PASS
    assert isinstance(result.verdict, EnumDispatchVerdict)
    assert ModelDispatchEvalResult.model_validate(result.model_dump()) == result


@pytest.mark.unit
def test_dispatch_eval_result_is_frozen() -> None:
    result = _result()

    with pytest.raises(ValidationError):
        result.task_id = "task-2"


@pytest.mark.unit
def test_dispatch_eval_result_uses_pep_604_optional_annotations() -> None:
    ticket_field = ModelDispatchEvalResult.model_fields["ticket_id"]
    score_field = ModelDispatchEvalResult.model_fields["quality_score"]

    assert get_origin(ticket_field.annotation) is type(str | None)
    assert set(get_args(ticket_field.annotation)) == {str, type(None)}
    assert get_origin(score_field.annotation) is type(float | None)
    assert set(get_args(score_field.annotation)) == {float, type(None)}


@pytest.mark.unit
def test_dispatch_eval_result_rejects_unknown_verdict_string() -> None:
    with pytest.raises(ValidationError):
        _result(verdict="success")


@pytest.mark.unit
def test_cost_provenance_rollup_measured_when_all_cost_bearing_calls_measured() -> None:
    rollup = ModelCostProvenance.rollup(
        [
            _call(
                provenance=ModelCostProvenance(
                    usage_source=EnumUsageSource.MEASURED,
                    source_payload_hash="hash-1",
                )
            ),
            _call(
                provenance=ModelCostProvenance(
                    usage_source=EnumUsageSource.MEASURED,
                    source_payload_hash="hash-2",
                )
            ),
        ]
    )

    assert rollup.usage_source == EnumUsageSource.MEASURED
    assert rollup.source_payload_hash is not None
    assert rollup.estimation_method is None


@pytest.mark.unit
def test_cost_provenance_rollup_estimated_when_any_cost_bearing_call_estimated() -> (
    None
):
    rollup = ModelCostProvenance.rollup(
        [
            _call(),
            _call(
                provenance=ModelCostProvenance(
                    usage_source=EnumUsageSource.ESTIMATED,
                    estimation_method="pricing_table",
                )
            ),
        ]
    )

    assert rollup.usage_source == EnumUsageSource.ESTIMATED
    assert rollup.estimation_method == "model_call_rollup"
    assert rollup.source_payload_hash is None


@pytest.mark.unit
def test_cost_provenance_rollup_unknown_when_no_cost_bearing_calls_exist() -> None:
    rollup = ModelCostProvenance.rollup(
        [
            _call(
                input_tokens=0,
                output_tokens=0,
                cost_dollars=0,
                provenance=ModelCostProvenance(usage_source=EnumUsageSource.UNKNOWN),
            )
        ]
    )

    assert rollup.usage_source == EnumUsageSource.UNKNOWN
    assert rollup.estimation_method is None
    assert rollup.source_payload_hash is None
