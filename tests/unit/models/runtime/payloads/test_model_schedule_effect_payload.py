# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for ModelScheduleEffectPayload.

This module tests the SCHEDULE_EFFECT directive payload, verifying:
1. Discriminator field (kind="schedule_effect")
2. Required and optional fields
3. Validation constraints (min_length on effect_node_type)
4. Integration with ModelSchemaValue
5. Serialization/deserialization roundtrip
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.runtime.payloads import ModelScheduleEffectPayload


@pytest.mark.unit
class TestModelScheduleEffectPayloadDiscriminator:
    """Test discriminator field behavior."""

    def test_kind_is_literal_schedule_effect(self) -> None:
        """Test that kind field is always 'schedule_effect'."""
        payload = ModelScheduleEffectPayload(effect_node_type="http_request")
        assert payload.kind == "schedule_effect"

    def test_kind_rejects_non_literal_value(self) -> None:
        """Test that kind field rejects values other than 'schedule_effect'."""
        with pytest.raises(ValidationError):
            ModelScheduleEffectPayload(
                effect_node_type="http_request",
                kind="other_kind",  # type: ignore[arg-type]
            )

    def test_kind_default_value(self) -> None:
        """Test that kind has correct default value."""
        payload = ModelScheduleEffectPayload(effect_node_type="test")
        assert payload.kind == "schedule_effect"


@pytest.mark.unit
class TestModelScheduleEffectPayloadRequiredFields:
    """Test required field validation."""

    def test_effect_node_type_required(self) -> None:
        """Test that effect_node_type is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelScheduleEffectPayload()  # type: ignore[call-arg]
        assert "effect_node_type" in str(exc_info.value)

    def test_effect_node_type_rejects_empty_string(self) -> None:
        """Test that effect_node_type rejects empty string (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelScheduleEffectPayload(effect_node_type="")
        assert "effect_node_type" in str(exc_info.value)

    def test_effect_node_type_valid(self) -> None:
        """Test valid effect_node_type values."""
        payload = ModelScheduleEffectPayload(effect_node_type="http_request")
        assert payload.effect_node_type == "http_request"


@pytest.mark.unit
class TestModelScheduleEffectPayloadOptionalFields:
    """Test optional field behavior."""

    def test_effect_input_defaults_to_none(self) -> None:
        """Test that effect_input defaults to None."""
        payload = ModelScheduleEffectPayload(effect_node_type="test")
        assert payload.effect_input is None

    def test_effect_input_with_schema_value(self) -> None:
        """Test effect_input with ModelSchemaValue."""
        input_data = ModelSchemaValue.create_object({"url": "https://api.example.com"})
        payload = ModelScheduleEffectPayload(
            effect_node_type="http_request",
            effect_input=input_data,
        )
        assert payload.effect_input is not None
        assert payload.effect_input.value_type == "object"

    def test_effect_input_with_string_value(self) -> None:
        """Test effect_input with string ModelSchemaValue."""
        input_data = ModelSchemaValue.create_string("test_input")
        payload = ModelScheduleEffectPayload(
            effect_node_type="test",
            effect_input=input_data,
        )
        assert payload.effect_input is not None
        assert payload.effect_input.string_value == "test_input"


@pytest.mark.unit
class TestModelScheduleEffectPayloadSerialization:
    """Test serialization/deserialization."""

    def test_serialization_minimal(self) -> None:
        """Test serialization with minimal fields."""
        payload = ModelScheduleEffectPayload(effect_node_type="test")
        data = payload.model_dump()

        assert data["kind"] == "schedule_effect"
        assert data["effect_node_type"] == "test"
        assert data["effect_input"] is None

    def test_serialization_with_input(self) -> None:
        """Test serialization with effect_input."""
        input_data = ModelSchemaValue.create_object({"key": "value"})
        payload = ModelScheduleEffectPayload(
            effect_node_type="test",
            effect_input=input_data,
        )
        data = payload.model_dump()

        assert data["effect_input"] is not None
        assert data["effect_input"]["value_type"] == "object"

    def test_roundtrip_serialization_minimal(self) -> None:
        """Test roundtrip serialization with minimal fields."""
        original = ModelScheduleEffectPayload(effect_node_type="http_request")
        data = original.model_dump()
        restored = ModelScheduleEffectPayload.model_validate(data)

        assert restored.kind == original.kind
        assert restored.effect_node_type == original.effect_node_type
        assert restored.effect_input == original.effect_input

    def test_roundtrip_serialization_with_input(self) -> None:
        """Test roundtrip serialization with effect_input."""
        input_data = ModelSchemaValue.create_object(
            {"url": "https://api.example.com", "method": "POST"}
        )
        original = ModelScheduleEffectPayload(
            effect_node_type="http_request",
            effect_input=input_data,
        )
        data = original.model_dump()
        restored = ModelScheduleEffectPayload.model_validate(data)

        assert restored.effect_input is not None
        assert restored.effect_input.value_type == "object"

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        payload = ModelScheduleEffectPayload(effect_node_type="test")
        json_str = payload.model_dump_json()

        assert '"kind":"schedule_effect"' in json_str
        assert '"effect_node_type":"test"' in json_str


@pytest.mark.unit
class TestModelScheduleEffectPayloadImmutability:
    """Test immutability (frozen model)."""

    def test_cannot_modify_effect_node_type(self) -> None:
        """Test that effect_node_type cannot be modified."""
        payload = ModelScheduleEffectPayload(effect_node_type="test")
        with pytest.raises(ValidationError):
            payload.effect_node_type = "modified"  # type: ignore[misc]

    def test_cannot_modify_kind(self) -> None:
        """Test that kind cannot be modified."""
        payload = ModelScheduleEffectPayload(effect_node_type="test")
        with pytest.raises(ValidationError):
            payload.kind = "other"  # type: ignore[misc]


@pytest.mark.unit
class TestModelScheduleEffectPayloadExtraFieldsRejected:
    """Test extra fields rejection."""

    def test_reject_extra_fields(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelScheduleEffectPayload(
                effect_node_type="test",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)


@pytest.mark.unit
class TestModelScheduleEffectPayloadEdgeCases:
    """Test edge cases."""

    def test_effect_node_type_with_common_separators(self) -> None:
        """Test effect_node_type with hyphens, underscores, and dots."""
        payload = ModelScheduleEffectPayload(effect_node_type="http-request_v2.0")
        assert payload.effect_node_type == "http-request_v2.0"

    def test_effect_node_type_single_character(self) -> None:
        """Test effect_node_type with single character (min_length boundary)."""
        payload = ModelScheduleEffectPayload(effect_node_type="e")
        assert payload.effect_node_type == "e"

    def test_effect_input_nested_structure(self) -> None:
        """Test effect_input with deeply nested structure."""
        nested_data = ModelSchemaValue.create_object(
            {
                "level1": {
                    "level2": {
                        "values": [1, 2, 3],
                    }
                }
            }
        )
        payload = ModelScheduleEffectPayload(
            effect_node_type="test",
            effect_input=nested_data,
        )
        assert payload.effect_input is not None

    def test_effect_input_empty_object(self) -> None:
        """Test effect_input with empty object."""
        empty_obj = ModelSchemaValue.create_object({})
        payload = ModelScheduleEffectPayload(
            effect_node_type="test",
            effect_input=empty_obj,
        )
        assert payload.effect_input is not None
        assert payload.effect_input.value_type == "object"
