# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelReplayInput.

Tests cover:
- Model immutability (frozen)
- Default UUID generation for input_id
- Generic type preservation
- has_overrides property logic
- Immutable update pattern (with_overrides method)
- Serialization roundtrip (JSON export/import)

.. versionadded:: 0.4.0
    Added as part of Configuration Override Injection (OMN-1205)
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.replay import ModelConfigOverride, ModelConfigOverrideSet
from omnibase_core.models.replay.model_replay_input import ModelReplayInput


@pytest.fixture
def sample_data() -> dict[str, Any]:
    """Create sample input data."""
    return {
        "event_type": "user.created",
        "payload": {"user_id": 123, "email": "test@example.com"},
        "timestamp": "2024-06-15T12:30:45Z",
    }


@pytest.fixture
def simple_override() -> ModelConfigOverride:
    """Create a simple config override."""
    return ModelConfigOverride(path="test.path", value=42)


@pytest.fixture
def override_set(simple_override: ModelConfigOverride) -> ModelConfigOverrideSet:
    """Create an override set with one override."""
    return ModelConfigOverrideSet(overrides=(simple_override,))


@pytest.fixture
def replay_input_with_data(
    sample_data: dict[str, Any],
) -> ModelReplayInput[dict[str, Any]]:
    """Create a replay input with data only."""
    return ModelReplayInput(data=sample_data)


@pytest.fixture
def replay_input_with_overrides(
    sample_data: dict[str, Any],
    override_set: ModelConfigOverrideSet,
) -> ModelReplayInput[dict[str, Any]]:
    """Create a replay input with data and overrides."""
    return ModelReplayInput(data=sample_data, config_overrides=override_set)


@pytest.mark.unit
class TestModelReplayInputCreation:
    """Test ModelReplayInput creation and defaults."""

    def test_create_with_data_only(self, sample_data: dict[str, Any]) -> None:
        """Can create with just data."""
        replay_input = ModelReplayInput(data=sample_data)

        assert replay_input.data == sample_data
        assert replay_input.config_overrides is None

    def test_default_input_id_generated(self, sample_data: dict[str, Any]) -> None:
        """Test that input_id is auto-generated as UUID."""
        replay_input = ModelReplayInput(data=sample_data)

        assert replay_input.input_id is not None
        assert isinstance(replay_input.input_id, UUID)

    def test_unique_input_ids_for_different_instances(
        self, sample_data: dict[str, Any]
    ) -> None:
        """Test that each instance gets a unique input_id."""
        input1 = ModelReplayInput(data=sample_data)
        input2 = ModelReplayInput(data=sample_data)

        assert input1.input_id != input2.input_id

    def test_create_with_explicit_input_id(self, sample_data: dict[str, Any]) -> None:
        """Can create with explicit input_id."""
        explicit_id = UUID("12345678-1234-5678-1234-567812345678")
        replay_input = ModelReplayInput(data=sample_data, input_id=explicit_id)

        assert replay_input.input_id == explicit_id

    def test_create_with_overrides(
        self,
        sample_data: dict[str, Any],
        override_set: ModelConfigOverrideSet,
    ) -> None:
        """Can create with config overrides."""
        replay_input = ModelReplayInput(
            data=sample_data,
            config_overrides=override_set,
        )

        assert replay_input.config_overrides is not None
        assert len(replay_input.config_overrides.overrides) == 1


@pytest.mark.unit
class TestModelReplayInputImmutability:
    """Test ModelReplayInput immutability characteristics."""

    def test_model_is_frozen(
        self, replay_input_with_data: ModelReplayInput[dict[str, Any]]
    ) -> None:
        """Test that ModelReplayInput is frozen (immutable)."""
        with pytest.raises(ValidationError):
            replay_input_with_data.data = {"new": "data"}

    def test_cannot_modify_input_id(
        self, replay_input_with_data: ModelReplayInput[dict[str, Any]]
    ) -> None:
        """Test that input_id field cannot be reassigned."""
        with pytest.raises(ValidationError):
            replay_input_with_data.input_id = uuid4()

    def test_cannot_modify_config_overrides(
        self,
        replay_input_with_overrides: ModelReplayInput[dict[str, Any]],
        override_set: ModelConfigOverrideSet,
    ) -> None:
        """Test that config_overrides field cannot be reassigned."""
        with pytest.raises(ValidationError):
            replay_input_with_overrides.config_overrides = override_set


