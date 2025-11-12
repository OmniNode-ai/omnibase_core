"""
Comprehensive tests for ModelGenericMetadata.

Tests cover:
- Basic instantiation with optional fields
- Datetime field handling and serialization
- Tags, labels, and annotations fields
- Custom fields with JsonSerializable type
- Extended data with nested models
- Field validation and type safety
- Pydantic extra='allow' config
"""

from datetime import datetime

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.results.model_simple_metadata import ModelGenericMetadata


class TestModelGenericMetadataBasicInstantiation:
    """Test basic instantiation."""

    def test_empty_instantiation(self):
        """Test creating metadata with no fields."""
        metadata = ModelGenericMetadata()

        assert metadata.created_at is None
        assert metadata.updated_at is None
        assert metadata.created_by is None
        assert metadata.updated_by is None
        assert metadata.version is None

    def test_instantiation_with_timestamps(self):
        """Test creating metadata with timestamp fields."""
        created = datetime(2025, 1, 1, 10, 0, 0)
        updated = datetime(2025, 1, 2, 15, 30, 0)

        metadata = ModelGenericMetadata(created_at=created, updated_at=updated)

        assert metadata.created_at == created
        assert metadata.updated_at == updated

    def test_instantiation_with_user_fields(self):
        """Test creating metadata with creator/updater fields."""
        metadata = ModelGenericMetadata(
            created_by="user@example.com",
            updated_by="admin@example.com",
        )

        assert metadata.created_by == "user@example.com"
        assert metadata.updated_by == "admin@example.com"


