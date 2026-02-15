"""
Tests for ModelIntentPublishResult.

This module tests the intent publish result model used for coordination I/O.
Validates field types, constraints, serialization, and Pydantic behavior.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.models.reducer.model_intent_publish_result import (
    ModelIntentPublishResult,
)


@pytest.mark.unit
class TestModelIntentPublishResultInstantiation:
    """Test ModelIntentPublishResult instantiation."""

    def test_create_with_all_fields(self):
        """Test creating ModelIntentPublishResult with all required fields."""
        intent_id = uuid4()
        published_at = datetime.now(UTC)
        target_topic = "test.topic"
        correlation_id = uuid4()

        result = ModelIntentPublishResult(
            intent_id=intent_id,
            published_at=published_at,
            target_topic=target_topic,
            correlation_id=correlation_id,
        )

        assert result.intent_id == intent_id
        assert result.published_at == published_at
        assert result.target_topic == target_topic
        assert result.correlation_id == correlation_id

    def test_create_with_uuid_strings(self):
        """Test creating with UUID strings (Pydantic auto-converts)."""
        intent_id_str = str(uuid4())
        correlation_id_str = str(uuid4())
        published_at = datetime.now(UTC)

        result = ModelIntentPublishResult(
            intent_id=intent_id_str,
            published_at=published_at,
            target_topic="test.topic",
            correlation_id=correlation_id_str,
        )

        assert isinstance(result.intent_id, UUID)
        assert isinstance(result.correlation_id, UUID)
        assert str(result.intent_id) == intent_id_str
        assert str(result.correlation_id) == correlation_id_str

    def test_create_with_datetime_string(self):
        """Test creating with datetime string (Pydantic auto-converts)."""
        intent_id = uuid4()
        correlation_id = uuid4()
        published_at_str = "2024-01-15T12:00:00Z"

        result = ModelIntentPublishResult(
            intent_id=intent_id,
            published_at=published_at_str,
            target_topic="test.topic",
            correlation_id=correlation_id,
        )

        assert isinstance(result.published_at, datetime)

    def test_inheritance_from_basemodel(self):
        """Test that ModelIntentPublishResult inherits from BaseModel."""
        result = ModelIntentPublishResult(
            intent_id=uuid4(),
            published_at=datetime.now(UTC),
            target_topic="test.topic",
            correlation_id=uuid4(),
        )

        assert isinstance(result, BaseModel)


@pytest.mark.unit
class TestModelIntentPublishResultFieldValidation:
    """Test field validation and constraints."""

    def test_missing_intent_id_raises_error(self):
        """Test that missing intent_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentPublishResult(
                published_at=datetime.now(UTC),
                target_topic="test.topic",
                correlation_id=uuid4(),
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("intent_id",) for error in errors)
        assert any(error["type"] == "missing" for error in errors)

    def test_missing_published_at_raises_error(self):
        """Test that missing published_at raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentPublishResult(
                intent_id=uuid4(),
                target_topic="test.topic",
                correlation_id=uuid4(),
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("published_at",) for error in errors)

    def test_missing_target_topic_raises_error(self):
        """Test that missing target_topic raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentPublishResult(
                intent_id=uuid4(),
                published_at=datetime.now(UTC),
                correlation_id=uuid4(),
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("target_topic",) for error in errors)

    def test_missing_correlation_id_raises_error(self):
        """Test that missing correlation_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentPublishResult(
                intent_id=uuid4(),
                published_at=datetime.now(UTC),
                target_topic="test.topic",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("correlation_id",) for error in errors)

    def test_invalid_intent_id_type_raises_error(self):
        """Test that invalid intent_id type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentPublishResult(
                intent_id="not-a-uuid",
                published_at=datetime.now(UTC),
                target_topic="test.topic",
                correlation_id=uuid4(),
            )

        errors = exc_info.value.errors()
        assert any("intent_id" in error["loc"] for error in errors)

    def test_invalid_correlation_id_type_raises_error(self):
        """Test that invalid correlation_id type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentPublishResult(
                intent_id=uuid4(),
                published_at=datetime.now(UTC),
                target_topic="test.topic",
                correlation_id="not-a-uuid",
            )

        errors = exc_info.value.errors()
        assert any("correlation_id" in error["loc"] for error in errors)

    def test_invalid_published_at_type_raises_error(self):
        """Test that invalid published_at type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentPublishResult(
                intent_id=uuid4(),
                published_at="invalid-datetime",
                target_topic="test.topic",
                correlation_id=uuid4(),
            )

        errors = exc_info.value.errors()
        assert any("published_at" in error["loc"] for error in errors)

    def test_invalid_target_topic_type_raises_error(self):
        """Test that invalid target_topic type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentPublishResult(
                intent_id=uuid4(),
                published_at=datetime.now(UTC),
                target_topic=12345,  # type: ignore[arg-type]
                correlation_id=uuid4(),
            )

        errors = exc_info.value.errors()
        assert any("target_topic" in error["loc"] for error in errors)

    def test_empty_target_topic_allowed(self):
        """Test that empty string target_topic is allowed."""
        result = ModelIntentPublishResult(
            intent_id=uuid4(),
            published_at=datetime.now(UTC),
            target_topic="",
            correlation_id=uuid4(),
        )

        assert result.target_topic == ""

    def test_none_values_raise_error(self):
        """Test that None values raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelIntentPublishResult(
                intent_id=None,  # type: ignore[arg-type]
                published_at=datetime.now(UTC),
                target_topic="test.topic",
                correlation_id=uuid4(),
            )


