# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RED-first tests for ``ModelDelegationDispatchResult`` (OMN-19838, Task A).

The result replaces the untyped ``dict[str, object]`` a dispatch returns. Its
field set is the union of the keys the consumer handler reads today, with one
canonical field for each pair of names a provider has used for the same fact.
A provider payload that still uses the older name of a pair validates into the
canonical field, and the older name is never emitted.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.delegation.wire import (
    EnumDelegationOutputRefusalReason,
    EnumDelegationOutputShape,
    EnumDelegationTerminalFailureCause,
    EnumQualityScoreComparison,
    ModelDelegationDispatchResult,
)

pytestmark = pytest.mark.unit

# A representative payload in the shape the in-process local dispatch port
# builds today: the older name of every aliased pair, plus the keys the
# handler reads under a single name.
_LOCAL_PORT_PAYLOAD: dict[str, object] = {
    "status": "failed",
    "content": "partial answer",
    "failure_reason": "quality gate refused the answer",
    "model_used": "qwen3-coder-30b",
    "delegated_to": "lab-vllm",
    "baseline_model": "claude-sonnet",
    "quality_passed": False,
    "prompt_tokens": 1200,
    "completion_tokens": 300,
    "latency_ms": 4200,
    "total_tokens": 1500,
    "quality_score": 0.4,
    "required_quality_bar": 0.7,
    "score_vs_required_bar": "below_bar",
    "failed_acceptance_criteria": ["names the changed files"],
    "terminal_failure_cause": "quality_gate_refused",
    "cost_usd": 0.0012,
    "cumulative_attempt_cost": 0.0015,
    "final_attempt_cost": 0.0012,
    "cumulative_input_tokens": 2400,
    "cumulative_output_tokens": 600,
    "escalation_count": 1,
    "attempts_count": 2,
    "compliance_attempts": 2,
    "tokens_to_compliance": 0,
    "pricing_manifest_version": 7,
    "secret_source": "store",  # pragma: allowlist secret
    "secret_ref": "lab/vllm/api-key",  # pragma: allowlist secret
    "preamble_chars": 12,
    "output_refusal": {
        "reason": "no_schema_conforming_json",
        "output_shape": "json",
        "contract_failure_reasons": ["missing key: files"],
    },
    "credential_refusal": None,
    "credential_withheld": None,
    "attempts": [
        {"tier": "local", "backend_id": "lab-vllm", "quality_gate_passed": False},
        {"tier": "local", "backend_id": "lab-vllm-2", "quality_gate_passed": False},
    ],
}


def test_a_local_port_payload_validates_into_the_canonical_fields() -> None:
    result = ModelDelegationDispatchResult.model_validate(_LOCAL_PORT_PAYLOAD)

    assert result.status == "failed"
    assert result.content == "partial answer"
    assert result.error_message == "quality gate refused the answer"
    assert result.model_name == "qwen3-coder-30b"
    assert result.provider == "lab-vllm"
    assert result.model_cloud_baseline == "claude-sonnet"
    assert result.quality_gate_passed is False
    assert result.input_tokens == 1200
    assert result.output_tokens == 300
    assert result.delegation_latency_ms == 4200
    assert result.total_tokens == 1500
    assert result.quality_score == 0.4
    assert result.required_quality_bar == 0.7
    assert result.score_vs_required_bar is EnumQualityScoreComparison.BELOW_BAR
    assert result.failed_acceptance_criteria == ("names the changed files",)
    assert (
        result.terminal_failure_cause
        is EnumDelegationTerminalFailureCause.QUALITY_GATE_REFUSED
    )
    assert result.cumulative_attempt_cost == 0.0015
    assert result.final_attempt_cost == 0.0012
    assert result.cumulative_input_tokens == 2400
    assert result.cumulative_output_tokens == 600
    assert result.attempts_count == 2
    assert result.pricing_manifest_version == 7
    assert result.secret_source == "store"  # pragma: allowlist secret
    assert result.output_refusal is not None
    assert (
        result.output_refusal.reason
        is EnumDelegationOutputRefusalReason.NO_SCHEMA_CONFORMING_JSON
    )
    assert result.output_refusal.output_shape is EnumDelegationOutputShape.JSON
    assert result.attempts is not None
    assert [attempt["backend_id"] for attempt in result.attempts] == [
        "lab-vllm",
        "lab-vllm-2",
    ]


