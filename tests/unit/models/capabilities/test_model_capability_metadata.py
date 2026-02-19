# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelCapabilityMetadata.

Tests for the capability metadata model used for documentation and discovery.

OMN-1156: ModelCapabilityMetadata unit tests.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.capabilities.model_capability_metadata import (
    ModelCapabilityMetadata,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelCapabilityMetadataCreation:
    """Tests for ModelCapabilityMetadata creation with various field combinations."""

    def test_creation_with_all_required_fields(self) -> None:
        """Test creating metadata with all required fields."""
        metadata = ModelCapabilityMetadata(
            capability="database.relational",
            name="Relational Database",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="SQL-based relational database operations",
        )

        assert metadata.capability == "database.relational"
        assert metadata.name == "Relational Database"
        assert metadata.version == ModelSemVer(major=1, minor=0, patch=0)
        assert metadata.description == "SQL-based relational database operations"

    def test_creation_with_all_fields(self) -> None:
        """Test creating metadata with all fields populated."""
        metadata = ModelCapabilityMetadata(
            capability="cache.distributed",
            name="Distributed Cache",
            version=ModelSemVer(major=2, minor=1, patch=0),
            description="High-performance distributed caching",
            tags=("cache", "distributed", "high-performance"),
            required_features=("get", "set", "delete"),
            optional_features=("ttl", "batch_operations", "pubsub"),
            example_providers=("Redis", "Memcached", "Hazelcast"),
        )

        assert metadata.capability == "cache.distributed"
        assert metadata.name == "Distributed Cache"
        assert metadata.version == ModelSemVer(major=2, minor=1, patch=0)
        assert metadata.description == "High-performance distributed caching"
        assert metadata.tags == ("cache", "distributed", "high-performance")
        assert metadata.required_features == ("get", "set", "delete")
        assert metadata.optional_features == ("ttl", "batch_operations", "pubsub")
        assert metadata.example_providers == ("Redis", "Memcached", "Hazelcast")

    def test_default_values_for_optional_fields(self) -> None:
        """Test that optional fields have correct default values."""
        metadata = ModelCapabilityMetadata(
            capability="logging.structured",
            name="Structured Logging",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Structured logging capability",
        )

        assert metadata.tags == ()
        assert metadata.required_features == ()
        assert metadata.optional_features == ()
        assert metadata.example_providers == ()

    def test_semantic_capability_identifiers(self) -> None:
        """Test various semantic capability identifier formats."""
        identifiers = [
            "database.relational",
            "cache.memory",
            "messaging.pubsub",
            "storage.object",
            "auth.oauth2",
            "compute.serverless",
        ]

        for cap_id in identifiers:
            metadata = ModelCapabilityMetadata(
                capability=cap_id,
                name=f"Test {cap_id}",
                version=ModelSemVer(major=1, minor=0, patch=0),
                description=f"Description for {cap_id}",
            )
            assert metadata.capability == cap_id


@pytest.mark.unit
class TestModelCapabilityMetadataFrozen:
    """Tests for frozen (immutability) behavior."""

    def test_frozen_model_prevents_attribute_modification(self) -> None:
        """Test that frozen model prevents modification of attributes."""
        metadata = ModelCapabilityMetadata(
            capability="test.capability",
            name="Test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test description",
        )

        with pytest.raises(ValidationError):
            metadata.capability = "modified.capability"  # type: ignore[misc]

    def test_frozen_model_prevents_name_modification(self) -> None:
        """Test that frozen model prevents modification of name."""
        metadata = ModelCapabilityMetadata(
            capability="test.capability",
            name="Original Name",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test description",
        )

        with pytest.raises(ValidationError):
            metadata.name = "Modified Name"  # type: ignore[misc]

    def test_frozen_model_prevents_version_modification(self) -> None:
        """Test that frozen model prevents modification of version."""
        metadata = ModelCapabilityMetadata(
            capability="test.capability",
            name="Test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test description",
        )

        with pytest.raises(ValidationError):
            metadata.version = ModelSemVer(major=2, minor=0, patch=0)  # type: ignore[misc]

    def test_frozen_model_prevents_tags_modification(self) -> None:
        """Test that frozen model prevents modification of tags."""
        metadata = ModelCapabilityMetadata(
            capability="test.capability",
            name="Test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test description",
            tags=("original",),
        )

        with pytest.raises(ValidationError):
            metadata.tags = ("modified",)  # type: ignore[misc]


@pytest.mark.unit
class TestModelCapabilityMetadataExtraForbid:
    """Tests for extra='forbid' behavior."""

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                capability="test.capability",
                name="Test",
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Test description",
                unknown_field="should fail",  # type: ignore[call-arg]
            )

        # Verify the error is about the extra field
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "extra_forbidden"
        assert "unknown_field" in str(errors[0])

    def test_multiple_extra_fields_rejected(self) -> None:
        """Test that multiple extra fields are all rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                capability="test.capability",
                name="Test",
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Test description",
                extra1="value1",  # type: ignore[call-arg]
                extra2="value2",  # type: ignore[call-arg]
            )

        errors = exc_info.value.errors()
        assert len(errors) == 2


@pytest.mark.unit
class TestModelCapabilityMetadataRequiredFields:
    """Tests for required field validation."""

    def test_missing_capability_raises_error(self) -> None:
        """Test that missing capability field raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                name="Test",  # type: ignore[call-arg]
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Test description",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("capability",) for e in errors)

    def test_missing_name_raises_error(self) -> None:
        """Test that missing name field raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                capability="test.capability",  # type: ignore[call-arg]
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Test description",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_missing_version_raises_error(self) -> None:
        """Test that missing version field raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                capability="test.capability",  # type: ignore[call-arg]
                name="Test",
                description="Test description",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("version",) for e in errors)

    def test_missing_description_raises_error(self) -> None:
        """Test that missing description field raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                capability="test.capability",  # type: ignore[call-arg]
                name="Test",
                version=ModelSemVer(major=1, minor=0, patch=0),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("description",) for e in errors)

    def test_all_required_fields_missing_raises_error(self) -> None:
        """Test that missing all required fields raises validation errors."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        # Should have errors for all 4 required fields
        assert len(errors) == 4


