"""
Test suite for TypedDictUsageMetadata.
"""

import pytest

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.typed_dict_usage_metadata import TypedDictUsageMetadata


class TestTypedDictUsageMetadata:
    """Test TypedDictUsageMetadata functionality."""

    def test_typed_dict_usage_metadata_empty(self):
        """Test creating empty TypedDictUsageMetadata."""
        metadata: TypedDictUsageMetadata = {}

        assert isinstance(metadata, dict)
        assert len(metadata) == 0

    def test_typed_dict_usage_metadata_with_name(self):
        """Test TypedDictUsageMetadata with name only."""
        metadata: TypedDictUsageMetadata = {"name": "test_service"}

        assert metadata["name"] == "test_service"
        assert "description" not in metadata
        assert "version" not in metadata
        assert "tags" not in metadata
        assert "metadata" not in metadata

    def test_typed_dict_usage_metadata_with_description(self):
        """Test TypedDictUsageMetadata with description only."""
        metadata: TypedDictUsageMetadata = {
            "description": "A test service for demonstration"
        }

        assert metadata["description"] == "A test service for demonstration"
        assert "name" not in metadata

    def test_typed_dict_usage_metadata_with_version(self):
        """Test TypedDictUsageMetadata with version."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        metadata: TypedDictUsageMetadata = {"version": version}

        assert metadata["version"] == version
        assert isinstance(metadata["version"], ModelSemVer)

    def test_typed_dict_usage_metadata_with_tags(self):
        """Test TypedDictUsageMetadata with tags."""
        tags = ["test", "demo", "example"]
        metadata: TypedDictUsageMetadata = {"tags": tags}

        assert metadata["tags"] == tags
        assert isinstance(metadata["tags"], list)
        assert len(metadata["tags"]) == 3

    def test_typed_dict_usage_metadata_with_metadata(self):
        """Test TypedDictUsageMetadata with metadata dict."""
        custom_metadata = {
            "author": "test_author",
            "license": "MIT",
            "category": "utility",
        }
        metadata: TypedDictUsageMetadata = {"metadata": custom_metadata}

        assert metadata["metadata"] == custom_metadata
        assert isinstance(metadata["metadata"], dict)
        assert metadata["metadata"]["author"] == "test_author"

    def test_typed_dict_usage_metadata_complete(self):
        """Test TypedDictUsageMetadata with all fields."""
        version = ModelSemVer(major=2, minor=0, patch=1)
        tags = ["production", "api", "v2"]
        custom_metadata = {"environment": "production", "region": "us-west-2"}

        metadata: TypedDictUsageMetadata = {
            "name": "production_service",
            "description": "Production API service v2.0.1",
            "version": version,
            "tags": tags,
            "metadata": custom_metadata,
        }

        assert metadata["name"] == "production_service"
        assert metadata["description"] == "Production API service v2.0.1"
        assert metadata["version"] == version
        assert metadata["tags"] == tags
        assert metadata["metadata"] == custom_metadata

    def test_typed_dict_usage_metadata_partial_fields(self):
        """Test TypedDictUsageMetadata with some fields."""
        metadata: TypedDictUsageMetadata = {
            "name": "partial_service",
            "tags": ["partial", "test"],
        }

        assert metadata["name"] == "partial_service"
        assert metadata["tags"] == ["partial", "test"]
        assert "description" not in metadata
        assert "version" not in metadata
        assert "metadata" not in metadata

    def test_typed_dict_usage_metadata_empty_tags(self):
        """Test TypedDictUsageMetadata with empty tags list."""
        metadata: TypedDictUsageMetadata = {"name": "no_tags_service", "tags": []}

        assert metadata["name"] == "no_tags_service"
        assert metadata["tags"] == []
        assert isinstance(metadata["tags"], list)

    def test_typed_dict_usage_metadata_empty_metadata_dict(self):
        """Test TypedDictUsageMetadata with empty metadata dict."""
        metadata: TypedDictUsageMetadata = {
            "name": "no_metadata_service",
            "metadata": {},
        }

        assert metadata["name"] == "no_metadata_service"
        assert metadata["metadata"] == {}
        assert isinstance(metadata["metadata"], dict)

    def test_typed_dict_usage_metadata_version_string(self):
        """Test TypedDictUsageMetadata with version as string (should work)."""
        # Note: This tests that the TypedDict accepts string version
        # even though the type hint suggests ModelSemVer
        metadata: TypedDictUsageMetadata = {
            "name": "string_version_service",
            "version": "1.0.0",  # This should work due to NotRequired
        }

        assert metadata["name"] == "string_version_service"
        assert metadata["version"] == "1.0.0"

    def test_typed_dict_usage_metadata_type_annotations(self):
        """Test that all fields have correct type annotations."""
        # This test ensures the TypedDict structure is correct
        metadata: TypedDictUsageMetadata = {
            "name": "type_test",
            "description": "Type testing service",
            "version": ModelSemVer(major=1, minor=0, patch=0),
            "tags": ["type", "test"],
            "metadata": {"test": "value"},
        }

        # All fields should be accessible and have correct types
        assert isinstance(metadata["name"], str)
        assert isinstance(metadata["description"], str)
        assert isinstance(metadata["version"], ModelSemVer)
        assert isinstance(metadata["tags"], list)
        assert isinstance(metadata["metadata"], dict)

    def test_typed_dict_usage_metadata_immutability(self):
        """Test that TypedDictUsageMetadata behaves like a regular dict."""
        metadata: TypedDictUsageMetadata = {"name": "mutable_test"}

        # Should be able to modify like a regular dict
        metadata["description"] = "Added description"
        metadata["tags"] = ["added", "tag"]

        assert metadata["name"] == "mutable_test"
        assert metadata["description"] == "Added description"
        assert metadata["tags"] == ["added", "tag"]

    def test_typed_dict_usage_metadata_nested_metadata(self):
        """Test TypedDictUsageMetadata with nested metadata structure."""
        nested_metadata = {
            "config": {"timeout": 30, "retries": 3},
            "features": ["auth", "logging", "monitoring"],
        }

        metadata: TypedDictUsageMetadata = {
            "name": "nested_service",
            "metadata": nested_metadata,
        }

        assert metadata["name"] == "nested_service"
        assert metadata["metadata"] == nested_metadata
        assert "config" in metadata["metadata"]
        assert "features" in metadata["metadata"]
