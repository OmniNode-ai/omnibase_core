# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for omnibase_core.models.delegation (OMN-9637)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_agent_capability import EnumAgentCapability
from omnibase_core.enums.enum_agent_protocol import EnumAgentProtocol
from omnibase_core.enums.enum_agent_task_lifecycle_type import (
    EnumAgentTaskLifecycleType,
)
from omnibase_core.enums.enum_invocation_kind import EnumInvocationKind
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.delegation.model_a2a_task_request import ModelA2ATaskRequest
from omnibase_core.models.delegation.model_a2a_task_response import ModelA2ATaskResponse
from omnibase_core.models.delegation.model_agent_task_lifecycle_event import (
    ModelAgentTaskLifecycleEvent,
)
from omnibase_core.models.delegation.model_invocation_command import (
    ModelInvocationCommand,
)
from omnibase_core.models.delegation.model_remote_task_state import ModelRemoteTaskState
from omnibase_core.models.delegation.model_routing_rule import ModelRoutingRule
from omnibase_core.models.delegation.model_target_agent import ModelTargetAgent

_NOW = datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC)
_TASK_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
_CORR_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")


@pytest.mark.unit
class TestModelInvocationCommand:
    def test_minimal_valid(self) -> None:
        cmd = ModelInvocationCommand(
            task_id=_TASK_ID,
            correlation_id=_CORR_ID,
            invocation_kind=EnumInvocationKind.AGENT,
            agent_protocol=EnumAgentProtocol.A2A,
            target_ref="adk-scout",
        )
        assert cmd.task_id == _TASK_ID
        assert cmd.invocation_kind is EnumInvocationKind.AGENT
        assert cmd.agent_protocol is EnumAgentProtocol.A2A
        assert cmd.payload == {}

    def test_with_protocol_and_payload(self) -> None:
        cmd = ModelInvocationCommand(
            task_id=_TASK_ID,
            correlation_id=_CORR_ID,
            invocation_kind=EnumInvocationKind.AGENT,
            agent_protocol=EnumAgentProtocol.A2A,
            target_ref="adk-scout",
            payload={"x": ModelSchemaValue.from_value("hello")},
        )
        assert cmd.agent_protocol is EnumAgentProtocol.A2A
        assert "x" in cmd.payload

    def test_frozen(self) -> None:
        cmd = ModelInvocationCommand(
            task_id=_TASK_ID,
            correlation_id=_CORR_ID,
            invocation_kind=EnumInvocationKind.MODEL,
            model_backend="qwen3",
            target_ref="qwen3",
        )
        with pytest.raises(Exception):
            cmd.target_ref = "changed"  # type: ignore[misc]

    def test_agent_without_protocol_raises(self) -> None:
        with pytest.raises(ValidationError, match="agent_protocol is required"):
            ModelInvocationCommand(
                task_id=_TASK_ID,
                correlation_id=_CORR_ID,
                invocation_kind=EnumInvocationKind.AGENT,
                target_ref="adk-scout",
            )

    def test_model_without_backend_raises(self) -> None:
        with pytest.raises(ValidationError, match="model_backend is required"):
            ModelInvocationCommand(
                task_id=_TASK_ID,
                correlation_id=_CORR_ID,
                invocation_kind=EnumInvocationKind.MODEL,
                target_ref="qwen3",
            )

    def test_agent_with_model_backend_raises(self) -> None:
        with pytest.raises(
            ValidationError,
            match="model_backend must be None when invocation_kind is AGENT",
        ):
            ModelInvocationCommand(
                task_id=_TASK_ID,
                correlation_id=_CORR_ID,
                invocation_kind=EnumInvocationKind.AGENT,
                agent_protocol=EnumAgentProtocol.A2A,
                model_backend="qwen3",
                target_ref="adk-scout",
            )

    def test_model_with_agent_protocol_raises(self) -> None:
        with pytest.raises(
            ValidationError,
            match="agent_protocol must be None when invocation_kind is MODEL",
        ):
            ModelInvocationCommand(
                task_id=_TASK_ID,
                correlation_id=_CORR_ID,
                invocation_kind=EnumInvocationKind.MODEL,
                model_backend="qwen3",
                agent_protocol=EnumAgentProtocol.A2A,
                target_ref="qwen3",
            )


