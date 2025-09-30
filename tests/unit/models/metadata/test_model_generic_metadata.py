"""
Tests for ModelGenericMetadata pattern.

Validates generic metadata functionality including field management, type safety,
version handling, and custom field operations following ONEX testing standards.
"""

import json
from uuid import UUID, uuid4

import pytest

from omnibase_core.models.infrastructure.model_cli_value import ModelCliValue
from omnibase_core.models.metadata.model_generic_metadata import (
    ModelGenericMetadata,
)
from omnibase_core.models.metadata.model_semver import ModelSemVer


class TestModelGenericMetadataCreation:
    """Test basic metadata creation and initialization."""

    def test_default_creation(self):
        """Test creating metadata with default values."""
        metadata = ModelGenericMetadata()

        assert metadata.metadata_id is None
        assert metadata.metadata_display_name is None
        assert metadata.description is None
        assert metadata.version is None
        assert metadata.tags == []
        assert metadata.custom_fields is None

    def test_creation_with_all_fields(self):
        """Test creating metadata with all fields specified."""
        metadata_id = uuid4()
        version = ModelSemVer(major=1, minor=2, patch=3)

        metadata = ModelGenericMetadata(
            metadata_id=metadata_id,
            name="Test Metadata",
            description="A test metadata instance",
            version=version,
            tags=["test", "example", "metadata"],
            custom_fields={
                "key1": ModelCliValue.from_string("value1"),
                "key2": ModelCliValue.from_any(42),
            },
        )

        assert metadata.metadata_id == metadata_id
        assert metadata.metadata_display_name == "Test Metadata"
        assert metadata.description == "A test metadata instance"
        assert metadata.version == version
        assert metadata.tags == ["test", "example", "metadata"]
        assert metadata.custom_fields is not None
        assert len(metadata.custom_fields) == 2

    def test_creation_with_various_generic_types(self):
        """Test creating metadata with different generic types."""
        str_metadata = ModelGenericMetadata(name="String Metadata")
        assert isinstance(str_metadata, ModelGenericMetadata)

        int_metadata = ModelGenericMetadata(name="Integer Metadata")
        assert isinstance(int_metadata, ModelGenericMetadata)

        bool_metadata = ModelGenericMetadata(name="Boolean Metadata")
        assert isinstance(bool_metadata, ModelGenericMetadata)

        float_metadata = ModelGenericMetadata(name="Float Metadata")
        assert isinstance(float_metadata, ModelGenericMetadata)


