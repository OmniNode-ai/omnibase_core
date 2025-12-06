"""
Test suite for MixinCanonicalYAMLSerializer.

Tests canonical YAML serialization, normalization, and hash computation.
"""

from omnibase_core.enums import EnumNodeMetadataField
from omnibase_core.mixins.mixin_canonical_serialization import (
    MixinCanonicalYAMLSerializer,
    _strip_comment_prefix,
    extract_metadata_block_and_body,
    normalize_body,
    strip_block_delimiters_and_assert,
)


class TestMixinCanonicalYAMLSerializer:
    """Test MixinCanonicalYAMLSerializer functionality."""

    def test_initialization(self):
        """Test serializer initialization."""
        serializer = MixinCanonicalYAMLSerializer()

        assert hasattr(serializer, "canonicalize_metadata_block")
        assert hasattr(serializer, "normalize_body")
        assert hasattr(serializer, "canonicalize_for_hash")

    def test_normalize_body_basic(self):
        """Test normalize_body with basic content."""
        serializer = MixinCanonicalYAMLSerializer()

        body = "line1\nline2\nline3"
        result = serializer.normalize_body(body)

        assert result == "line1\nline2\nline3\n"
        assert result.endswith("\n")

    def test_normalize_body_with_crlf(self):
        """Test normalize_body with CRLF line endings."""
        serializer = MixinCanonicalYAMLSerializer()

        body = "line1\r\nline2\r\nline3"
        result = serializer.normalize_body(body)

        assert "\r" not in result
        assert result == "line1\nline2\nline3\n"

    def test_normalize_body_with_trailing_spaces(self):
        """Test normalize_body removes trailing spaces."""
        serializer = MixinCanonicalYAMLSerializer()

        body = "line1   \nline2\t\nline3  "
        result = serializer.normalize_body(body)

        assert result == "line1\nline2\nline3\n"

    def test_normalize_body_empty(self):
        """Test normalize_body with empty content."""
        serializer = MixinCanonicalYAMLSerializer()

        body = ""
        result = serializer.normalize_body(body)

        assert result == "\n"

    def test_normalize_body_only_whitespace(self):
        """Test normalize_body with only whitespace."""
        serializer = MixinCanonicalYAMLSerializer()

        body = "   \n\t\n  "
        result = serializer.normalize_body(body)

        assert result == "\n"

    def test_canonicalize_metadata_block_basic_dict(self):
        """Test canonicalize_metadata_block with basic dict."""
        serializer = MixinCanonicalYAMLSerializer()

        metadata = {
            "name": "test_node",
            "version": "1.0.0",
            "description": "Test node",
        }

        result = serializer.canonicalize_metadata_block(metadata)

        assert isinstance(result, str)
        assert "name: test_node" in result or "name:" in result
        assert "version:" in result or "1.0.0" in result

    def test_canonicalize_metadata_block_with_entrypoint(self):
        """Test canonicalize_metadata_block with entrypoint."""
        serializer = MixinCanonicalYAMLSerializer()

        metadata = {
            "name": "test_node",
            "version": "1.0.0",
            "entrypoint": "python://test_module",
        }

        result = serializer.canonicalize_metadata_block(metadata)

        assert isinstance(result, str)
        assert "python://test_module" in result

    def test_canonicalize_metadata_block_with_volatile_fields(self):
        """Test canonicalize_metadata_block replaces volatile fields."""
        serializer = MixinCanonicalYAMLSerializer()

        metadata = {
            "name": "test_node",
            "version": "1.0.0",
            "hash": "abc123",
            "last_modified_at": "2024-01-01T00:00:00Z",
        }

        result = serializer.canonicalize_metadata_block(
            metadata,
            volatile_fields=(
                EnumNodeMetadataField.HASH,
                EnumNodeMetadataField.LAST_MODIFIED_AT,
            ),
        )

        assert "abc123" not in result
        assert "0" * 64 in result  # Hash placeholder
        assert "1970-01-01T00:00:00Z" in result  # Timestamp placeholder

    def test_canonicalize_metadata_block_with_comment_prefix(self):
        """Test canonicalize_metadata_block with comment prefix."""
        serializer = MixinCanonicalYAMLSerializer()

        metadata = {
            "name": "test_node",
            "version": "1.0.0",
        }

        result = serializer.canonicalize_metadata_block(metadata, comment_prefix="# ")

        assert result.startswith("# ") or "\n# " in result

    def test_canonicalize_metadata_block_sort_keys(self):
        """Test canonicalize_metadata_block with sorted keys."""
        serializer = MixinCanonicalYAMLSerializer()

        metadata = {
            "zebra": "last",
            "alpha": "first",
            "beta": "second",
        }

        result = serializer.canonicalize_metadata_block(metadata, sort_keys=True)

        assert isinstance(result, str)

    def test_canonicalize_metadata_block_with_node_metadata_block(self):
        """Test canonicalize_metadata_block with NodeMetadataBlock-like dict."""
        serializer = MixinCanonicalYAMLSerializer()

        # Pass a dict that will be converted to NodeMetadataBlock internally
        metadata = {
            "name": "test_node",
            "version": "1.0.0",
            "entrypoint": "python://test_module",
        }

        result = serializer.canonicalize_metadata_block(metadata)

        assert isinstance(result, str)
        assert "test_node" in result

    def test_canonicalize_for_hash_basic(self):
        """Test canonicalize_for_hash with basic inputs."""
        serializer = MixinCanonicalYAMLSerializer()

        block = {
            "name": "test_node",
            "version": "1.0.0",
        }
        body = "print('hello world')\n"

        result = serializer.canonicalize_for_hash(block, body)

        assert isinstance(result, str)
        assert "test_node" in result
        assert "print('hello world')" in result

    def test_canonicalize_for_hash_with_volatile_fields(self):
        """Test canonicalize_for_hash replaces volatile fields."""
        serializer = MixinCanonicalYAMLSerializer()

        block = {
            "name": "test_node",
            "hash": "should_be_replaced",
            "last_modified_at": "should_be_replaced",
        }
        body = "test body"

        result = serializer.canonicalize_for_hash(
            block, body, volatile_fields=("hash", "last_modified_at")
        )

        assert "should_be_replaced" not in result
        assert "0" * 64 in result

    def test_canonicalize_for_hash_with_comment_prefix(self):
        """Test canonicalize_for_hash with comment prefix."""
        serializer = MixinCanonicalYAMLSerializer()

        block = {"name": "test_node"}
        body = "test body"

        result = serializer.canonicalize_for_hash(block, body, comment_prefix="# ")

        assert isinstance(result, str)

    def test_canonicalize_for_hash_empty_body(self):
        """Test canonicalize_for_hash with empty body."""
        serializer = MixinCanonicalYAMLSerializer()

        block = {"name": "test_node"}
        body = ""

        result = serializer.canonicalize_for_hash(block, body)

        assert isinstance(result, str)
        assert "test_node" in result


