# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelCliExecutionMetadata.

Validates CLI execution metadata model functionality including
tag management, custom context handling, and factory methods.
"""

import pytest

from omnibase_core.enums.enum_context_source import EnumContextSource
from omnibase_core.enums.enum_context_type import EnumContextType
from omnibase_core.models.cli.model_cli_execution_context import (
    ModelCliExecutionContext,
)
from omnibase_core.models.cli.model_cli_execution_metadata import (
    ModelCliExecutionMetadata,
)


@pytest.mark.unit
class TestModelCliExecutionMetadataBasic:
    """Test basic CLI execution metadata functionality."""

    def test_default_metadata_creation(self):
        """Test creating metadata with default values."""
        metadata = ModelCliExecutionMetadata()

        assert metadata.custom_context == {}
        assert metadata.execution_tags == []

    def test_metadata_with_tags(self):
        """Test creating metadata with tags."""
        tags = ["production", "critical", "monitoring"]
        metadata = ModelCliExecutionMetadata(execution_tags=tags)

        assert metadata.execution_tags == tags

    def test_metadata_with_custom_context(self):
        """Test creating metadata with custom context."""
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
        )
        custom_context = {"test_key": context}

        metadata = ModelCliExecutionMetadata(custom_context=custom_context)

        assert "test_key" in metadata.custom_context
        assert metadata.custom_context["test_key"] == context


@pytest.mark.unit
class TestModelCliExecutionMetadataTagManagement:
    """Test tag management methods."""

    def test_add_tag(self):
        """Test adding a tag."""
        metadata = ModelCliExecutionMetadata()

        metadata.add_tag("new_tag")

        assert "new_tag" in metadata.execution_tags
        assert len(metadata.execution_tags) == 1

    def test_add_multiple_tags(self):
        """Test adding multiple tags."""
        metadata = ModelCliExecutionMetadata()

        metadata.add_tag("tag1")
        metadata.add_tag("tag2")
        metadata.add_tag("tag3")

        assert len(metadata.execution_tags) == 3
        assert "tag1" in metadata.execution_tags
        assert "tag2" in metadata.execution_tags
        assert "tag3" in metadata.execution_tags

    def test_add_duplicate_tag(self):
        """Test adding duplicate tag doesn't create duplicates."""
        metadata = ModelCliExecutionMetadata()

        metadata.add_tag("duplicate")
        metadata.add_tag("duplicate")

        assert metadata.execution_tags.count("duplicate") == 1
        assert len(metadata.execution_tags) == 1

    def test_remove_tag(self):
        """Test removing a tag."""
        metadata = ModelCliExecutionMetadata(execution_tags=["tag1", "tag2"])

        metadata.remove_tag("tag1")

        assert "tag1" not in metadata.execution_tags
        assert "tag2" in metadata.execution_tags
        assert len(metadata.execution_tags) == 1

    def test_remove_nonexistent_tag(self):
        """Test removing a tag that doesn't exist does nothing."""
        metadata = ModelCliExecutionMetadata(execution_tags=["tag1"])

        # Should not raise exception
        metadata.remove_tag("nonexistent")

        assert metadata.execution_tags == ["tag1"]

    def test_has_tag_true(self):
        """Test has_tag returns True when tag exists."""
        metadata = ModelCliExecutionMetadata(execution_tags=["existing_tag"])

        assert metadata.has_tag("existing_tag") is True

    def test_has_tag_false(self):
        """Test has_tag returns False when tag doesn't exist."""
        metadata = ModelCliExecutionMetadata(execution_tags=["tag1"])

        assert metadata.has_tag("nonexistent") is False

    def test_clear_tags(self):
        """Test clearing all tags."""
        metadata = ModelCliExecutionMetadata(
            execution_tags=["tag1", "tag2", "tag3"],
        )

        metadata.clear_tags()

        assert metadata.execution_tags == []