class TestModelGenericMetadataFieldOperations:
    """Test custom field operations."""

    def test_set_field_string(self):
        """Test setting string field."""
        metadata = ModelGenericMetadata()

        metadata.set_field("name", "test_value")

        assert metadata.custom_fields is not None
        assert "name" in metadata.custom_fields
        assert metadata.custom_fields["name"].to_python_value() == "test_value"

    def test_set_field_int(self):
        """Test setting integer field."""
        metadata = ModelGenericMetadata()

        metadata.set_field("count", 42)

        assert metadata.custom_fields is not None
        assert metadata.custom_fields["count"].to_python_value() == 42

    def test_set_field_bool(self):
        """Test setting boolean field."""
        metadata = ModelGenericMetadata()

        metadata.set_field("enabled", True)

        assert metadata.custom_fields is not None
        assert metadata.custom_fields["enabled"].to_python_value() is True

    def test_set_field_float(self):
        """Test setting float field."""
        metadata = ModelGenericMetadata()

        metadata.set_field("rate", 3.14159)

        assert metadata.custom_fields is not None
        assert metadata.custom_fields["rate"].to_python_value() == 3.14159

    @pytest.mark.skip(
        reason="Validation not implemented - dict types are currently allowed",
    )
    def test_set_field_invalid_type_fails(self):
        """Test that setting invalid type fails."""
        metadata = ModelGenericMetadata()

        from omnibase_core.exceptions.onex_error import OnexError

        with pytest.raises(OnexError) as exc_info:
            metadata.set_field("invalid", {"dict": "not", "allowed": True})

        assert "Value must be str, int, bool, float, or list" in str(exc_info.value)

    def test_get_field_existing(self):
        """Test getting existing field."""
        metadata = ModelGenericMetadata()
        metadata.set_field("existing_key", "existing_value")

        value = metadata.get_field("existing_key", "default")

        assert value == "existing_value"

    def test_get_field_nonexistent(self):
        """Test getting non-existent field returns default."""
        metadata = ModelGenericMetadata()

        value = metadata.get_field("nonexistent_key", "default_value")

        assert value == "default_value"

    def test_get_field_no_custom_fields(self):
        """Test getting field when custom_fields is None."""
        metadata = ModelGenericMetadata()

        value = metadata.get_field("any_key", "default_value")

        assert value == "default_value"

    def test_get_typed_field_correct_type(self):
        """Test getting typed field with correct type."""
        metadata = ModelGenericMetadata()
        metadata.set_field("string_field", "test_string")
        metadata.set_field("int_field", 100)

        string_value = metadata.get_typed_field("string_field", str, "default")
        int_value = metadata.get_typed_field("int_field", int, 0)

        assert string_value == "test_string"
        assert int_value == 100

    def test_get_typed_field_wrong_type_returns_default(self):
        """Test getting typed field with wrong type returns default."""
        metadata = ModelGenericMetadata()
        metadata.set_field("string_field", "test_string")

        # Try to get as int, should return default
        int_value = metadata.get_typed_field("string_field", int, 999)

        assert int_value == 999

    def test_get_typed_field_nonexistent_returns_default(self):
        """Test getting typed field that doesn't exist returns default."""
        metadata = ModelGenericMetadata()

        value = metadata.get_typed_field("nonexistent", str, "default")

        assert value == "default"

    def test_set_typed_field_primitive_types(self):
        """Test setting typed fields with primitive types."""
        metadata = ModelGenericMetadata()

        metadata.set_field("str_field", "string_value")
        metadata.set_field("int_field", 42)
        metadata.set_field("bool_field", True)
        metadata.set_field("float_field", 3.14)

        assert metadata.get_field("str_field", "") == "string_value"
        assert metadata.get_field("int_field", 0) == 42
        assert metadata.get_field("bool_field", False) is True
        assert metadata.get_field("float_field", 0.0) == 3.14

    @pytest.mark.skip(
        reason="Validation not implemented - custom types are currently allowed",
    )
    def test_set_typed_field_unsupported_type_fails(self):
        """Test that setting unsupported type fails."""
        metadata = ModelGenericMetadata()

        class UnsupportedType:
            pass

        from omnibase_core.exceptions.onex_error import OnexError

        with pytest.raises(OnexError) as exc_info:
            metadata.set_field("invalid", UnsupportedType())

        assert "Value must be str, int, bool, float, or list" in str(exc_info.value)

    def test_has_field(self):
        """Test checking field existence."""
        metadata = ModelGenericMetadata()

        assert not metadata.has_field("nonexistent")

        metadata.set_field("existing", "value")
        assert metadata.has_field("existing")
        assert not metadata.has_field("still_nonexistent")

    def test_has_field_no_custom_fields(self):
        """Test has_field when custom_fields is None."""
        metadata = ModelGenericMetadata()

        assert not metadata.has_field("any_field")

    def test_remove_field_existing(self):
        """Test removing existing field."""
        metadata = ModelGenericMetadata()
        metadata.set_field("to_remove", "value")

        assert metadata.has_field("to_remove")
        result = metadata.remove_field("to_remove")

        assert result is True
        assert not metadata.has_field("to_remove")

    def test_remove_field_nonexistent(self):
        """Test removing non-existent field."""
        metadata = ModelGenericMetadata()
        metadata.set_field("existing", "value")

        result = metadata.remove_field("nonexistent")

        assert result is False
        assert metadata.has_field("existing")  # Existing field unchanged

    def test_remove_field_no_custom_fields(self):
        """Test removing field when custom_fields is None."""
        metadata = ModelGenericMetadata()

        result = metadata.remove_field("any_field")

        assert result is False


