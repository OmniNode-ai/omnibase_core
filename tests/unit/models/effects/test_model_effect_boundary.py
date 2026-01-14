"""Tests for ModelEffectBoundary.

Part of OMN-1147: Effect Classification System test suite.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_effect_category import EnumEffectCategory
from omnibase_core.enums.enum_effect_policy_level import EnumEffectPolicyLevel
from omnibase_core.models.effects.model_effect_boundary import ModelEffectBoundary
from omnibase_core.models.effects.model_effect_classification import (
    ModelEffectClassification,
)


@pytest.mark.unit
class TestModelEffectBoundary:
    """Test cases for ModelEffectBoundary model."""

    def test_model_creation_with_all_fields(self) -> None:
        """Test creating model with all fields specified."""
        network_classification = ModelEffectClassification(
            category=EnumEffectCategory.NETWORK,
            description="HTTP API calls",
        )
        db_classification = ModelEffectClassification(
            category=EnumEffectCategory.DATABASE,
            description="Database queries",
        )

        boundary = ModelEffectBoundary(
            boundary_id="user_service.fetch_data",
            classifications=(network_classification, db_classification),
            default_policy=EnumEffectPolicyLevel.STRICT,
            determinism_marker=True,
            isolation_mechanisms=("DATABASE_READONLY_SNAPSHOT", "MOCK_NETWORK"),
        )

        assert boundary.boundary_id == "user_service.fetch_data"
        assert len(boundary.classifications) == 2
        assert boundary.default_policy == EnumEffectPolicyLevel.STRICT
        assert boundary.determinism_marker is True
        assert "DATABASE_READONLY_SNAPSHOT" in boundary.isolation_mechanisms

    def test_model_creation_minimal_required_fields(self) -> None:
        """Test creating model with only required fields."""
        boundary = ModelEffectBoundary(
            boundary_id="test.boundary",
        )

        assert boundary.boundary_id == "test.boundary"
        # Check defaults
        assert boundary.classifications == ()
        assert boundary.default_policy == EnumEffectPolicyLevel.WARN
        assert boundary.determinism_marker is False
        assert boundary.isolation_mechanisms == ()

    def test_default_policy_is_warn(self) -> None:
        """Test that default_policy defaults to WARN."""
        boundary = ModelEffectBoundary(
            boundary_id="test.boundary",
        )
        assert boundary.default_policy == EnumEffectPolicyLevel.WARN

    def test_immutability_frozen_model(self) -> None:
        """Test that model is immutable (frozen=True in ConfigDict)."""
        boundary = ModelEffectBoundary(
            boundary_id="test.boundary",
            default_policy=EnumEffectPolicyLevel.STRICT,
        )

        with pytest.raises(ValidationError):
            boundary.boundary_id = "new.boundary"  # type: ignore[misc]

        with pytest.raises(ValidationError):
            boundary.default_policy = EnumEffectPolicyLevel.PERMISSIVE  # type: ignore[misc]

    def test_boundary_id_is_required(self) -> None:
        """Test that boundary_id field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectBoundary()  # type: ignore[call-arg]

        assert "boundary_id" in str(exc_info.value)

    def test_has_isolation_mechanism_method(self) -> None:
        """Test has_isolation_mechanism() method returns correct results."""
        boundary = ModelEffectBoundary(
            boundary_id="test.boundary",
            isolation_mechanisms=(
                "DATABASE_READONLY_SNAPSHOT",
                "MOCK_NETWORK",
                "MOCK_TIME",
            ),
        )

        assert boundary.has_isolation_mechanism("DATABASE_READONLY_SNAPSHOT") is True
        assert boundary.has_isolation_mechanism("MOCK_NETWORK") is True
        assert boundary.has_isolation_mechanism("MOCK_TIME") is True
        assert boundary.has_isolation_mechanism("NONEXISTENT") is False
        assert boundary.has_isolation_mechanism("") is False

    def test_has_isolation_mechanism_empty_mechanisms(self) -> None:
        """Test has_isolation_mechanism() with no mechanisms defined."""
        boundary = ModelEffectBoundary(
            boundary_id="test.boundary",
        )

        assert boundary.has_isolation_mechanism("DATABASE_READONLY_SNAPSHOT") is False
        assert boundary.has_isolation_mechanism("ANY_MECHANISM") is False

    def test_has_classification_for_category_method(self) -> None:
        """Test has_classification_for_category() method returns correct results."""
        network_classification = ModelEffectClassification(
            category=EnumEffectCategory.NETWORK,
            description="HTTP calls",
        )
        time_classification = ModelEffectClassification(
            category=EnumEffectCategory.TIME,
            description="Timestamps",
        )

        boundary = ModelEffectBoundary(
            boundary_id="test.boundary",
            classifications=(network_classification, time_classification),
        )

        assert (
            boundary.has_classification_for_category(EnumEffectCategory.NETWORK) is True
        )
        assert boundary.has_classification_for_category(EnumEffectCategory.TIME) is True
        assert (
            boundary.has_classification_for_category(EnumEffectCategory.DATABASE)
            is False
        )
        assert (
            boundary.has_classification_for_category(EnumEffectCategory.RANDOM) is False
        )

    def test_has_classification_for_category_empty_classifications(self) -> None:
        """Test has_classification_for_category() with no classifications."""
        boundary = ModelEffectBoundary(
            boundary_id="test.boundary",
        )

        for category in EnumEffectCategory:
            assert boundary.has_classification_for_category(category) is False

    def test_database_readonly_snapshot_isolation_mechanism(self) -> None:
        """Test DATABASE_READONLY_SNAPSHOT isolation mechanism support."""
        boundary = ModelEffectBoundary(
            boundary_id="db_service.query",
            isolation_mechanisms=("DATABASE_READONLY_SNAPSHOT",),
        )

        assert boundary.has_isolation_mechanism("DATABASE_READONLY_SNAPSHOT") is True
        # This mechanism enables deterministic database replay
        assert len(boundary.isolation_mechanisms) == 1

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are not allowed (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectBoundary(
                boundary_id="test.boundary",
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert (
            "unknown_field" in str(exc_info.value).lower()
            or "extra" in str(exc_info.value).lower()
        )

    def test_model_equality(self) -> None:
        """Test model equality comparison."""
        boundary1 = ModelEffectBoundary(
            boundary_id="test.boundary",
            default_policy=EnumEffectPolicyLevel.WARN,
        )
        boundary2 = ModelEffectBoundary(
            boundary_id="test.boundary",
            default_policy=EnumEffectPolicyLevel.WARN,
        )
        boundary3 = ModelEffectBoundary(
            boundary_id="other.boundary",
            default_policy=EnumEffectPolicyLevel.WARN,
        )

        assert boundary1 == boundary2
        assert boundary1 != boundary3

    def test_model_hashable(self) -> None:
        """Test that frozen model can be hashed."""
        boundary = ModelEffectBoundary(
            boundary_id="test.boundary",
        )

        hash_value = hash(boundary)
        assert isinstance(hash_value, int)

        # Can be used in sets
        boundary_set = {boundary}
        assert boundary in boundary_set

    def test_all_policy_levels_accepted(self) -> None:
        """Test that all EnumEffectPolicyLevel values are valid."""
        for policy in EnumEffectPolicyLevel:
            boundary = ModelEffectBoundary(
                boundary_id="test.boundary",
                default_policy=policy,
            )
            assert boundary.default_policy == policy

    def test_classifications_as_tuple_immutable(self) -> None:
        """Test that classifications tuple is immutable."""
        classification = ModelEffectClassification(
            category=EnumEffectCategory.NETWORK,
            description="Test",
        )
        boundary = ModelEffectBoundary(
            boundary_id="test.boundary",
            classifications=(classification,),
        )

        assert isinstance(boundary.classifications, tuple)
        with pytest.raises(AttributeError):
            boundary.classifications.append(classification)  # type: ignore[attr-defined]

    def test_isolation_mechanisms_as_tuple_immutable(self) -> None:
        """Test that isolation_mechanisms tuple is immutable."""
        boundary = ModelEffectBoundary(
            boundary_id="test.boundary",
            isolation_mechanisms=("MOCK_TIME",),
        )

        assert isinstance(boundary.isolation_mechanisms, tuple)
        with pytest.raises(AttributeError):
            boundary.isolation_mechanisms.append("NEW")  # type: ignore[attr-defined]

    def test_from_attributes_enabled(self) -> None:
        """Test that from_attributes=True allows ORM-style creation."""

        class MockORM:
            boundary_id = "orm.boundary"
            classifications = ()
            default_policy = EnumEffectPolicyLevel.STRICT
            determinism_marker = True
            isolation_mechanisms = ("MOCK_NETWORK",)

        boundary = ModelEffectBoundary.model_validate(MockORM())
        assert boundary.boundary_id == "orm.boundary"
        assert boundary.default_policy == EnumEffectPolicyLevel.STRICT

    def test_model_dump(self) -> None:
        """Test that model can be serialized to dict."""
        boundary = ModelEffectBoundary(
            boundary_id="test.boundary",
            default_policy=EnumEffectPolicyLevel.MOCKED,
            determinism_marker=True,
        )

        data = boundary.model_dump()

        assert data["boundary_id"] == "test.boundary"
        assert data["default_policy"] == EnumEffectPolicyLevel.MOCKED
        assert data["determinism_marker"] is True
        assert data["classifications"] == ()
        assert data["isolation_mechanisms"] == ()

    def test_model_json_serialization(self) -> None:
        """Test that model can be serialized to JSON."""
        boundary = ModelEffectBoundary(
            boundary_id="json.test",
            default_policy=EnumEffectPolicyLevel.PERMISSIVE,
        )

        json_str = boundary.model_dump_json()
        assert "json.test" in json_str
        assert "permissive" in json_str

    def test_multiple_classifications_same_category(self) -> None:
        """Test boundary can have multiple classifications of different categories."""
        classifications = tuple(
            ModelEffectClassification(
                category=cat,
                description=f"Effect for {cat.value}",
            )
            for cat in EnumEffectCategory
        )

        boundary = ModelEffectBoundary(
            boundary_id="all.categories",
            classifications=classifications,
        )

        assert len(boundary.classifications) == 6
        for cat in EnumEffectCategory:
            assert boundary.has_classification_for_category(cat) is True

    def test_determinism_marker_semantics(self) -> None:
        """Test determinism_marker field behavior."""
        # Default is False
        boundary_default = ModelEffectBoundary(
            boundary_id="test",
        )
        assert boundary_default.determinism_marker is False

        # Can be set to True
        boundary_marked = ModelEffectBoundary(
            boundary_id="test",
            determinism_marker=True,
        )
        assert boundary_marked.determinism_marker is True
