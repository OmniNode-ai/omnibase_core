# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelIntentClassificationOutput.

Tests comprehensive intent classification output functionality including:
- Model instantiation with minimal and full fields
- Immutability (frozen model)
- Extra fields rejection
- Confidence range validation (0.0-1.0)
- Default values (intent_category="unknown", confidence=0.0)
- secondary_intents list handling
- metadata optional field
- Helper methods (is_high_confidence, get_all_intents)
- Serialization and deserialization
"""

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.models.intelligence.model_intent_classification_output import (
    IntentMetadataDict,
    ModelIntentClassificationOutput,
    SecondaryIntentDict,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def minimal_output_data() -> dict:
    """Minimal required data for creating an output model."""
    return {
        "success": True,
    }


@pytest.fixture
def full_output_data() -> dict:
    """Complete data including all fields."""
    secondary_intents: list[SecondaryIntentDict] = [
        {
            "intent_category": "billing_inquiry",
            "confidence": 0.3,
            "description": "Questions about billing",
            "keywords": ["bill", "payment", "invoice"],
            "parent_intent": "support",
        },
        {
            "intent_category": "account_access",
            "confidence": 0.2,
            "description": "Account access issues",
        },
    ]
    metadata: IntentMetadataDict = {
        "status": "success",
        "message": "Classification completed",
        "tracking_url": "https://example.com/track/123",
        "classifier_version": "2.1.0",
        "classification_time_ms": 45.5,
        "model_name": "intent-classifier-v2",
        "token_count": 128,
        "threshold_used": 0.7,
        "raw_scores": {"cancellation": 0.95, "billing": 0.3, "access": 0.2},
    }
    return {
        "success": True,
        "intent_category": "cancellation_request",
        "confidence": 0.95,
        "secondary_intents": secondary_intents,
        "metadata": metadata,
    }


# ============================================================================
# Test: Model Instantiation
# ============================================================================


class TestModelIntentClassificationOutputInstantiation:
    """Tests for model instantiation and basic functionality."""

    def test_create_with_minimal_data(self, minimal_output_data: dict) -> None:
        """Test creating output with only required fields."""
        model = ModelIntentClassificationOutput(**minimal_output_data)

        assert model.success is True
        assert model.intent_category == "unknown"
        assert model.confidence == 0.0
        assert model.secondary_intents == []
        assert model.metadata is None

    def test_create_with_full_data(self, full_output_data: dict) -> None:
        """Test creating output with all fields explicitly set."""
        model = ModelIntentClassificationOutput(**full_output_data)

        assert model.success is True
        assert model.intent_category == "cancellation_request"
        assert model.confidence == 0.95
        assert len(model.secondary_intents) == 2
        assert model.metadata is not None
        assert model.metadata["classifier_version"] == "2.1.0"

    def test_success_false(self, minimal_output_data: dict) -> None:
        """Test output with success=False."""
        minimal_output_data["success"] = False
        model = ModelIntentClassificationOutput(**minimal_output_data)

        assert model.success is False

    def test_default_values(self) -> None:
        """Test that defaults are correctly applied."""
        model = ModelIntentClassificationOutput(success=True)

        assert model.intent_category == "unknown"
        assert model.confidence == 0.0
        assert model.secondary_intents == []
        assert model.metadata is None

    def test_custom_intent_category(self, minimal_output_data: dict) -> None:
        """Test setting custom intent_category."""
        minimal_output_data["intent_category"] = "custom_intent"
        model = ModelIntentClassificationOutput(**minimal_output_data)

        assert model.intent_category == "custom_intent"


# ============================================================================
# Test: Immutability (Frozen Model)
# ============================================================================


class TestModelIntentClassificationOutputImmutability:
    """Tests for frozen model behavior."""

    def test_model_is_frozen(self, minimal_output_data: dict) -> None:
        """Test that the model is immutable."""
        model = ModelIntentClassificationOutput(**minimal_output_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - Pydantic raises at runtime
            model.success = False

    def test_cannot_modify_intent_category(self, full_output_data: dict) -> None:
        """Test that intent_category cannot be modified."""
        model = ModelIntentClassificationOutput(**full_output_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - Pydantic raises at runtime
            model.intent_category = "modified"

    def test_cannot_modify_confidence(self, full_output_data: dict) -> None:
        """Test that confidence cannot be modified."""
        model = ModelIntentClassificationOutput(**full_output_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - Pydantic raises at runtime
            model.confidence = 0.5

    def test_cannot_modify_secondary_intents(self, full_output_data: dict) -> None:
        """Test that secondary_intents cannot be reassigned."""
        model = ModelIntentClassificationOutput(**full_output_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - Pydantic raises at runtime
            model.secondary_intents = []

    def test_cannot_modify_metadata(self, full_output_data: dict) -> None:
        """Test that metadata cannot be reassigned."""
        model = ModelIntentClassificationOutput(**full_output_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - Pydantic raises at runtime
            model.metadata = None


# ============================================================================
# Test: Confidence Range Validation
# ============================================================================


class TestModelIntentClassificationOutputConfidenceValidation:
    """Tests for confidence field bounds validation."""

    def test_confidence_at_minimum(self, minimal_output_data: dict) -> None:
        """Test that confidence of 0.0 is accepted."""
        minimal_output_data["confidence"] = 0.0
        model = ModelIntentClassificationOutput(**minimal_output_data)
        assert model.confidence == 0.0

    def test_confidence_at_maximum(self, minimal_output_data: dict) -> None:
        """Test that confidence of 1.0 is accepted."""
        minimal_output_data["confidence"] = 1.0
        model = ModelIntentClassificationOutput(**minimal_output_data)
        assert model.confidence == 1.0

    def test_confidence_in_middle(self, minimal_output_data: dict) -> None:
        """Test that confidence of 0.5 is accepted."""
        minimal_output_data["confidence"] = 0.5
        model = ModelIntentClassificationOutput(**minimal_output_data)
        assert model.confidence == 0.5

    def test_confidence_below_minimum_rejected(self, minimal_output_data: dict) -> None:
        """Test that confidence below 0.0 is rejected."""
        minimal_output_data["confidence"] = -0.01

        with pytest.raises(ValidationError) as exc_info:
            ModelIntentClassificationOutput(**minimal_output_data)

        assert "confidence" in str(exc_info.value)

    def test_confidence_above_maximum_rejected(self, minimal_output_data: dict) -> None:
        """Test that confidence above 1.0 is rejected."""
        minimal_output_data["confidence"] = 1.01

        with pytest.raises(ValidationError) as exc_info:
            ModelIntentClassificationOutput(**minimal_output_data)

        assert "confidence" in str(exc_info.value)

    def test_confidence_high_precision(self, minimal_output_data: dict) -> None:
        """Test that high-precision confidence values are accepted."""
        minimal_output_data["confidence"] = 0.123456789
        model = ModelIntentClassificationOutput(**minimal_output_data)
        assert model.confidence == 0.123456789

    def test_confidence_accepts_int_coerced_to_float(
        self, minimal_output_data: dict
    ) -> None:
        """Test that int confidence is coerced to float."""
        minimal_output_data["confidence"] = 1
        model = ModelIntentClassificationOutput(**minimal_output_data)
        assert model.confidence == 1.0
        assert isinstance(model.confidence, float)


# ============================================================================
# Test: Secondary Intents Handling
# ============================================================================


class TestModelIntentClassificationOutputSecondaryIntents:
    """Tests for secondary_intents list handling."""

    def test_empty_secondary_intents(self, minimal_output_data: dict) -> None:
        """Test with empty secondary_intents list."""
        minimal_output_data["secondary_intents"] = []
        model = ModelIntentClassificationOutput(**minimal_output_data)
        assert model.secondary_intents == []

    def test_single_secondary_intent(self, minimal_output_data: dict) -> None:
        """Test with single secondary intent."""
        secondary: SecondaryIntentDict = {
            "intent_category": "follow_up",
            "confidence": 0.5,
        }
        minimal_output_data["secondary_intents"] = [secondary]

        model = ModelIntentClassificationOutput(**minimal_output_data)
        assert len(model.secondary_intents) == 1
        assert model.secondary_intents[0]["intent_category"] == "follow_up"

    def test_multiple_secondary_intents(self, minimal_output_data: dict) -> None:
        """Test with multiple secondary intents."""
        secondaries: list[SecondaryIntentDict] = [
            {"intent_category": "intent_a", "confidence": 0.4},
            {"intent_category": "intent_b", "confidence": 0.3},
            {"intent_category": "intent_c", "confidence": 0.2},
        ]
        minimal_output_data["secondary_intents"] = secondaries

        model = ModelIntentClassificationOutput(**minimal_output_data)
        assert len(model.secondary_intents) == 3

    def test_secondary_intent_partial_fields(self, minimal_output_data: dict) -> None:
        """Test secondary intent with partial fields (total=False)."""
        secondary: SecondaryIntentDict = {
            "intent_category": "partial_intent",
        }
        minimal_output_data["secondary_intents"] = [secondary]

        model = ModelIntentClassificationOutput(**minimal_output_data)
        assert model.secondary_intents[0]["intent_category"] == "partial_intent"
        assert "confidence" not in model.secondary_intents[0]

    def test_secondary_intent_full_fields(self, minimal_output_data: dict) -> None:
        """Test secondary intent with all fields."""
        secondary: SecondaryIntentDict = {
            "intent_category": "full_intent",
            "confidence": 0.7,
            "description": "A fully described intent",
            "keywords": ["key1", "key2"],
            "parent_intent": "parent",
        }
        minimal_output_data["secondary_intents"] = [secondary]

        model = ModelIntentClassificationOutput(**minimal_output_data)
        assert model.secondary_intents[0]["description"] == "A fully described intent"
        assert len(model.secondary_intents[0]["keywords"]) == 2


# ============================================================================
# Test: Metadata Handling
# ============================================================================


class TestModelIntentClassificationOutputMetadata:
    """Tests for metadata optional field handling."""

    def test_metadata_none(self, minimal_output_data: dict) -> None:
        """Test metadata defaults to None."""
        model = ModelIntentClassificationOutput(**minimal_output_data)
        assert model.metadata is None

    def test_metadata_partial_fields(self, minimal_output_data: dict) -> None:
        """Test metadata with partial fields (total=False)."""
        metadata: IntentMetadataDict = {
            "status": "success",
            "classification_time_ms": 25.5,
        }
        minimal_output_data["metadata"] = metadata

        model = ModelIntentClassificationOutput(**minimal_output_data)
        assert model.metadata is not None
        assert model.metadata["status"] == "success"
        assert model.metadata["classification_time_ms"] == 25.5
        assert "model_name" not in model.metadata

    def test_metadata_full_fields(self, full_output_data: dict) -> None:
        """Test metadata with all fields."""
        model = ModelIntentClassificationOutput(**full_output_data)

        assert model.metadata is not None
        assert model.metadata["status"] == "success"
        assert model.metadata["message"] == "Classification completed"
        assert model.metadata["classifier_version"] == "2.1.0"
        assert model.metadata["model_name"] == "intent-classifier-v2"
        assert model.metadata["token_count"] == 128
        assert "cancellation" in model.metadata["raw_scores"]


# ============================================================================
# Test: Helper Methods
# ============================================================================


class TestModelIntentClassificationOutputHelperMethods:
    """Tests for helper methods."""

    def test_is_high_confidence_true_default_threshold(
        self, minimal_output_data: dict
    ) -> None:
        """Test is_high_confidence returns True above default threshold."""
        minimal_output_data["confidence"] = 0.9
        model = ModelIntentClassificationOutput(**minimal_output_data)

        assert model.is_high_confidence() is True

    def test_is_high_confidence_false_default_threshold(
        self, minimal_output_data: dict
    ) -> None:
        """Test is_high_confidence returns False below default threshold."""
        minimal_output_data["confidence"] = 0.7
        model = ModelIntentClassificationOutput(**minimal_output_data)

        assert model.is_high_confidence() is False

    def test_is_high_confidence_at_threshold(self, minimal_output_data: dict) -> None:
        """Test is_high_confidence at exactly the threshold."""
        minimal_output_data["confidence"] = 0.8
        model = ModelIntentClassificationOutput(**minimal_output_data)

        assert model.is_high_confidence() is True  # >= threshold

    def test_is_high_confidence_custom_threshold(
        self, minimal_output_data: dict
    ) -> None:
        """Test is_high_confidence with custom threshold."""
        minimal_output_data["confidence"] = 0.6
        model = ModelIntentClassificationOutput(**minimal_output_data)

        assert model.is_high_confidence(threshold=0.5) is True
        assert model.is_high_confidence(threshold=0.7) is False

    def test_get_all_intents_primary_only(self, minimal_output_data: dict) -> None:
        """Test get_all_intents with only primary intent."""
        minimal_output_data["intent_category"] = "main_intent"
        minimal_output_data["confidence"] = 0.9
        model = ModelIntentClassificationOutput(**minimal_output_data)

        intents = model.get_all_intents()
        assert len(intents) == 1
        assert intents[0] == ("main_intent", 0.9)

    def test_get_all_intents_with_secondary(self, minimal_output_data: dict) -> None:
        """Test get_all_intents with secondary intents."""
        minimal_output_data["intent_category"] = "primary"
        minimal_output_data["confidence"] = 0.85
        minimal_output_data["secondary_intents"] = [
            {"intent_category": "secondary_a", "confidence": 0.4},
            {"intent_category": "secondary_b", "confidence": 0.25},
        ]
        model = ModelIntentClassificationOutput(**minimal_output_data)

        intents = model.get_all_intents()
        assert len(intents) == 3
        assert intents[0] == ("primary", 0.85)
        assert intents[1] == ("secondary_a", 0.4)
        assert intents[2] == ("secondary_b", 0.25)

    def test_get_all_intents_missing_fields_in_secondary(
        self, minimal_output_data: dict
    ) -> None:
        """Test get_all_intents handles missing fields in secondary intents."""
        minimal_output_data["intent_category"] = "primary"
        minimal_output_data["confidence"] = 0.9
        minimal_output_data["secondary_intents"] = [
            {},  # Empty dict, should get defaults
            {"intent_category": "has_category"},  # Missing confidence
        ]
        model = ModelIntentClassificationOutput(**minimal_output_data)

        intents = model.get_all_intents()
        assert len(intents) == 3
        assert intents[0] == ("primary", 0.9)
        assert intents[1] == ("unknown", 0.0)  # Defaults applied
        assert intents[2] == ("has_category", 0.0)  # Default confidence


# ============================================================================
# Test: Extra Fields Rejection
# ============================================================================


class TestModelIntentClassificationOutputExtraFields:
    """Tests for extra fields rejection."""

    def test_extra_fields_forbidden(self, minimal_output_data: dict) -> None:
        """Test that extra fields are forbidden."""
        minimal_output_data["extra_field"] = "not_allowed"

        with pytest.raises(ValidationError) as exc_info:
            ModelIntentClassificationOutput(**minimal_output_data)

        assert "extra_field" in str(exc_info.value)

    def test_unknown_parameter_rejected(self, minimal_output_data: dict) -> None:
        """Test that unknown parameters are rejected."""
        minimal_output_data["unknown_param"] = 123

        with pytest.raises(ValidationError):
            ModelIntentClassificationOutput(**minimal_output_data)


# ============================================================================
# Test: Required Fields
# ============================================================================


class TestModelIntentClassificationOutputRequiredFields:
    """Tests for required field validation."""

    def test_missing_success_rejected(self) -> None:
        """Test that missing success field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntentClassificationOutput()  # type: ignore[call-arg]

        assert "success" in str(exc_info.value)


