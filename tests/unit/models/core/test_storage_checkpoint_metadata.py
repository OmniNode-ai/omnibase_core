"""Comprehensive tests for ModelStorageCheckpointMetadata.

Tests cover:
- Basic instantiation with valid data
- Default values
- Immutability (frozen=True)
- from_attributes=True (creation from object with attributes)
- Integration with ModelCheckpointData
"""

from dataclasses import dataclass
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_checkpoint_status import EnumCheckpointStatus
from omnibase_core.enums.enum_checkpoint_type import EnumCheckpointType
from omnibase_core.models.core.model_checkpoint_data import ModelCheckpointData
from omnibase_core.models.core.model_storage_checkpoint_metadata import (
    ModelStorageCheckpointMetadata,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Rebuild ModelCheckpointData to resolve forward reference to SerializedDict
ModelCheckpointData.model_rebuild()


# =============================================================================
# Basic Instantiation Tests
# =============================================================================


@pytest.mark.unit
class TestModelStorageCheckpointMetadataBasicInstantiation:
    """Test basic instantiation of ModelStorageCheckpointMetadata."""

    def test_instantiation_with_all_fields(self) -> None:
        """Test creating metadata with all fields populated."""
        metadata = ModelStorageCheckpointMetadata(
            source="workflow_step_1",
            environment="production",
            tags=["critical", "backup"],
            labels={"team": "platform", "priority": "high"},
            description="Checkpoint after data transformation",
            parent_checkpoint_id="parent-123",
            retention_policy="30-days",
        )

        assert metadata.source == "workflow_step_1"
        assert metadata.environment == "production"
        assert metadata.tags == ["critical", "backup"]
        assert metadata.labels == {"team": "platform", "priority": "high"}
        assert metadata.description == "Checkpoint after data transformation"
        assert metadata.parent_checkpoint_id == "parent-123"
        assert metadata.retention_policy == "30-days"

    def test_instantiation_minimal(self) -> None:
        """Test creating metadata with no fields (all defaults)."""
        metadata = ModelStorageCheckpointMetadata()

        assert metadata.source is None
        assert metadata.environment is None
        assert metadata.tags == []
        assert metadata.labels == {}
        assert metadata.description is None
        assert metadata.parent_checkpoint_id is None
        assert metadata.retention_policy is None

    def test_instantiation_partial_fields(self) -> None:
        """Test creating metadata with some fields populated."""
        metadata = ModelStorageCheckpointMetadata(
            source="node-compute-123",
            environment="staging",
        )

        assert metadata.source == "node-compute-123"
        assert metadata.environment == "staging"
        assert metadata.tags == []
        assert metadata.labels == {}


# =============================================================================
# Default Values Tests
# =============================================================================


@pytest.mark.unit
class TestModelStorageCheckpointMetadataDefaultValues:
    """Test default values of ModelStorageCheckpointMetadata."""

    def test_tags_default_is_empty_list(self) -> None:
        """Test that tags defaults to empty list."""
        metadata = ModelStorageCheckpointMetadata()
        assert metadata.tags == []
        assert isinstance(metadata.tags, list)

    def test_labels_default_is_empty_dict(self) -> None:
        """Test that labels defaults to empty dict."""
        metadata = ModelStorageCheckpointMetadata()
        assert metadata.labels == {}
        assert isinstance(metadata.labels, dict)

    def test_optional_fields_default_to_none(self) -> None:
        """Test all optional fields default to None."""
        metadata = ModelStorageCheckpointMetadata()
        assert metadata.source is None
        assert metadata.environment is None
        assert metadata.description is None
        assert metadata.parent_checkpoint_id is None
        assert metadata.retention_policy is None

    def test_default_factory_creates_new_instances(self) -> None:
        """Test that default_factory creates new instances for each model."""
        metadata1 = ModelStorageCheckpointMetadata()
        metadata2 = ModelStorageCheckpointMetadata()

        # The lists and dicts should be different instances
        assert metadata1.tags is not metadata2.tags
        assert metadata1.labels is not metadata2.labels


# =============================================================================
# Immutability Tests (frozen=True)
# =============================================================================


@pytest.mark.unit
class TestModelStorageCheckpointMetadataImmutability:
    """Test immutability of ModelStorageCheckpointMetadata (frozen=True)."""

    def test_cannot_modify_source(self) -> None:
        """Test that source field cannot be modified after creation."""
        metadata = ModelStorageCheckpointMetadata(source="original")
        with pytest.raises(ValidationError):
            metadata.source = "modified"  # type: ignore[misc]

    def test_cannot_modify_environment(self) -> None:
        """Test that environment field cannot be modified after creation."""
        metadata = ModelStorageCheckpointMetadata(environment="prod")
        with pytest.raises(ValidationError):
            metadata.environment = "dev"  # type: ignore[misc]

    def test_cannot_modify_tags(self) -> None:
        """Test that tags field cannot be reassigned after creation."""
        metadata = ModelStorageCheckpointMetadata(tags=["tag1"])
        with pytest.raises(ValidationError):
            metadata.tags = ["tag2"]  # type: ignore[misc]

    def test_cannot_modify_labels(self) -> None:
        """Test that labels field cannot be reassigned after creation."""
        metadata = ModelStorageCheckpointMetadata(labels={"key": "value"})
        with pytest.raises(ValidationError):
            metadata.labels = {"new_key": "new_value"}  # type: ignore[misc]

    def test_cannot_modify_description(self) -> None:
        """Test that description field cannot be modified after creation."""
        metadata = ModelStorageCheckpointMetadata(description="original")
        with pytest.raises(ValidationError):
            metadata.description = "modified"  # type: ignore[misc]

    def test_cannot_modify_parent_checkpoint_id(self) -> None:
        """Test that parent_checkpoint_id cannot be modified after creation."""
        metadata = ModelStorageCheckpointMetadata(parent_checkpoint_id="parent-1")
        with pytest.raises(ValidationError):
            metadata.parent_checkpoint_id = "parent-2"  # type: ignore[misc]

    def test_cannot_modify_retention_policy(self) -> None:
        """Test that retention_policy cannot be modified after creation."""
        metadata = ModelStorageCheckpointMetadata(retention_policy="7-days")
        with pytest.raises(ValidationError):
            metadata.retention_policy = "30-days"  # type: ignore[misc]


# =============================================================================
# from_attributes=True Tests
# =============================================================================


@pytest.mark.unit
class TestModelStorageCheckpointMetadataFromAttributes:
    """Test from_attributes=True functionality."""

    def test_create_from_dataclass_with_all_fields(self) -> None:
        """Test creating model from a dataclass with all fields."""

        @dataclass
        class MockMetadataSource:
            source: str = "dataclass_source"
            environment: str = "test"
            tags: list[str] | None = None
            labels: dict[str, str] | None = None
            description: str = "From dataclass"
            parent_checkpoint_id: str = "dc-parent"
            retention_policy: str = "1-week"

            def __post_init__(self) -> None:
                if self.tags is None:
                    self.tags = ["dc_tag"]
                if self.labels is None:
                    self.labels = {"dc_key": "dc_value"}

        source_obj = MockMetadataSource()
        metadata = ModelStorageCheckpointMetadata.model_validate(source_obj)

        assert metadata.source == "dataclass_source"
        assert metadata.environment == "test"
        assert metadata.tags == ["dc_tag"]
        assert metadata.labels == {"dc_key": "dc_value"}
        assert metadata.description == "From dataclass"
        assert metadata.parent_checkpoint_id == "dc-parent"
        assert metadata.retention_policy == "1-week"

    def test_create_from_object_with_attributes(self) -> None:
        """Test creating model from a plain object with attributes."""

        class MockObject:
            def __init__(self) -> None:
                self.source = "obj_source"
                self.environment = "obj_env"
                self.tags = ["obj_tag"]
                self.labels = {"obj_key": "obj_value"}
                self.description = "From object"
                self.parent_checkpoint_id = None
                self.retention_policy = None

        source_obj = MockObject()
        metadata = ModelStorageCheckpointMetadata.model_validate(source_obj)

        assert metadata.source == "obj_source"
        assert metadata.environment == "obj_env"
        assert metadata.tags == ["obj_tag"]
        assert metadata.labels == {"obj_key": "obj_value"}
        assert metadata.description == "From object"

    def test_create_from_object_with_partial_attributes(self) -> None:
        """Test creating model from object with only some attributes."""

        class PartialMockObject:
            def __init__(self) -> None:
                self.source = "partial_source"
                self.environment = None
                self.tags = []
                self.labels = {}
                self.description = None
                self.parent_checkpoint_id = None
                self.retention_policy = None

        source_obj = PartialMockObject()
        metadata = ModelStorageCheckpointMetadata.model_validate(source_obj)

        assert metadata.source == "partial_source"
        assert metadata.environment is None
        assert metadata.tags == []


# =============================================================================
# Integration with ModelCheckpointData Tests
# =============================================================================


@pytest.mark.unit
class TestModelStorageCheckpointMetadataIntegration:
    """Test integration with ModelCheckpointData parent model."""

    def test_checkpoint_data_with_metadata(self) -> None:
        """Test ModelCheckpointData can contain ModelStorageCheckpointMetadata."""
        metadata = ModelStorageCheckpointMetadata(
            source="integration_test",
            environment="test",
            tags=["integration"],
            labels={"test": "true"},
        )

        checkpoint_data = ModelCheckpointData(
            checkpoint_id=uuid4(),
            workflow_id=uuid4(),
            checkpoint_type=EnumCheckpointType.MANUAL,
            status=EnumCheckpointStatus.ACTIVE,
            metadata=metadata,
            version=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert checkpoint_data.metadata is not None
        assert checkpoint_data.metadata.source == "integration_test"
        assert checkpoint_data.metadata.environment == "test"
        assert checkpoint_data.metadata.tags == ["integration"]
        assert checkpoint_data.metadata.labels == {"test": "true"}

    def test_checkpoint_data_without_metadata(self) -> None:
        """Test ModelCheckpointData with no metadata (None)."""
        checkpoint_data = ModelCheckpointData(
            checkpoint_id=uuid4(),
            workflow_id=uuid4(),
            checkpoint_type=EnumCheckpointType.AUTOMATIC,
            version=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert checkpoint_data.metadata is None

    def test_checkpoint_data_serialization_with_metadata(self) -> None:
        """Test serialization of ModelCheckpointData with metadata."""
        metadata = ModelStorageCheckpointMetadata(
            source="serialization_test",
            tags=["serialize"],
        )

        checkpoint_id = uuid4()
        workflow_id = uuid4()
        checkpoint_data = ModelCheckpointData(
            checkpoint_id=checkpoint_id,
            workflow_id=workflow_id,
            checkpoint_type=EnumCheckpointType.STEP_COMPLETION,
            metadata=metadata,
            version=ModelSemVer(major=2, minor=1, patch=0),
        )

        # Serialize to dict
        data_dict = checkpoint_data.model_dump()

        assert data_dict["metadata"]["source"] == "serialization_test"
        assert data_dict["metadata"]["tags"] == ["serialize"]
        assert data_dict["checkpoint_id"] == checkpoint_id
        assert data_dict["workflow_id"] == workflow_id


# =============================================================================
# Edge Cases and Special Scenarios
# =============================================================================


@pytest.mark.unit
class TestModelStorageCheckpointMetadataEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_string_values(self) -> None:
        """Test that empty strings are valid for optional string fields."""
        metadata = ModelStorageCheckpointMetadata(
            source="",
            environment="",
            description="",
            parent_checkpoint_id="",
            retention_policy="",
        )

        assert metadata.source == ""
        assert metadata.environment == ""
        assert metadata.description == ""

    def test_unicode_values(self) -> None:
        """Test that unicode values are handled correctly."""
        metadata = ModelStorageCheckpointMetadata(
            source="workflow-unicode",
            description="Description with unicode: test",
            tags=["tag-unicode"],
            labels={"key-unicode": "value-unicode"},
        )

        assert "unicode" in metadata.description  # type: ignore[operator]
        assert "unicode" in metadata.tags[0]

    def test_large_tags_list(self) -> None:
        """Test handling of large tags list."""
        large_tags = [f"tag_{i}" for i in range(100)]
        metadata = ModelStorageCheckpointMetadata(tags=large_tags)

        assert len(metadata.tags) == 100
        assert metadata.tags[0] == "tag_0"
        assert metadata.tags[99] == "tag_99"

    def test_large_labels_dict(self) -> None:
        """Test handling of large labels dict."""
        large_labels = {f"key_{i}": f"value_{i}" for i in range(100)}
        metadata = ModelStorageCheckpointMetadata(labels=large_labels)

        assert len(metadata.labels) == 100
        assert metadata.labels["key_0"] == "value_0"
        assert metadata.labels["key_99"] == "value_99"

    def test_model_dump_roundtrip(self) -> None:
        """Test that model_dump and model_validate roundtrip works."""
        original = ModelStorageCheckpointMetadata(
            source="roundtrip_test",
            environment="test",
            tags=["tag1", "tag2"],
            labels={"a": "1", "b": "2"},
            description="Test description",
            parent_checkpoint_id="parent-roundtrip",
            retention_policy="permanent",
        )

        # Serialize to dict and back
        data_dict = original.model_dump()
        restored = ModelStorageCheckpointMetadata.model_validate(data_dict)

        assert restored.source == original.source
        assert restored.environment == original.environment
        assert restored.tags == original.tags
        assert restored.labels == original.labels
        assert restored.description == original.description
        assert restored.parent_checkpoint_id == original.parent_checkpoint_id
        assert restored.retention_policy == original.retention_policy

    def test_model_json_roundtrip(self) -> None:
        """Test that JSON serialization roundtrip works."""
        original = ModelStorageCheckpointMetadata(
            source="json_test",
            tags=["json"],
            labels={"format": "json"},
        )

        # Serialize to JSON and back
        json_str = original.model_dump_json()
        restored = ModelStorageCheckpointMetadata.model_validate_json(json_str)

        assert restored.source == original.source
        assert restored.tags == original.tags
        assert restored.labels == original.labels
