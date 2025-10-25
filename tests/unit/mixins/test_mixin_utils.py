"""
Tests for MixinUtils - Utility functions for metadata canonicalization.

Coverage target: 100% (single function with simple behavior)
"""

import pytest
from pydantic import BaseModel

from omnibase_core.enums import EnumNodeMetadataField
from omnibase_core.mixins.mixin_utils import canonicalize_metadata_block


class SampleMetadataModel(BaseModel):
    """Sample model for testing."""

    name: str
    version_str: str  # Using version_str to avoid string version validation
    hash: str
    last_modified_at: str
    description: str


class TestCanonicalizeMetadataBlock:
    """Test suite for canonicalize_metadata_block function."""

    def test_canonicalize_dict_basic(self):
        """Test basic canonicalization with dictionary input."""
        metadata_dict = {
            "name": "test_node",
            "version_str": "1.0.0",
            "hash": "abc123",
            "last_modified_at": "2025-01-01T00:00:00",
            "description": "Test node",
        }

        result = canonicalize_metadata_block(metadata_dict)

        # Should return YAML string
        assert isinstance(result, str)
        # Should contain ---  and ... markers
        assert "---" in result
        assert result.endswith("...\n")
        # Function creates full ONEX metadata block with defaults
        # Hash is normalized to 64 zeros, not <PLACEHOLDER>
        assert (
            "0000000000000000000000000000000000000000000000000000000000000000" in result
        )
        # Should contain non-volatile fields
        assert "test_node" in result

    def test_canonicalize_dict_returns_yaml_string(self):
        """Test that result is a valid YAML string."""
        metadata_dict = {
            "name": "test_node",
            "description": "Test description",
        }

        result = canonicalize_metadata_block(metadata_dict)

        assert isinstance(result, str)
        assert "test_node" in result
        # Validates YAML structure
        assert "---" in result
        assert "..." in result

    def test_volatile_fields_normalized(self):
        """Test that volatile fields are normalized."""
        metadata_dict = {
            "name": "test",
            "hash": "should_be_normalized",
            "last_modified_at": "should_be_normalized_too",
        }

        result = canonicalize_metadata_block(metadata_dict)

        # Volatile fields should be normalized (not appear as-is)
        assert "should_be_normalized" not in result
        assert "should_be_normalized_too" not in result
        # Hash is normalized to 64 zeros
        assert (
            "0000000000000000000000000000000000000000000000000000000000000000" in result
        )

    def test_function_accepts_custom_parameters(self):
        """Test that function accepts various custom parameters."""
        metadata_dict = {
            "name": "test",
            "description": "test description",
        }

        # Should not raise error with custom parameters
        result = canonicalize_metadata_block(
            metadata_dict,
            sort_keys=True,
            explicit_start=True,
            explicit_end=True,
        )

        assert isinstance(result, str)
        assert "test" in result

    def test_explicit_markers_control(self):
        """Test control of explicit YAML markers."""
        metadata_dict = {"name": "test"}

        # With explicit markers
        with_markers = canonicalize_metadata_block(
            metadata_dict,
            explicit_start=True,
            explicit_end=True,
            volatile_fields=(),
        )
        assert with_markers.startswith("---")
        assert with_markers.endswith("...\n")

        # Without start marker
        without_start = canonicalize_metadata_block(
            metadata_dict,
            explicit_start=False,
            explicit_end=True,
            volatile_fields=(),
        )
        assert not without_start.startswith("---")

    def test_comment_prefix(self):
        """Test adding comment prefix to each line."""
        metadata_dict = {"name": "test", "version_str": "1.0.0"}

        result = canonicalize_metadata_block(
            metadata_dict,
            comment_prefix="# ",
            volatile_fields=(),
        )

        # Each line should start with comment prefix
        lines = result.strip().split("\n")
        for line in lines:
            if line.strip():  # Skip empty lines
                assert line.startswith("# ")

    def test_empty_dict(self):
        """Test canonicalization of empty dictionary."""
        result = canonicalize_metadata_block({})

        assert isinstance(result, str)
        assert "---" in result
        # Should handle empty dict gracefully

    def test_handles_various_data_types(self):
        """Test canonicalization handles various data structures."""
        metadata_dict = {
            "name": "test",
            "description": "Test with various types",
            "hash": "will_be_normalized",
        }

        result = canonicalize_metadata_block(metadata_dict)

        assert "test" in result
        assert "Test with various types" in result
        # Hash should be normalized
        assert "will_be_normalized" not in result

    def test_unicode_handling(self):
        """Test handling of unicode characters."""
        metadata_dict = {
            "name": "test_unicode",
            "description": "Test with ü, é, and 中文",
        }

        result = canonicalize_metadata_block(
            metadata_dict,
            allow_unicode=True,
            volatile_fields=(),
        )

        # Unicode characters should be preserved
        assert "ü" in result or "\\u" in result  # May be escaped or preserved
        assert isinstance(result, str)

    def test_additional_kwargs_passed_through(self):
        """Test that additional kwargs are passed to underlying method."""
        metadata_dict = {"name": "test"}

        # Should not raise error even with extra kwargs
        # (they get passed through to MixinCanonicalYAMLSerializer)
        result = canonicalize_metadata_block(
            metadata_dict,
            volatile_fields=(),
            some_extra_param="value",  # Extra param
        )

        assert isinstance(result, str)
        # Main functionality should still work
        assert "test" in result
