# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Test ModelInvocationCommand."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_agent_protocol import EnumAgentProtocol
from omnibase_core.enums.enum_invocation_kind import EnumInvocationKind
from omnibase_core.enums.enum_model_routing_backend import EnumModelRoutingBackend
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.delegation.model_invocation_command import (
    ModelInvocationCommand,
)


@pytest.mark.unit
def test_agent_command_shape() -> None:
    command = ModelInvocationCommand(
        task_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        invocation_kind=EnumInvocationKind.AGENT,
        agent_protocol=EnumAgentProtocol.A2A,
        model_backend=None,
        target_ref="adk-type-debt-scout",
        payload={"findings": ModelSchemaValue.from_value([])},
    )

    assert command.invocation_kind is EnumInvocationKind.AGENT
    assert command.payload["findings"].value_type == "array"


@pytest.mark.unit
def test_model_command_shape() -> None:
    command = ModelInvocationCommand(
        task_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        invocation_kind=EnumInvocationKind.MODEL,
        agent_protocol=None,
        model_backend=EnumModelRoutingBackend.BIFROST,
        target_ref="bifrost://pool-a",
        payload={"prompt": ModelSchemaValue.from_value("hi")},
    )

    assert command.model_backend is EnumModelRoutingBackend.BIFROST


@pytest.mark.unit
def test_mixed_axes_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelInvocationCommand(
            task_id=uuid.uuid4(),
            correlation_id=uuid.uuid4(),
            invocation_kind=EnumInvocationKind.AGENT,
            agent_protocol=EnumAgentProtocol.A2A,
            model_backend=EnumModelRoutingBackend.BIFROST,
            target_ref="x",
            payload={},
        )


@pytest.mark.unit
def test_agent_without_protocol_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelInvocationCommand(
            task_id=uuid.uuid4(),
            correlation_id=uuid.uuid4(),
            invocation_kind=EnumInvocationKind.AGENT,
            agent_protocol=None,
            model_backend=None,
            target_ref="x",
            payload={},
        )


@pytest.mark.unit
def test_model_with_protocol_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelInvocationCommand(
            task_id=uuid.uuid4(),
            correlation_id=uuid.uuid4(),
            invocation_kind=EnumInvocationKind.MODEL,
            agent_protocol=EnumAgentProtocol.A2A,
            model_backend=EnumModelRoutingBackend.BIFROST,
            target_ref="x",
            payload={},
        )