@pytest.mark.unit
class TestModelCliExecutionMetadataContextManagement:
    """Test custom context management methods."""

    def test_add_context(self):
        """Test adding custom context."""
        metadata = ModelCliExecutionMetadata()
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
        )

        metadata.add_context("key1", context)

        assert "key1" in metadata.custom_context
        assert metadata.custom_context["key1"] == context

    def test_add_multiple_contexts(self):
        """Test adding multiple contexts."""
        metadata = ModelCliExecutionMetadata()

        context1 = ModelCliExecutionContext(
            key="key1",
            value="value1",
            context_type=EnumContextType.SYSTEM,
        )
        context2 = ModelCliExecutionContext(
            key="key2",
            value="value2",
            context_type=EnumContextType.USER,
        )

        metadata.add_context("context1", context1)
        metadata.add_context("context2", context2)

        assert len(metadata.custom_context) == 2
        assert metadata.custom_context["context1"] == context1
        assert metadata.custom_context["context2"] == context2

    def test_get_context(self):
        """Test getting custom context."""
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
        )
        metadata = ModelCliExecutionMetadata(custom_context={"key1": context})

        retrieved = metadata.get_context("key1")

        assert retrieved == context

    def test_get_context_nonexistent(self):
        """Test getting nonexistent context returns None."""
        metadata = ModelCliExecutionMetadata()

        retrieved = metadata.get_context("nonexistent")

        assert retrieved is None

    def test_get_context_with_default(self):
        """Test getting context with default value."""
        default_context = ModelCliExecutionContext(
            key="default",
            value="default_value",
            context_type=EnumContextType.SYSTEM,
        )
        metadata = ModelCliExecutionMetadata()

        retrieved = metadata.get_context("nonexistent", default_context)

        assert retrieved == default_context

    def test_remove_context(self):
        """Test removing custom context."""
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
        )
        metadata = ModelCliExecutionMetadata(custom_context={"key1": context})

        metadata.remove_context("key1")

        assert "key1" not in metadata.custom_context

    def test_remove_nonexistent_context(self):
        """Test removing nonexistent context does nothing."""
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
        )
        metadata = ModelCliExecutionMetadata(custom_context={"key1": context})

        # Should not raise exception
        metadata.remove_context("nonexistent")

        assert "key1" in metadata.custom_context

    def test_has_context_true(self):
        """Test has_context returns True when context exists."""
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
        )
        metadata = ModelCliExecutionMetadata(custom_context={"key1": context})

        assert metadata.has_context("key1") is True

    def test_has_context_false(self):
        """Test has_context returns False when context doesn't exist."""
        metadata = ModelCliExecutionMetadata()

        assert metadata.has_context("nonexistent") is False

    def test_clear_context(self):
        """Test clearing all custom context."""
        context1 = ModelCliExecutionContext(
            key="key1",
            value="value1",
            context_type=EnumContextType.SYSTEM,
        )
        context2 = ModelCliExecutionContext(
            key="key2",
            value="value2",
            context_type=EnumContextType.USER,
        )
        metadata = ModelCliExecutionMetadata(
            custom_context={"key1": context1, "key2": context2},
        )

        metadata.clear_context()

        assert metadata.custom_context == {}


@pytest.mark.unit
class TestModelCliExecutionMetadataFailureHandling:
    """Test failure reason handling."""

    def test_add_failure_reason(self):
        """Test adding failure reason."""
        metadata = ModelCliExecutionMetadata()

        metadata.add_failure_reason("Connection timeout")

        assert metadata.has_context("failure_reason")
        failure_context = metadata.get_context("failure_reason")
        assert failure_context is not None
        assert failure_context.value == "Connection timeout"

    def test_get_failure_reason(self):
        """Test getting failure reason."""
        metadata = ModelCliExecutionMetadata()

        metadata.add_failure_reason("Database error")

        reason = metadata.get_failure_reason()

        assert reason == "Database error"

    def test_get_failure_reason_none(self):
        """Test getting failure reason when not set."""
        metadata = ModelCliExecutionMetadata()

        reason = metadata.get_failure_reason()

        assert reason is None

    def test_failure_reason_overwrites_previous(self):
        """Test that adding failure reason overwrites previous one."""
        metadata = ModelCliExecutionMetadata()

        metadata.add_failure_reason("First error")
        metadata.add_failure_reason("Second error")

        reason = metadata.get_failure_reason()

        assert reason == "Second error"

    def test_failure_reason_context_properties(self):
        """Test that failure reason has correct context properties."""
        metadata = ModelCliExecutionMetadata()

        metadata.add_failure_reason("Test error")

        failure_context = metadata.get_context("failure_reason")

        assert failure_context.key == "failure_reason"
        assert failure_context.context_type == EnumContextType.SYSTEM
        assert failure_context.source == EnumContextSource.SYSTEM
        assert failure_context.description == "Execution failure reason"