def test_a_failure_reason_with_no_gate_list_becomes_the_one_failed_gate() -> None:
    result = ModelDelegationDispatchResult.model_validate(_LOCAL_PORT_PAYLOAD)

    assert result.quality_gates_failed == ("quality gate refused the answer",)


def test_the_older_names_are_never_emitted() -> None:
    dumped = ModelDelegationDispatchResult.model_validate(
        _LOCAL_PORT_PAYLOAD
    ).model_dump(mode="json")

    for older in (
        "failure_reason",
        "model_used",
        "delegated_to",
        "baseline_model",
        "quality_passed",
        "prompt_tokens",
        "completion_tokens",
        "latency_ms",
    ):
        assert older not in dumped


def test_a_canonical_payload_round_trips() -> None:
    canonical = ModelDelegationDispatchResult.model_validate(_LOCAL_PORT_PAYLOAD)
    again = ModelDelegationDispatchResult.model_validate(
        canonical.model_dump(mode="json")
    )

    assert again == canonical


@pytest.mark.parametrize(
    ("canonical", "older", "canonical_value", "older_value", "expected"),
    [
        # A non-empty canonical value wins over the older name.
        ("error_message", "failure_reason", "canonical", "older", "canonical"),
        ("model_name", "model_used", "m-canonical", "m-older", "m-canonical"),
        ("provider", "delegated_to", "p-canonical", "p-older", "p-canonical"),
        (
            "model_cloud_baseline",
            "baseline_model",
            "b-canonical",
            "b-older",
            "b-canonical",
        ),
        # An empty canonical string falls through to the older name, which is
        # how the handler reads these pairs today (``a or b``).
        ("error_message", "failure_reason", "", "older", "older"),
        ("model_name", "model_used", "", "m-older", "m-older"),
        ("provider", "delegated_to", "", "p-older", "p-older"),
        ("model_cloud_baseline", "baseline_model", "", "b-older", "b-older"),
    ],
)
def test_text_pairs_prefer_a_non_empty_canonical_value(
    canonical: str,
    older: str,
    canonical_value: str,
    older_value: str,
    expected: str,
) -> None:
    result = ModelDelegationDispatchResult.model_validate(
        {canonical: canonical_value, older: older_value}
    )

    assert getattr(result, canonical) == expected


@pytest.mark.parametrize(
    ("canonical", "older", "canonical_value", "older_value"),
    [
        ("quality_gate_passed", "quality_passed", False, True),
        ("input_tokens", "prompt_tokens", 0, 99),
        ("output_tokens", "completion_tokens", 0, 99),
        ("delegation_latency_ms", "latency_ms", 0, 99),
    ],
)
def test_value_pairs_prefer_a_present_canonical_value(
    canonical: str,
    older: str,
    canonical_value: object,
    older_value: object,
) -> None:
    """These pairs are read by presence (``get(a, get(b))``), so a present
    canonical value wins even when it is falsy."""
    result = ModelDelegationDispatchResult.model_validate(
        {canonical: canonical_value, older: older_value}
    )

    assert getattr(result, canonical) == canonical_value


def test_an_empty_payload_carries_the_handler_defaults() -> None:
    result = ModelDelegationDispatchResult.model_validate({})

    assert result.status == "completed"
    assert result.content == ""
    assert result.error_message == ""
    assert result.quality_gate_passed is False
    assert result.quality_gates_failed == ()
    assert result.failed_acceptance_criteria == ()
    assert result.provider == ""
    assert result.model_name == ""
    assert result.model_cloud_baseline is None
    assert result.pricing_manifest_version is None
    assert result.quality_score is None
    assert result.input_tokens == 0
    assert result.output_tokens == 0
    assert result.cumulative_input_tokens is None
    assert result.cumulative_output_tokens is None
    assert result.cumulative_attempt_cost is None
    assert result.final_attempt_cost is None
    assert result.cost_savings_usd is None
    assert result.compliance_attempts is None
    assert result.attempts_count is None
    assert result.attempts is None
    assert result.escalation_history == ()
    assert result.terminal_failure_cause is None


def test_a_single_gate_name_string_becomes_a_one_item_tuple() -> None:
    result = ModelDelegationDispatchResult.model_validate(
        {"quality_gates_failed": "no_refusal"}
    )

    assert result.quality_gates_failed == ("no_refusal",)


def test_an_unknown_key_is_rejected() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ModelDelegationDispatchResult.model_validate({"endpoint_url": "http://x"})


def test_an_unknown_score_comparison_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelDelegationDispatchResult.model_validate(
            {"score_vs_required_bar": "sideways"}
        )
