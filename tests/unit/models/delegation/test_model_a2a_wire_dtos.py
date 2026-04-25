# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Test A2A wire DTOs."""

from __future__ import annotations

import uuid

import pytest

from omnibase_core.models.delegation.model_a2a_task_request import (
    ModelA2ATaskRequest,
)
from omnibase_core.models.delegation.model_a2a_task_response import (
    ModelA2ATaskResponse,
)


@pytest.mark.unit
def test_request_shape_accepts_a2a_skill_id_alias() -> None:
    request = ModelA2ATaskRequest(
        skill_id="tech_debt_finding_triage",
        input={"findings": []},
        correlation_id=uuid.uuid4(),
    )

    assert request.skill_ref == "tech_debt_finding_triage"
    assert request.input["findings"].value_type == "array"
    assert request.model_dump(by_alias=True)["skill_id"] == "tech_debt_finding_triage"


@pytest.mark.unit
def test_request_ignores_unknown_fields() -> None:
    request = ModelA2ATaskRequest.model_validate(
        {
            "skill_id": "tech_debt_finding_triage",
            "input": {"limit": 5},
            "correlation_id": uuid.uuid4(),
            "future_field": "ignored",
        },
    )

    assert "future_field" not in request.model_fields_set


@pytest.mark.unit
def test_response_ignores_unknown_fields_and_types_artifacts() -> None:
    response = ModelA2ATaskResponse.model_validate(
        {
            "remote_task_handle": "h-123",
            "status": "completed",
            "artifacts": [{"mimeType": "application/json", "data": {}}],
            "error": None,
            "unknown_future_field": "fine",
        },
    )

    assert response.remote_task_handle == "h-123"
    assert response.status == "completed"
    assert response.artifacts[0]["mimeType"].string_value == "application/json"