@pytest.mark.unit
class TestModelIntentPublishResultSerialization:
    """Test model serialization and deserialization."""

    def test_model_dump(self):
        """Test model_dump() serialization."""
        intent_id = uuid4()
        published_at = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        correlation_id = uuid4()

        result = ModelIntentPublishResult(
            intent_id=intent_id,
            published_at=published_at,
            target_topic="test.topic",
            correlation_id=correlation_id,
        )

        data = result.model_dump()

        assert isinstance(data, dict)
        assert data["intent_id"] == intent_id
        assert data["published_at"] == published_at
        assert data["target_topic"] == "test.topic"
        assert data["correlation_id"] == correlation_id

    def test_model_dump_json(self):
        """Test model_dump_json() serialization."""
        intent_id = uuid4()
        published_at = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        correlation_id = uuid4()

        result = ModelIntentPublishResult(
            intent_id=intent_id,
            published_at=published_at,
            target_topic="test.topic",
            correlation_id=correlation_id,
        )

        json_str = result.model_dump_json()

        assert isinstance(json_str, str)
        assert str(intent_id) in json_str
        assert str(correlation_id) in json_str
        assert "test.topic" in json_str

    def test_model_validate(self):
        """Test model_validate() deserialization."""
        intent_id = uuid4()
        published_at = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        correlation_id = uuid4()

        data = {
            "intent_id": intent_id,
            "published_at": published_at,
            "target_topic": "test.topic",
            "correlation_id": correlation_id,
        }

        result = ModelIntentPublishResult.model_validate(data)

        assert result.intent_id == intent_id
        assert result.published_at == published_at
        assert result.target_topic == "test.topic"
        assert result.correlation_id == correlation_id

    def test_model_validate_json(self):
        """Test model_validate_json() deserialization."""
        intent_id = uuid4()
        published_at = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        correlation_id = uuid4()

        result = ModelIntentPublishResult(
            intent_id=intent_id,
            published_at=published_at,
            target_topic="test.topic",
            correlation_id=correlation_id,
        )

        json_str = result.model_dump_json()
        restored = ModelIntentPublishResult.model_validate_json(json_str)

        assert restored.intent_id == intent_id
        assert restored.target_topic == "test.topic"
        assert restored.correlation_id == correlation_id

    def test_serialization_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        original = ModelIntentPublishResult(
            intent_id=uuid4(),
            published_at=datetime.now(UTC),
            target_topic="roundtrip.topic",
            correlation_id=uuid4(),
        )

        # Serialize and deserialize
        data = original.model_dump()
        restored = ModelIntentPublishResult.model_validate(data)

        assert restored.intent_id == original.intent_id
        assert restored.published_at == original.published_at
        assert restored.target_topic == original.target_topic
        assert restored.correlation_id == original.correlation_id

    def test_json_serialization_roundtrip(self):
        """Test JSON serialization and deserialization roundtrip."""
        original = ModelIntentPublishResult(
            intent_id=uuid4(),
            published_at=datetime.now(UTC),
            target_topic="json.roundtrip.topic",
            correlation_id=uuid4(),
        )

        json_str = original.model_dump_json()
        restored = ModelIntentPublishResult.model_validate_json(json_str)

        assert restored.intent_id == original.intent_id
        assert restored.target_topic == original.target_topic
        assert restored.correlation_id == original.correlation_id


