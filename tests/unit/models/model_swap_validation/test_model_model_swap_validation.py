# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Model-swap validation wire contracts reject invalid or ambiguous evidence."""

from __future__ import annotations

import json
from collections.abc import Callable
from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.models.model_swap_validation import (
    ModelModelSwapValidationGatewayCall,
    ModelModelSwapValidationRequest,
    ModelModelSwapValidationResult,
)

pytestmark = pytest.mark.unit


def request_data() -> dict[str, object]:
    return {
        "correlation_id": uuid4(),
        "task_type": "sample-task",
        "reference_model": "example-vendor/reference-model",
        "candidate_model": "example-other/candidate-model",
        "judge_mode": "backend",
        "judge_backend_id": "sample-judge",
        "answer_source": "recorded",
        "replay_set_digest": "a" * 64,
        "quality_floor": 0.95,
        "max_cost_usd": 1.0,
        "work_unit_repository": "sample/work-unit",
    }


def result_data() -> dict[str, object]:
    return {
        "correlation_id": uuid4(),
        "status": "completed",
        "judge_mode": "stub",
        "quality_floor": 0.95,
        "tool_commit": "a" * 40,
        "image_digest": "sha256:" + "b" * 64,
        "decision": "recommend",
        "recommended_model": "example-other/candidate-model",
        "lower_bound": 0.96,
        "gates": [{"id": "quality", "pass": True, "reason": "floor met"}],
        "per_case": [
            {
                "case_id": "case-1",
                "verdict_reference_first": "equivalent",
                "verdict_candidate_first": "equivalent",
                "score": 1.0,
            }
        ],
    }