@pytest.mark.unit
class TestModelCliExecutionMetadataFactoryMethods:
    """Test factory methods."""

    def test_create_tagged(self):
        """Test create_tagged factory method."""
        tags = ["production", "critical"]

        metadata = ModelCliExecutionMetadata.create_tagged(tags)

        assert metadata.execution_tags == tags
        assert metadata.custom_context == {}

    def test_create_tagged_empty_list(self):
        """Test create_tagged with empty list."""
        metadata = ModelCliExecutionMetadata.create_tagged([])

        assert metadata.execution_tags == []

    def test_create_with_context(self):
        """Test create_with_context factory method."""
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
        )
        custom_context = {"key1": context}

        metadata = ModelCliExecutionMetadata.create_with_context(custom_context)

        assert metadata.custom_context == custom_context
        assert metadata.execution_tags == []

    def test_create_with_context_empty_dict(self):
        """Test create_with_context with empty dict."""
        metadata = ModelCliExecutionMetadata.create_with_context({})

        assert metadata.custom_context == {}


@pytest.mark.unit
class TestModelCliExecutionMetadataProtocols:
    """Test protocol method implementations."""

    def test_serialize(self):
        """Test serialize method (Serializable protocol)."""
        metadata = ModelCliExecutionMetadata(
            execution_tags=["tag1", "tag2"],
        )

        data = metadata.serialize()

        assert isinstance(data, dict)
        assert "execution_tags" in data
        assert "custom_context" in data

    def test_get_name(self):
        """Test get_name method (Nameable protocol)."""
        metadata = ModelCliExecutionMetadata()

        name = metadata.get_name()

        assert "ModelCliExecutionMetadata" in name

    def test_set_name(self):
        """Test set_name method (Nameable protocol)."""
        metadata = ModelCliExecutionMetadata()

        # Should not raise exception
        metadata.set_name("test_name")

    def test_validate_instance(self):
        """Test validate_instance method (ProtocolValidatable protocol)."""
        metadata = ModelCliExecutionMetadata()

        result = metadata.validate_instance()

        assert result is True


@pytest.mark.unit
class TestModelCliExecutionMetadataSerialization:
    """Test serialization and deserialization."""

    def test_model_dump(self):
        """Test serialization to dictionary."""
        metadata = ModelCliExecutionMetadata(
            execution_tags=["tag1", "tag2"],
        )

        data = metadata.model_dump()

        assert data["execution_tags"] == ["tag1", "tag2"]
        assert "custom_context" in data

    def test_round_trip_serialization_with_tags(self):
        """Test serialization and deserialization with tags."""
        original = ModelCliExecutionMetadata(
            execution_tags=["production", "monitoring"],
        )

        # Serialize
        data = original.model_dump()

        # Deserialize
        restored = ModelCliExecutionMetadata.model_validate(data)

        assert restored.execution_tags == original.execution_tags

    def test_round_trip_serialization_with_context(self):
        """Test serialization and deserialization with context."""
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
        )
        original = ModelCliExecutionMetadata(
            custom_context={"key1": context},
        )

        # Serialize
        data = original.model_dump()

        # Deserialize
        restored = ModelCliExecutionMetadata.model_validate(data)

        assert "key1" in restored.custom_context


