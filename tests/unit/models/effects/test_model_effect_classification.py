"""Tests for ModelEffectClassification.

Part of OMN-1147: Effect Classification System test suite.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_effect_category import EnumEffectCategory
from omnibase_core.models.effects.model_effect_classification import (
    ModelEffectClassification,
)


@pytest.mark.unit
class TestModelEffectClassification:
    """Test cases for ModelEffectClassification model."""

    def test_model_creation_with_all_fields(self) -> None:
        """Test creating model with all fields specified."""
        classification = ModelEffectClassification(
            category=EnumEffectCategory.NETWORK,
            description="HTTP API call to external service",
            nondeterministic=True,
            replay_risk_notes="May return different data on replay",
            tags=("api", "external", "http"),
        )

        assert classification.category == EnumEffectCategory.NETWORK
        assert classification.description == "HTTP API call to external service"
        assert classification.nondeterministic is True
        assert classification.replay_risk_notes == "May return different data on replay"
        assert classification.tags == ("api", "external", "http")

    def test_model_creation_minimal_required_fields(self) -> None:
        """Test creating model with only required fields."""
        classification = ModelEffectClassification(
            category=EnumEffectCategory.DATABASE,
            description="Query user table",
        )

        assert classification.category == EnumEffectCategory.DATABASE
        assert classification.description == "Query user table"
        # Check defaults
        assert classification.nondeterministic is True
        assert classification.replay_risk_notes is None
        assert classification.tags == ()

    def test_default_nondeterministic_is_true(self) -> None:
        """Test that nondeterministic defaults to True."""
        classification = ModelEffectClassification(
            category=EnumEffectCategory.TIME,
            description="Get current timestamp",
        )
        assert classification.nondeterministic is True

    def test_default_tags_empty_tuple(self) -> None:
        """Test that tags defaults to empty tuple."""
        classification = ModelEffectClassification(
            category=EnumEffectCategory.RANDOM,
            description="Generate UUID",
        )
        assert classification.tags == ()
        assert isinstance(classification.tags, tuple)

    def test_nondeterministic_can_be_false(self) -> None:
        """Test that nondeterministic can be explicitly set to False."""
        classification = ModelEffectClassification(
            category=EnumEffectCategory.DATABASE,
            description="Read from immutable config table",
            nondeterministic=False,
        )
        assert classification.nondeterministic is False

    def test_immutability_frozen_model(self) -> None:
        """Test that model is immutable (frozen=True in ConfigDict)."""
        classification = ModelEffectClassification(
            category=EnumEffectCategory.FILESYSTEM,
            description="Read config file",
        )

        with pytest.raises(ValidationError):
            classification.category = EnumEffectCategory.NETWORK  # type: ignore[misc]

        with pytest.raises(ValidationError):
            classification.description = "New description"  # type: ignore[misc]

    def test_category_is_required(self) -> None:
        """Test that category field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectClassification(description="Missing category")  # type: ignore[call-arg]

        assert "category" in str(exc_info.value)

    def test_description_is_required(self) -> None:
        """Test that description field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectClassification(category=EnumEffectCategory.NETWORK)  # type: ignore[call-arg]

        assert "description" in str(exc_info.value)

    def test_all_effect_categories_accepted(self) -> None:
        """Test that all EnumEffectCategory values are valid."""
        for category in EnumEffectCategory:
            classification = ModelEffectClassification(
                category=category,
                description=f"Test effect for {category}",
            )
            assert classification.category == category

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are not allowed (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectClassification(
                category=EnumEffectCategory.NETWORK,
                description="Test",
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert (
            "unknown_field" in str(exc_info.value).lower()
            or "extra" in str(exc_info.value).lower()
        )

    def test_model_equality(self) -> None:
        """Test model equality comparison."""
        classification1 = ModelEffectClassification(
            category=EnumEffectCategory.NETWORK,
            description="HTTP call",
            tags=("api",),
        )
        classification2 = ModelEffectClassification(
            category=EnumEffectCategory.NETWORK,
            description="HTTP call",
            tags=("api",),
        )
        classification3 = ModelEffectClassification(
            category=EnumEffectCategory.DATABASE,
            description="HTTP call",
            tags=("api",),
        )

        assert classification1 == classification2
        assert classification1 != classification3

    def test_model_hashable_for_use_in_sets(self) -> None:
        """Test that frozen model can be hashed for use in sets/dicts."""
        classification = ModelEffectClassification(
            category=EnumEffectCategory.TIME,
            description="Get timestamp",
        )

        # Should be hashable
        hash_value = hash(classification)
        assert isinstance(hash_value, int)

        # Can be used in sets
        classifications_set = {classification}
        assert classification in classifications_set

    def test_model_can_be_dict_key(self) -> None:
        """Test that model can be used as dictionary key."""
        classification = ModelEffectClassification(
            category=EnumEffectCategory.RANDOM,
            description="Generate random number",
        )

        effect_policies: dict[ModelEffectClassification, str] = {classification: "mock"}

        assert effect_policies[classification] == "mock"

    def test_tags_as_tuple_is_immutable(self) -> None:
        """Test that tags tuple cannot be modified."""
        classification = ModelEffectClassification(
            category=EnumEffectCategory.NETWORK,
            description="API call",
            tags=("a", "b", "c"),
        )

        # Tuples are immutable, cannot append
        assert isinstance(classification.tags, tuple)
        with pytest.raises(AttributeError):
            classification.tags.append("d")  # type: ignore[attr-defined]

    def test_from_attributes_enabled(self) -> None:
        """Test that from_attributes=True allows ORM-style creation."""

        class MockORM:
            category = EnumEffectCategory.DATABASE
            description = "Query database"
            nondeterministic = True
            replay_risk_notes = "Data may change"
            tags = ("db", "query")

        classification = ModelEffectClassification.model_validate(MockORM())
        assert classification.category == EnumEffectCategory.DATABASE
        assert classification.description == "Query database"

    def test_model_dump(self) -> None:
        """Test that model can be serialized to dict."""
        classification = ModelEffectClassification(
            category=EnumEffectCategory.FILESYSTEM,
            description="Read file",
            tags=("io", "file"),
        )

        data = classification.model_dump()

        assert data["category"] == EnumEffectCategory.FILESYSTEM
        assert data["description"] == "Read file"
        assert data["nondeterministic"] is True
        assert data["replay_risk_notes"] is None
        assert data["tags"] == ("io", "file")

    def test_model_json_serialization(self) -> None:
        """Test that model can be serialized to JSON."""
        classification = ModelEffectClassification(
            category=EnumEffectCategory.EXTERNAL_STATE,
            description="Read environment variable",
        )

        json_str = classification.model_dump_json()
        assert "external_state" in json_str
        assert "Read environment variable" in json_str

    def test_replay_risk_notes_optional(self) -> None:
        """Test that replay_risk_notes can be None or a string."""
        # None case
        classification1 = ModelEffectClassification(
            category=EnumEffectCategory.NETWORK,
            description="HTTP call",
            replay_risk_notes=None,
        )
        assert classification1.replay_risk_notes is None

        # String case
        classification2 = ModelEffectClassification(
            category=EnumEffectCategory.NETWORK,
            description="HTTP call",
            replay_risk_notes="External state may change between runs",
        )
        assert (
            classification2.replay_risk_notes
            == "External state may change between runs"
        )
