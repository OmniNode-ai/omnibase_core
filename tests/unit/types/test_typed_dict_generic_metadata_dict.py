# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Test suite for TypedDictGenericMetadataDict.
"""

from uuid import UUID, uuid4

import pytest

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.typed_dict_generic_metadata_dict import (
    TypedDictGenericMetadataDict,
)


@pytest.mark.unit
class TestTypedDictGenericMetadataDict:
    """Test TypedDictGenericMetadataDict functionality."""

    def test_typed_dict_generic_metadata_dict_empty(self):
        """Test creating empty TypedDictGenericMetadataDict."""
        metadata: TypedDictGenericMetadataDict = {}

        # All fields are optional, so empty dict should be valid
        assert isinstance(metadata, dict)

    def test_typed_dict_generic_metadata_dict_with_all_fields(self):
        """Test TypedDictGenericMetadataDict with all fields."""
        metadata_id = uuid4()
        version = ModelSemVer(major=1, minor=2, patch=3)

        metadata: TypedDictGenericMetadataDict = {
            "metadata_id": metadata_id,
            "metadata_display_name": "Test Metadata",
            "description": "Test description",
            "version": version,
            "tags": ["test", "metadata", "example"],
            "custom_fields": {"key1": "value1", "key2": 42, "key3": True},
        }

        assert metadata["metadata_id"] == metadata_id
        assert metadata["metadata_display_name"] == "Test Metadata"
        assert metadata["description"] == "Test description"
        assert metadata["version"] == version
        assert metadata["tags"] == ["test", "metadata", "example"]
        assert metadata["custom_fields"]["key1"] == "value1"
        assert metadata["custom_fields"]["key2"] == 42
        assert metadata["custom_fields"]["key3"] is True

    def test_typed_dict_generic_metadata_dict_partial_fields(self):
        """Test TypedDictGenericMetadataDict with partial fields."""
        metadata: TypedDictGenericMetadataDict = {
            "metadata_display_name": "Partial Metadata",
            "tags": ["partial"],
            "custom_fields": {"status": "active"},
        }

        assert metadata["metadata_display_name"] == "Partial Metadata"
        assert metadata["tags"] == ["partial"]
        assert metadata["custom_fields"]["status"] == "active"
        # Other fields should be None or not present

    def test_typed_dict_generic_metadata_dict_field_types(self):
        """Test that all fields have correct types."""
        metadata_id = uuid4()
        version = ModelSemVer(major=2, minor=0, patch=1)

        metadata: TypedDictGenericMetadataDict = {
            "metadata_id": metadata_id,
            "metadata_display_name": "Type Test",
            "description": "Testing types",
            "version": version,
            "tags": ["type", "test"],
            "custom_fields": {"number": 123, "boolean": False},
        }

        assert isinstance(metadata["metadata_id"], UUID)
        assert isinstance(metadata["metadata_display_name"], str)
        assert isinstance(metadata["description"], str)
        assert isinstance(metadata["version"], ModelSemVer)
        assert isinstance(metadata["tags"], list)
        assert isinstance(metadata["custom_fields"], dict)

    def test_typed_dict_generic_metadata_dict_empty_tags(self):
        """Test TypedDictGenericMetadataDict with empty tags list."""
        metadata: TypedDictGenericMetadataDict = {
            "metadata_display_name": "No Tags",
            "tags": [],
            "custom_fields": {},
        }

        assert metadata["tags"] == []
        assert len(metadata["tags"]) == 0

    def test_typed_dict_generic_metadata_dict_multiple_tags(self):
        """Test TypedDictGenericMetadataDict with multiple tags."""
        metadata: TypedDictGenericMetadataDict = {
            "metadata_display_name": "Multi Tag",
            "tags": ["tag1", "tag2", "tag3", "production", "v1.0"],
            "custom_fields": {"priority": "high"},
        }

        assert len(metadata["tags"]) == 5
        assert "tag1" in metadata["tags"]
        assert "production" in metadata["tags"]
        assert "v1.0" in metadata["tags"]

    def test_typed_dict_generic_metadata_dict_complex_custom_fields(self):
        """Test TypedDictGenericMetadataDict with complex custom fields."""
        metadata: TypedDictGenericMetadataDict = {
            "metadata_display_name": "Complex Fields",
            "tags": ["complex"],
            "custom_fields": {
                "string_field": "test",
                "number_field": 42.5,
                "boolean_field": True,
                "list_field": [1, 2, 3],
                "dict_field": {"nested": "value"},
                "none_field": None,
            },
        }

        custom_fields = metadata["custom_fields"]
        assert custom_fields["string_field"] == "test"
        assert custom_fields["number_field"] == 42.5
        assert custom_fields["boolean_field"] is True
        assert custom_fields["list_field"] == [1, 2, 3]
        assert custom_fields["dict_field"]["nested"] == "value"
        assert custom_fields["none_field"] is None

    def test_typed_dict_generic_metadata_dict_version_handling(self):
        """Test TypedDictGenericMetadataDict with different version scenarios."""
        version1 = ModelSemVer(major=1, minor=0, patch=0)
        version2 = ModelSemVer(major=2, minor=1, patch=5)

        metadata1: TypedDictGenericMetadataDict = {
            "metadata_display_name": "Version 1",
            "version": version1,
            "tags": ["v1"],
            "custom_fields": {},
        }

        metadata2: TypedDictGenericMetadataDict = {
            "metadata_display_name": "Version 2",
            "version": version2,
            "tags": ["v2"],
            "custom_fields": {},
        }

        assert metadata1["version"] == version1
        assert metadata2["version"] == version2
        assert metadata1["version"].major == 1
        assert metadata2["version"].major == 2

    def test_typed_dict_generic_metadata_dict_none_values(self):
        """Test TypedDictGenericMetadataDict with None values."""
        metadata: TypedDictGenericMetadataDict = {
            "metadata_id": None,
            "metadata_display_name": None,
            "description": None,
            "version": None,
            "tags": [],
            "custom_fields": {},
        }

        assert metadata["metadata_id"] is None
        assert metadata["metadata_display_name"] is None
        assert metadata["description"] is None
        assert metadata["version"] is None

    def test_typed_dict_generic_metadata_dict_metadata_id_variations(self):
        """Test TypedDictGenericMetadataDict with different metadata_id scenarios."""
        metadata_id1 = uuid4()
        metadata_id2 = uuid4()

        metadata1: TypedDictGenericMetadataDict = {
            "metadata_id": metadata_id1,
            "metadata_display_name": "With ID 1",
            "tags": ["id1"],
            "custom_fields": {},
        }

        metadata2: TypedDictGenericMetadataDict = {
            "metadata_id": metadata_id2,
            "metadata_display_name": "With ID 2",
            "tags": ["id2"],
            "custom_fields": {},
        }

        assert metadata1["metadata_id"] == metadata_id1
        assert metadata2["metadata_id"] == metadata_id2
        assert metadata1["metadata_id"] != metadata2["metadata_id"]
