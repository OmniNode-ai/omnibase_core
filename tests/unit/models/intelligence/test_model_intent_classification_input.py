# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelIntentClassificationInput.

Tests comprehensive intent classification input functionality including:
- Model instantiation with minimal and full fields
- Immutability (frozen model)
- Extra fields rejection
- Content min_length validation
- correlation_id UUID handling
- Context default factory behavior
- Serialization and deserialization
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.models.intelligence.model_intent_classification_input import (
    ModelIntentClassificationInput,
    TypedDictConversationMessage,
    TypedDictIntentContext,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def minimal_input_data() -> dict:
    """Minimal required data for creating an input model."""
    return {
        "content": "I want to cancel my subscription",
    }


@pytest.fixture
def full_input_data() -> dict:
    """Complete data including all fields."""
    context: TypedDictIntentContext = {
        "user_id": "user-123",
        "session_id": "session-456",
        "request_id": "request-789",
        "previous_intents": ["greeting", "inquiry"],
        "language": "en",
        "domain": "customer_support",
        "conversation_history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"},
        ],
        "custom_labels": ["cancellation", "billing", "support"],
        "confidence_threshold": 0.7,
        "max_intents": 5,
        "include_confidence_scores": True,
        "source_system": "web-chat",
        "timestamp_utc": "2025-01-01T12:00:00Z",
    }
    return {
        "content": "I want to cancel my subscription",
        "correlation_id": uuid4(),
        "context": context,
    }


# ============================================================================
# Test: Model Instantiation
# ============================================================================