@pytest.mark.unit
class TestModelIntentPublishResultEquality:
    """Test equality and comparison operations."""

    def test_equality_same_values(self):
        """Test that models with same values are equal."""
        intent_id = uuid4()
        published_at = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        correlation_id = uuid4()

        result1 = ModelIntentPublishResult(
            intent_id=intent_id,
            published_at=published_at,
            target_topic="test.topic",
            correlation_id=correlation_id,
        )

        result2 = ModelIntentPublishResult(
            intent_id=intent_id,
            published_at=published_at,
            target_topic="test.topic",
            correlation_id=correlation_id,
        )

        assert result1 == result2

    def test_inequality_different_intent_id(self):
        """Test that models with different intent_id are not equal."""
        published_at = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        correlation_id = uuid4()

        result1 = ModelIntentPublishResult(
            intent_id=uuid4(),
            published_at=published_at,
            target_topic="test.topic",
            correlation_id=correlation_id,
        )

        result2 = ModelIntentPublishResult(
            intent_id=uuid4(),
            published_at=published_at,
            target_topic="test.topic",
            correlation_id=correlation_id,
        )

        assert result1 != result2

    def test_inequality_different_correlation_id(self):
        """Test that models with different correlation_id are not equal."""
        intent_id = uuid4()
        published_at = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        result1 = ModelIntentPublishResult(
            intent_id=intent_id,
            published_at=published_at,
            target_topic="test.topic",
            correlation_id=uuid4(),
        )

        result2 = ModelIntentPublishResult(
            intent_id=intent_id,
            published_at=published_at,
            target_topic="test.topic",
            correlation_id=uuid4(),
        )

        assert result1 != result2

    def test_inequality_different_topic(self):
        """Test that models with different target_topic are not equal."""
        intent_id = uuid4()
        published_at = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        correlation_id = uuid4()

        result1 = ModelIntentPublishResult(
            intent_id=intent_id,
            published_at=published_at,
            target_topic="topic1",
            correlation_id=correlation_id,
        )

        result2 = ModelIntentPublishResult(
            intent_id=intent_id,
            published_at=published_at,
            target_topic="topic2",
            correlation_id=correlation_id,
        )

        assert result1 != result2

    def test_inequality_different_published_at(self):
        """Test that models with different published_at are not equal."""
        intent_id = uuid4()
        correlation_id = uuid4()

        result1 = ModelIntentPublishResult(
            intent_id=intent_id,
            published_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
            target_topic="test.topic",
            correlation_id=correlation_id,
        )

        result2 = ModelIntentPublishResult(
            intent_id=intent_id,
            published_at=datetime(2024, 1, 16, 12, 0, 0, tzinfo=UTC),
            target_topic="test.topic",
            correlation_id=correlation_id,
        )

        assert result1 != result2


@pytest.mark.unit
class TestModelIntentPublishResultCopy:
    """Test model copying operations."""

    def test_model_copy(self):
        """Test model_copy() creates independent copy."""
        original = ModelIntentPublishResult(
            intent_id=uuid4(),
            published_at=datetime.now(UTC),
            target_topic="test.topic",
            correlation_id=uuid4(),
        )

        copied = original.model_copy()

        assert copied == original
        assert copied is not original
        assert copied.intent_id == original.intent_id
        assert copied.published_at == original.published_at
        assert copied.target_topic == original.target_topic
        assert copied.correlation_id == original.correlation_id

    def test_model_copy_with_update(self):
        """Test model_copy() with update."""
        original = ModelIntentPublishResult(
            intent_id=uuid4(),
            published_at=datetime.now(UTC),
            target_topic="original.topic",
            correlation_id=uuid4(),
        )

        updated = original.model_copy(update={"target_topic": "updated.topic"})

        assert updated.intent_id == original.intent_id
        assert updated.target_topic == "updated.topic"
        assert updated.target_topic != original.target_topic


@pytest.mark.unit
class TestModelIntentPublishResultRepresentation:
    """Test string representations."""

    def test_str_representation(self):
        """Test __str__ representation."""
        result = ModelIntentPublishResult(
            intent_id=uuid4(),
            published_at=datetime.now(UTC),
            target_topic="test.topic",
            correlation_id=uuid4(),
        )

        str_repr = str(result)
        assert isinstance(str_repr, str)
        assert len(str_repr) > 0

    def test_repr_representation(self):
        """Test __repr__ representation."""
        result = ModelIntentPublishResult(
            intent_id=uuid4(),
            published_at=datetime.now(UTC),
            target_topic="test.topic",
            correlation_id=uuid4(),
        )

        repr_str = repr(result)
        assert isinstance(repr_str, str)
        assert "ModelIntentPublishResult" in repr_str