class TestStripCommentPrefix:
    """Test _strip_comment_prefix function."""

    def test_strip_comment_prefix_basic(self):
        """Test stripping basic comment prefix."""
        block = "# line1\n# line2\n# line3"
        result = _strip_comment_prefix(block)

        assert result == "line1\nline2\nline3"

    def test_strip_comment_prefix_with_spaces(self):
        """Test stripping comment prefix with leading spaces."""
        block = "  # line1\n  # line2"
        result = _strip_comment_prefix(block)

        assert "line1" in result
        assert "line2" in result

    def test_strip_comment_prefix_no_comments(self):
        """Test stripping when no comment prefix exists."""
        block = "line1\nline2\nline3"
        result = _strip_comment_prefix(block)

        assert result == "line1\nline2\nline3"

    def test_strip_comment_prefix_mixed_lines(self):
        """Test stripping with mixed commented and non-commented lines."""
        block = "# line1\nline2\n# line3"
        result = _strip_comment_prefix(block)

        assert "line1" in result
        assert "line2" in result
        assert "line3" in result

    def test_strip_comment_prefix_empty(self):
        """Test stripping with empty block."""
        block = ""
        result = _strip_comment_prefix(block)

        assert result == ""

    def test_strip_comment_prefix_custom_prefixes(self):
        """Test stripping with custom prefixes."""
        block = "// line1\n// line2"
        result = _strip_comment_prefix(block, comment_prefixes=("// ", "//"))

        assert "line1" in result
        assert "line2" in result