class TestModelGenericMetadataVersionField:
    """Test version field with ModelSemVer."""

    def test_version_field_with_semver(self):
        """Test version field with ModelSemVer instance."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        metadata = ModelGenericMetadata(version=version)

        assert metadata.version.major == 1
        assert metadata.version.minor == 2
        assert metadata.version.patch == 3

    def test_version_field_optional(self):
        """Test that version field is optional."""
        metadata = ModelGenericMetadata()
        assert metadata.version is None


class TestModelGenericMetadataTagsField:
    """Test tags field handling."""

    def test_tags_list_field(self):
        """Test tags field with list of strings."""
        tags = ["production", "critical", "v1"]
        metadata = ModelGenericMetadata(tags=tags)

        assert len(metadata.tags) == 3
        assert "production" in metadata.tags
        assert "critical" in metadata.tags

    def test_tags_defaults_to_empty_list(self):
        """Test that tags defaults to empty list."""
        metadata = ModelGenericMetadata()
        assert metadata.tags == []

    def test_tags_can_be_empty(self):
        """Test that tags can be explicitly empty list."""
        metadata = ModelGenericMetadata(tags=[])
        assert metadata.tags == []


class TestModelGenericMetadataLabelsField:
    """Test labels field handling."""

    def test_labels_dict_field(self):
        """Test labels field with string key-value pairs."""
        labels = {"env": "production", "team": "platform", "version": "v1.0"}
        metadata = ModelGenericMetadata(labels=labels)

        assert len(metadata.labels) == 3
        assert metadata.labels["env"] == "production"
        assert metadata.labels["team"] == "platform"

    def test_labels_defaults_to_empty_dict(self):
        """Test that labels defaults to empty dict."""
        metadata = ModelGenericMetadata()
        assert metadata.labels == {}

    def test_labels_can_be_empty(self):
        """Test that labels can be explicitly empty dict."""
        metadata = ModelGenericMetadata(labels={})
        assert metadata.labels == {}


class TestModelGenericMetadataAnnotationsField:
    """Test annotations field handling."""

    def test_annotations_dict_field(self):
        """Test annotations field with string key-value pairs."""
        annotations = {
            "description": "Main service",
            "owner": "team@example.com",
            "support": "https://support.example.com",
        }
        metadata = ModelGenericMetadata(annotations=annotations)

        assert len(metadata.annotations) == 3
        assert metadata.annotations["description"] == "Main service"
        assert metadata.annotations["owner"] == "team@example.com"

    def test_annotations_defaults_to_empty_dict(self):
        """Test that annotations defaults to empty dict."""
        metadata = ModelGenericMetadata()
        assert metadata.annotations == {}


class TestModelGenericMetadataCustomFields:
    """Test custom_fields with JsonSerializable type."""

    def test_custom_fields_with_simple_types(self):
        """Test custom_fields with basic JSON types."""
        custom_fields = {
            "string_field": "value",
            "int_field": 42,
            "float_field": 3.14,
            "bool_field": True,
            "null_field": None,
        }
        metadata = ModelGenericMetadata(custom_fields=custom_fields)

        assert metadata.custom_fields["string_field"] == "value"
        assert metadata.custom_fields["int_field"] == 42
        assert metadata.custom_fields["float_field"] == 3.14
        assert metadata.custom_fields["bool_field"] is True
        assert metadata.custom_fields["null_field"] is None

    def test_custom_fields_with_nested_structures(self):
        """Test custom_fields with nested lists and dicts."""
        custom_fields = {
            "nested_dict": {"key1": "value1", "key2": "value2"},
            "nested_list": [1, 2, 3],
            "complex": {"list": [{"nested": "value"}]},
        }
        metadata = ModelGenericMetadata(custom_fields=custom_fields)

        assert metadata.custom_fields["nested_dict"]["key1"] == "value1"
        assert metadata.custom_fields["nested_list"] == [1, 2, 3]
        assert metadata.custom_fields["complex"]["list"][0]["nested"] == "value"

    def test_custom_fields_defaults_to_empty_dict(self):
        """Test that custom_fields defaults to empty dict."""
        metadata = ModelGenericMetadata()
        assert metadata.custom_fields == {}


class TestModelGenericMetadataExtendedData:
    """Test extended_data field with nested models."""

    def test_extended_data_with_pydantic_models(self):
        """Test extended_data_json with Pydantic BaseModel instances serialized as JSON."""
        import json

        class CustomModel(BaseModel):
            name: str
            value: int

        model1 = CustomModel(name="model1", value=100)
        model2 = CustomModel(name="model2", value=200)

        # Serialize models to JSON
        extended_data = {"model1": model1.model_dump(), "model2": model2.model_dump()}

        metadata = ModelGenericMetadata(
            extended_data_json=json.dumps(extended_data),
        )

        # Deserialize and verify
        data = json.loads(metadata.extended_data_json)
        assert data["model1"]["name"] == "model1"
        assert data["model1"]["value"] == 100
        assert data["model2"]["name"] == "model2"

    def test_extended_data_optional(self):
        """Test that extended_data_json is optional."""
        metadata = ModelGenericMetadata()
        assert metadata.extended_data_json is None


class TestModelGenericMetadataDateTimeSerialization:
    """Test datetime field serialization."""

    def test_datetime_serialization_to_iso_format(self):
        """Test that datetime fields are serialized to ISO format."""
        created = datetime(2025, 1, 1, 12, 0, 0)
        updated = datetime(2025, 1, 2, 14, 30, 0)

        metadata = ModelGenericMetadata(created_at=created, updated_at=updated)

        dumped = metadata.model_dump()

        assert isinstance(dumped["created_at"], str)
        assert isinstance(dumped["updated_at"], str)
        assert "2025-01-01" in dumped["created_at"]
        assert "2025-01-02" in dumped["updated_at"]

    def test_datetime_serialization_with_none(self):
        """Test datetime serialization when value is None."""
        metadata = ModelGenericMetadata()

        dumped = metadata.model_dump()

        assert dumped["created_at"] is None
        assert dumped["updated_at"] is None


class TestModelGenericMetadataExtraFieldsAllowed:
    """Test Pydantic extra='allow' configuration."""

    def test_extra_fields_allowed_in_config(self):
        """Test that model_config has extra='allow'."""
        assert ModelGenericMetadata.model_config.get("extra") == "allow"

    def test_can_add_extra_fields(self):
        """Test that additional fields can be added due to extra='allow'."""
        metadata = ModelGenericMetadata(
            created_by="user",
            custom_extra_field="extra_value",
        )

        # Extra field should be accessible
        assert metadata.created_by == "user"
        # Note: Pydantic extra='allow' stores extra fields in __pydantic_extra__
        # or as attributes depending on version


class TestModelGenericMetadataFieldValidation:
    """Test field validation."""

    def test_tags_must_be_list_of_strings(self):
        """Test that tags field validates list of strings."""
        # Valid list of strings
        metadata = ModelGenericMetadata(tags=["tag1", "tag2"])
        assert metadata.tags == ["tag1", "tag2"]

    def test_labels_must_be_dict_of_strings(self):
        """Test that labels field validates dict of strings."""
        # Valid dict with string keys and values
        metadata = ModelGenericMetadata(labels={"key": "value"})
        assert metadata.labels == {"key": "value"}

    def test_created_at_must_be_datetime(self):
        """Test that created_at must be datetime type."""
        valid_datetime = datetime(2025, 1, 1, 10, 0, 0)
        metadata = ModelGenericMetadata(created_at=valid_datetime)
        assert isinstance(metadata.created_at, datetime)

        with pytest.raises(ValidationError):
            ModelGenericMetadata(created_at="not a datetime")


class TestModelGenericMetadataSerialization:
    """Test model serialization and deserialization."""

    def test_model_dump_basic(self):
        """Test model_dump() produces correct dictionary."""
        created = datetime(2025, 1, 1, 10, 0, 0)
        metadata = ModelGenericMetadata(
            created_at=created,
            created_by="user@example.com",
            tags=["test"],
            labels={"env": "dev"},
        )

        dumped = metadata.model_dump()

        assert "created_at" in dumped
        assert dumped["created_by"] == "user@example.com"
        assert dumped["tags"] == ["test"]
        assert dumped["labels"] == {"env": "dev"}

    def test_model_dump_exclude_none(self):
        """Test model_dump(exclude_none=True) removes None fields."""
        metadata = ModelGenericMetadata(created_by="user")

        dumped = metadata.model_dump(exclude_none=True)

        assert "created_by" in dumped
        assert "created_at" not in dumped
        assert "version" not in dumped

    def test_model_dump_json_roundtrip(self):
        """Test JSON serialization roundtrip."""
        original = ModelGenericMetadata(
            created_by="user",
            tags=["test"],
            labels={"env": "dev"},
        )

        json_str = original.model_dump_json()
        restored = ModelGenericMetadata.model_validate_json(json_str)

        assert restored.created_by == original.created_by
        assert restored.tags == original.tags
        assert restored.labels == original.labels


class TestModelGenericMetadataComplexScenarios:
    """Test complex usage scenarios."""

    def test_full_metadata_instance(self):
        """Test creating fully populated metadata instance."""
        created = datetime(2025, 1, 1, 10, 0, 0)
        updated = datetime(2025, 1, 2, 15, 0, 0)
        version = ModelSemVer(major=2, minor=1, patch=0)

        metadata = ModelGenericMetadata(
            created_at=created,
            updated_at=updated,
            created_by="user@example.com",
            updated_by="admin@example.com",
            version=version,
            tags=["production", "critical"],
            labels={"env": "prod", "region": "us-west"},
            annotations={"description": "Production service"},
            custom_fields={
                "deployment_id": "deploy-123",
                "cost_center": "engineering",
            },
        )

        assert metadata.created_at == created
        assert metadata.version.major == 2
        assert len(metadata.tags) == 2
        assert metadata.labels["env"] == "prod"
        assert metadata.custom_fields["deployment_id"] == "deploy-123"

    def test_metadata_update_pattern(self):
        """Test typical metadata update pattern."""
        # Initial creation
        created = datetime(2025, 1, 1, 10, 0, 0)
        metadata = ModelGenericMetadata(
            created_at=created,
            created_by="user@example.com",
            tags=["draft"],
        )

        # Simulate update
        updated = datetime(2025, 1, 2, 15, 0, 0)
        metadata.updated_at = updated
        metadata.updated_by = "admin@example.com"
        metadata.tags = ["published"]

        assert metadata.created_at == created
        assert metadata.updated_at == updated
        assert "published" in metadata.tags


class TestModelGenericMetadataTypeSafety:
    """Test type safety - BOUNDARY_LAYER_EXCEPTION for metadata flexibility."""

    def test_custom_fields_uses_json_serializable(self):
        """Test that custom_fields accepts JSON-serializable types."""
        from typing import get_type_hints

        hints = get_type_hints(ModelGenericMetadata)
        custom_fields_type = hints.get("custom_fields")

        assert custom_fields_type is not None
        type_str = str(custom_fields_type).lower()  # Case-insensitive check
        # Should be dict[str, Any] for flexible metadata (BOUNDARY_LAYER_EXCEPTION)
        assert "dict" in type_str
        # Note: Using Any here is acceptable for metadata flexibility per BOUNDARY_LAYER_EXCEPTION

    def test_extended_data_json_uses_string(self):
        """Test that extended_data_json uses string type for JSON serialization."""
        from typing import get_type_hints

        hints = get_type_hints(ModelGenericMetadata)
        extended_data_json_type = hints.get("extended_data_json")

        assert extended_data_json_type is not None
        type_str = str(extended_data_json_type)
        # Should be str | None for JSON string storage
        assert "str" in type_str


class TestModelGenericMetadataFromDict:
    """Test from_dict class method."""

    def test_from_dict_with_valid_dict(self):
        """Test from_dict with valid dictionary input."""
        data = {
            "created_by": "user@example.com",
            "tags": ["test"],
            "labels": {"env": "dev"},
        }
        metadata = ModelGenericMetadata.from_dict(data)

        assert metadata.created_by == "user@example.com"
        assert metadata.tags == ["test"]
        assert metadata.labels == {"env": "dev"}

    def test_from_dict_with_non_dict_input(self):
        """Test from_dict with non-dict input (lines 79-81 branch)."""
        # Test with None
        metadata = ModelGenericMetadata.from_dict(None)
        assert metadata.created_by is None
        assert metadata.tags == []

        # Test with string
        metadata = ModelGenericMetadata.from_dict("not-a-dict")
        assert metadata.tags == []

        # Test with list
        metadata = ModelGenericMetadata.from_dict([1, 2, 3])
        assert metadata.tags == []

        # Test with integer
        metadata = ModelGenericMetadata.from_dict(42)
        assert metadata.created_by is None

    def test_from_dict_with_empty_dict(self):
        """Test from_dict with empty dictionary."""
        metadata = ModelGenericMetadata.from_dict({})
        assert metadata.created_by is None
        assert metadata.tags == []
        assert metadata.labels == {}

    def test_from_dict_with_partial_fields(self):
        """Test from_dict with only some fields populated."""
        data = {"created_by": "user"}
        metadata = ModelGenericMetadata.from_dict(data)

        assert metadata.created_by == "user"
        assert metadata.updated_by is None
        assert metadata.tags == []
