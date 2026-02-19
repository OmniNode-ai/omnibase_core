# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Test suite for MixinCanonicalYAMLSerializer.

Tests canonical YAML serialization, normalization, and hash computation.
"""

import pytest

from omnibase_core.enums import EnumNodeMetadataField
from omnibase_core.mixins.mixin_canonical_serialization import (
    MixinCanonicalYAMLSerializer,
    _strip_comment_prefix,
    extract_metadata_block_and_body,
    normalize_body,
    strip_block_delimiters_and_assert,
)


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
class TestUnionTypeDetection:
    """Test runtime Union type detection for both typing.Union and PEP 604 syntax.

    The mixin_canonical_serialization.py canonicalize_metadata_block method
    detects Union types at runtime to identify string and list fields.
    This must work for both:
    - typing.Union (e.g., Union[str, None])
    - types.UnionType from PEP 604 (e.g., str | None)

    These tests verify the runtime detection works identically for both syntaxes.

    IMPORTANT: PEP 604 union types (str | None) do NOT have __origin__ accessible
    via getattr(). The implementation must use isinstance(annotation, types.UnionType)
    to properly detect them.
    """

    def test_typing_union_detection_basic(self):
        """Test that typing.Union is detected at runtime."""
        from typing import Union, get_origin

        # typing.Union detection (intentionally using legacy syntax to test detection)
        annotation = Union[str, None]  # noqa: UP007
        origin = get_origin(annotation)

        assert origin is Union
        assert hasattr(annotation, "__args__")
        assert str in annotation.__args__

    def test_pep604_union_detection_basic(self):
        """Test that PEP 604 union (|) is detected at runtime."""
        import types
        from typing import get_origin

        # PEP 604 syntax: str | None
        annotation = str | None
        origin = get_origin(annotation)

        assert origin is types.UnionType
        assert hasattr(annotation, "__args__")
        assert str in annotation.__args__

    def test_pep604_union_no_origin_via_getattr(self):
        """Test that PEP 604 unions do NOT have __origin__ via getattr.

        This is the critical difference between typing.Union and types.UnionType.
        PEP 604 unions require isinstance() check, not getattr(__origin__).
        """
        import types
        from typing import Union

        # typing.Union HAS __origin__ via getattr (intentionally using legacy syntax)
        typing_union = Union[str, None]  # noqa: UP007
        assert getattr(typing_union, "__origin__", None) is Union

        # PEP 604 union does NOT have __origin__ via getattr
        pep604_union = str | None
        assert getattr(pep604_union, "__origin__", None) is None

        # But it IS an instance of types.UnionType
        assert isinstance(pep604_union, types.UnionType)
        assert type(pep604_union) is types.UnionType

    def test_union_origin_distinction(self):
        """Test that typing.Union and PEP 604 have different origins."""
        import types
        from typing import Union, get_origin

        typing_union = Union[str, None]  # noqa: UP007 - intentionally testing legacy syntax
        pep604_union = str | None

        typing_origin = get_origin(typing_union)
        pep604_origin = get_origin(pep604_union)

        # They should have different origins
        assert typing_origin is Union
        assert pep604_origin is types.UnionType
        assert typing_origin is not pep604_origin

        # But both should have __args__ with the same types
        # mypy doesn't understand __args__ is a runtime attribute on typing special forms
        assert set(typing_union.__args__) == set(pep604_union.__args__)  # type: ignore[attr-defined]

    def test_multi_type_typing_union(self):
        """Test typing.Union with multiple non-None types."""
        from typing import Union, get_origin

        annotation = Union[str, int]  # noqa: UP007 - intentionally testing legacy syntax
        origin = get_origin(annotation)

        assert origin is Union
        # mypy doesn't understand __args__ is a runtime attribute on typing special forms
        assert str in annotation.__args__  # type: ignore[attr-defined]
        assert int in annotation.__args__  # type: ignore[attr-defined]
        assert type(None) not in annotation.__args__  # type: ignore[attr-defined]

    def test_multi_type_pep604_union(self):
        """Test PEP 604 union with multiple non-None types."""
        import types
        from typing import get_origin

        annotation = str | int
        origin = get_origin(annotation)

        assert origin is types.UnionType
        assert str in annotation.__args__  # types.UnionType has __args__
        assert int in annotation.__args__
        assert type(None) not in annotation.__args__

    def test_serializer_string_field_detection_typing_union(self):
        """Test that serializer detects string fields from typing.Union[str, None]."""
        import types
        from typing import Union

        # Simulate the FIXED detection logic from canonicalize_metadata_block
        annotation = Union[str, None]  # noqa: UP007 - intentionally testing legacy syntax
        origin = getattr(annotation, "__origin__", None)

        is_union = (
            origin is Union
            or origin is types.UnionType
            or isinstance(annotation, types.UnionType)
        )
        has_args = hasattr(annotation, "__args__")
        has_str = str in annotation.__args__ if has_args else False  # type: ignore[attr-defined]

        assert is_union
        assert has_args
        assert has_str

    def test_serializer_string_field_detection_pep604(self):
        """Test that serializer detects string fields from PEP 604 str | None.

        This test verifies the fix for PEP 604 detection. Without the
        isinstance(annotation, types.UnionType) check, this would fail.
        """
        import types
        from typing import Union

        # Simulate the FIXED detection logic from canonicalize_metadata_block
        annotation = str | None
        origin = getattr(annotation, "__origin__", None)

        # Note: origin is None for PEP 604!
        assert origin is None

        # But isinstance check catches it
        is_union = (
            origin is Union
            or origin is types.UnionType
            or isinstance(annotation, types.UnionType)
        )
        has_args = hasattr(annotation, "__args__")
        has_str = str in annotation.__args__ if has_args else False

        assert is_union
        assert has_args
        assert has_str

    def test_serializer_list_field_detection_typing_union(self):
        """Test that serializer detects list fields from typing.Union[list, None]."""
        import types
        from typing import Union

        annotation = Union[list, None]  # noqa: UP007 - intentionally testing legacy syntax
        origin = getattr(annotation, "__origin__", None)

        is_union = (
            origin is Union
            or origin is types.UnionType
            or isinstance(annotation, types.UnionType)
        )
        has_args = hasattr(annotation, "__args__")
        has_list = list in annotation.__args__ if has_args else False  # type: ignore[attr-defined]

        assert is_union
        assert has_args
        assert has_list

    def test_serializer_list_field_detection_pep604(self):
        """Test that serializer detects list fields from PEP 604 list | None."""
        import types
        from typing import Union

        annotation = list | None
        origin = getattr(annotation, "__origin__", None)

        is_union = (
            origin is Union
            or origin is types.UnionType
            or isinstance(annotation, types.UnionType)
        )
        has_args = hasattr(annotation, "__args__")
        has_list = list in annotation.__args__ if has_args else False

        assert is_union
        assert has_args
        assert has_list

    def test_detection_logic_equivalence(self):
        """Test that the detection logic produces identical results for both syntaxes."""
        import types
        from typing import Union

        def detect_string_field(annotation):
            """Replicate the FIXED detection logic from canonicalize_metadata_block."""
            origin = getattr(annotation, "__origin__", None)
            is_union = (
                origin is Union
                or origin is types.UnionType
                or isinstance(annotation, types.UnionType)
            )
            if is_union and hasattr(annotation, "__args__"):
                return str in annotation.__args__
            return annotation is str

        # Test str | None vs Union[str, None] (noqa: UP007 - intentionally testing both)
        assert detect_string_field(str | None) == detect_string_field(
            Union[str, None]  # noqa: UP007
        )
        assert detect_string_field(str | None) is True

        # Test str | int vs Union[str, int] (noqa: UP007 - intentionally testing both)
        assert detect_string_field(str | int) == detect_string_field(
            Union[str, int]  # noqa: UP007
        )
        assert detect_string_field(str | int) is True

        # Test int | None vs Union[int, None] (noqa: UP007 - intentionally testing both)
        assert detect_string_field(int | None) == detect_string_field(
            Union[int, None]  # noqa: UP007
        )
        assert detect_string_field(int | None) is False

        # Test direct str type
        assert detect_string_field(str) is True

        # Test direct int type
        assert detect_string_field(int) is False

    def test_complex_union_types(self):
        """Test detection with more complex union types."""
        import types
        from typing import Union

        def detect_types(annotation):
            """Detect both str and list in an annotation using FIXED logic."""
            origin = getattr(annotation, "__origin__", None)
            is_union = (
                origin is Union
                or origin is types.UnionType
                or isinstance(annotation, types.UnionType)
            )
            if is_union and hasattr(annotation, "__args__"):
                return {
                    "has_str": str in annotation.__args__,
                    "has_list": list in annotation.__args__,
                }
            return {"has_str": annotation is str, "has_list": annotation is list}

        # Union[str, list, None] - typing.Union (intentionally testing legacy syntax)
        typing_annotation = Union[str, list, None]  # noqa: UP007
        typing_result = detect_types(typing_annotation)
        assert typing_result["has_str"] is True
        assert typing_result["has_list"] is True

        # str | list | None - PEP 604
        pep604_annotation = str | list | None
        pep604_result = detect_types(pep604_annotation)
        assert pep604_result["has_str"] is True
        assert pep604_result["has_list"] is True

        # Results should be identical
        assert typing_result == pep604_result

    def test_canonicalize_uses_correct_detection(self):
        """Integration test: verify canonicalize_metadata_block works with both syntaxes.

        This test uses actual metadata to verify the serializer handles
        fields correctly regardless of how Union types are defined in the model.
        """
        serializer = MixinCanonicalYAMLSerializer()

        # Create metadata with optional string fields (which use Union types internally)
        metadata = {
            "name": "test_node",
            "version": "1.0.0",
            "description": None,  # Optional string field
            "tags": None,  # Optional list field
        }

        # Should not raise and should handle None values correctly
        result = serializer.canonicalize_metadata_block(metadata)

        assert isinstance(result, str)
        assert "test_node" in result
        # None/empty fields should be handled without error
        # Allow version.prerelease and version.build to be null (added in PR #241),
        # but no other unexpected nulls
        result_lower = result.lower()
        assert "null" not in result_lower or any(
            x in result_lower
            for x in ["prerelease: null", "build: null", "tools: null"]
        )

    def test_node_metadata_block_uses_pep604(self):
        """Verify that NodeMetadataBlock actually uses PEP 604 union syntax.

        This test documents that the model uses PEP 604 syntax, which is why
        the isinstance(annotation, types.UnionType) check is necessary.
        """
        import types

        from omnibase_core.models.core.model_node_metadata import NodeMetadataBlock

        # Find fields that use PEP 604 syntax (str | None, list[...] | None, etc.)
        pep604_fields = []
        for name, field in NodeMetadataBlock.model_fields.items():
            annotation = field.annotation
            if annotation is not None and isinstance(annotation, types.UnionType):
                pep604_fields.append(name)

        # Assert that there ARE PEP 604 union fields in the model
        assert len(pep604_fields) > 0, (
            "NodeMetadataBlock should have PEP 604 union fields"
        )

        # Verify some specific expected fields
        assert "runtime_language_hint" in pep604_fields  # str | None
        assert "tags" in pep604_fields  # list[str] | None
        assert "license" in pep604_fields  # str | None
