# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression tests for the ModelPermissionAction UUID wire contract."""

import json
from uuid import UUID

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from omnibase_core.models.security.model_permission_action import ModelPermissionAction

ACTION_ID = "11111111-1111-4111-8111-111111111111"
ACTION_PAYLOAD: dict[str, object] = {
    "action_id": ACTION_ID,
    "action_name": "Read deployment metadata",
    "action_type": "read",
    "resource_types": ["deployment"],
    "requires_approval": False,
    "risk_level": "low",
    "description": "Read-only deployment inspection",
    "max_frequency_per_hour": 60,
    "cooldown_minutes": 0,
    "audit_required": True,
    "audit_detail_level": "detailed",
}


class _ActionEnvelope(BaseModel):
    """Representative typed container for the permission action."""

    model_config = ConfigDict(extra="forbid")

    action: ModelPermissionAction


@pytest.mark.parametrize("action_id", [ACTION_ID, UUID(ACTION_ID)])
def test_canonical_uuid_inputs_preserve_typed_and_json_values(
    action_id: str | UUID,
) -> None:
    """Canonical mapping inputs become UUID while retaining their wire value."""
    action = ModelPermissionAction.model_validate(
        {**ACTION_PAYLOAD, "action_id": action_id}
    )

    assert action.action_id == UUID(ACTION_ID)
    assert action.model_dump(mode="json") == ACTION_PAYLOAD


def test_canonical_json_round_trip_preserves_action() -> None:
    """The canonical string UUID remains valid at the JSON boundary."""
    action = ModelPermissionAction.model_validate_json(json.dumps(ACTION_PAYLOAD))

    assert (
        ModelPermissionAction.model_validate_json(action.model_dump_json()).model_dump(
            mode="json"
        )
        == ACTION_PAYLOAD
    )


def test_malformed_uuid_fails_with_typed_validation_error() -> None:
    """Malformed identifiers fail through the UUID contract, never TypeError."""
    with pytest.raises(ValidationError) as error:
        ModelPermissionAction.model_validate(
            {**ACTION_PAYLOAD, "action_id": "not-a-uuid"}
        )

    assert any(
        item["loc"] == ("action_id",) and item["type"] == "uuid_parsing"
        for item in error.value.errors()
    )


def test_schema_declares_uuid_without_string_pattern() -> None:
    """The schema describes the actual UUID input instead of a string regex."""
    action_id_schema = ModelPermissionAction.model_json_schema()["properties"][
        "action_id"
    ]

    assert action_id_schema["format"] == "uuid"
    assert "pattern" not in action_id_schema


def test_nested_unknown_action_key_fails_closed() -> None:
    """Typed containers preserve the composed extra-forbid action boundary."""
    with pytest.raises(ValidationError) as error:
        _ActionEnvelope.model_validate(
            {"action": {**ACTION_PAYLOAD, "omn17736_unknown": True}}
        )

    assert any(
        item["loc"] == ("action", "omn17736_unknown")
        and item["type"] == "extra_forbidden"
        for item in error.value.errors()
    )