@pytest.mark.parametrize(
    ("model", "data"),
    [
        (ModelModelSwapValidationRequest, request_data),
        (ModelModelSwapValidationResult, result_data),
    ],
)
@pytest.mark.parametrize(
    "floor", [0.8, 1.0, 0.79, 1.01, float("nan"), float("inf"), float("-inf")]
)
def test_models_refuse_quality_floor_outside_open_bounds(
    model: type[BaseModel], data: Callable[[], dict[str, object]], floor: float
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(data() | {"quality_floor": floor})


@pytest.mark.parametrize(
    ("model", "data"),
    [
        (ModelModelSwapValidationRequest, request_data),
        (ModelModelSwapValidationResult, result_data),
    ],
)
def test_quality_floor_schema_preserves_open_bounds(
    model: type[BaseModel], data: Callable[[], dict[str, object]]
) -> None:
    bounds = model.model_json_schema()["properties"]["quality_floor"]
    assert bounds["exclusiveMinimum"] == 0.8
    assert bounds["exclusiveMaximum"] == 1.0
    value = model.model_validate(data())
    assert model.model_validate_json(value.model_dump_json()) == value


def test_backend_judge_requires_backend_identifier() -> None:
    with pytest.raises(ValidationError, match="judge_backend_id"):
        ModelModelSwapValidationRequest.model_validate(
            request_data() | {"judge_backend_id": None}
        )
    stub = ModelModelSwapValidationRequest.model_validate(
        request_data() | {"judge_mode": "stub", "judge_backend_id": None}
    )
    assert stub.judge_backend_id is None


def test_missing_repository_can_be_refused_by_handler() -> None:
    request = ModelModelSwapValidationRequest.model_validate(
        request_data() | {"work_unit_repository": None}
    )
    assert request.work_unit_repository is None


@pytest.mark.parametrize(
    "update",
    [
        {"max_cost_usd": 0},
        {"max_cost_usd": float("inf")},
        {"replay_set_digest": "not-a-digest"},
        {"unexpected": True},
    ],
)
def test_request_refuses_invalid_data(update: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ModelModelSwapValidationRequest.model_validate(request_data() | update)


def test_result_round_trips_gate_and_case_evidence() -> None:
    result = ModelModelSwapValidationResult.model_validate(result_data())
    assert result.evidence_only is True
    assert result.per_case[0].case_id == "case-1"
    assert result.gates[0].passed is True
    payload = json.loads(result.model_dump_json())
    assert payload["gates"][0] == {"id": "quality", "pass": True, "reason": "floor met"}
    assert (
        ModelModelSwapValidationResult.model_validate_json(result.model_dump_json())
        == result
    )
    schema = ModelModelSwapValidationResult.model_json_schema()
    assert schema["properties"]["evidence_only"]["const"] is True


@pytest.mark.parametrize(
    "update",
    [
        {"evidence_only": False},
        {"failure_reason": "tool_failed"},
        {"tool_commit": None},
        {"image_digest": None},
        {"decision": None},
        {"tool_commit": "branch-name"},
        {"image_digest": "image:latest"},
        {"tool_cost_measurement_source": "provider_reported_charge"},
        {"tool_cost_measurement_source": "unpriced"},
        {"decision": "reject"},
        {
            "per_case": [
                {
                    "case_id": "case-1",
                    "verdict_reference_first": "equivalent",
                    "score": 1,
                }
            ]
        },
    ],
)
def test_result_refuses_invalid_or_contradictory_evidence(
    update: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ModelModelSwapValidationResult.model_validate(result_data() | update)


def test_preflight_failure_does_not_invent_an_image_or_report() -> None:
    result = ModelModelSwapValidationResult(
        correlation_id=uuid4(),
        status="failed",
        failure_reason="repository_refused",
        quality_floor=0.95,
        judge_mode="stub",
    )
    assert result.tool_commit is None
    assert result.image_digest is None
    assert result.decision is None
    with pytest.raises(ValidationError, match="failure reason"):
        ModelModelSwapValidationResult(
            correlation_id=uuid4(),
            status="failed",
            quality_floor=0.95,
            judge_mode="stub",
        )


@pytest.mark.parametrize(
    ("source", "cost"),
    [
        ("provider_reported_charge", 0.02),
        ("estimated_list_price", 0.01),
        ("unpriced", None),
    ],
)
def test_gateway_cost_provenance(source: str, cost: float | None) -> None:
    call = ModelModelSwapValidationGatewayCall(
        role="judge",
        model_id="example-judge/judge-model",
        tokens_in=10,
        tokens_out=3,
        cost_usd=cost,
        cost_measurement_source=source,
    )
    assert call.cost_usd == cost


@pytest.mark.parametrize(
    ("source", "cost"), [("unpriced", 0.01), ("estimated_list_price", None)]
)
def test_gateway_refuses_cost_provenance_mismatch(
    source: str, cost: float | None
) -> None:
    with pytest.raises(ValidationError, match="unpriced"):
        ModelModelSwapValidationGatewayCall(
            role="judge",
            model_id="example-judge/judge-model",
            tokens_in=10,
            tokens_out=3,
            cost_usd=cost,
            cost_measurement_source=source,
        )


@pytest.mark.parametrize("count", [True, -1, 1.5])
def test_gateway_token_counts_are_nonnegative_integers(count: object) -> None:
    with pytest.raises(ValidationError):
        ModelModelSwapValidationGatewayCall(
            role="judge",
            model_id="example-judge/judge-model",
            tokens_in=count,
            tokens_out=3,
            cost_usd=None,
            cost_measurement_source="unpriced",
        )


def test_ineligible_recommendation_preserves_reported_decision() -> None:
    result = ModelModelSwapValidationResult.model_validate(
        result_data()
        | {
            "decision": "inconclusive",
            "reported_decision": "recommend",
            "recommendation_effective": False,
            "recommended_model": None,
        }
    )
    payload = json.loads(result.model_dump_json())
    assert payload["decision"] == "inconclusive"
    assert payload["reported_decision"] == "recommend"
    assert payload["recommendation_effective"] is False


def gateway_call_data(source: str, cost: float | None) -> dict[str, object]:
    return {
        "role": "judge",
        "model_id": "example-judge/judge-model",
        "tokens_in": 10,
        "tokens_out": 3,
        "cost_usd": cost,
        "cost_measurement_source": source,
    }


def cost_result_data() -> dict[str, object]:
    return result_data() | {
        "gateway_calls": [
            gateway_call_data("provider_reported_charge", 0.1),
            gateway_call_data("provider_reported_charge", 0.2),
            gateway_call_data("estimated_list_price", 0.04),
            gateway_call_data("unpriced", None),
        ],
        "provider_reported_cost_usd": 0.1 + 0.2,
        "estimated_cost_usd": 0.04,
        "tool_estimated_cost_usd": 0.9,
    }


@pytest.mark.parametrize("provider_total", [0.3, 0.1 + 0.2])
def test_result_cost_totals_match_mixed_receipts_with_float_rounding(
    provider_total: float,
) -> None:
    result = ModelModelSwapValidationResult.model_validate(
        cost_result_data() | {"provider_reported_cost_usd": provider_total}
    )
    assert result.provider_reported_cost_usd == pytest.approx(0.3)
    assert result.estimated_cost_usd == 0.04
    assert result.gateway_calls[-1].cost_usd is None
    assert (
        ModelModelSwapValidationResult.model_validate_json(result.model_dump_json())
        == result
    )


@pytest.mark.parametrize(
    ("field", "total"),
    [
        ("provider_reported_cost_usd", 0.31),
        ("provider_reported_cost_usd", 0),
        ("estimated_cost_usd", 0.05),
        ("estimated_cost_usd", 0),
        ("estimated_cost_usd", 0.94),
    ],
)
def test_result_refuses_cost_total_mismatches(field: str, total: float) -> None:
    with pytest.raises(ValidationError, match=field):
        ModelModelSwapValidationResult.model_validate(
            cost_result_data() | {field: total}
        )


@pytest.mark.parametrize("field", ["provider_reported_cost_usd", "estimated_cost_usd"])
@pytest.mark.parametrize("calls", [[], [gateway_call_data("unpriced", None)]])
def test_result_refuses_nonzero_totals_without_priced_receipts(
    field: str, calls: list[dict[str, object]]
) -> None:
    with pytest.raises(ValidationError, match=field):
        ModelModelSwapValidationResult.model_validate(
            result_data() | {"gateway_calls": calls, field: 1e-20}
        )


def test_result_accepts_zero_cost_and_unpriced_receipts() -> None:
    result = ModelModelSwapValidationResult.model_validate(
        result_data()
        | {
            "gateway_calls": [
                gateway_call_data("provider_reported_charge", 0),
                gateway_call_data("estimated_list_price", 0),
                gateway_call_data("unpriced", None),
            ]
        }
    )
    assert result.provider_reported_cost_usd == result.estimated_cost_usd == 0


@pytest.mark.parametrize(
    ("source", "field"),
    [
        ("provider_reported_charge", "provider_reported_cost_usd"),
        ("estimated_list_price", "estimated_cost_usd"),
    ],
)
def test_result_refuses_overflowing_gateway_cost_totals(
    source: str, field: str
) -> None:
    with pytest.raises(ValidationError, match=field):
        ModelModelSwapValidationResult.model_validate(
            result_data()
            | {
                "gateway_calls": [gateway_call_data(source, 1e308)] * 2,
                field: 1e308,
            }
        )


def test_tool_cost_source_preserves_wire_value_as_schema_constant() -> None:
    default = ModelModelSwapValidationResult.model_validate(result_data())
    explicit = ModelModelSwapValidationResult.model_validate(
        result_data()
        | {
            "correlation_id": default.correlation_id,
            "tool_cost_measurement_source": "estimated_list_price",
        }
    )
    assert explicit == default
    assert json.loads(default.model_dump_json())["tool_cost_measurement_source"] == (
        "estimated_list_price"
    )
    source_schema = default.model_json_schema()["properties"][
        "tool_cost_measurement_source"
    ]
    assert source_schema["const"] == "estimated_list_price"