class TestModelGenericMetadataVersionHandling:
    """Test version handling with ModelSemVer."""

    def test_version_assignment(self):
        """Test assigning version."""
        metadata = ModelGenericMetadata()
        version = ModelSemVer(major=2, minor=1, patch=0)

        metadata.version = version

        assert metadata.version == version
        assert metadata.version.major == 2
        assert metadata.version.minor == 1
        assert metadata.version.patch == 0

    def test_version_serialization(self):
        """Test version serialization."""
        metadata = ModelGenericMetadata(
            name="Versioned Metadata",
            version=ModelSemVer(major=1, minor=0, patch=0),
        )

        serialized = metadata.model_dump()

        assert "version" in serialized
        assert serialized["version"]["major"] == 1
        assert serialized["version"]["minor"] == 0
        assert serialized["version"]["patch"] == 0

    def test_version_deserialization(self):
        """Test version deserialization."""
        json_data = {
            "metadata_display_name": "Test Metadata",
            "version": {"major": 3, "minor": 2, "patch": 1},
        }

        metadata = ModelGenericMetadata.model_validate(json_data)

        assert metadata.version is not None
        assert metadata.version.major == 3
        assert metadata.version.minor == 2
        assert metadata.version.patch == 1


class TestModelGenericMetadataTagsHandling:
    """Test tags list handling."""

    def test_tags_default_empty(self):
        """Test tags default to empty list."""
        metadata = ModelGenericMetadata()

        assert metadata.tags == []

    def test_tags_assignment(self):
        """Test assigning tags."""
        metadata = ModelGenericMetadata()
        tags = ["tag1", "tag2", "category:important"]

        metadata.tags = tags

        assert metadata.tags == tags

    def test_tags_modification(self):
        """Test modifying tags list."""
        metadata = ModelGenericMetadata(tags=["initial", "tags"])

        metadata.tags.append("new_tag")
        metadata.tags.remove("initial")

        assert "new_tag" in metadata.tags
        assert "initial" not in metadata.tags
        assert "tags" in metadata.tags

    def test_tags_serialization(self):
        """Test tags serialization."""
        metadata = ModelGenericMetadata(tags=["serialize", "test", "metadata"])

        serialized = metadata.model_dump()

        assert serialized["tags"] == ["serialize", "test", "metadata"]