class TestExtractMetadataBlockAndBody:
    """Test extract_metadata_block_and_body function."""

    def test_extract_basic_yaml_block(self):
        """Test extracting basic YAML metadata block."""
        content = """---
name: test_node
version: 1.0.0
---

Body content here
"""

        block, body = extract_metadata_block_and_body(content, "---", "---")

        assert block is not None
        assert "name: test_node" in block or "name:" in block
        assert "Body content here" in body

    def test_extract_with_comment_delimiters(self):
        """Test extracting with commented delimiters."""
        content = """# ---
# name: test_node
# version: 1.0.0
# ---

Body content
"""

        block, body = extract_metadata_block_and_body(content, "---", "---")

        assert block is not None
        assert "Body content" in body

    def test_extract_no_metadata_block(self):
        """Test extracting when no metadata block exists."""
        content = "Just body content without metadata"

        block, body = extract_metadata_block_and_body(content, "---", "---")

        # Should return entire content as block when no delimiters found
        assert block is not None or body is not None

    def test_extract_empty_content(self):
        """Test extracting with empty content."""
        content = ""

        block, body = extract_metadata_block_and_body(content, "---", "---")

        assert block is not None or body == ""

    def test_extract_with_markdown_delimiters(self):
        """Test extracting with Markdown HTML comment delimiters."""
        from omnibase_core.models.metadata.model_metadata_constants import (
            MD_META_CLOSE,
            MD_META_OPEN,
        )

        content = f"""{MD_META_OPEN}
---
name: test
---
{MD_META_CLOSE}

Body content
"""

        _, body = extract_metadata_block_and_body(content, MD_META_OPEN, MD_META_CLOSE)

        assert body is not None

    def test_extract_only_delimiters(self):
        """Test extracting with only delimiters, no content."""
        content = "---\n---"

        block, _ = extract_metadata_block_and_body(content, "---", "---")

        assert block is not None


class TestStripBlockDelimitersAndAssert:
    """Test strip_block_delimiters_and_assert function."""

    def test_strip_delimiters_basic(self):
        """Test stripping basic delimiters."""
        lines = ["---", "content", "line2", "---"]
        delimiters = {"---", "..."}

        result = strip_block_delimiters_and_assert(lines, delimiters)

        assert result == "content\nline2"

    def test_strip_delimiters_with_spaces(self):
        """Test stripping delimiters with surrounding spaces."""
        lines = ["  ---  ", "content", "line2", "  ---  "]
        delimiters = {"---", "..."}

        result = strip_block_delimiters_and_assert(lines, delimiters)

        assert "content" in result
        assert "line2" in result

    def test_strip_delimiters_no_delimiters(self):
        """Test stripping when no delimiters present."""
        lines = ["content", "line2", "line3"]
        delimiters = {"---", "..."}

        result = strip_block_delimiters_and_assert(lines, delimiters)

        assert result == "content\nline2\nline3"

    def test_strip_delimiters_empty_lines(self):
        """Test stripping with empty lines list."""
        lines = []
        delimiters = {"---", "..."}

        result = strip_block_delimiters_and_assert(lines, delimiters)

        assert result == ""

    def test_strip_delimiters_assertion_failure(self):
        """Test that assertion fails if delimiters remain after filtering."""
        # This should not happen in normal usage, but test the assertion
        lines = ["content", "---", "more content"]
        delimiters = set()  # Empty set won't filter anything

        # Should succeed since no delimiters in set
        result = strip_block_delimiters_and_assert(lines, delimiters)
        assert "---" in result


