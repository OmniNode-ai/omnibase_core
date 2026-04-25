# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Test ModelAgentTaskLifecycleEvent."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_agent_task_lifecycle_type import (
    EnumAgentTaskLifecycleType,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.delegation.model_agent_task_lifecycle_event import (
    ModelAgentTaskLifecycleEvent,
)


@pytest.mark.unit
def test_submitted_event_minimum_fields() -> None:
    event = ModelAgentTaskLifecycleEvent(
        task_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        lifecycle_type=EnumAgentTaskLifecycleType.SUBMITTED,
        remote_task_handle=None,
        artifact=None,
        error=None,
        occurred_at=datetime.now(UTC),
    )

    assert event.lifecycle_type is EnumAgentTaskLifecycleType.SUBMITTED


@pytest.mark.unit
def test_artifact_event_preserves_typed_artifact() -> None:
    event = ModelAgentTaskLifecycleEvent(
        task_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        lifecycle_type=EnumAgentTaskLifecycleType.ARTIFACT,
        remote_task_handle="remote-123",
        artifact={"report": ModelSchemaValue.from_value("ok")},
        error=None,
        occurred_at=datetime.now(UTC),
    )

    assert event.artifact is not None
    assert event.artifact["report"].string_value == "ok"


@pytest.mark.unit
def test_failed_event_preserves_error_field() -> None:
    event = ModelAgentTaskLifecycleEvent(
        task_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        lifecycle_type=EnumAgentTaskLifecycleType.FAILED,
        remote_task_handle="remote-123",
        artifact=None,
        error="upstream 503",
        occurred_at=datetime.now(UTC),
    )

    assert event.error == "upstream 503"


@pytest.mark.unit
def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        ModelAgentTaskLifecycleEvent(
            task_id=uuid.uuid4(),
            correlation_id=uuid.uuid4(),
            lifecycle_type=EnumAgentTaskLifecycleType.SUBMITTED,
            occurred_at=datetime.now(UTC),
            unexpected=True,  # type: ignore[call-arg]
        )