class TestModelIntentClassificationInputInstantiation:
    """Tests for model instantiation and basic functionality."""

    def test_create_with_minimal_data(self, minimal_input_data: dict) -> None:
        """Test creating input with only required fields."""
        model = ModelIntentClassificationInput(**minimal_input_data)

        assert model.content == "I want to cancel my subscription"
        assert model.correlation_id is None
        assert model.context == {}

    def test_create_with_full_data(self, full_input_data: dict) -> None:
        """Test creating input with all fields explicitly set."""
        model = ModelIntentClassificationInput(**full_input_data)

        assert model.content == "I want to cancel my subscription"
        assert model.correlation_id == full_input_data["correlation_id"]
        assert model.context["user_id"] == "user-123"
        assert model.context["language"] == "en"
        assert model.context["domain"] == "customer_support"
        assert len(model.context["conversation_history"]) == 2

    def test_correlation_id_as_uuid(self, minimal_input_data: dict) -> None:
        """Test that correlation_id accepts UUID objects."""
        test_uuid = uuid4()
        minimal_input_data["correlation_id"] = test_uuid

        model = ModelIntentClassificationInput(**minimal_input_data)
        assert model.correlation_id == test_uuid
        assert isinstance(model.correlation_id, UUID)

    def test_correlation_id_from_string(self, minimal_input_data: dict) -> None:
        """Test that correlation_id accepts UUID strings."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        minimal_input_data["correlation_id"] = uuid_str

        model = ModelIntentClassificationInput(**minimal_input_data)
        assert isinstance(model.correlation_id, UUID)
        assert str(model.correlation_id) == uuid_str

    def test_context_default_factory(self) -> None:
        """Test that context uses default_factory for empty dict."""
        model1 = ModelIntentClassificationInput(content="First request")
        model2 = ModelIntentClassificationInput(content="Second request")

        # Verify both have empty dicts but are different instances
        assert model1.context == {}
        assert model2.context == {}

    def test_context_with_partial_fields(self, minimal_input_data: dict) -> None:
        """Test context with only some fields set (total=False)."""
        partial_context: TypedDictIntentContext = {
            "language": "es",
            "domain": "sales",
        }
        minimal_input_data["context"] = partial_context

        model = ModelIntentClassificationInput(**minimal_input_data)
        assert model.context["language"] == "es"
        assert model.context["domain"] == "sales"
        assert "user_id" not in model.context


# ============================================================================
# Test: Immutability (Frozen Model)
# ============================================================================


class TestModelIntentClassificationInputImmutability:
    """Tests for frozen model behavior."""

    def test_model_is_frozen(self, minimal_input_data: dict) -> None:
        """Test that the model is immutable."""
        model = ModelIntentClassificationInput(**minimal_input_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - Pydantic raises at runtime
            model.content = "Modified content"

    def test_cannot_modify_correlation_id(self, full_input_data: dict) -> None:
        """Test that correlation_id cannot be modified."""
        model = ModelIntentClassificationInput(**full_input_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - Pydantic raises at runtime
            model.correlation_id = uuid4()

    def test_cannot_modify_context(self, full_input_data: dict) -> None:
        """Test that context cannot be reassigned."""
        model = ModelIntentClassificationInput(**full_input_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - Pydantic raises at runtime
            model.context = {}


# ============================================================================
# Test: Content Validation
# ============================================================================


class TestModelIntentClassificationInputContentValidation:
    """Tests for content field validation."""

    def test_content_min_length_of_one(self) -> None:
        """Test that content requires at least 1 character."""
        model = ModelIntentClassificationInput(content="a")
        assert model.content == "a"

    def test_empty_content_rejected(self) -> None:
        """Test that empty content string is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentClassificationInput(content="")

        assert "content" in str(exc_info.value)

    def test_missing_content_rejected(self) -> None:
        """Test that missing content raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentClassificationInput()  # type: ignore[call-arg]

        assert "content" in str(exc_info.value)

    def test_whitespace_only_content_accepted(self) -> None:
        """Test that whitespace-only content is accepted (min_length=1)."""
        model = ModelIntentClassificationInput(content=" ")
        assert model.content == " "

    def test_long_content_accepted(self) -> None:
        """Test that very long content is accepted."""
        long_content = "A" * 10000
        model = ModelIntentClassificationInput(content=long_content)
        assert len(model.content) == 10000

    def test_unicode_content_accepted(self) -> None:
        """Test that unicode content is accepted."""
        unicode_content = "Quiero cancelar mi subscripcion"
        model = ModelIntentClassificationInput(content=unicode_content)
        assert "cancelar" in model.content


# ============================================================================
# Test: Correlation ID Validation
# ============================================================================


class TestModelIntentClassificationInputCorrelationIdValidation:
    """Tests for correlation_id field validation."""

    def test_correlation_id_none_accepted(self, minimal_input_data: dict) -> None:
        """Test that None correlation_id is accepted."""
        model = ModelIntentClassificationInput(**minimal_input_data)
        assert model.correlation_id is None

    def test_invalid_uuid_string_rejected(self, minimal_input_data: dict) -> None:
        """Test that invalid UUID string is rejected."""
        minimal_input_data["correlation_id"] = "not-a-valid-uuid"

        with pytest.raises(ValidationError) as exc_info:
            ModelIntentClassificationInput(**minimal_input_data)

        assert "correlation_id" in str(exc_info.value)

    def test_valid_uuid_formats(self, minimal_input_data: dict) -> None:
        """Test various valid UUID formats."""
        valid_uuids = [
            uuid4(),
            "550e8400-e29b-41d4-a716-446655440000",
            UUID("550e8400-e29b-41d4-a716-446655440000"),
        ]

        for uuid_val in valid_uuids:
            minimal_input_data["correlation_id"] = uuid_val
            model = ModelIntentClassificationInput(**minimal_input_data)
            assert isinstance(model.correlation_id, UUID)


# ============================================================================
# Test: Extra Fields Rejection
# ============================================================================


class TestModelIntentClassificationInputExtraFields:
    """Tests for extra fields rejection."""

    def test_extra_fields_forbidden(self, minimal_input_data: dict) -> None:
        """Test that extra fields are forbidden."""
        minimal_input_data["extra_field"] = "not_allowed"

        with pytest.raises(ValidationError) as exc_info:
            ModelIntentClassificationInput(**minimal_input_data)

        assert "extra_field" in str(exc_info.value)

    def test_unknown_parameter_rejected(self, minimal_input_data: dict) -> None:
        """Test that unknown parameters are rejected."""
        minimal_input_data["unknown_param"] = 123

        with pytest.raises(ValidationError):
            ModelIntentClassificationInput(**minimal_input_data)


# ============================================================================
# Test: Serialization
# ============================================================================


class TestModelIntentClassificationInputSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump(self, minimal_input_data: dict) -> None:
        """Test serialization to dictionary."""
        model = ModelIntentClassificationInput(**minimal_input_data)
        data = model.model_dump()

        assert "content" in data
        assert "correlation_id" in data
        assert "context" in data
        assert data["content"] == "I want to cancel my subscription"

    def test_model_dump_json(self, minimal_input_data: dict) -> None:
        """Test serialization to JSON string."""
        model = ModelIntentClassificationInput(**minimal_input_data)
        json_str = model.model_dump_json()

        assert isinstance(json_str, str)
        assert "cancel my subscription" in json_str

    def test_round_trip_serialization(self, full_input_data: dict) -> None:
        """Test that model survives serialization round-trip."""
        original = ModelIntentClassificationInput(**full_input_data)
        data = original.model_dump()
        restored = ModelIntentClassificationInput(**data)

        assert original.content == restored.content
        assert original.correlation_id == restored.correlation_id
        assert original.context == restored.context

    def test_json_round_trip_serialization(self, full_input_data: dict) -> None:
        """Test JSON serialization and deserialization roundtrip."""
        original = ModelIntentClassificationInput(**full_input_data)

        json_str = original.model_dump_json()
        restored = ModelIntentClassificationInput.model_validate_json(json_str)

        assert original.content == restored.content
        assert original.correlation_id == restored.correlation_id
        assert original.context["user_id"] == restored.context["user_id"]
        assert original.context["language"] == restored.context["language"]

    def test_model_dump_contains_all_fields(self, full_input_data: dict) -> None:
        """Test model_dump contains all expected fields."""
        model = ModelIntentClassificationInput(**full_input_data)
        data = model.model_dump()

        expected_fields = ["content", "correlation_id", "context"]
        for field in expected_fields:
            assert field in data

    def test_model_validate_from_dict(self, full_input_data: dict) -> None:
        """Test model validation from dictionary."""
        model = ModelIntentClassificationInput.model_validate(full_input_data)

        assert model.content == full_input_data["content"]
        assert model.correlation_id == full_input_data["correlation_id"]


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestModelIntentClassificationInputEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_conversation_history_structure(self, minimal_input_data: dict) -> None:
        """Test conversation_history with proper message structure."""
        context: TypedDictIntentContext = {
            "conversation_history": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
        }
        minimal_input_data["context"] = context

        model = ModelIntentClassificationInput(**minimal_input_data)
        assert len(model.context["conversation_history"]) == 3
        assert model.context["conversation_history"][0]["role"] == "system"

    def test_empty_conversation_history(self, minimal_input_data: dict) -> None:
        """Test with empty conversation history list."""
        context: TypedDictIntentContext = {
            "conversation_history": [],
        }
        minimal_input_data["context"] = context

        model = ModelIntentClassificationInput(**minimal_input_data)
        assert model.context["conversation_history"] == []

    def test_custom_labels_list(self, minimal_input_data: dict) -> None:
        """Test custom_labels list in context."""
        context: TypedDictIntentContext = {
            "custom_labels": ["intent_a", "intent_b", "intent_c"],
        }
        minimal_input_data["context"] = context

        model = ModelIntentClassificationInput(**minimal_input_data)
        assert len(model.context["custom_labels"]) == 3

    def test_confidence_threshold_in_context(self, minimal_input_data: dict) -> None:
        """Test confidence_threshold in context."""
        context: TypedDictIntentContext = {
            "confidence_threshold": 0.85,
        }
        minimal_input_data["context"] = context

        model = ModelIntentClassificationInput(**minimal_input_data)
        assert model.context["confidence_threshold"] == 0.85

    def test_model_equality(self, minimal_input_data: dict) -> None:
        """Test model equality comparison."""
        model1 = ModelIntentClassificationInput(**minimal_input_data)
        model2 = ModelIntentClassificationInput(**minimal_input_data)

        assert model1 == model2

    def test_model_inequality_different_content(self, minimal_input_data: dict) -> None:
        """Test model inequality when content differs."""
        model1 = ModelIntentClassificationInput(**minimal_input_data)

        minimal_input_data["content"] = "Different content"
        model2 = ModelIntentClassificationInput(**minimal_input_data)

        assert model1 != model2

    def test_model_not_hashable_due_to_mutable_context(
        self, minimal_input_data: dict
    ) -> None:
        """Test that model is not hashable due to mutable dict field.

        Frozen Pydantic models with mutable fields (dict, list) are not
        hashable because the underlying fields cannot be hashed.
        """
        model = ModelIntentClassificationInput(**minimal_input_data)

        with pytest.raises(TypeError, match="unhashable type"):
            hash(model)

    def test_str_representation(self, minimal_input_data: dict) -> None:
        """Test __str__ method returns meaningful string."""
        model = ModelIntentClassificationInput(**minimal_input_data)
        str_repr = str(model)

        assert isinstance(str_repr, str)
        assert "cancel my subscription" in str_repr

    def test_repr_representation(self, minimal_input_data: dict) -> None:
        """Test __repr__ method returns string with class name."""
        model = ModelIntentClassificationInput(**minimal_input_data)
        repr_str = repr(model)

        assert isinstance(repr_str, str)
        assert "ModelIntentClassificationInput" in repr_str


# ============================================================================
# Test: TypedDict Compatibility
# ============================================================================


class TestTypedDictCompatibility:
    """Tests for TypedDict usage in the model."""

    def test_conversation_message_dict_structure(self) -> None:
        """Test TypedDictConversationMessage structure."""
        message: TypedDictConversationMessage = {
            "role": "user",
            "content": "Hello, world!",
        }
        assert message["role"] == "user"
        assert message["content"] == "Hello, world!"

    def test_intent_context_dict_partial(self) -> None:
        """Test TypedDictIntentContext with partial fields (total=False)."""
        # Only some fields provided
        context: TypedDictIntentContext = {
            "language": "en",
            "domain": "support",
        }
        assert context["language"] == "en"
        assert "user_id" not in context

    def test_intent_context_dict_full(self) -> None:
        """Test TypedDictIntentContext with all fields."""
        context: TypedDictIntentContext = {
            "user_id": "user-123",
            "session_id": "session-456",
            "request_id": "request-789",
            "previous_intents": ["greeting"],
            "language": "en",
            "domain": "support",
            "conversation_history": [{"role": "user", "content": "Hi"}],
            "custom_labels": ["label1"],
            "confidence_threshold": 0.8,
            "max_intents": 3,
            "include_confidence_scores": True,
            "source_system": "api",
            "timestamp_utc": "2025-01-01T00:00:00Z",
        }

        model = ModelIntentClassificationInput(
            content="Test content",
            context=context,
        )
        assert model.context["user_id"] == "user-123"
        assert model.context["max_intents"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
