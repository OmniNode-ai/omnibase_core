# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelRuntimeAlivenessProbeCommand and ModelRuntimeAlivenessProbeReceipt."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.models.runtime.model_runtime_aliveness_probe import (
    ModelRuntimeAlivenessProbeCommand,
)
from omnibase_core.models.runtime.model_runtime_aliveness_probe_receipt import (
    ModelRuntimeAlivenessProbeReceipt,
)


def _command_kwargs() -> dict[str, object]:
    return {
        "correlation_id": "prb-2026-04-26-001",
        "target_command_topic": "onex.cmd.omnimarket.build-loop-orchestrator-start.v1",
        "target_handler_id": "node_build_loop_orchestrator.handlers.handler_build_loop_orchestrator",
        "expected_terminal_topic": "onex.evt.omnimarket.build-loop-orchestrator-completed.v1",
        "projection_key_template": "public.build_loop_runs:run_id={correlation_id}",
        "timeout_seconds": 30,
    }


def test_probe_command_required_fields() -> None:
    cmd = ModelRuntimeAlivenessProbeCommand(**_command_kwargs())  # type: ignore[arg-type]
    assert cmd.failure_states == ()
    assert cmd.timeout_seconds == 30


def test_probe_command_rejects_unknown_failure_state() -> None:
    kwargs = _command_kwargs()
    kwargs["failure_states"] = ("not_a_real_state",)
    with pytest.raises(ValidationError):
        ModelRuntimeAlivenessProbeCommand(**kwargs)  # type: ignore[arg-type]


def test_timeout_default_is_30s_and_configurable_via_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RUNTIME_ALIVENESS_TIMEOUT_SECONDS", raising=False)
    base = _command_kwargs()
    base.pop("timeout_seconds")
    cmd_default = ModelRuntimeAlivenessProbeCommand.from_env(**base)  # type: ignore[arg-type]
    assert cmd_default.timeout_seconds == 30

    monkeypatch.setenv("RUNTIME_ALIVENESS_TIMEOUT_SECONDS", "60")
    cmd_override = ModelRuntimeAlivenessProbeCommand.from_env(**base)  # type: ignore[arg-type]
    assert cmd_override.timeout_seconds == 60


def test_timeout_env_invalid_value_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RUNTIME_ALIVENESS_TIMEOUT_SECONDS", "not-an-int")
    base = _command_kwargs()
    base.pop("timeout_seconds")
    cmd = ModelRuntimeAlivenessProbeCommand.from_env(**base)  # type: ignore[arg-type]
    assert cmd.timeout_seconds == 30


def _receipt_kwargs() -> dict[str, object]:
    now = datetime.now(UTC)
    return {
        "correlation_id": "prb-2026-04-26-001",
        "status": "PASS",
        "failure_states": (),
        "terminal_event_observed": True,
        "projection_row_observed": True,
        "lag_at_sample": 0,
        "timeout_seconds": 30,
        "started_at": now,
        "completed_at": now,
    }


def test_receipt_pass_requires_empty_failure_states() -> None:
    kwargs = _receipt_kwargs()
    kwargs["failure_states"] = ("timeout",)
    with pytest.raises(ValidationError):
        ModelRuntimeAlivenessProbeReceipt(**kwargs)  # type: ignore[arg-type]


def test_receipt_fail_requires_at_least_one_failure_state() -> None:
    kwargs = _receipt_kwargs()
    kwargs["status"] = "FAIL"
    kwargs["failure_states"] = ()
    with pytest.raises(ValidationError):
        ModelRuntimeAlivenessProbeReceipt(**kwargs)  # type: ignore[arg-type]


def test_receipt_pass_round_trip_serializes() -> None:
    receipt = ModelRuntimeAlivenessProbeReceipt(**_receipt_kwargs())  # type: ignore[arg-type]
    payload = receipt.model_dump(mode="json")
    assert payload["status"] == "PASS"
    assert payload["failure_states"] == []
    assert payload["lag_at_sample"] == 0
