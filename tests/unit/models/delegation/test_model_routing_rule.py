# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Test ModelRoutingRule."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_agent_capability import EnumAgentCapability
from omnibase_core.enums.enum_agent_protocol import EnumAgentProtocol
from omnibase_core.enums.enum_invocation_kind import EnumInvocationKind
from omnibase_core.enums.enum_model_routing_backend import EnumModelRoutingBackend
from omnibase_core.models.delegation.model_routing_rule import ModelRoutingRule


@pytest.mark.unit
def test_agent_rule_requires_protocol_not_backend() -> None:
    rule = ModelRoutingRule(
        capability=EnumAgentCapability.TECH_DEBT_TRIAGE,
        invocation_kind=EnumInvocationKind.AGENT,
        agent_protocol=EnumAgentProtocol.A2A,
        model_backend=None,
        target_ref="adk-type-debt-scout",
        fallbacks=(),
    )

    assert rule.invocation_kind is EnumInvocationKind.AGENT
    assert rule.agent_protocol is EnumAgentProtocol.A2A
    assert rule.model_backend is None


@pytest.mark.unit
def test_model_rule_requires_backend_not_protocol() -> None:
    rule = ModelRoutingRule(
        capability=EnumAgentCapability.TECH_DEBT_TRIAGE,
        invocation_kind=EnumInvocationKind.MODEL,
        agent_protocol=None,
        model_backend=EnumModelRoutingBackend.BIFROST,
        target_ref="bifrost://pool-a",
        fallbacks=(),
    )

    assert rule.model_backend is EnumModelRoutingBackend.BIFROST


@pytest.mark.unit
def test_cross_axis_combo_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelRoutingRule(
            capability=EnumAgentCapability.TECH_DEBT_TRIAGE,
            invocation_kind=EnumInvocationKind.AGENT,
            agent_protocol=EnumAgentProtocol.A2A,
            model_backend=EnumModelRoutingBackend.BIFROST,
            target_ref="x",
            fallbacks=(),
        )


@pytest.mark.unit
def test_agent_without_protocol_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelRoutingRule(
            capability=EnumAgentCapability.TECH_DEBT_TRIAGE,
            invocation_kind=EnumInvocationKind.AGENT,
            agent_protocol=None,
            model_backend=None,
            target_ref="x",
            fallbacks=(),
        )


@pytest.mark.unit
def test_model_with_protocol_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelRoutingRule(
            capability=EnumAgentCapability.TECH_DEBT_TRIAGE,
            invocation_kind=EnumInvocationKind.MODEL,
            agent_protocol=EnumAgentProtocol.A2A,
            model_backend=EnumModelRoutingBackend.BIFROST,
            target_ref="x",
            fallbacks=(),
        )
