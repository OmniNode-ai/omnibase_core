# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Test ModelTargetAgent."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_agent_protocol import EnumAgentProtocol
from omnibase_core.models.delegation.model_target_agent import ModelTargetAgent


@pytest.mark.unit
def test_construct_valid_target() -> None:
    target = ModelTargetAgent(
        agent_ref="adk-type-debt-scout",
        protocol=EnumAgentProtocol.A2A,
        base_url="http://127.0.0.1:8050",
        protocol_version="0.3",
    )

    assert target.agent_ref == "adk-type-debt-scout"
    assert target.protocol is EnumAgentProtocol.A2A


@pytest.mark.unit
def test_frozen_rejects_mutation() -> None:
    target = ModelTargetAgent(
        agent_ref="x",
        protocol=EnumAgentProtocol.A2A,
        base_url="http://127.0.0.1:8050",
        protocol_version="0.3",
    )

    with pytest.raises(ValidationError):
        target.agent_ref = "y"  # type: ignore[misc]


@pytest.mark.unit
def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        ModelTargetAgent(
            agent_ref="x",
            protocol=EnumAgentProtocol.A2A,
            base_url="http://127.0.0.1:8050",
            protocol_version="0.3",
            unknown_field="boom",  # type: ignore[call-arg]
        )
