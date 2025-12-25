# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for PayloadPersistResult.

This module tests the PayloadPersistResult model for result persistence intents, verifying:
1. Field validation (result_key, result_data, ttl_seconds, metadata)
2. Discriminator value
3. Serialization/deserialization
4. Immutability
5. Default values
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.reducer.payloads import PayloadPersistResult


@pytest.mark.unit
class TestPayloadPersistResultInstantiation:
    """Test PayloadPersistResult instantiation."""

    def test_create_with_required_fields(self) -> None:
        """Test creating payload with required fields only."""
        payload = PayloadPersistResult(
            result_key="compute:transform:batch-001",
            result_data={"records": 1000, "status": "success"},
        )
        assert payload.result_key == "compute:transform:batch-001"
        assert payload.result_data == {"records": 1000, "status": "success"}
        assert payload.intent_type == "persist_result"

    def test_create_with_all_fields(self) -> None:
        """Test creating payload with all fields."""
        payload = PayloadPersistResult(
            result_key="compute:transform:batch-001",
            result_data={"records": 1000},
            ttl_seconds=7200,
            metadata={"compute_ms": 1250, "node_id": "compute-a1b2"},
        )
        assert payload.result_key == "compute:transform:batch-001"
        assert payload.result_data == {"records": 1000}
        assert payload.ttl_seconds == 7200
        assert payload.metadata == {"compute_ms": 1250, "node_id": "compute-a1b2"}


@pytest.mark.unit
class TestPayloadPersistResultDiscriminator:
    """Test discriminator field."""

    def test_intent_type_value(self) -> None:
        """Test that intent_type is 'persist_result'."""
        payload = PayloadPersistResult(result_key="key", result_data={"value": 1})
        assert payload.intent_type == "persist_result"

    def test_intent_type_in_serialization(self) -> None:
        """Test that intent_type is included in serialization."""
        payload = PayloadPersistResult(result_key="key", result_data={"value": 1})
        data = payload.model_dump()
        assert data["intent_type"] == "persist_result"


@pytest.mark.unit
class TestPayloadPersistResultKeyValidation:
    """Test result_key field validation."""

    def test_result_key_required(self) -> None:
        """Test that result_key is required."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadPersistResult(result_data={"value": 1})  # type: ignore[call-arg]
        assert "result_key" in str(exc_info.value)

    def test_result_key_min_length(self) -> None:
        """Test result_key minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadPersistResult(result_key="", result_data={"value": 1})
        assert "result_key" in str(exc_info.value)

    def test_result_key_max_length(self) -> None:
        """Test result_key maximum length validation."""
        long_key = "a" * 513
        with pytest.raises(ValidationError) as exc_info:
            PayloadPersistResult(result_key=long_key, result_data={"value": 1})
        assert "result_key" in str(exc_info.value)


@pytest.mark.unit
class TestPayloadPersistResultDataValidation:
    """Test result_data field validation."""

    def test_result_data_required(self) -> None:
        """Test that result_data is required."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadPersistResult(result_key="key")  # type: ignore[call-arg]
        assert "result_data" in str(exc_info.value)

    def test_result_data_accepts_various_types(self) -> None:
        """Test result_data accepts various value types."""
        payload = PayloadPersistResult(
            result_key="key",
            result_data={
                "string": "value",
                "number": 42,
                "float": 3.14,
                "boolean": True,
                "null": None,
                "list": [1, 2, 3],
                "nested": {"inner": "value"},
            },
        )
        assert payload.result_data["string"] == "value"
        assert payload.result_data["number"] == 42


@pytest.mark.unit
class TestPayloadPersistResultDefaultValues:
    """Test default values."""

    def test_default_ttl_seconds(self) -> None:
        """Test default ttl_seconds is None."""
        payload = PayloadPersistResult(result_key="key", result_data={"value": 1})
        assert payload.ttl_seconds is None

    def test_default_metadata(self) -> None:
        """Test default metadata is empty dict."""
        payload = PayloadPersistResult(result_key="key", result_data={"value": 1})
        assert payload.metadata == {}


@pytest.mark.unit
class TestPayloadPersistResultTTLValidation:
    """Test ttl_seconds field validation."""

    def test_ttl_minimum(self) -> None:
        """Test ttl_seconds minimum value."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadPersistResult(
                result_key="key", result_data={"value": 1}, ttl_seconds=-1
            )
        assert "ttl_seconds" in str(exc_info.value)

    def test_ttl_zero_valid(self) -> None:
        """Test ttl_seconds accepts zero."""
        payload = PayloadPersistResult(
            result_key="key", result_data={"value": 1}, ttl_seconds=0
        )
        assert payload.ttl_seconds == 0

    def test_ttl_positive_valid(self) -> None:
        """Test ttl_seconds accepts positive values."""
        payload = PayloadPersistResult(
            result_key="key", result_data={"value": 1}, ttl_seconds=7200
        )
        assert payload.ttl_seconds == 7200


@pytest.mark.unit
class TestPayloadPersistResultImmutability:
    """Test frozen/immutability."""

    def test_cannot_modify_result_key(self) -> None:
        """Test that result_key cannot be modified after creation."""
        payload = PayloadPersistResult(result_key="key", result_data={"value": 1})
        with pytest.raises(ValidationError):
            payload.result_key = "new_key"  # type: ignore[misc]

    def test_cannot_modify_result_data(self) -> None:
        """Test that result_data cannot be modified after creation."""
        payload = PayloadPersistResult(result_key="key", result_data={"value": 1})
        with pytest.raises(ValidationError):
            payload.result_data = {"value": 2}  # type: ignore[misc]


@pytest.mark.unit
class TestPayloadPersistResultSerialization:
    """Test serialization/deserialization."""

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        original = PayloadPersistResult(
            result_key="compute:batch:001",
            result_data={"records": 100, "processed": True},
            ttl_seconds=3600,
            metadata={"node": "worker-1"},
        )
        data = original.model_dump()
        restored = PayloadPersistResult.model_validate(data)
        assert restored == original

    def test_json_roundtrip(self) -> None:
        """Test JSON roundtrip serialization."""
        original = PayloadPersistResult(result_key="key", result_data={"value": 1})
        json_str = original.model_dump_json()
        restored = PayloadPersistResult.model_validate_json(json_str)
        assert restored == original

    def test_serialization_includes_all_fields(self) -> None:
        """Test that serialization includes all fields."""
        payload = PayloadPersistResult(result_key="key", result_data={"value": 1})
        data = payload.model_dump()
        expected_keys = {
            "intent_type",
            "result_key",
            "result_data",
            "ttl_seconds",
            "metadata",
        }
        assert set(data.keys()) == expected_keys


@pytest.mark.unit
class TestPayloadPersistResultExtraFieldsRejected:
    """Test that extra fields are rejected."""

    def test_reject_extra_field(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadPersistResult(
                result_key="key",
                result_data={"value": 1},
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)