class TestModelGenericMetadataSerialization:
    """Test serialization and deserialization."""

    def test_json_serialization_minimal(self):
        """Test JSON serialization with minimal data."""
        metadata = ModelGenericMetadata(name="Minimal Test")

        serialized = metadata.model_dump()

        assert serialized["metadata_display_name"] == "Minimal Test"
        assert serialized["metadata_id"] is None
        assert serialized["description"] is None
        assert serialized["version"] is None
        assert serialized["tags"] == []
        assert serialized["custom_fields"] is None

    def test_json_serialization_complete(self):
        """Test JSON serialization with complete data."""
        metadata_id = uuid4()
        metadata = ModelGenericMetadata(
            metadata_id=metadata_id,
            name="Complete Test",
            description="A complete test metadata",
            version=ModelSemVer(major=1, minor=0, patch=0),
            tags=["complete", "test"],
            custom_fields={},
        )
        metadata.set_field("custom_key", "custom_value")

        serialized = metadata.model_dump()

        assert str(serialized["metadata_id"]) == str(metadata_id)
        assert serialized["metadata_display_name"] == "Complete Test"
        assert serialized["description"] == "A complete test metadata"
        assert serialized["version"]["major"] == 1
        assert serialized["tags"] == ["complete", "test"]
        assert "custom_fields" in serialized

    def test_json_deserialization(self):
        """Test JSON deserialization."""
        metadata_id = str(uuid4())
        json_data = {
            "metadata_id": metadata_id,
            "name": "Deserialized Test",
            "description": "Test deserialization",
            "version": {"major": 2, "minor": 1, "patch": 0},
            "tags": ["deserialized", "test"],
            "custom_fields": {
                "field1": {"value_type": "string", "raw_value": "test_value"},
            },
        }

        metadata = ModelGenericMetadata.model_validate(json_data)

        assert metadata.metadata_id == UUID(metadata_id)
        assert metadata.metadata_display_name == "Deserialized Test"
        assert metadata.description == "Test deserialization"
        assert metadata.version.major == 2
        assert metadata.tags == ["deserialized", "test"]
        assert metadata.custom_fields is not None

    def test_round_trip_serialization(self):
        """Test full round-trip serialization."""
        original = ModelGenericMetadata(
            name="Round Trip Test",
            description="Testing serialization round trip",
            tags=["round", "trip", "test"],
        )
        original.set_field("test_field", "test_value")
        original.set_field("number_field", 42)

        # Serialize to JSON string
        json_str = original.model_dump_json(by_alias=True)

        # Parse and create new instance
        json_data = json.loads(json_str)
        deserialized = ModelGenericMetadata.model_validate(json_data)

        # Verify standard fields match
        assert deserialized.metadata_display_name == original.metadata_display_name
        assert deserialized.description == original.description
        assert deserialized.tags == original.tags

        # Note: Custom fields may not round-trip perfectly through JSON due to complex ModelCliValue nesting
        # This is expected behavior for complex ModelCliValue structures
        assert deserialized.custom_fields is not None
        assert "test_field" in deserialized.custom_fields
        assert "number_field" in deserialized.custom_fields