# ============================================================================
# Test: Serialization
# ============================================================================


class TestModelIntentClassificationOutputSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump(self, minimal_output_data: dict) -> None:
        """Test serialization to dictionary."""
        model = ModelIntentClassificationOutput(**minimal_output_data)
        data = model.model_dump()

        assert "success" in data
        assert "intent_category" in data
        assert "confidence" in data
        assert "secondary_intents" in data
        assert "metadata" in data
        assert data["success"] is True

    def test_model_dump_json(self, minimal_output_data: dict) -> None:
        """Test serialization to JSON string."""
        model = ModelIntentClassificationOutput(**minimal_output_data)
        json_str = model.model_dump_json()

        assert isinstance(json_str, str)
        assert "success" in json_str
        assert "true" in json_str.lower()

    def test_round_trip_serialization(self, full_output_data: dict) -> None:
        """Test that model survives serialization round-trip."""
        original = ModelIntentClassificationOutput(**full_output_data)
        data = original.model_dump()
        restored = ModelIntentClassificationOutput(**data)

        assert original.success == restored.success
        assert original.intent_category == restored.intent_category
        assert original.confidence == restored.confidence
        assert len(original.secondary_intents) == len(restored.secondary_intents)

    def test_json_round_trip_serialization(self, full_output_data: dict) -> None:
        """Test JSON serialization and deserialization roundtrip."""
        original = ModelIntentClassificationOutput(**full_output_data)

        json_str = original.model_dump_json()
        restored = ModelIntentClassificationOutput.model_validate_json(json_str)

        assert original.success == restored.success
        assert original.intent_category == restored.intent_category
        assert original.confidence == restored.confidence
        assert original.metadata == restored.metadata

    def test_model_dump_contains_all_fields(self, full_output_data: dict) -> None:
        """Test model_dump contains all expected fields."""
        model = ModelIntentClassificationOutput(**full_output_data)
        data = model.model_dump()

        expected_fields = [
            "success",
            "intent_category",
            "confidence",
            "secondary_intents",
            "metadata",
        ]
        for field in expected_fields:
            assert field in data

    def test_model_validate_from_dict(self, full_output_data: dict) -> None:
        """Test model validation from dictionary."""
        model = ModelIntentClassificationOutput.model_validate(full_output_data)

        assert model.success == full_output_data["success"]
        assert model.intent_category == full_output_data["intent_category"]


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestModelIntentClassificationOutputEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_model_equality(self, minimal_output_data: dict) -> None:
        """Test model equality comparison."""
        model1 = ModelIntentClassificationOutput(**minimal_output_data)
        model2 = ModelIntentClassificationOutput(**minimal_output_data)

        assert model1 == model2

    def test_model_inequality_different_success(
        self, minimal_output_data: dict
    ) -> None:
        """Test model inequality when success differs."""
        model1 = ModelIntentClassificationOutput(**minimal_output_data)

        minimal_output_data["success"] = False
        model2 = ModelIntentClassificationOutput(**minimal_output_data)

        assert model1 != model2

    def test_model_inequality_different_confidence(
        self, minimal_output_data: dict
    ) -> None:
        """Test model inequality when confidence differs."""
        minimal_output_data["confidence"] = 0.5
        model1 = ModelIntentClassificationOutput(**minimal_output_data)

        minimal_output_data["confidence"] = 0.9
        model2 = ModelIntentClassificationOutput(**minimal_output_data)

        assert model1 != model2

    def test_model_not_hashable_due_to_mutable_fields(
        self, minimal_output_data: dict
    ) -> None:
        """Test that model is not hashable due to mutable list field.

        Frozen Pydantic models with mutable fields (dict, list) are not
        hashable because the underlying fields cannot be hashed.
        """
        model = ModelIntentClassificationOutput(**minimal_output_data)

        with pytest.raises(TypeError, match="unhashable type"):
            hash(model)

    def test_str_representation(self, minimal_output_data: dict) -> None:
        """Test __str__ method returns meaningful string."""
        model = ModelIntentClassificationOutput(**minimal_output_data)
        str_repr = str(model)

        assert isinstance(str_repr, str)
        assert "success" in str_repr.lower()

    def test_repr_representation(self, minimal_output_data: dict) -> None:
        """Test __repr__ method returns string with class name."""
        model = ModelIntentClassificationOutput(**minimal_output_data)
        repr_str = repr(model)

        assert isinstance(repr_str, str)
        assert "ModelIntentClassificationOutput" in repr_str

    def test_unicode_in_intent_category(self, minimal_output_data: dict) -> None:
        """Test unicode characters in intent_category."""
        minimal_output_data["intent_category"] = "solicitud_cancelacion"
        model = ModelIntentClassificationOutput(**minimal_output_data)

        assert "cancelacion" in model.intent_category

    def test_long_intent_category(self, minimal_output_data: dict) -> None:
        """Test with very long intent_category string."""
        long_category = "a" * 1000
        minimal_output_data["intent_category"] = long_category

        model = ModelIntentClassificationOutput(**minimal_output_data)
        assert len(model.intent_category) == 1000