@pytest.mark.unit
class TestModelAgentTaskLifecycleEvent:
    def test_minimal_valid(self) -> None:
        evt = ModelAgentTaskLifecycleEvent(
            task_id=_TASK_ID,
            correlation_id=_CORR_ID,
            lifecycle_type=EnumAgentTaskLifecycleType.SUBMITTED,
            occurred_at=_NOW,
        )
        assert evt.lifecycle_type is EnumAgentTaskLifecycleType.SUBMITTED
        assert evt.artifact is None
        assert evt.error is None

    def test_with_artifact_and_error(self) -> None:
        evt = ModelAgentTaskLifecycleEvent(
            task_id=_TASK_ID,
            correlation_id=_CORR_ID,
            lifecycle_type=EnumAgentTaskLifecycleType.FAILED,
            occurred_at=_NOW,
            artifact={"k": ModelSchemaValue.from_value("v")},
            error="timeout",
        )
        assert evt.error == "timeout"
        assert evt.artifact is not None and "k" in evt.artifact


@pytest.mark.unit
class TestModelRoutingRule:
    def test_valid_agent_rule(self) -> None:
        rule = ModelRoutingRule(
            capability=EnumAgentCapability.TECH_DEBT_TRIAGE,
            invocation_kind=EnumInvocationKind.AGENT,
            agent_protocol=EnumAgentProtocol.A2A,
            target_ref="adk-scout",
        )
        assert rule.capability is EnumAgentCapability.TECH_DEBT_TRIAGE
        assert rule.fallbacks == ()

    def test_missing_required_fields_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelRoutingRule.model_validate({"invocation_kind": "agent"})

    def test_agent_rule_without_protocol_raises(self) -> None:
        with pytest.raises(ValidationError, match="agent_protocol is required"):
            ModelRoutingRule(
                capability=EnumAgentCapability.TECH_DEBT_TRIAGE,
                invocation_kind=EnumInvocationKind.AGENT,
                target_ref="adk-scout",
            )


@pytest.mark.unit
class TestModelTargetAgent:
    def test_valid(self) -> None:
        agent = ModelTargetAgent(
            target_ref="adk-scout",
            base_url="http://localhost:9080",
            protocol=EnumAgentProtocol.A2A,
        )
        assert agent.protocol is EnumAgentProtocol.A2A


@pytest.mark.unit
class TestModelA2ATaskRequest:
    def test_valid(self) -> None:
        req = ModelA2ATaskRequest(
            skill_ref="scout",
            input={"prompt": ModelSchemaValue.from_value("triage these")},
            correlation_id=_CORR_ID,
        )
        assert req.skill_ref == "scout"
        assert "prompt" in req.input


@pytest.mark.unit
class TestModelA2ATaskResponse:
    def test_minimal(self) -> None:
        resp = ModelA2ATaskResponse(
            remote_task_handle="t-123",
            status=EnumAgentTaskLifecycleType.PROGRESS,
        )
        assert resp.artifacts == []
        assert resp.error is None

    def test_with_artifacts(self) -> None:
        resp = ModelA2ATaskResponse(
            remote_task_handle="t-123",
            status=EnumAgentTaskLifecycleType.COMPLETED,
            artifacts=[{"result": ModelSchemaValue.from_value("done")}],
        )
        assert len(resp.artifacts) == 1

    def test_invalid_status_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelA2ATaskResponse(
                remote_task_handle="t-123", status="not_a_valid_status"
            )


@pytest.mark.unit
class TestModelRemoteTaskState:
    def test_valid(self) -> None:
        state = ModelRemoteTaskState(
            task_id=_TASK_ID,
            invocation_kind=EnumInvocationKind.AGENT,
            protocol=EnumAgentProtocol.A2A,
            target_ref="adk-scout",
            correlation_id=_CORR_ID,
            status=EnumAgentTaskLifecycleType.SUBMITTED,
            submitted_at=_NOW,
            updated_at=_NOW,
        )
        assert state.status is EnumAgentTaskLifecycleType.SUBMITTED
        assert state.completed_at is None

    def test_agent_without_protocol_raises(self) -> None:
        with pytest.raises(ValidationError, match="protocol is required"):
            ModelRemoteTaskState(
                task_id=_TASK_ID,
                invocation_kind=EnumInvocationKind.AGENT,
                protocol=None,
                target_ref="adk-scout",
                correlation_id=_CORR_ID,
                status=EnumAgentTaskLifecycleType.SUBMITTED,
                submitted_at=_NOW,
                updated_at=_NOW,
            )

    def test_model_validate_from_dict(self) -> None:
        data = {
            "task_id": str(_TASK_ID),
            "invocation_kind": "agent",
            "protocol": "A2A",
            "target_ref": "adk-scout",
            "correlation_id": str(_CORR_ID),
            "status": "SUBMITTED",
            "submitted_at": _NOW,
            "updated_at": _NOW,
        }
        state = ModelRemoteTaskState.model_validate(data)
        assert state.invocation_kind is EnumInvocationKind.AGENT
        assert state.protocol is EnumAgentProtocol.A2A