@pytest.mark.unit
class TestModelCliExecutionMetadataEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_tags_and_context(self):
        """Test with empty tags and context."""
        metadata = ModelCliExecutionMetadata()

        assert metadata.execution_tags == []
        assert metadata.custom_context == {}

    def test_many_tags(self):
        """Test with many tags."""
        tags = [f"tag{i}" for i in range(100)]
        metadata = ModelCliExecutionMetadata(execution_tags=tags)

        assert len(metadata.execution_tags) == 100

    def test_many_contexts(self):
        """Test with many custom contexts."""
        contexts = {}
        for i in range(50):
            contexts[f"key{i}"] = ModelCliExecutionContext(
                key=f"key{i}",
                value=f"value{i}",
                context_type=EnumContextType.SYSTEM,
            )

        metadata = ModelCliExecutionMetadata(custom_context=contexts)

        assert len(metadata.custom_context) == 50

    def test_long_tag_names(self):
        """Test with very long tag names."""
        long_tag = "x" * 1000
        metadata = ModelCliExecutionMetadata()

        metadata.add_tag(long_tag)

        assert long_tag in metadata.execution_tags

    def test_special_characters_in_tags(self):
        """Test with special characters in tags."""
        special_tags = ["tag-with-dash", "tag_with_underscore", "tag.with.dot"]
        metadata = ModelCliExecutionMetadata()

        for tag in special_tags:
            metadata.add_tag(tag)

        assert len(metadata.execution_tags) == len(special_tags)
        for tag in special_tags:
            assert tag in metadata.execution_tags

    def test_context_key_with_special_characters(self):
        """Test context keys with special characters."""
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
        )
        special_keys = ["key-with-dash", "key_with_underscore", "key.with.dot"]
        metadata = ModelCliExecutionMetadata()

        for key in special_keys:
            metadata.add_context(key, context)

        assert len(metadata.custom_context) == len(special_keys)

    def test_add_and_remove_same_tag_multiple_times(self):
        """Test adding and removing the same tag multiple times."""
        metadata = ModelCliExecutionMetadata()

        metadata.add_tag("test")
        metadata.remove_tag("test")
        metadata.add_tag("test")
        metadata.remove_tag("test")

        assert "test" not in metadata.execution_tags

    def test_add_and_remove_same_context_multiple_times(self):
        """Test adding and removing the same context multiple times."""
        metadata = ModelCliExecutionMetadata()
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
        )

        metadata.add_context("key", context)
        metadata.remove_context("key")
        metadata.add_context("key", context)
        metadata.remove_context("key")

        assert "key" not in metadata.custom_context

    def test_clear_operations_on_empty_metadata(self):
        """Test clear operations on already empty metadata."""
        metadata = ModelCliExecutionMetadata()

        # Should not raise exceptions
        metadata.clear_tags()
        metadata.clear_context()

        assert metadata.execution_tags == []
        assert metadata.custom_context == {}

    def test_update_context_with_same_key(self):
        """Test updating context by adding with same key."""
        metadata = ModelCliExecutionMetadata()

        context1 = ModelCliExecutionContext(
            key="test",
            value="value1",
            context_type=EnumContextType.SYSTEM,
        )
        context2 = ModelCliExecutionContext(
            key="test",
            value="value2",
            context_type=EnumContextType.USER,
        )

        metadata.add_context("key", context1)
        metadata.add_context("key", context2)

        # Should have overwritten
        retrieved = metadata.get_context("key")
        assert retrieved == context2
        assert retrieved.value == "value2"

    def test_combined_operations(self):
        """Test combined tag and context operations."""
        metadata = ModelCliExecutionMetadata()

        # Add tags
        metadata.add_tag("tag1")
        metadata.add_tag("tag2")

        # Add contexts
        context = ModelCliExecutionContext(
            key="test",
            value="value",
            context_type=EnumContextType.SYSTEM,
        )
        metadata.add_context("key1", context)

        # Add failure reason
        metadata.add_failure_reason("Test error")

        assert len(metadata.execution_tags) == 2
        assert len(metadata.custom_context) == 2  # key1 + failure_reason
        assert metadata.get_failure_reason() == "Test error"