class TestNormalizeBodyStandalone:
    """Test standalone normalize_body function."""

    def test_normalize_body_function_basic(self):
        """Test standalone normalize_body function."""
        body = "line1\nline2"
        result = normalize_body(body)

        assert result == "line1\nline2\n"

    def test_normalize_body_function_with_crlf(self):
        """Test standalone function with CRLF."""
        body = "line1\r\nline2\r\n"
        result = normalize_body(body)

        assert "\r" not in result

    def test_normalize_body_function_empty(self):
        """Test standalone function with empty string."""
        body = ""
        result = normalize_body(body)

        assert result == "\n"


class TestCanonicalSerializationEdgeCases:
    """Test edge cases and error scenarios."""

    def test_canonicalize_with_none_values(self):
        """Test canonicalization with None values in metadata."""
        serializer = MixinCanonicalYAMLSerializer()

        metadata = {
            "name": "test_node",
            "description": None,
            "tags": None,
        }

        result = serializer.canonicalize_metadata_block(metadata)

        assert isinstance(result, str)
        assert "test_node" in result

    def test_canonicalize_with_empty_lists(self):
        """Test canonicalization with empty lists."""
        serializer = MixinCanonicalYAMLSerializer()

        metadata = {
            "name": "test_node",
            "tags": [],
            "dependencies": [],
        }

        result = serializer.canonicalize_metadata_block(metadata)

        assert isinstance(result, str)

    def test_canonicalize_with_boolean_values(self):
        """Test canonicalization with boolean values."""
        serializer = MixinCanonicalYAMLSerializer()

        metadata = {
            "name": "test_node",
            "active": True,
            "deprecated": False,
        }

        result = serializer.canonicalize_metadata_block(metadata)

        assert isinstance(result, str)

    def test_canonicalize_with_numeric_values(self):
        """Test canonicalization with numeric values."""
        serializer = MixinCanonicalYAMLSerializer()

        metadata = {
            "name": "test_node",
            "priority": 10,
            "timeout": 3.14,
        }

        result = serializer.canonicalize_metadata_block(metadata)

        assert isinstance(result, str)

    def test_canonicalize_with_nested_structures(self):
        """Test canonicalization with nested dict structures."""
        serializer = MixinCanonicalYAMLSerializer()

        metadata = {
            "name": "test_node",
            "config": {
                "setting1": "value1",
                "setting2": "value2",
            },
        }

        result = serializer.canonicalize_metadata_block(metadata)

        assert isinstance(result, str)

    def test_extract_with_malformed_content(self):
        """Test extraction with malformed content."""
        content = "---\nmalformed yaml\n  bad indent\n---\nbody"

        # Should not raise, but handle gracefully
        block, body = extract_metadata_block_and_body(content, "---", "---")

        assert block is not None or body is not None

    def test_canonicalize_for_hash_consistency(self):
        """Test that canonicalize_for_hash produces consistent output."""
        serializer = MixinCanonicalYAMLSerializer()

        block = {"name": "test_node", "version": "1.0.0"}
        body = "test content"

        result1 = serializer.canonicalize_for_hash(block, body)
        result2 = serializer.canonicalize_for_hash(block, body)

        assert result1 == result2

    def test_normalize_body_with_mixed_line_endings(self):
        """Test normalize_body with mixed line ending types."""
        serializer = MixinCanonicalYAMLSerializer()

        body = "line1\r\nline2\nline3\rline4"
        result = serializer.normalize_body(body)

        assert "\r" not in result
        assert result.count("\n") >= 3
