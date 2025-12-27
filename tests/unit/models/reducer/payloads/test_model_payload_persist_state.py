# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for ModelPayloadPersistState.

This module tests the ModelPayloadPersistState model for state persistence intents, verifying:
1. Field validation (state_key, state_data, ttl_seconds, version)
2. Discriminator value
3. Serialization/deserialization
4. Immutability
5. Default values
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.reducer.payloads import ModelPayloadPersistState


@pytest.mark.unit
class TestModelPayloadPersistStateInstantiation:
    """Test ModelPayloadPersistState instantiation."""

    def test_create_with_required_fields(self) -> None:
        """Test creating payload with required fields only."""
        payload = ModelPayloadPersistState(
            state_key="fsm:order:123:state",
            state_data={"status": "pending"},
        )
        assert payload.state_key == "fsm:order:123:state"
        assert payload.state_data == {"status": "pending"}
        assert payload.intent_type == "persist_state"

    def test_create_with_all_fields(self) -> None:
        """Test creating payload with all fields."""
        payload = ModelPayloadPersistState(
            state_key="fsm:order:123:state",
            state_data={"status": "pending", "items": ["a", "b"]},
            ttl_seconds=86400,
            version=5,
        )
        assert payload.state_key == "fsm:order:123:state"
        assert payload.state_data == {"status": "pending", "items": ["a", "b"]}
        assert payload.ttl_seconds == 86400
        assert payload.version == 5


@pytest.mark.unit
class TestModelPayloadPersistStateDiscriminator:
    """Test discriminator field."""

    def test_intent_type_value(self) -> None:
        """Test that intent_type is 'persist_state'."""
        payload = ModelPayloadPersistState(
            state_key="key", state_data={"status": "active"}
        )
        assert payload.intent_type == "persist_state"

    def test_intent_type_in_serialization(self) -> None:
        """Test that intent_type is included in serialization."""
        payload = ModelPayloadPersistState(
            state_key="key", state_data={"status": "active"}
        )
        data = payload.model_dump()
        assert data["intent_type"] == "persist_state"


@pytest.mark.unit
class TestModelPayloadPersistStateKeyValidation:
    """Test state_key field validation."""

    def test_state_key_required(self) -> None:
        """Test that state_key is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadPersistState(state_data={"status": "active"})  # type: ignore[call-arg]
        assert "state_key" in str(exc_info.value)

    def test_state_key_min_length(self) -> None:
        """Test state_key minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadPersistState(state_key="", state_data={"status": "active"})
        assert "state_key" in str(exc_info.value)

    def test_state_key_max_length(self) -> None:
        """Test state_key maximum length validation."""
        long_key = "a" * 513
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadPersistState(
                state_key=long_key, state_data={"status": "active"}
            )
        assert "state_key" in str(exc_info.value)


@pytest.mark.unit
class TestModelPayloadPersistStateDataValidation:
    """Test state_data field validation."""

    def test_state_data_required(self) -> None:
        """Test that state_data is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadPersistState(state_key="key")  # type: ignore[call-arg]
        assert "state_data" in str(exc_info.value)

    def test_state_data_accepts_various_types(self) -> None:
        """Test state_data accepts various value types."""
        payload = ModelPayloadPersistState(
            state_key="key",
            state_data={
                "string": "value",
                "number": 42,
                "float": 3.14,
                "boolean": True,
                "null": None,
                "list": [1, 2, 3],
                "nested": {"inner": "value"},
            },
        )
        assert payload.state_data["string"] == "value"
        assert payload.state_data["number"] == 42
        assert payload.state_data["list"] == [1, 2, 3]


@pytest.mark.unit
class TestModelPayloadPersistStateDefaultValues:
    """Test default values."""

    def test_default_ttl_seconds(self) -> None:
        """Test default ttl_seconds is None."""
        payload = ModelPayloadPersistState(
            state_key="key", state_data={"status": "active"}
        )
        assert payload.ttl_seconds is None

    def test_default_version(self) -> None:
        """Test default version is None."""
        payload = ModelPayloadPersistState(
            state_key="key", state_data={"status": "active"}
        )
        assert payload.version is None


@pytest.mark.unit
class TestModelPayloadPersistStateTTLValidation:
    """Test ttl_seconds field validation."""

    def test_ttl_minimum(self) -> None:
        """Test ttl_seconds minimum value."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadPersistState(
                state_key="key", state_data={"status": "active"}, ttl_seconds=-1
            )
        assert "ttl_seconds" in str(exc_info.value)

    def test_ttl_zero_valid(self) -> None:
        """Test ttl_seconds accepts zero."""
        payload = ModelPayloadPersistState(
            state_key="key", state_data={"status": "active"}, ttl_seconds=0
        )
        assert payload.ttl_seconds == 0

    def test_ttl_positive_valid(self) -> None:
        """Test ttl_seconds accepts positive values."""
        payload = ModelPayloadPersistState(
            state_key="key", state_data={"status": "active"}, ttl_seconds=86400
        )
        assert payload.ttl_seconds == 86400