@pytest.mark.unit
class TestModelCapabilityMetadataSerialization:
    """Tests for serialization and deserialization."""

    def test_serialization_to_dict(self) -> None:
        """Test serialization to dictionary."""
        metadata = ModelCapabilityMetadata(
            capability="test.capability",
            name="Test Capability",
            version=ModelSemVer(major=1, minor=2, patch=3),
            description="A test capability",
            tags=("tag1", "tag2"),
            required_features=("feature1",),
            optional_features=("opt1",),
            example_providers=("Provider1",),
        )

        data = metadata.model_dump()

        assert data["capability"] == "test.capability"
        assert data["name"] == "Test Capability"
        assert data["version"]["major"] == 1
        assert data["version"]["minor"] == 2
        assert data["version"]["patch"] == 3
        assert data["description"] == "A test capability"
        # Tuples become lists in dict serialization
        assert data["tags"] == ("tag1", "tag2")
        assert data["required_features"] == ("feature1",)
        assert data["optional_features"] == ("opt1",)
        assert data["example_providers"] == ("Provider1",)

    def test_serialization_to_json(self) -> None:
        """Test serialization to JSON string."""
        metadata = ModelCapabilityMetadata(
            capability="json.test",
            name="JSON Test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test JSON serialization",
        )

        json_str = metadata.model_dump_json()

        assert isinstance(json_str, str)
        assert "json.test" in json_str
        assert "JSON Test" in json_str
        assert "Test JSON serialization" in json_str

    def test_deserialization_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "capability": "restored.capability",
            "name": "Restored Capability",
            "version": {"major": 2, "minor": 1, "patch": 0},
            "description": "Restored from dict",
            "tags": ["tag1", "tag2"],  # Lists should be converted to tuples
            "required_features": ["req1"],
            "optional_features": [],
            "example_providers": ["Provider"],
        }

        metadata = ModelCapabilityMetadata.model_validate(data)

        assert metadata.capability == "restored.capability"
        assert metadata.name == "Restored Capability"
        assert metadata.version == ModelSemVer(major=2, minor=1, patch=0)
        assert metadata.description == "Restored from dict"
        assert metadata.tags == ("tag1", "tag2")
        assert metadata.required_features == ("req1",)
        assert metadata.optional_features == ()
        assert metadata.example_providers == ("Provider",)

    def test_roundtrip_serialization(self) -> None:
        """Test that serialization and deserialization are reversible."""
        original = ModelCapabilityMetadata(
            capability="roundtrip.test",
            name="Roundtrip Test",
            version=ModelSemVer(major=3, minor=2, patch=1),
            description="Testing roundtrip serialization",
            tags=("a", "b", "c"),
            required_features=("x", "y"),
            optional_features=("z",),
            example_providers=("P1", "P2"),
        )

        # Serialize and deserialize
        data = original.model_dump()
        restored = ModelCapabilityMetadata.model_validate(data)

        assert restored == original