@pytest.mark.unit
class TestModelIntentPublishResultMetadata:
    """Test model metadata and configuration."""

    def test_model_fields(self):
        """Test that model_fields contains all expected fields."""
        result = ModelIntentPublishResult(
            intent_id=uuid4(),
            published_at=datetime.now(UTC),
            target_topic="test.topic",
            correlation_id=uuid4(),
        )

        fields = result.model_fields
        assert "intent_id" in fields
        assert "published_at" in fields
        assert "target_topic" in fields
        assert "correlation_id" in fields

    def test_model_fields_required(self):
        """Test that all fields are required."""
        fields = ModelIntentPublishResult.model_fields

        assert fields["intent_id"].is_required()
        assert fields["published_at"].is_required()
        assert fields["target_topic"].is_required()
        assert fields["correlation_id"].is_required()

    def test_class_name(self):
        """Test class name."""
        assert ModelIntentPublishResult.__name__ == "ModelIntentPublishResult"

    def test_module_name(self):
        """Test module name."""
        assert (
            ModelIntentPublishResult.__module__
            == "omnibase_core.models.reducer.model_intent_publish_result"
        )

    def test_docstring(self):
        """Test that model has docstring."""
        assert ModelIntentPublishResult.__doc__ is not None
        assert "Result of publishing an intent" in ModelIntentPublishResult.__doc__

    def test_field_descriptions(self):
        """Test that fields have descriptions."""
        fields = ModelIntentPublishResult.model_fields

        assert fields["intent_id"].description is not None
        assert fields["published_at"].description is not None
        assert fields["target_topic"].description is not None
        assert fields["correlation_id"].description is not None


@pytest.mark.unit
class TestModelIntentPublishResultEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_topic_name(self):
        """Test with very long topic name."""
        long_topic = "a" * 10000

        result = ModelIntentPublishResult(
            intent_id=uuid4(),
            published_at=datetime.now(UTC),
            target_topic=long_topic,
            correlation_id=uuid4(),
        )

        assert result.target_topic == long_topic
        assert len(result.target_topic) == 10000

    def test_topic_with_special_characters(self):
        """Test topic with special characters."""
        special_topic = "test.topic-with_special/chars@123!#"

        result = ModelIntentPublishResult(
            intent_id=uuid4(),
            published_at=datetime.now(UTC),
            target_topic=special_topic,
            correlation_id=uuid4(),
        )

        assert result.target_topic == special_topic

    def test_past_published_at(self):
        """Test with past datetime."""
        past_date = datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)

        result = ModelIntentPublishResult(
            intent_id=uuid4(),
            published_at=past_date,
            target_topic="test.topic",
            correlation_id=uuid4(),
        )

        assert result.published_at == past_date

    def test_future_published_at(self):
        """Test with future datetime."""
        future_date = datetime(2030, 12, 31, 23, 59, 59, tzinfo=UTC)

        result = ModelIntentPublishResult(
            intent_id=uuid4(),
            published_at=future_date,
            target_topic="test.topic",
            correlation_id=uuid4(),
        )

        assert result.published_at == future_date

    def test_same_intent_and_correlation_id(self):
        """Test when intent_id and correlation_id are the same."""
        same_id = uuid4()

        result = ModelIntentPublishResult(
            intent_id=same_id,
            published_at=datetime.now(UTC),
            target_topic="test.topic",
            correlation_id=same_id,
        )

        assert result.intent_id == result.correlation_id
        assert result.intent_id == same_id

    def test_extra_fields_forbidden(self):
        """Test that extra fields raise ValidationError (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentPublishResult(
                intent_id=uuid4(),
                published_at=datetime.now(UTC),
                target_topic="test.topic",
                correlation_id=uuid4(),
                extra_field="forbidden",  # type: ignore[call-arg]
            )

        errors = exc_info.value.errors()
        assert any(error["type"] == "extra_forbidden" for error in errors)


@pytest.mark.unit
class TestModelIntentPublishResultAttributes:
    """Test model attributes and methods."""

    def test_has_required_methods(self):
        """Test that model has required Pydantic methods."""
        assert hasattr(ModelIntentPublishResult, "model_validate")
        assert hasattr(ModelIntentPublishResult, "model_validate_json")
        assert callable(ModelIntentPublishResult.model_validate)
        assert callable(ModelIntentPublishResult.model_validate_json)

    def test_instance_has_required_methods(self):
        """Test that instance has required methods."""
        result = ModelIntentPublishResult(
            intent_id=uuid4(),
            published_at=datetime.now(UTC),
            target_topic="test.topic",
            correlation_id=uuid4(),
        )

        assert hasattr(result, "model_dump")
        assert hasattr(result, "model_dump_json")
        assert hasattr(result, "model_copy")
        assert callable(result.model_dump)
        assert callable(result.model_dump_json)
        assert callable(result.model_copy)