@pytest.mark.unit
class TestModelReplayInputValidation:
    """Test ModelReplayInput field validation."""

    def test_data_required(self) -> None:
        """Test that data is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReplayInput()  # type: ignore[call-arg]

        assert "data" in str(exc_info.value)

    def test_extra_fields_forbidden(self, sample_data: dict[str, Any]) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReplayInput(
                data=sample_data,
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower() or "unknown_field" in str(
            exc_info.value
        )


@pytest.mark.unit
class TestModelReplayInputHasOverrides:
    """Test ModelReplayInput.has_overrides property."""

    def test_has_overrides_false_when_none(
        self, replay_input_with_data: ModelReplayInput[dict[str, Any]]
    ) -> None:
        """has_overrides is False when config_overrides is None."""
        assert replay_input_with_data.has_overrides is False

    def test_has_overrides_false_when_empty(self, sample_data: dict[str, Any]) -> None:
        """has_overrides is False when empty override set."""
        replay_input = ModelReplayInput(
            data=sample_data,
            config_overrides=ModelConfigOverrideSet(),
        )
        assert replay_input.has_overrides is False

    def test_has_overrides_true_when_present(
        self,
        replay_input_with_overrides: ModelReplayInput[dict[str, Any]],
    ) -> None:
        """has_overrides is True when overrides present."""
        assert replay_input_with_overrides.has_overrides is True


@pytest.mark.unit
class TestModelReplayInputWithOverrides:
    """Test ModelReplayInput.with_overrides method."""

    def test_with_overrides_returns_new_instance(
        self,
        replay_input_with_data: ModelReplayInput[dict[str, Any]],
        override_set: ModelConfigOverrideSet,
    ) -> None:
        """with_overrides returns new instance (immutable update)."""
        updated = replay_input_with_data.with_overrides(override_set)

        assert replay_input_with_data.config_overrides is None  # Original unchanged
        assert updated.config_overrides is not None
        assert updated is not replay_input_with_data

    def test_with_overrides_preserves_input_id(
        self,
        replay_input_with_data: ModelReplayInput[dict[str, Any]],
        override_set: ModelConfigOverrideSet,
    ) -> None:
        """with_overrides preserves the input_id."""
        updated = replay_input_with_data.with_overrides(override_set)

        assert updated.input_id == replay_input_with_data.input_id

    def test_with_overrides_preserves_data(
        self,
        replay_input_with_data: ModelReplayInput[dict[str, Any]],
        override_set: ModelConfigOverrideSet,
        sample_data: dict[str, Any],
    ) -> None:
        """with_overrides preserves the original data."""
        updated = replay_input_with_data.with_overrides(override_set)

        assert updated.data == sample_data

    def test_with_overrides_replaces_existing(
        self,
        replay_input_with_overrides: ModelReplayInput[dict[str, Any]],
    ) -> None:
        """with_overrides replaces existing overrides."""
        new_override = ModelConfigOverride(path="new.path", value="new_value")
        new_set = ModelConfigOverrideSet(overrides=(new_override,))

        updated = replay_input_with_overrides.with_overrides(new_set)

        assert updated.config_overrides is not None
        assert len(updated.config_overrides.overrides) == 1
        assert updated.config_overrides.overrides[0].path == "new.path"


@pytest.mark.unit
class TestModelReplayInputGenericType:
    """Test ModelReplayInput generic type behavior."""

    def test_generic_type_with_dict(self) -> None:
        """Generic type is preserved with dict."""
        data_dict: dict[str, int] = {"count": 42, "total": 100}
        replay_input: ModelReplayInput[dict[str, int]] = ModelReplayInput(
            data=data_dict
        )
        assert replay_input.data["count"] == 42
        assert replay_input.data["total"] == 100

    def test_generic_type_with_list(self) -> None:
        """Generic type works with list data."""
        data_list = [1, 2, 3, 4, 5]
        replay_input: ModelReplayInput[list[int]] = ModelReplayInput(data=data_list)
        assert replay_input.data == [1, 2, 3, 4, 5]

    def test_generic_type_with_string(self) -> None:
        """Generic type works with string data."""
        data_str = "simple string data"
        replay_input: ModelReplayInput[str] = ModelReplayInput(data=data_str)
        assert replay_input.data == "simple string data"

    def test_generic_type_with_nested_structure(self) -> None:
        """Generic type works with complex nested data."""
        nested_data: dict[str, list[dict[str, int]]] = {
            "items": [{"a": 1}, {"b": 2}],
        }
        replay_input: ModelReplayInput[dict[str, list[dict[str, int]]]] = (
            ModelReplayInput(data=nested_data)
        )
        assert replay_input.data["items"][0]["a"] == 1


@pytest.mark.unit
class TestModelReplayInputSerialization:
    """Test ModelReplayInput serialization and deserialization."""

    def test_serialization_roundtrip_without_overrides(
        self, replay_input_with_data: ModelReplayInput[dict[str, Any]]
    ) -> None:
        """Test that model can be serialized and deserialized without overrides."""
        # Serialize to dict
        data = replay_input_with_data.model_dump()

        # Deserialize back
        restored = ModelReplayInput.model_validate(data)

        assert restored.input_id == replay_input_with_data.input_id
        assert restored.data == replay_input_with_data.data
        assert restored.config_overrides is None

    def test_serialization_roundtrip_with_overrides(
        self, replay_input_with_overrides: ModelReplayInput[dict[str, Any]]
    ) -> None:
        """Test that model can be serialized and deserialized with overrides."""
        # Serialize to dict
        data = replay_input_with_overrides.model_dump()

        # Deserialize back
        restored = ModelReplayInput.model_validate(data)

        assert restored.input_id == replay_input_with_overrides.input_id
        assert restored.data == replay_input_with_overrides.data
        assert restored.config_overrides is not None
        assert len(restored.config_overrides.overrides) == len(
            replay_input_with_overrides.config_overrides.overrides
        )  # type: ignore[union-attr]

    def test_json_serialization_roundtrip(
        self, replay_input_with_overrides: ModelReplayInput[dict[str, Any]]
    ) -> None:
        """Test that model can be serialized to JSON and back."""
        # Serialize to JSON
        json_str = replay_input_with_overrides.model_dump_json()

        # Deserialize back
        restored = ModelReplayInput.model_validate_json(json_str)

        assert restored.input_id == replay_input_with_overrides.input_id
        assert restored.data == replay_input_with_overrides.data

    def test_serialized_input_id_is_string(
        self, replay_input_with_data: ModelReplayInput[dict[str, Any]]
    ) -> None:
        """Test that input_id serializes to string in JSON."""
        json_str = replay_input_with_data.model_dump_json()
        data = json.loads(json_str)

        assert isinstance(data["input_id"], str)