@pytest.mark.unit
class TestModelPayloadPersistStateVersionValidation:
    """Test version field validation."""

    def test_version_minimum(self) -> None:
        """Test version minimum value."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadPersistState(
                state_key="key", state_data={"status": "active"}, version=-1
            )
        assert "version" in str(exc_info.value)

    def test_version_zero_valid(self) -> None:
        """Test version accepts zero."""
        payload = ModelPayloadPersistState(
            state_key="key", state_data={"status": "active"}, version=0
        )
        assert payload.version == 0

    def test_version_positive_valid(self) -> None:
        """Test version accepts positive values."""
        payload = ModelPayloadPersistState(
            state_key="key", state_data={"status": "active"}, version=10
        )
        assert payload.version == 10


@pytest.mark.unit
class TestModelPayloadPersistStateImmutability:
    """Test frozen/immutability."""

    def test_cannot_modify_state_key(self) -> None:
        """Test that state_key cannot be modified after creation."""
        payload = ModelPayloadPersistState(
            state_key="key", state_data={"status": "active"}
        )
        with pytest.raises(ValidationError):
            payload.state_key = "new_key"  # type: ignore[misc]

    def test_cannot_modify_state_data(self) -> None:
        """Test that state_data cannot be modified after creation."""
        payload = ModelPayloadPersistState(
            state_key="key", state_data={"status": "active"}
        )
        with pytest.raises(ValidationError):
            payload.state_data = {"status": "new"}  # type: ignore[misc]


@pytest.mark.unit
class TestModelPayloadPersistStateSerialization:
    """Test serialization/deserialization."""

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        original = ModelPayloadPersistState(
            state_key="fsm:order:123",
            state_data={"status": "pending", "count": 5},
            ttl_seconds=3600,
            version=2,
        )
        data = original.model_dump()
        restored = ModelPayloadPersistState.model_validate(data)
        assert restored == original

    def test_json_roundtrip(self) -> None:
        """Test JSON roundtrip serialization."""
        original = ModelPayloadPersistState(
            state_key="key", state_data={"status": "active"}
        )
        json_str = original.model_dump_json()
        restored = ModelPayloadPersistState.model_validate_json(json_str)
        assert restored == original

    def test_serialization_includes_all_fields(self) -> None:
        """Test that serialization includes all fields."""
        payload = ModelPayloadPersistState(
            state_key="key", state_data={"status": "active"}
        )
        data = payload.model_dump()
        expected_keys = {
            "intent_type",
            "state_key",
            "state_data",
            "ttl_seconds",
            "version",
        }
        assert set(data.keys()) == expected_keys


@pytest.mark.unit
class TestModelPayloadPersistStateExtraFieldsRejected:
    """Test that extra fields are rejected."""

    def test_reject_extra_field(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadPersistState(
                state_key="key",
                state_data={"status": "active"},
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)