@pytest.mark.unit
class TestModelCapabilityMetadataEquality:
    """Tests for equality and hashing behavior."""

    def test_equal_instances_are_equal(self) -> None:
        """Test that instances with same values are equal."""
        metadata1 = ModelCapabilityMetadata(
            capability="test.capability",
            name="Test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test description",
        )

        metadata2 = ModelCapabilityMetadata(
            capability="test.capability",
            name="Test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test description",
        )

        assert metadata1 == metadata2

    def test_different_capability_not_equal(self) -> None:
        """Test that instances with different capability are not equal."""
        metadata1 = ModelCapabilityMetadata(
            capability="capability.one",
            name="Test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test description",
        )

        metadata2 = ModelCapabilityMetadata(
            capability="capability.two",
            name="Test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test description",
        )

        assert metadata1 != metadata2

    def test_different_version_not_equal(self) -> None:
        """Test that instances with different version are not equal."""
        metadata1 = ModelCapabilityMetadata(
            capability="test.capability",
            name="Test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test description",
        )

        metadata2 = ModelCapabilityMetadata(
            capability="test.capability",
            name="Test",
            version=ModelSemVer(major=2, minor=0, patch=0),
            description="Test description",
        )

        assert metadata1 != metadata2

    def test_hashable_for_set_membership(self) -> None:
        """Test that instances can be used in sets."""
        metadata1 = ModelCapabilityMetadata(
            capability="test.capability",
            name="Test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test description",
        )

        metadata2 = ModelCapabilityMetadata(
            capability="test.capability",
            name="Test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test description",
        )

        metadata3 = ModelCapabilityMetadata(
            capability="other.capability",
            name="Other",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Other description",
        )

        capability_set = {metadata1, metadata2, metadata3}

        # metadata1 and metadata2 are equal, so set should have 2 elements
        assert len(capability_set) == 2

    def test_hashable_for_dict_keys(self) -> None:
        """Test that instances can be used as dictionary keys."""
        metadata = ModelCapabilityMetadata(
            capability="dict.key.test",
            name="Dict Key Test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Testing dict key usage",
        )

        cache: dict[ModelCapabilityMetadata, str] = {metadata: "cached_value"}

        assert cache[metadata] == "cached_value"