# ============================================================================
# Test: TypedDict Compatibility
# ============================================================================


class TestTypedDictCompatibility:
    """Tests for TypedDict usage in the model."""

    def test_secondary_intent_dict_structure(self) -> None:
        """Test SecondaryIntentDict structure."""
        intent: SecondaryIntentDict = {
            "intent_category": "test_intent",
            "confidence": 0.5,
        }
        assert intent["intent_category"] == "test_intent"
        assert intent["confidence"] == 0.5

    def test_secondary_intent_dict_full(self) -> None:
        """Test SecondaryIntentDict with all fields."""
        intent: SecondaryIntentDict = {
            "intent_category": "full_intent",
            "confidence": 0.8,
            "description": "Full description",
            "keywords": ["key1", "key2", "key3"],
            "parent_intent": "parent_category",
        }

        assert intent["description"] == "Full description"
        assert len(intent["keywords"]) == 3
        assert intent["parent_intent"] == "parent_category"

    def test_intent_metadata_dict_structure(self) -> None:
        """Test IntentMetadataDict structure."""
        metadata: IntentMetadataDict = {
            "status": "success",
            "classification_time_ms": 50.0,
        }
        assert metadata["status"] == "success"
        assert metadata["classification_time_ms"] == 50.0

    def test_intent_metadata_dict_full(self) -> None:
        """Test IntentMetadataDict with all fields."""
        metadata: IntentMetadataDict = {
            "status": "success",
            "message": "Done",
            "tracking_url": "https://example.com",
            "classifier_version": "1.0.0",
            "classification_time_ms": 100.0,
            "model_name": "model-v1",
            "token_count": 256,
            "threshold_used": 0.75,
            "raw_scores": {"a": 0.9, "b": 0.1},
        }

        model = ModelIntentClassificationOutput(
            success=True,
            metadata=metadata,
        )
        assert model.metadata is not None
        assert model.metadata["token_count"] == 256
        assert model.metadata["raw_scores"]["a"] == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
