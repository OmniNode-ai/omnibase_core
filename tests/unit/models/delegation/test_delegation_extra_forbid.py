# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unknown-field rejection at audited delegation boundaries (OMN-20188)."""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.delegation.model_a2a_task_request import ModelA2ATaskRequest
from omnibase_core.models.delegation.model_a2a_task_response import ModelA2ATaskResponse
from omnibase_core.models.delegation.model_remote_task_state import ModelRemoteTaskState
from omnibase_core.models.delegation.model_routing_rule import ModelRoutingRule
from omnibase_core.models.delegation.model_target_agent import ModelTargetAgent
from omnibase_core.models.governance.model_delegation_health import (
    ModelDelegationHealth,
)
from omnibase_core.models.governance.model_dogfood_scorecard import (
    ModelDogfoodScorecard,
)

_TASK_ID = "aaaaaaaa-0000-0000-0000-000000000001"
_CORRELATION_ID = "bbbbbbbb-0000-0000-0000-000000000002"
_TIMESTAMP = "2026-04-25T12:00:00Z"
_SCHEMA_VALUE = ModelSchemaValue.from_value("triage these").model_dump(mode="json")
_HEALTH_PAYLOAD: dict[str, object] = {
    "task_type_coverage": {"triage": "pass", "research": "warn"},
    "classifier_coverage_pct": 95.0,
    "model_health": "pass",
    "status": "warn",
}

_CASES: tuple[tuple[type[BaseModel], dict[str, object]], ...] = (
    (
        ModelA2ATaskRequest,
        {
            "skill_ref": "scout",
            "input": {"prompt": _SCHEMA_VALUE},
            "correlation_id": _CORRELATION_ID,
        },
    ),
    (
        ModelA2ATaskResponse,
        {
            "remote_task_handle": "task-123",
            "status": "COMPLETED",
            "artifacts": [{"result": _SCHEMA_VALUE}],
            "error": None,
        },
    ),
    (
        ModelRemoteTaskState,
        {
            "task_id": _TASK_ID,
            "invocation_kind": "agent",
            "protocol": "A2A",
            "target_ref": "scout",
            "remote_task_handle": "task-123",
            "correlation_id": _CORRELATION_ID,
            "status": "COMPLETED",
            "last_remote_status": "completed",
            "last_emitted_event_type": "COMPLETED",
            "submitted_at": _TIMESTAMP,
            "updated_at": _TIMESTAMP,
            "completed_at": _TIMESTAMP,
            "error": None,
        },
    ),
    (
        ModelRoutingRule,
        {
            "capability": "tech_debt_triage",
            "invocation_kind": "agent",
            "agent_protocol": "A2A",
            "model_backend": None,
            "target_ref": "scout",
            "fallbacks": ["backup-scout"],
        },
    ),
    (
        ModelTargetAgent,
        {
            "target_ref": "scout",
            "base_url": "http://localhost:9080",
            "protocol": "A2A",
        },
    ),
    (ModelDelegationHealth, _HEALTH_PAYLOAD),
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("model", "payload"), _CASES, ids=[model.__name__ for model, _ in _CASES]
)
def test_valid_payload_parses_at_each_boundary(
    model: type[BaseModel], payload: dict[str, object]
) -> None:
    """Declared fields, including open content maps, survive wire round trips."""
    parsed = model.model_validate(payload)
    assert parsed == model.model_validate_json(json.dumps(payload))
    assert parsed == model(**payload)
    assert model.model_validate_json(parsed.model_dump_json()) == parsed
    assert set(payload) <= parsed.model_fields_set
    assert model.model_config["frozen"] is True
    assert model.model_json_schema()["additionalProperties"] is False


@pytest.mark.unit
@pytest.mark.parametrize(
    ("model", "payload"), _CASES, ids=[model.__name__ for model, _ in _CASES]
)
def test_unknown_field_is_rejected_at_each_boundary(
    model: type[BaseModel], payload: dict[str, object]
) -> None:
    """Schema skew must fail with an extra_forbidden error at the unknown key."""
    bad_payload = {**payload, "unexpected_wire_field": True}
    with pytest.raises(ValidationError) as mapping_error:
        model.model_validate(bad_payload)
    with pytest.raises(ValidationError) as json_error:
        model.model_validate_json(json.dumps(bad_payload))
    with pytest.raises(ValidationError) as constructor_error:
        model(**bad_payload)

    for error in (mapping_error, json_error, constructor_error):
        assert [(item["type"], item["loc"]) for item in error.value.errors()] == [
            ("extra_forbidden", ("unexpected_wire_field",))
        ]


@pytest.mark.unit
def test_scorecard_validates_nested_delegation_health() -> None:
    payload = {
        "captured_at": _TIMESTAMP,
        "run_id": "delegation-audit",
        "overall_status": "warn",
        "delegation": _HEALTH_PAYLOAD,
    }
    scorecard = ModelDogfoodScorecard.model_validate(payload)
    assert scorecard.delegation == ModelDelegationHealth.model_validate(_HEALTH_PAYLOAD)
    assert ModelDogfoodScorecard.model_validate_json(json.dumps(payload)) == scorecard

    payload["delegation"] = {**_HEALTH_PAYLOAD, "unexpected_wire_field": True}
    with pytest.raises(ValidationError) as mapping_error:
        ModelDogfoodScorecard.model_validate(payload)
    with pytest.raises(ValidationError) as json_error:
        ModelDogfoodScorecard.model_validate_json(json.dumps(payload))

    for error in (mapping_error, json_error):
        assert [(item["type"], item["loc"]) for item in error.value.errors()] == [
            ("extra_forbidden", ("delegation", "unexpected_wire_field"))
        ]
