# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-19448: pre-dispatch refusals retain their cause across wire models."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.delegation.wire import (
    ModelDelegationDispatchResult,
    ModelDelegationFailed,
)
from omnibase_core.models.delegation.wire.model_delegation_terminal_v2 import (
    ModelDelegationProviderFailureCause,
)

pytestmark = pytest.mark.unit


def test_dispatch_result_preserves_pre_dispatch_refusal() -> None:
    result = ModelDelegationDispatchResult.model_validate(
        {
            "status": "failed",
            "terminal_failure_cause": "pre_dispatch_refused",
            "attempts_count": 0,
        }
    )

    assert result.terminal_failure_cause is not None
    assert result.terminal_failure_cause.name == "PRE_DISPATCH_REFUSED"
    assert result.attempts_count == 0
    assert (
        ModelDelegationDispatchResult.model_validate_json(result.model_dump_json())
        == result
    )


@pytest.fixture
def boundary_failure_payload() -> dict[str, object]:
    return {
        "correlation_id": str(uuid4()),
        "task_type": "reasoning",
        "model_used": "unrouted",
        "endpoint_url": "unrouted",
        "content": "",
        "quality_passed": False,
        "quality_score": None,
        "latency_ms": 0,
        "fallback_to_claude": False,
        "failure_reason": "task-class timeout ceiling exceeded",
        "terminal_failure_reason": "task-class timeout ceiling exceeded",
        "terminal_failure_cause": "pre_dispatch_refused",
        "operational_outcome": "boundary_failure",
        "content_verdict": "not_applicable",
        "attempts_count": 0,
        "budget_refusal": {
            "reason": "timeout_exceeds_task_class_ceiling",
            "task_type": "reasoning",
            "requested_timeout_seconds": 301,
            "task_class_timeout_ceiling_seconds": 300,
        },
    }


def test_zero_attempt_boundary_failure_preserves_pre_dispatch_refusal(
    boundary_failure_payload: dict[str, object],
) -> None:
    terminal = ModelDelegationFailed.model_validate(boundary_failure_payload)

    dumped = terminal.model_dump(mode="json")
    assert dumped["terminal_failure_cause"] == "pre_dispatch_refused"
    assert dumped["attempts_count"] == 0
    assert ModelDelegationFailed.model_validate(dumped) == terminal


@pytest.mark.parametrize(
    "cause",
    [
        "provider_quota_exhausted",
        "auth_failed",
        "provider_error",
        "quality_gate_refused",
        "timeout",
        "no_terminal",
        "runtime_shutdown",
    ],
)
def test_zero_attempt_failure_still_rejects_other_causes(
    boundary_failure_payload: dict[str, object], cause: str
) -> None:
    boundary_failure_payload["terminal_failure_cause"] = cause

    with pytest.raises(ValidationError, match="zero attempts"):
        ModelDelegationFailed.model_validate(boundary_failure_payload)


def test_pre_dispatch_refusal_cannot_be_a_routed_provider_failure() -> None:
    with pytest.raises(ValidationError, match="pre_dispatch_refused"):
        ModelDelegationProviderFailureCause.model_validate(
            {"kind": "provider", "cause": "pre_dispatch_refused"}
        )


@pytest.mark.parametrize(
    "cause", ["provider_quota_exhausted", "auth_failed", "provider_error"]
)
def test_routed_provider_failure_still_accepts_provider_causes(cause: str) -> None:
    failure = ModelDelegationProviderFailureCause.model_validate(
        {"kind": "provider", "cause": cause}
    )

    assert failure.cause.value == cause
