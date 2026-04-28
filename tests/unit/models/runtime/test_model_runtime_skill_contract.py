# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.dispatch.model_dispatch_bus_terminal_result import (
    ModelDispatchBusTerminalResult,
)
from omnibase_core.models.runtime import (
    ModelRuntimeSkillError,
    ModelRuntimeSkillRequest,
    ModelRuntimeSkillResponse,
)


def test_runtime_skill_request_requires_non_blank_command_name() -> None:
    with pytest.raises(
        ValidationError, match="command_name must be a non-empty string"
    ):
        ModelRuntimeSkillRequest(command_name="   ")


def test_runtime_skill_response_requires_dispatch_result_when_ok() -> None:
    with pytest.raises(
        ValidationError, match="ok responses must include dispatch_result"
    ):
        ModelRuntimeSkillResponse(ok=True, command_name="session_orchestrator")


def test_runtime_skill_response_accepts_failed_shape() -> None:
    response = ModelRuntimeSkillResponse(
        ok=False,
        command_name="session_orchestrator",
        error=ModelRuntimeSkillError(
            code="dispatch_timeout",
            message="timed out",
            retryable=True,
        ),
    )

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == "dispatch_timeout"


def test_runtime_skill_response_round_trip_success() -> None:
    correlation_id = uuid4()
    response = ModelRuntimeSkillResponse(
        ok=True,
        command_name="session_orchestrator",
        contract_name="session_orchestrator",
        command_topic="onex.cmd.omnimarket.session-orchestrator-start.v1",
        terminal_event="onex.evt.omnimarket.session-orchestrator-completed.v1",
        correlation_id=correlation_id,
        dispatch_result=ModelDispatchBusTerminalResult(
            correlation_id=correlation_id,
            status="completed",
            payload={"status": "complete"},
            completed_at=datetime.now(UTC),
        ),
        output_payloads=[{"status": "complete"}],
    )

    restored = ModelRuntimeSkillResponse.model_validate_json(
        response.model_dump_json(exclude_none=True)
    )

    assert restored == response