@pytest.mark.unit
class TestModelCapabilityMetadataFromAttributes:
    """Tests for from_attributes behavior (pytest-xdist compatibility)."""

    def test_from_attributes_accepts_matching_object(self) -> None:
        """Test that from_attributes allows object-based construction."""

        # Create a mock object with matching attributes
        class MockCapabilityMetadata:
            capability = "mock.capability"
            name = "Mock"
            version = ModelSemVer(major=1, minor=0, patch=0)
            description = "Mock description"
            tags = ("mock",)
            required_features = ()
            optional_features = ()
            example_providers = ()

        mock = MockCapabilityMetadata()
        metadata = ModelCapabilityMetadata.model_validate(mock)

        assert metadata.capability == "mock.capability"
        assert metadata.name == "Mock"
        assert metadata.description == "Mock description"
        assert metadata.tags == ("mock",)


@pytest.mark.unit
class TestModelCapabilityMetadataEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_strings_allowed_for_non_capability_fields(self) -> None:
        """Test that empty strings are allowed for name and description fields."""
        metadata = ModelCapabilityMetadata(
            capability="test.capability",
            name="",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="",
        )

        assert metadata.name == ""
        assert metadata.description == ""

    def test_single_element_tuples(self) -> None:
        """Test that single-element tuples work correctly."""
        metadata = ModelCapabilityMetadata(
            capability="test.capability",
            name="Test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test description",
            tags=("single",),
            required_features=("one",),
            optional_features=("only",),
            example_providers=("Provider",),
        )

        assert len(metadata.tags) == 1
        assert len(metadata.required_features) == 1
        assert len(metadata.optional_features) == 1
        assert len(metadata.example_providers) == 1

    def test_many_elements_in_tuples(self) -> None:
        """Test that tuples can hold many elements."""
        many_tags = tuple(f"tag{i}" for i in range(100))

        metadata = ModelCapabilityMetadata(
            capability="test.capability",
            name="Test",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test description",
            tags=many_tags,
        )

        assert len(metadata.tags) == 100
        assert metadata.tags[0] == "tag0"
        assert metadata.tags[99] == "tag99"

    def test_unicode_in_strings(self) -> None:
        """Test that unicode strings are handled correctly."""
        metadata = ModelCapabilityMetadata(
            capability="database.relational",
            name="Base de Donnees Relationnelle",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Operations SQL avec support UTF-8",
            tags=("base", "donnees"),
        )

        assert metadata.name == "Base de Donnees Relationnelle"
        assert "UTF-8" in metadata.description

    def test_underscores_and_numbers_in_capability(self) -> None:
        """Test that underscores and numbers in capability segments work."""
        metadata = ModelCapabilityMetadata(
            capability="my_org.service_v2.feature123",
            name="Underscores and Numbers",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Capability with underscores and numbers in segments",
        )

        assert metadata.capability == "my_org.service_v2.feature123"

    def test_prerelease_version(self) -> None:
        """Test that prerelease versions work correctly."""
        metadata = ModelCapabilityMetadata(
            capability="test.capability",
            name="Test",
            version=ModelSemVer(major=1, minor=0, patch=0, prerelease=("alpha", 1)),
            description="Test with prerelease version",
        )

        assert metadata.version.prerelease == ("alpha", 1)
        assert str(metadata.version) == "1.0.0-alpha.1"


