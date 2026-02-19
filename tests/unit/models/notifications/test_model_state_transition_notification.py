# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelStateTransitionNotification.

Tests verify:
- Model instantiation with all required fields
- Model validation for required and optional fields
- UUID field validation
- Serialization and deserialization (model_dump, model_validate)
- Immutability (frozen model)
- ConfigDict settings (extra="forbid", from_attributes=True)

Timeout Protection:
- All test classes use @pytest.mark.timeout(5) for unit tests
- These are pure model tests with no I/O
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.notifications.model_state_transition_notification import (
    ModelStateTransitionNotification,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

# ---- Test Fixtures ----


@pytest.fixture
def valid_notification_data() -> dict[str, Any]:
    """Return valid data for creating a notification."""
    return {
        "aggregate_type": "registration",
        "aggregate_id": uuid4(),
        "from_state": "pending",
        "to_state": "active",
        "projection_version": 1,
        "correlation_id": uuid4(),
        "causation_id": uuid4(),
        "timestamp": datetime.now(UTC),
    }


@pytest.fixture
def valid_notification(
    valid_notification_data: dict[str, Any],
) -> ModelStateTransitionNotification:
    """Return a valid notification instance."""
    return ModelStateTransitionNotification(**valid_notification_data)


# ---- Test Model Instantiation ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelInstantiation:
    """Tests for ModelStateTransitionNotification instantiation."""

    def test_instantiation_with_required_fields(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test notification creation with all required fields."""
        notification = ModelStateTransitionNotification(**valid_notification_data)

        assert notification.aggregate_type == valid_notification_data["aggregate_type"]
        assert notification.aggregate_id == valid_notification_data["aggregate_id"]
        assert notification.from_state == valid_notification_data["from_state"]
        assert notification.to_state == valid_notification_data["to_state"]
        assert (
            notification.projection_version
            == valid_notification_data["projection_version"]
        )
        assert notification.correlation_id == valid_notification_data["correlation_id"]
        assert notification.causation_id == valid_notification_data["causation_id"]
        assert notification.timestamp == valid_notification_data["timestamp"]

    def test_instantiation_with_all_optional_fields(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test notification creation with all optional fields."""
        valid_notification_data["projection_hash"] = "abc123def456"
        valid_notification_data["reducer_version"] = ModelSemVer(
            major=1, minor=2, patch=3
        )
        valid_notification_data["workflow_view"] = {
            "step": "completed",
            "progress": 100,
        }

        notification = ModelStateTransitionNotification(**valid_notification_data)

        assert notification.projection_hash == "abc123def456"
        assert notification.reducer_version == ModelSemVer(major=1, minor=2, patch=3)
        assert notification.workflow_view == {"step": "completed", "progress": 100}

    def test_optional_fields_default_to_none(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that optional fields default to None."""
        notification = ModelStateTransitionNotification(**valid_notification_data)

        assert notification.projection_hash is None
        assert notification.reducer_version is None
        assert notification.workflow_view is None

    def test_uuid_fields_are_uuid_type(
        self, valid_notification: ModelStateTransitionNotification
    ) -> None:
        """Test that UUID fields are properly typed as UUID."""
        assert isinstance(valid_notification.aggregate_id, UUID)
        assert isinstance(valid_notification.correlation_id, UUID)
        assert isinstance(valid_notification.causation_id, UUID)


# ---- Test Model Validation ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelValidation:
    """Tests for field validation on ModelStateTransitionNotification."""

    def test_missing_required_field_aggregate_type(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that missing aggregate_type raises ValidationError."""
        del valid_notification_data["aggregate_type"]
        with pytest.raises(ValidationError) as exc_info:
            ModelStateTransitionNotification(**valid_notification_data)
        assert "aggregate_type" in str(exc_info.value)

    def test_missing_required_field_aggregate_id(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that missing aggregate_id raises ValidationError."""
        del valid_notification_data["aggregate_id"]
        with pytest.raises(ValidationError) as exc_info:
            ModelStateTransitionNotification(**valid_notification_data)
        assert "aggregate_id" in str(exc_info.value)

    def test_missing_required_field_from_state(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that missing from_state raises ValidationError."""
        del valid_notification_data["from_state"]
        with pytest.raises(ValidationError) as exc_info:
            ModelStateTransitionNotification(**valid_notification_data)
        assert "from_state" in str(exc_info.value)

    def test_missing_required_field_to_state(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that missing to_state raises ValidationError."""
        del valid_notification_data["to_state"]
        with pytest.raises(ValidationError) as exc_info:
            ModelStateTransitionNotification(**valid_notification_data)
        assert "to_state" in str(exc_info.value)

    def test_missing_required_field_projection_version(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that missing projection_version raises ValidationError."""
        del valid_notification_data["projection_version"]
        with pytest.raises(ValidationError) as exc_info:
            ModelStateTransitionNotification(**valid_notification_data)
        assert "projection_version" in str(exc_info.value)

    def test_missing_required_field_correlation_id(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that missing correlation_id raises ValidationError."""
        del valid_notification_data["correlation_id"]
        with pytest.raises(ValidationError) as exc_info:
            ModelStateTransitionNotification(**valid_notification_data)
        assert "correlation_id" in str(exc_info.value)

    def test_missing_required_field_causation_id(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that missing causation_id raises ValidationError."""
        del valid_notification_data["causation_id"]
        with pytest.raises(ValidationError) as exc_info:
            ModelStateTransitionNotification(**valid_notification_data)
        assert "causation_id" in str(exc_info.value)

    def test_missing_required_field_timestamp(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that missing timestamp raises ValidationError."""
        del valid_notification_data["timestamp"]
        with pytest.raises(ValidationError) as exc_info:
            ModelStateTransitionNotification(**valid_notification_data)
        assert "timestamp" in str(exc_info.value)

    def test_invalid_uuid_for_aggregate_id(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that invalid UUID for aggregate_id raises ValidationError."""
        valid_notification_data["aggregate_id"] = "not-a-valid-uuid"
        with pytest.raises(ValidationError) as exc_info:
            ModelStateTransitionNotification(**valid_notification_data)
        # Pydantic will report uuid validation failure
        assert (
            "aggregate_id" in str(exc_info.value).lower()
            or "uuid" in str(exc_info.value).lower()
        )

    def test_invalid_uuid_for_correlation_id(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that invalid UUID for correlation_id raises ValidationError."""
        valid_notification_data["correlation_id"] = "invalid"
        with pytest.raises(ValidationError) as exc_info:
            ModelStateTransitionNotification(**valid_notification_data)
        assert (
            "correlation_id" in str(exc_info.value).lower()
            or "uuid" in str(exc_info.value).lower()
        )

    def test_invalid_uuid_for_causation_id(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that invalid UUID for causation_id raises ValidationError."""
        valid_notification_data["causation_id"] = 12345  # Not a valid UUID
        with pytest.raises(ValidationError) as exc_info:
            ModelStateTransitionNotification(**valid_notification_data)
        assert (
            "causation_id" in str(exc_info.value).lower()
            or "uuid" in str(exc_info.value).lower()
        )

    def test_projection_version_must_be_int(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that projection_version must be an integer."""
        valid_notification_data["projection_version"] = "not-an-int"
        with pytest.raises(ValidationError) as exc_info:
            ModelStateTransitionNotification(**valid_notification_data)
        assert "projection_version" in str(exc_info.value).lower()

    def test_uuid_string_is_coerced_to_uuid(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that valid UUID string is coerced to UUID type."""
        test_uuid = uuid4()
        valid_notification_data["aggregate_id"] = str(test_uuid)
        notification = ModelStateTransitionNotification(**valid_notification_data)
        assert notification.aggregate_id == test_uuid
        assert isinstance(notification.aggregate_id, UUID)


# ---- Test ConfigDict Settings ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestConfigDictSettings:
    """Tests for ConfigDict settings (frozen, extra, from_attributes)."""

    def test_model_is_frozen(
        self, valid_notification: ModelStateTransitionNotification
    ) -> None:
        """Test that the model is frozen (immutable)."""
        with pytest.raises(ValidationError, match="frozen"):
            valid_notification.aggregate_type = "changed"  # type: ignore[misc]

    def test_extra_fields_forbidden(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that extra fields are forbidden."""
        valid_notification_data["unknown_field"] = "should_fail"
        with pytest.raises(ValidationError) as exc_info:
            ModelStateTransitionNotification(**valid_notification_data)
        assert "extra" in str(exc_info.value).lower() or "unknown_field" in str(
            exc_info.value
        )

    def test_from_attributes_enabled(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that from_attributes=True allows attribute-based construction."""

        class AttributeSource:
            def __init__(self, data: dict[str, Any]) -> None:
                for key, value in data.items():
                    setattr(self, key, value)

        source = AttributeSource(valid_notification_data)
        notification = ModelStateTransitionNotification.model_validate(source)

        assert notification.aggregate_type == valid_notification_data["aggregate_type"]
        assert notification.aggregate_id == valid_notification_data["aggregate_id"]


# ---- Test Serialization ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestSerialization:
    """Tests for model serialization and deserialization."""

    def test_model_dump(
        self, valid_notification: ModelStateTransitionNotification
    ) -> None:
        """Test that model_dump() serializes correctly."""
        data = valid_notification.model_dump()

        assert isinstance(data, dict)
        assert data["aggregate_type"] == valid_notification.aggregate_type
        assert data["aggregate_id"] == valid_notification.aggregate_id
        assert data["from_state"] == valid_notification.from_state
        assert data["to_state"] == valid_notification.to_state
        assert data["projection_version"] == valid_notification.projection_version
        assert data["correlation_id"] == valid_notification.correlation_id
        assert data["causation_id"] == valid_notification.causation_id
        assert data["timestamp"] == valid_notification.timestamp

    def test_model_dump_json_mode(
        self, valid_notification: ModelStateTransitionNotification
    ) -> None:
        """Test that model_dump(mode='json') produces JSON-serializable output."""
        data = valid_notification.model_dump(mode="json")

        # UUIDs should be strings in JSON mode
        assert isinstance(data["aggregate_id"], str)
        assert isinstance(data["correlation_id"], str)
        assert isinstance(data["causation_id"], str)

        # Timestamp should be ISO format string
        assert isinstance(data["timestamp"], str)

    def test_model_dump_json(
        self, valid_notification: ModelStateTransitionNotification
    ) -> None:
        """Test JSON serialization with model_dump_json()."""
        json_str = valid_notification.model_dump_json()

        assert isinstance(json_str, str)
        assert valid_notification.aggregate_type in json_str
        assert valid_notification.from_state in json_str
        assert valid_notification.to_state in json_str

    def test_model_validate_from_dict(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test deserialization from dictionary with model_validate()."""
        notification = ModelStateTransitionNotification.model_validate(
            valid_notification_data
        )

        assert notification.aggregate_type == valid_notification_data["aggregate_type"]
        assert notification.aggregate_id == valid_notification_data["aggregate_id"]

    def test_model_validate_json(
        self, valid_notification: ModelStateTransitionNotification
    ) -> None:
        """Test JSON deserialization with model_validate_json()."""
        json_str = valid_notification.model_dump_json()
        restored = ModelStateTransitionNotification.model_validate_json(json_str)

        assert restored.aggregate_type == valid_notification.aggregate_type
        assert restored.aggregate_id == valid_notification.aggregate_id
        assert restored.from_state == valid_notification.from_state
        assert restored.to_state == valid_notification.to_state
        assert restored.projection_version == valid_notification.projection_version

    def test_round_trip_serialization(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test full round-trip serialization (dict -> model -> json -> model)."""
        # Add optional fields for full test
        valid_notification_data["projection_hash"] = "hash123"
        valid_notification_data["reducer_version"] = ModelSemVer(
            major=2, minor=0, patch=0
        )
        valid_notification_data["workflow_view"] = {"key": "value"}

        original = ModelStateTransitionNotification(**valid_notification_data)
        json_str = original.model_dump_json()
        restored = ModelStateTransitionNotification.model_validate_json(json_str)

        assert restored.aggregate_type == original.aggregate_type
        assert restored.aggregate_id == original.aggregate_id
        assert restored.from_state == original.from_state
        assert restored.to_state == original.to_state
        assert restored.projection_version == original.projection_version
        assert restored.correlation_id == original.correlation_id
        assert restored.causation_id == original.causation_id
        assert restored.projection_hash == original.projection_hash
        assert restored.reducer_version == original.reducer_version
        assert restored.workflow_view == original.workflow_view


# ---- Test Optional Fields ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestOptionalFields:
    """Tests for optional field behavior."""

    def test_projection_hash_optional(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that projection_hash is optional."""
        notification = ModelStateTransitionNotification(**valid_notification_data)
        assert notification.projection_hash is None

        valid_notification_data["projection_hash"] = "sha256:abc123"
        notification_with_hash = ModelStateTransitionNotification(
            **valid_notification_data
        )
        assert notification_with_hash.projection_hash == "sha256:abc123"

    def test_reducer_version_optional(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that reducer_version is optional."""
        notification = ModelStateTransitionNotification(**valid_notification_data)
        assert notification.reducer_version is None

        valid_notification_data["reducer_version"] = ModelSemVer(
            major=3, minor=1, patch=4
        )
        notification_with_version = ModelStateTransitionNotification(
            **valid_notification_data
        )
        assert notification_with_version.reducer_version == ModelSemVer(
            major=3, minor=1, patch=4
        )

    def test_workflow_view_optional(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that workflow_view is optional."""
        notification = ModelStateTransitionNotification(**valid_notification_data)
        assert notification.workflow_view is None

        valid_notification_data["workflow_view"] = {
            "current_step": "validation",
            "steps_completed": ["init", "processing"],
            "metadata": {"user": "admin"},
        }
        notification_with_view = ModelStateTransitionNotification(
            **valid_notification_data
        )
        assert notification_with_view.workflow_view == {
            "current_step": "validation",
            "steps_completed": ["init", "processing"],
            "metadata": {"user": "admin"},
        }

    def test_workflow_view_with_nested_data(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test workflow_view with complex nested data."""
        complex_view = {
            "level1": {
                "level2": {
                    "level3": ["a", "b", "c"],
                    "number": 42,
                    "boolean": True,
                }
            },
            "list": [1, 2, {"nested": "dict"}],
        }
        valid_notification_data["workflow_view"] = complex_view

        notification = ModelStateTransitionNotification(**valid_notification_data)
        assert notification.workflow_view == complex_view


# ---- Test Edge Cases ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_string_states(self, valid_notification_data: dict[str, Any]) -> None:
        """Test that empty string states are accepted."""
        valid_notification_data["from_state"] = ""
        valid_notification_data["to_state"] = ""

        notification = ModelStateTransitionNotification(**valid_notification_data)
        assert notification.from_state == ""
        assert notification.to_state == ""

    def test_same_from_and_to_state(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test notification where from_state equals to_state."""
        valid_notification_data["from_state"] = "active"
        valid_notification_data["to_state"] = "active"

        notification = ModelStateTransitionNotification(**valid_notification_data)
        assert notification.from_state == notification.to_state

    def test_projection_version_zero(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that projection_version can be 0."""
        valid_notification_data["projection_version"] = 0

        notification = ModelStateTransitionNotification(**valid_notification_data)
        assert notification.projection_version == 0

    def test_projection_version_large_number(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test that projection_version can be a large number."""
        valid_notification_data["projection_version"] = (
            2**31 - 1
        )  # Max 32-bit signed int

        notification = ModelStateTransitionNotification(**valid_notification_data)
        assert notification.projection_version == 2**31 - 1

    def test_unicode_in_string_fields(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test unicode characters in string fields."""
        valid_notification_data["aggregate_type"] = "registro"
        valid_notification_data["from_state"] = "pendiente"
        valid_notification_data["to_state"] = "activo"

        notification = ModelStateTransitionNotification(**valid_notification_data)
        assert notification.aggregate_type == "registro"
        assert notification.from_state == "pendiente"
        assert notification.to_state == "activo"

    def test_timestamp_with_timezone(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test timestamp with explicit timezone."""
        ts = datetime.now(UTC)
        valid_notification_data["timestamp"] = ts

        notification = ModelStateTransitionNotification(**valid_notification_data)
        assert notification.timestamp == ts

    def test_same_correlation_and_causation_id(
        self, valid_notification_data: dict[str, Any]
    ) -> None:
        """Test when correlation_id equals causation_id (root cause)."""
        same_id = uuid4()
        valid_notification_data["correlation_id"] = same_id
        valid_notification_data["causation_id"] = same_id

        notification = ModelStateTransitionNotification(**valid_notification_data)
        assert notification.correlation_id == notification.causation_id


# ---- Test Model Copy ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestModelCopy:
    """Tests for model_copy functionality."""

    def test_model_copy_creates_new_instance(
        self, valid_notification: ModelStateTransitionNotification
    ) -> None:
        """Test that model_copy creates a new instance."""
        copied = valid_notification.model_copy()

        assert copied is not valid_notification
        assert copied.aggregate_type == valid_notification.aggregate_type
        assert copied.aggregate_id == valid_notification.aggregate_id

    def test_model_copy_with_update(
        self, valid_notification: ModelStateTransitionNotification
    ) -> None:
        """Test model_copy with field updates."""
        new_state = "completed"
        copied = valid_notification.model_copy(update={"to_state": new_state})

        # Original unchanged (frozen model)
        assert valid_notification.to_state != new_state

        # Copied has new value
        assert copied.to_state == new_state

        # Other fields unchanged
        assert copied.aggregate_type == valid_notification.aggregate_type
        assert copied.from_state == valid_notification.from_state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
