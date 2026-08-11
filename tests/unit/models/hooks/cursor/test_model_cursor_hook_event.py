# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the Cursor hook event model.

Focused on the agent_source seam (OMN-14750): the field is typed
EnumAgentSource with str-accepting coercion until the B3 read-mapping
(OMN-14751) lands, and the JSON wire shape is unchanged from the prior
plain-str field.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.hooks.cursor.enum_cursor_hook_event_type import (
    EnumCursorHookEventType,
)
from omnibase_core.enums.hooks.enum_agent_source import EnumAgentSource
from omnibase_core.models.hooks.cursor.model_cursor_hook_event import (
    ModelCursorHookEvent,
)
from omnibase_core.models.hooks.cursor.model_cursor_hook_event_payload import (
    ModelCursorHookEventPayload,
)


@pytest.mark.unit
class TestModelCursorHookEventAgentSource:
    """Test the agent_source retype str -> EnumAgentSource (OMN-14750)."""

    def _event(self, **overrides: object) -> ModelCursorHookEvent:
        kwargs: dict[str, object] = {
            "event_type": EnumCursorHookEventType.USER_PROMPT_SUBMIT,
            "session_id": "session-abc123",
            "timestamp_utc": datetime.now(UTC),
            "payload": ModelCursorHookEventPayload(),
        }
        kwargs.update(overrides)
        return ModelCursorHookEvent(**kwargs)  # type: ignore[arg-type]  # NOTE(OMN-14750): helper unpacks dict[str, object] test overrides; values are runtime-correct per-field

    def test_default_is_cursor(self) -> None:
        """Omitting agent_source defaults to CURSOR."""
        assert self._event().agent_source is EnumAgentSource.CURSOR

    def test_accepts_enum_member(self) -> None:
        """Explicit enum members are accepted as-is."""
        assert self._event(agent_source=EnumAgentSource.CURSOR).agent_source is (
            EnumAgentSource.CURSOR
        )

    def test_accepts_bare_string(self) -> None:
        """The canonical producer wire value ('cursor' as plain str) still validates.

        This is the str-accepting seam guarantee: omnicursor's
        build_cursor_event() emits agent_source as a bare JSON string and must
        keep working until OMN-14751 lands.
        """
        assert self._event(agent_source="cursor").agent_source is (
            EnumAgentSource.CURSOR
        )

    def test_accepts_string_case_insensitively(self) -> None:
        """Mixed-case strings coerce via the before-validator."""
        assert self._event(agent_source="Cursor").agent_source is (
            EnumAgentSource.CURSOR
        )

    def test_rejects_unknown_source(self) -> None:
        """Unknown dispatcher names fail validation (was: silently accepted as str)."""
        with pytest.raises(ValidationError):
            self._event(agent_source="copilot")

    def test_wire_serialization_is_plain_string(self) -> None:
        """JSON wire shape carries the bare value, unchanged from the str field."""
        wire = json.loads(self._event().model_dump_json())
        assert wire["agent_source"] == "cursor"

    def test_wire_round_trip_of_producer_shape(self) -> None:
        """The six-key producer dict (bare-str agent_source) validates end-to-end."""
        producer_wire = {
            "event_type": "UserPromptSubmit",
            "session_id": "session-abc123",
            "correlation_id": None,
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "agent_source": "cursor",
            "payload": {},
        }
        event = ModelCursorHookEvent.model_validate(producer_wire)
        assert event.agent_source is EnumAgentSource.CURSOR
