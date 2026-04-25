# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Test ModelRemoteTaskState."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_agent_protocol import EnumAgentProtocol
from omnibase_core.enums.enum_agent_task_lifecycle_type import (
    EnumAgentTaskLifecycleType,
)
from omnibase_core.enums.enum_invocation_kind import EnumInvocationKind
from omnibase_core.models.delegation.model_remote_task_state import (
    ModelRemoteTaskState,
)


@pytest.mark.unit
def test_minimum_submitted_row() -> None:
    now = datetime.now(UTC)
    row = ModelRemoteTaskState(
        task_id=uuid.uuid4(),
        invocation_kind=EnumInvocationKind.AGENT,
        protocol=EnumAgentProtocol.A2A,
        target_ref="adk-type-debt-scout",
        remote_task_handle=None,
        correlation_id=uuid.uuid4(),
        status=EnumAgentTaskLifecycleType.SUBMITTED,
        last_remote_status=None,
        last_emitted_event_type=None,
        submitted_at=now,
        updated_at=now,
        completed_at=None,
        error=None,
    )

    assert row.status is EnumAgentTaskLifecycleType.SUBMITTED
    assert row.completed_at is None


@pytest.mark.unit
def test_completed_row_allows_completed_timestamp() -> None:
    now = datetime.now(UTC)
    row = ModelRemoteTaskState(
        task_id=uuid.uuid4(),
        invocation_kind=EnumInvocationKind.AGENT,
        protocol=EnumAgentProtocol.A2A,
        target_ref="adk-type-debt-scout",
        remote_task_handle="remote-123",
        correlation_id=uuid.uuid4(),
        status=EnumAgentTaskLifecycleType.COMPLETED,
        submitted_at=now,
        updated_at=now,
        completed_at=now,
    )

    assert row.remote_task_handle == "remote-123"


@pytest.mark.unit
def test_extra_fields_forbidden() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        ModelRemoteTaskState(
            task_id=uuid.uuid4(),
            invocation_kind=EnumInvocationKind.AGENT,
            protocol=EnumAgentProtocol.A2A,
            target_ref="adk-type-debt-scout",
            correlation_id=uuid.uuid4(),
            status=EnumAgentTaskLifecycleType.SUBMITTED,
            submitted_at=now,
            updated_at=now,
            unexpected=True,  # type: ignore[call-arg]
        )
