# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract tests for the concrete delegation terminal v2 wire models."""

from __future__ import annotations

from typing import Any, get_type_hints
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.delegation.wire import (
    EnumDelegationRoutingDisposition,
    EnumDelegationTerminalOutcome,
    EnumDelegationUnroutedReason,
    EnumQualityScoreComparison,
    ModelDelegationTerminalCompletedV2,
    ModelDelegationTerminalFailedRoutedV2,
    ModelDelegationTerminalFailedUnroutedV2,
    ModelQualityBarEvaluation,
)
from omnibase_core.models.delegation.wire.model_delegation_terminal_v2 import (
    _ModelDelegationTerminalCommonV2,
)


def _common_payload() -> dict[str, Any]:
    return {
        "correlation_id": str(uuid4()),
        "task_type": "code_review",
        "model_used": "qwen3-coder",
        "endpoint_url": "https://diagnostic.example/v1",
        "content": "review complete",
        "latency_ms": 42,
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30,
        "fallback_to_claude": False,
        "failure_reason": "",
        "tokens_to_compliance": 30,
        "compliance_attempts": 1,
        "escalation_count": 0,
        "escalation_history": [],
        "routing_tiers_hash": "sha256:routing",
        "escalation_config_hash": "sha256:escalation",
        "attempts_count": 1,
        "cumulative_attempt_cost": 0.01,
        "cumulative_input_tokens": 10,
        "cumulative_output_tokens": 20,
        "final_attempt_cost": 0.01,
        "context_pack_hash": "",
        "cost_tier_name": "local",
        "tenant_id": "tenant-a",
    }


def _quality_bar_evaluation() -> dict[str, Any]:
    return {
        "quality_score": 0.95,
        "required_quality_bar": 0.9,
        "score_vs_required_bar": EnumQualityScoreComparison.AT_OR_ABOVE_BAR.value,
    }


def _completed_payload() -> dict[str, Any]:
    return {
        **_common_payload(),
        "routing_disposition": EnumDelegationRoutingDisposition.ROUTED.value,
        "terminal_outcome": EnumDelegationTerminalOutcome.COMPLETED.value,
        "backend_ref": "local-coder",
        "pricing_manifest_version": 7,
        "quality_passed": True,
        "quality_bar_evaluation": _quality_bar_evaluation(),
        "failed_acceptance_criteria": (),
    }


def _routed_failure_payload() -> dict[str, Any]:
    return {
        **_common_payload(),
        "routing_disposition": EnumDelegationRoutingDisposition.ROUTED.value,
        "terminal_outcome": EnumDelegationTerminalOutcome.FAILED.value,
        "backend_ref": "local-coder",
        "pricing_manifest_version": 7,
        "quality_passed": False,
        "failed_acceptance_criteria": ("response_non_empty",),
        "terminal_failure_reason": "provider refused the request",
        "routed_failure_cause": {
            "kind": "provider",
            "cause": "provider_error",
            "quality_bar_evaluation": _quality_bar_evaluation(),
        },
    }


def _unrouted_payload() -> dict[str, Any]:
    return {
        **_common_payload(),
        "routing_disposition": EnumDelegationRoutingDisposition.UNROUTED.value,
        "terminal_outcome": EnumDelegationTerminalOutcome.FAILED.value,
        "unrouted_reason": EnumDelegationUnroutedReason.NO_ELIGIBLE_BACKEND.value,
        "terminal_failure_reason": "no backend matched the route",
    }


@pytest.mark.unit
def test_completed_terminal_round_trips() -> None:
    terminal = ModelDelegationTerminalCompletedV2.model_validate(_completed_payload())

    restored = ModelDelegationTerminalCompletedV2.model_validate_json(
        terminal.model_dump_json()
    )

    assert restored == terminal
    assert restored.routing_disposition is EnumDelegationRoutingDisposition.ROUTED
    assert restored.terminal_outcome is EnumDelegationTerminalOutcome.COMPLETED


@pytest.mark.unit
def test_every_concrete_field_is_required_without_defaults() -> None:
    for model in (
        ModelDelegationTerminalCompletedV2,
        ModelDelegationTerminalFailedRoutedV2,
        ModelDelegationTerminalFailedUnroutedV2,
    ):
        assert all(field.is_required() for field in model.model_fields.values())


@pytest.mark.unit
def test_shared_base_has_no_nullable_field() -> None:
    annotations = get_type_hints(_ModelDelegationTerminalCommonV2)

    assert annotations
    assert all("NoneType" not in str(annotation) for annotation in annotations.values())