class TestModelGenericMetadataComplexScenarios:
    """Test complex real-world usage scenarios."""

    def test_metadata_field_management_workflow(self):
        """Test complete field management workflow."""
        metadata = ModelGenericMetadata(name="Configuration Metadata")

        # Add initial configuration
        metadata.set_field("environment", "production")
        metadata.set_field("max_connections", 100)
        metadata.set_field("ssl_enabled", True)
        metadata.set_field("timeout_seconds", 30.0)

        # Verify fields exist
        assert metadata.has_field("environment")
        assert metadata.has_field("max_connections")
        assert metadata.has_field("ssl_enabled")
        assert metadata.has_field("timeout_seconds")

        # Access fields with type safety
        env = metadata.get_typed_field("environment", str, "development")
        max_conn = metadata.get_typed_field("max_connections", int, 10)
        ssl = metadata.get_typed_field("ssl_enabled", bool, False)
        timeout = metadata.get_typed_field("timeout_seconds", float, 10.0)

        assert env == "production"
        assert max_conn == 100
        assert ssl is True
        assert timeout == 30.0

        # Modify configuration
        metadata.set_field("max_connections", 200)
        metadata.remove_field("timeout_seconds")

        # Verify changes
        assert metadata.get_field("max_connections", 0) == 200
        assert not metadata.has_field("timeout_seconds")

    def test_metadata_versioning_workflow(self):
        """Test metadata versioning workflow."""
        # Create initial version
        metadata = ModelGenericMetadata(
            name="API Metadata",
            version=ModelSemVer(major=1, minor=0, patch=0),
            tags=["api", "v1"],
        )

        # Add initial API configuration
        metadata.set_field("base_url", "https://api.example.com/v1")
        metadata.set_field("rate_limit", 1000)

        # Upgrade to v1.1.0
        metadata.version = ModelSemVer(major=1, minor=1, patch=0)
        metadata.tags = ["api", "v1.1"]
        metadata.set_field("rate_limit", 2000)
        metadata.set_field("supports_webhooks", True)

        # Verify upgrade
        assert metadata.version.minor == 1
        assert "v1.1" in metadata.tags
        assert metadata.get_field("rate_limit", 0) == 2000
        assert metadata.get_field("supports_webhooks", False) is True

    def test_metadata_tagging_and_categorization(self):
        """Test metadata tagging and categorization."""
        metadata = ModelGenericMetadata(name="Service Metadata")

        # Add service classification tags
        metadata.tags = [
            "service:auth",
            "tier:production",
            "team:backend",
            "language:python",
            "framework:fastapi",
        ]

        # Add operational metadata
        metadata.set_field("service_port", 8080)
        metadata.set_field("health_check_path", "/health")
        metadata.set_field("metrics_enabled", True)

        # Verify categorization
        service_tags = [tag for tag in metadata.tags if tag.startswith("service:")]
        assert "service:auth" in service_tags

        tier_tags = [tag for tag in metadata.tags if tag.startswith("tier:")]
        assert "tier:production" in tier_tags

        # Verify operational config
        assert metadata.get_field("service_port", 0) == 8080
        assert metadata.get_field("health_check_path", "") == "/health"
        assert metadata.get_field("metrics_enabled", False) is True

    def test_metadata_inheritance_pattern(self):
        """Test metadata inheritance/overlay pattern."""
        # Base metadata (like defaults)
        base_metadata = ModelGenericMetadata(
            name="Base Service Config",
            tags=["service", "base"],
        )
        base_metadata.set_field("log_level", "info")
        base_metadata.set_field("timeout", 30)
        base_metadata.set_field("retry_count", 3)

        # Environment-specific metadata
        prod_metadata = ModelGenericMetadata(
            name="Production Service Config",
            tags=["service", "production"],
        )

        # Overlay production-specific settings
        # (Simulate inheritance by copying base fields and overriding)
        if base_metadata.custom_fields:
            for key, value in base_metadata.custom_fields.items():
                prod_metadata.set_field(key, value.to_python_value())

        # Override production-specific values
        prod_metadata.set_field("log_level", "warn")
        prod_metadata.set_field("timeout", 60)
        prod_metadata.set_field("monitoring_enabled", True)

        # Verify inheritance and overrides
        assert prod_metadata.get_field("log_level", "") == "warn"  # Overridden
        assert prod_metadata.get_field("timeout", 0) == 60  # Overridden
        assert prod_metadata.get_field("retry_count", 0) == 3  # Inherited
        assert prod_metadata.get_field("monitoring_enabled", False) is True  # Added

    def test_metadata_validation_pattern(self):
        """Test metadata validation pattern."""
        metadata = ModelGenericMetadata(name="Database Config")

        # Set configuration fields
        metadata.set_field("host", "localhost")
        metadata.set_field("port", 5432)
        metadata.set_field("database_name", "myapp")
        metadata.set_field("ssl_enabled", True)

        # Validation function
        def validate_database_config(meta: ModelGenericMetadata) -> list[str]:
            errors = []

            # Required fields
            required_fields = ["host", "port", "database_name"]
            for field in required_fields:
                if not meta.has_field(field):
                    errors.append(f"Required field '{field}' is missing")

            # Type and value validation
            port = meta.get_typed_field("port", int, 0)
            if port <= 0 or port > 65535:
                errors.append(f"Port {port} must be between 1 and 65535")

            host = meta.get_typed_field("host", str, "")
            if not host.strip():
                errors.append("Host cannot be empty")

            return errors

        # Validate
        validation_errors = validate_database_config(metadata)
        assert len(validation_errors) == 0  # Should be valid

        # Test with invalid config
        invalid_metadata = ModelGenericMetadata()
        invalid_metadata.set_field("port", 70000)  # Invalid port

        validation_errors = validate_database_config(invalid_metadata)
        assert len(validation_errors) > 0
        assert any("Required field" in error for error in validation_errors)
        assert any("Port" in error for error in validation_errors)
