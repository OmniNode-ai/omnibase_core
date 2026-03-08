# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelUserPromptSubmitPayload and payload parsing utilities.

Validates typed payload construction, validation, serialization, and the
parse_hook_payload / get_payload_type helpers.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.hooks.claude_code.enum_claude_code_hook_event_type import (
    EnumClaudeCodeHookEventType,
)
from omnibase_core.models.hooks.claude_code.model_claude_code_hook_event import (
    ModelClaudeCodeHookEvent,
)
from omnibase_core.models.hooks.claude_code.model_claude_code_hook_event_payload import (
    ModelClaudeCodeHookEventPayload,
)
from omnibase_core.models.hooks.claude_code.model_user_prompt_submit_payload import (
    ModelUserPromptSubmitPayload,
)
from omnibase_core.utils.util_parse_hook_payload import (
    get_payload_type,
    parse_hook_payload,
)


@pytest.mark.unit
class TestModelUserPromptSubmitPayload:
    """Test ModelUserPromptSubmitPayload construction and validation."""

    def test_valid_construction(self) -> None:
        """Test construction with required prompt field."""
        payload = ModelUserPromptSubmitPayload(prompt="Hello, Claude!")

        assert payload.prompt == "Hello, Claude!"
        assert isinstance(payload, ModelClaudeCodeHookEventPayload)

    def test_missing_prompt_raises_validation_error(self) -> None:
        """Test that missing prompt field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelUserPromptSubmitPayload()  # type: ignore[call-arg]

        assert "prompt" in str(exc_info.value)

    def test_empty_prompt_allowed(self) -> None:
        """Test that empty string prompt is valid (not missing)."""
        payload = ModelUserPromptSubmitPayload(prompt="")

        assert payload.prompt == ""

    def test_frozen_immutability(self) -> None:
        """Test that payload is frozen and rejects mutation."""
        payload = ModelUserPromptSubmitPayload(prompt="test")

        with pytest.raises((ValidationError, TypeError, AttributeError)):
            payload.prompt = "modified"  # type: ignore[misc]

    def test_extra_allow_accepts_unknown_fields(self) -> None:
        """Test that extra='allow' inherited from base accepts unknown fields."""
        payload = ModelUserPromptSubmitPayload.model_validate(
            {"prompt": "test", "future_field": "extra_value"}
        )

        assert payload.prompt == "test"
        assert payload.model_extra is not None
        assert payload.model_extra.get("future_field") == "extra_value"

    def test_json_serialization(self) -> None:
        """Test JSON serialization includes prompt field."""
        payload = ModelUserPromptSubmitPayload(prompt="Serialize me")
        json_data = payload.model_dump(mode="json")

        assert json_data["prompt"] == "Serialize me"

    def test_json_deserialization(self) -> None:
        """Test JSON deserialization produces typed model."""
        payload = ModelUserPromptSubmitPayload.model_validate(
            {"prompt": "Deserialized"}
        )

        assert payload.prompt == "Deserialized"
        assert isinstance(payload, ModelUserPromptSubmitPayload)

    def test_round_trip_serialization(self) -> None:
        """Test round-trip serialization preserves data."""
        original = ModelUserPromptSubmitPayload(prompt="Round trip test")
        json_data = original.model_dump(mode="json")
        restored = ModelUserPromptSubmitPayload.model_validate(json_data)

        assert restored.prompt == original.prompt

    def test_multiline_prompt(self) -> None:
        """Test that multiline prompts are accepted."""
        multiline = "Line 1\nLine 2\nLine 3"
        payload = ModelUserPromptSubmitPayload(prompt=multiline)

        assert payload.prompt == multiline

    def test_unicode_prompt(self) -> None:
        """Test that Unicode prompts are accepted."""
        unicode_prompt = "Fix the bug in the code"
        payload = ModelUserPromptSubmitPayload(prompt=unicode_prompt)

        assert payload.prompt == unicode_prompt


@pytest.mark.unit
class TestModelUserPromptSubmitPayloadIntegration:
    """Test integration with ModelClaudeCodeHookEvent."""

    def test_event_with_typed_payload(self) -> None:
        """Test that ModelClaudeCodeHookEvent accepts typed payload."""
        payload = ModelUserPromptSubmitPayload(prompt="Hello")

        event = ModelClaudeCodeHookEvent(
            event_type=EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
            session_id="test-session",
            timestamp_utc=datetime.now(UTC),
            payload=payload,
        )

        assert isinstance(event.payload, ModelUserPromptSubmitPayload)
        assert event.payload.prompt == "Hello"  # type: ignore[attr-defined]

    def test_typed_payload_is_subclass_of_base(self) -> None:
        """Test that typed payload passes isinstance check for base class."""
        payload = ModelUserPromptSubmitPayload(prompt="test")

        assert isinstance(payload, ModelClaudeCodeHookEventPayload)


@pytest.mark.unit
class TestParseHookPayload:
    """Test parse_hook_payload utility function."""

    def test_parse_user_prompt_submit(self) -> None:
        """Test parsing UserPromptSubmit returns typed payload."""
        payload = parse_hook_payload(
            EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
            {"prompt": "Hello, Claude!"},
        )

        assert isinstance(payload, ModelUserPromptSubmitPayload)
        assert payload.prompt == "Hello, Claude!"  # type: ignore[attr-defined]

    def test_parse_user_prompt_submit_missing_prompt_raises(self) -> None:
        """Test that missing prompt raises ValidationError for UserPromptSubmit."""
        with pytest.raises(ValidationError):
            parse_hook_payload(
                EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
                {"not_prompt": "value"},
            )

    def test_parse_unregistered_event_returns_base(self) -> None:
        """Test that unregistered event types return base payload."""
        payload = parse_hook_payload(
            EnumClaudeCodeHookEventType.SESSION_START,
            {"some_field": "value"},
        )

        assert type(payload) is ModelClaudeCodeHookEventPayload
        assert payload.model_extra is not None
        assert payload.model_extra.get("some_field") == "value"

    def test_parse_all_event_types_without_error(self) -> None:
        """Test that all event types can be parsed (at least with base class)."""
        for event_type in EnumClaudeCodeHookEventType:
            if event_type == EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT:
                data = {"prompt": "test"}
            else:
                data = {}

            payload = parse_hook_payload(event_type, data)
            assert isinstance(payload, ModelClaudeCodeHookEventPayload)

    def test_parse_with_extra_fields_preserved(self) -> None:
        """Test that extra fields are preserved in parsed payload."""
        payload = parse_hook_payload(
            EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
            {"prompt": "test", "extra_key": "extra_val"},
        )

        assert isinstance(payload, ModelUserPromptSubmitPayload)
        assert payload.model_extra is not None
        assert payload.model_extra.get("extra_key") == "extra_val"


@pytest.mark.unit
class TestGetPayloadType:
    """Test get_payload_type utility function."""

    def test_user_prompt_submit_returns_typed_class(self) -> None:
        """Test that USER_PROMPT_SUBMIT returns ModelUserPromptSubmitPayload."""
        cls = get_payload_type(EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT)

        assert cls is ModelUserPromptSubmitPayload

    def test_unregistered_event_returns_base_class(self) -> None:
        """Test that unregistered event types return base payload class."""
        cls = get_payload_type(EnumClaudeCodeHookEventType.SESSION_START)

        assert cls is ModelClaudeCodeHookEventPayload

    def test_all_event_types_return_valid_class(self) -> None:
        """Test that all event types return a payload class."""
        for event_type in EnumClaudeCodeHookEventType:
            cls = get_payload_type(event_type)
            assert issubclass(cls, ModelClaudeCodeHookEventPayload)
