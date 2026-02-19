# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelEventBusOutputField.

Comprehensive tests for event bus output field model including:
- Construction with valid inputs
- Construction with optional fields
- Serialization and deserialization
- Edge cases
"""

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.models.event_bus.model_event_bus_output_field import (
    ModelEventBusOutputField,
)


@pytest.mark.unit
class TestModelEventBusOutputFieldConstruction:
    """Test ModelEventBusOutputField construction."""

    def test_create_with_required_field_only(self) -> None:
        """Test creating output field with only required backend field."""
        field = ModelEventBusOutputField(backend="kafka")

        assert field.backend == "kafka"
        assert field.processed is None
        assert field.integration is None
        assert field.custom is None

    def test_create_with_all_fields(self) -> None:
        """Test creating output field with all fields."""
        field = ModelEventBusOutputField(
            processed="completed",
            integration=True,
            backend="redpanda",
            custom={"key": "value"},
        )

        assert field.processed == "completed"
        assert field.integration is True
        assert field.backend == "redpanda"
        assert field.custom == {"key": "value"}

    def test_create_with_integration_false(self) -> None:
        """Test creating output field with integration=False."""
        field = ModelEventBusOutputField(
            backend="kafka",
            integration=False,
        )

        assert field.integration is False

    def test_create_with_various_backends(self) -> None:
        """Test creating output fields with various backend values."""
        backends = ["kafka", "redpanda", "rabbitmq", "sqs", "pubsub"]

        for backend in backends:
            field = ModelEventBusOutputField(backend=backend)
            assert field.backend == backend


@pytest.mark.unit
class TestModelEventBusOutputFieldValidation:
    """Test ModelEventBusOutputField validation."""

    def test_missing_backend_raises_error(self) -> None:
        """Test that missing backend raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventBusOutputField()  # type: ignore[call-arg]

        assert "backend" in str(exc_info.value)

    def test_none_backend_raises_error(self) -> None:
        """Test that None backend raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelEventBusOutputField(backend=None)  # type: ignore[arg-type]


@pytest.mark.unit
class TestModelEventBusOutputFieldCustomField:
    """Test ModelEventBusOutputField custom field behavior."""

    def test_custom_with_dict(self) -> None:
        """Test custom field with dictionary value."""
        custom_data = {"key": "value", "nested": {"inner": 123}}

        field = ModelEventBusOutputField(backend="kafka", custom=custom_data)

        assert field.custom == custom_data
        assert field.custom["key"] == "value"

    def test_custom_with_list(self) -> None:
        """Test custom field with list value."""
        custom_data = [1, 2, 3, "four"]

        field = ModelEventBusOutputField(backend="kafka", custom=custom_data)

        assert field.custom == custom_data

    def test_custom_with_string(self) -> None:
        """Test custom field with string value."""
        field = ModelEventBusOutputField(backend="kafka", custom="simple string")

        assert field.custom == "simple string"

    def test_custom_with_integer(self) -> None:
        """Test custom field with integer value."""
        field = ModelEventBusOutputField(backend="kafka", custom=42)

        assert field.custom == 42

    def test_custom_with_complex_object(self) -> None:
        """Test custom field with complex nested object."""
        complex_data: dict[str, Any] = {
            "level1": {
                "level2": {
                    "level3": [1, 2, {"deep": True}],
                },
            },
            "tags": ["a", "b", "c"],
            "count": 100,
        }

        field = ModelEventBusOutputField(backend="kafka", custom=complex_data)

        assert field.custom == complex_data
        assert field.custom["level1"]["level2"]["level3"][2]["deep"] is True


@pytest.mark.unit
class TestModelEventBusOutputFieldSerialization:
    """Test ModelEventBusOutputField serialization."""

    def test_model_dump_with_required_only(self) -> None:
        """Test model_dump() with only required field."""
        field = ModelEventBusOutputField(backend="kafka")

        data = field.model_dump()

        assert isinstance(data, dict)
        assert data["backend"] == "kafka"
        assert data["processed"] is None
        assert data["integration"] is None
        assert data["custom"] is None

    def test_model_dump_with_all_fields(self) -> None:
        """Test model_dump() with all fields."""
        field = ModelEventBusOutputField(
            processed="done",
            integration=True,
            backend="redpanda",
            custom={"data": "value"},
        )

        data = field.model_dump()

        assert data["processed"] == "done"
        assert data["integration"] is True
        assert data["backend"] == "redpanda"
        assert data["custom"] == {"data": "value"}

    def test_model_dump_exclude_none(self) -> None:
        """Test model_dump() with exclude_none option."""
        field = ModelEventBusOutputField(backend="kafka")

        data = field.model_dump(exclude_none=True)

        assert "backend" in data
        assert "processed" not in data
        assert "integration" not in data
        assert "custom" not in data

    def test_model_validate(self) -> None:
        """Test model_validate() deserialization."""
        data = {
            "processed": "complete",
            "integration": False,
            "backend": "sqs",
            "custom": None,
        }

        field = ModelEventBusOutputField.model_validate(data)

        assert field.processed == "complete"
        assert field.integration is False
        assert field.backend == "sqs"

    def test_serialization_roundtrip(self) -> None:
        """Test serialization and deserialization roundtrip."""
        original = ModelEventBusOutputField(
            processed="done",
            integration=True,
            backend="kafka",
            custom={"meta": "data"},
        )

        data = original.model_dump()
        restored = ModelEventBusOutputField.model_validate(data)

        assert restored.processed == original.processed
        assert restored.integration == original.integration
        assert restored.backend == original.backend
        assert restored.custom == original.custom

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        field = ModelEventBusOutputField(
            backend="kafka",
            integration=True,
        )

        json_data = field.model_dump_json()

        assert isinstance(json_data, str)
        assert "kafka" in json_data
        assert "integration" in json_data

    def test_json_deserialization(self) -> None:
        """Test JSON deserialization."""
        json_data = '{"backend": "redpanda", "processed": "complete"}'

        field = ModelEventBusOutputField.model_validate_json(json_data)

        assert field.backend == "redpanda"
        assert field.processed == "complete"


@pytest.mark.unit
class TestModelEventBusOutputFieldEdgeCases:
    """Test ModelEventBusOutputField edge cases."""

    def test_empty_backend_string(self) -> None:
        """Test creating field with empty backend string."""
        field = ModelEventBusOutputField(backend="")

        assert field.backend == ""

    def test_empty_processed_string(self) -> None:
        """Test creating field with empty processed string."""
        field = ModelEventBusOutputField(backend="kafka", processed="")

        assert field.processed == ""

    def test_whitespace_in_backend(self) -> None:
        """Test creating field with whitespace in backend."""
        field = ModelEventBusOutputField(backend="  kafka  ")

        assert field.backend == "  kafka  "

    def test_long_backend_string(self) -> None:
        """Test creating field with long backend string."""
        long_backend = "x" * 1000

        field = ModelEventBusOutputField(backend=long_backend)

        assert len(field.backend) == 1000

    def test_unicode_in_processed(self) -> None:
        """Test creating field with unicode in processed."""
        field = ModelEventBusOutputField(
            backend="kafka",
            processed="processed successfully",
        )

        assert "processed" in field.processed

    def test_model_copy(self) -> None:
        """Test model_copy() creates independent copy."""
        original = ModelEventBusOutputField(
            backend="kafka",
            processed="done",
            integration=True,
        )

        copied = original.model_copy()

        assert copied is not original
        assert copied.backend == original.backend
        assert copied.processed == original.processed
        assert copied.integration == original.integration

    def test_model_copy_with_update(self) -> None:
        """Test model_copy() with field updates."""
        original = ModelEventBusOutputField(
            backend="kafka",
            processed="done",
        )

        updated = original.model_copy(update={"backend": "redpanda"})

        assert original.backend == "kafka"
        assert updated.backend == "redpanda"
        assert updated.processed == "done"