@pytest.mark.unit
@pytest.mark.parametrize(
    "backend_ref",
    [
        "https://backend.example/v1",
        "//backend.example",
        "mailto:ops@example.com",
        " ",
        " local-coder ",
    ],
)
def test_backend_ref_rejects_url_or_uri_shape(backend_ref: str) -> None:
    payload = _completed_payload()
    payload["backend_ref"] = backend_ref

    with pytest.raises(ValidationError, match=r"not a URL or URI|nonblank"):
        ModelDelegationTerminalCompletedV2.model_validate(payload)


@pytest.mark.unit
def test_unrouted_terminal_rejects_routed_or_quality_fields() -> None:
    payload = _unrouted_payload()
    payload["backend_ref"] = "local-coder"
    payload["quality_passed"] = False

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ModelDelegationTerminalFailedUnroutedV2.model_validate(payload)


@pytest.mark.unit
def test_routed_failure_requires_exactly_one_closed_failure_cause() -> None:
    payload = _routed_failure_payload()
    del payload["routed_failure_cause"]

    with pytest.raises(ValidationError, match="routed_failure_cause"):
        ModelDelegationTerminalFailedRoutedV2.model_validate(payload)


@pytest.mark.unit
def test_provider_failure_requires_its_quality_bar_evaluation() -> None:
    payload = _routed_failure_payload()
    del payload["routed_failure_cause"]["quality_bar_evaluation"]

    with pytest.raises(ValidationError, match="quality_bar_evaluation"):
        ModelDelegationTerminalFailedRoutedV2.model_validate(payload)


@pytest.mark.unit
def test_provider_failure_carries_one_quality_bar_evaluation() -> None:
    terminal = ModelDelegationTerminalFailedRoutedV2.model_validate(
        _routed_failure_payload()
    )

    assert (
        terminal.routed_failure_cause.quality_bar_evaluation.required_quality_bar == 0.9
    )


@pytest.mark.unit
def test_quality_gate_rejection_cannot_claim_quality_passed() -> None:
    payload = _routed_failure_payload()
    payload["quality_passed"] = True
    payload["routed_failure_cause"] = {
        "kind": "quality_gate_rejection",
        "quality_bar_evaluation": _quality_bar_evaluation(),
    }

    with pytest.raises(ValidationError, match="quality_passed=false"):
        ModelDelegationTerminalFailedRoutedV2.model_validate(payload)


@pytest.mark.unit
def test_quality_gate_rejection_is_a_valid_routed_failure_cause() -> None:
    payload = _routed_failure_payload()
    payload["routed_failure_cause"] = {
        "kind": "quality_gate_rejection",
        "quality_bar_evaluation": _quality_bar_evaluation(),
    }

    terminal = ModelDelegationTerminalFailedRoutedV2.model_validate(payload)

    assert terminal.routed_failure_cause.kind == "quality_gate_rejection"


@pytest.mark.unit
def test_quality_bar_evaluation_rejects_contradictory_comparison() -> None:
    payload = _quality_bar_evaluation()
    payload["score_vs_required_bar"] = EnumQualityScoreComparison.BELOW_BAR.value

    with pytest.raises(ValidationError, match="must match quality_score"):
        ModelQualityBarEvaluation.model_validate(payload)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("payload_mutation", "match"),
    [
        (
            lambda payload: payload.update(
                quality_bar_evaluation={
                    "quality_score": 0.89,
                    "required_quality_bar": 0.9,
                    "score_vs_required_bar": "below_bar",
                }
            ),
            "cannot be below required_quality_bar",
        ),
        (
            lambda payload: payload.update(
                failed_acceptance_criteria=("response_non_empty",)
            ),
            "cannot carry failed_acceptance_criteria",
        ),
    ],
)
def test_completed_quality_invariants_are_preserved(
    payload_mutation: Any, match: str
) -> None:
    payload = _completed_payload()
    payload_mutation(payload)

    with pytest.raises(ValidationError, match=match):
        ModelDelegationTerminalCompletedV2.model_validate(payload)


@pytest.mark.unit
def test_quality_failure_above_bar_requires_failed_criteria() -> None:
    payload = _routed_failure_payload()
    payload["failed_acceptance_criteria"] = ()
    payload["routed_failure_cause"] = {
        "kind": "quality_gate_rejection",
        "quality_bar_evaluation": _quality_bar_evaluation(),
    }

    with pytest.raises(ValidationError, match="must carry failed_acceptance_criteria"):
        ModelDelegationTerminalFailedRoutedV2.model_validate(payload)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("payload_mutation", "match"),
    [
        (lambda payload: payload.update(total_tokens=31), "total_tokens must equal"),
        (
            lambda payload: payload.update(failed_acceptance_criteria=(" ",)),
            "must not be blank",
        ),
    ],
)
def test_v1_invariants_are_preserved(payload_mutation: Any, match: str) -> None:
    payload = _routed_failure_payload()
    payload_mutation(payload)

    with pytest.raises(ValidationError, match=match):
        ModelDelegationTerminalFailedRoutedV2.model_validate(payload)