@pytest.mark.unit
class TestModelCapabilityMetadataCapabilityFormatValidation:
    """Tests for capability field format validation."""

    def test_valid_simple_capability(self) -> None:
        """Test that simple single-segment capability is valid."""
        metadata = ModelCapabilityMetadata(
            capability="database",
            name="Database",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Database capability",
        )
        assert metadata.capability == "database"

    def test_valid_dot_separated_capability(self) -> None:
        """Test that dot-separated capability is valid."""
        metadata = ModelCapabilityMetadata(
            capability="llm.generation",
            name="LLM Generation",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="LLM text generation capability",
        )
        assert metadata.capability == "llm.generation"

    def test_valid_multi_segment_capability(self) -> None:
        """Test that multi-segment capability is valid."""
        metadata = ModelCapabilityMetadata(
            capability="compute.gpu.nvidia",
            name="NVIDIA GPU Compute",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="NVIDIA GPU compute capability",
        )
        assert metadata.capability == "compute.gpu.nvidia"

    def test_valid_capability_with_underscores(self) -> None:
        """Test that underscores in segments are valid."""
        metadata = ModelCapabilityMetadata(
            capability="storage.vector_db",
            name="Vector Database",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Vector database storage",
        )
        assert metadata.capability == "storage.vector_db"

    def test_valid_capability_with_numbers(self) -> None:
        """Test that numbers in segments are valid (after first char)."""
        metadata = ModelCapabilityMetadata(
            capability="auth.oauth2",
            name="OAuth 2.0",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="OAuth 2.0 authentication",
        )
        assert metadata.capability == "auth.oauth2"

    def test_invalid_capability_uppercase(self) -> None:
        """Test that uppercase letters are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                capability="LLM.Generation",
                name="Invalid",
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Should fail",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "capability" in str(errors[0]["loc"])
        assert "Invalid capability format" in str(errors[0]["msg"])

    def test_invalid_capability_starts_with_number(self) -> None:
        """Test that capability starting with number is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                capability="123.abc",
                name="Invalid",
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Should fail",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "capability" in str(errors[0]["loc"])

    def test_invalid_capability_starts_with_dot(self) -> None:
        """Test that capability starting with dot is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                capability=".invalid",
                name="Invalid",
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Should fail",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "capability" in str(errors[0]["loc"])

    def test_invalid_capability_ends_with_dot(self) -> None:
        """Test that capability ending with dot is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                capability="invalid.",
                name="Invalid",
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Should fail",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "capability" in str(errors[0]["loc"])

    def test_invalid_capability_empty_segment(self) -> None:
        """Test that empty segments (double dots) are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                capability="invalid..segment",
                name="Invalid",
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Should fail",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "capability" in str(errors[0]["loc"])

    def test_invalid_capability_empty_string(self) -> None:
        """Test that empty capability string is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                capability="",
                name="Invalid",
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Should fail",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "capability" in str(errors[0]["loc"])

    def test_invalid_capability_with_hyphen(self) -> None:
        """Test that hyphens are rejected (use underscores instead)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                capability="my-org.service",
                name="Invalid",
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Should fail",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "capability" in str(errors[0]["loc"])

    def test_invalid_capability_with_spaces(self) -> None:
        """Test that spaces are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                capability="invalid space",
                name="Invalid",
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Should fail",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "capability" in str(errors[0]["loc"])

    def test_invalid_capability_segment_starts_with_number(self) -> None:
        """Test that segment starting with number is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                capability="valid.2invalid",
                name="Invalid",
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Should fail",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "capability" in str(errors[0]["loc"])

    def test_invalid_capability_segment_starts_with_underscore(self) -> None:
        """Test that segment starting with underscore is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                capability="valid._invalid",
                name="Invalid",
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Should fail",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "capability" in str(errors[0]["loc"])

    def test_error_message_includes_examples(self) -> None:
        """Test that error message includes helpful examples."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityMetadata(
                capability="INVALID",
                name="Invalid",
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Should fail",
            )

        error_msg = str(exc_info.value.errors()[0]["msg"])
        assert "llm.generation" in error_msg
        assert "storage.vector_db" in error_msg
        assert "compute.gpu.nvidia" in error_msg


@pytest.mark.unit
class TestModelCapabilityMetadataImport:
    """Tests for import and module access."""

    def test_import_from_capabilities_package(self) -> None:
        """Test that model can be imported from capabilities package."""
        from omnibase_core.models.capabilities import ModelCapabilityMetadata

        assert ModelCapabilityMetadata is not None

    def test_import_from_model_module(self) -> None:
        """Test that model can be imported from model module directly."""
        from omnibase_core.models.capabilities.model_capability_metadata import (
            ModelCapabilityMetadata,
        )

        assert ModelCapabilityMetadata is not None

    def test_in_all_exports(self) -> None:
        """Test that model is in __all__ exports."""
        from omnibase_core.models.capabilities import __all__

        assert "ModelCapabilityMetadata" in __all__
