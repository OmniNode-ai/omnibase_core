"""
Unit tests for merge_rules module.

Tests cover all merge semantics:
- Scalar merge (None cases, override cases)
- Dict merge (simple, nested, override)
- List replace
- List add
- List remove (strings, objects with key_extractor)
- Combined add/remove operations
"""

from typing import Any

import pytest

from omnibase_core.merge.merge_rules import (
    apply_list_add,
    apply_list_operations,
    apply_list_remove,
    merge_dict,
    merge_list_replace,
    merge_scalar,
)

pytestmark = pytest.mark.unit


class TestMergeScalar:
    """Tests for merge_scalar function."""

    def test_patch_overrides_base(self) -> None:
        """Patch value should override base when both are provided."""
        assert merge_scalar("base", "patch") == "patch"
        assert merge_scalar(100, 200) == 200
        assert merge_scalar(True, False) is False

    def test_patch_none_keeps_base(self) -> None:
        """Base value should be kept when patch is None."""
        assert merge_scalar("base", None) == "base"
        assert merge_scalar(42, None) == 42
        assert merge_scalar(True, None) is True

    def test_base_none_uses_patch(self) -> None:
        """Patch value should be used when base is None."""
        assert merge_scalar(None, "patch") == "patch"
        assert merge_scalar(None, 42) == 42

    def test_both_none_returns_none(self) -> None:
        """Should return None when both are None."""
        assert merge_scalar(None, None) is None

    def test_patch_empty_string_overrides(self) -> None:
        """Empty string patch should override base (not None)."""
        assert merge_scalar("base", "") == ""

    def test_patch_zero_overrides(self) -> None:
        """Zero patch should override base (not None)."""
        assert merge_scalar(100, 0) == 0

    def test_patch_false_overrides(self) -> None:
        """False patch should override base (not None)."""
        assert merge_scalar(True, False) is False


class TestMergeDict:
    """Tests for merge_dict function."""

    def test_simple_override(self) -> None:
        """Patch keys should override base keys."""
        base = {"a": 1, "b": 2}
        patch = {"b": 3}
        result = merge_dict(base, patch)
        assert result == {"a": 1, "b": 3}

    def test_add_new_keys(self) -> None:
        """New keys in patch should be added."""
        base = {"a": 1}
        patch = {"b": 2}
        result = merge_dict(base, patch)
        assert result == {"a": 1, "b": 2}

    def test_nested_dict_merge(self) -> None:
        """Nested dicts should be merged recursively."""
        base = {"db": {"host": "localhost", "port": 5432}}
        patch = {"db": {"port": 5433}}
        result = merge_dict(base, patch)
        assert result == {"db": {"host": "localhost", "port": 5433}}

    def test_deeply_nested_merge(self) -> None:
        """Should handle deeply nested structures."""
        base = {"level1": {"level2": {"level3": {"value": "base"}}}}
        patch = {"level1": {"level2": {"level3": {"value": "patch"}}}}
        result = merge_dict(base, patch)
        assert result["level1"]["level2"]["level3"]["value"] == "patch"

    def test_nested_add_new_keys(self) -> None:
        """Should add new nested keys."""
        base = {"db": {"host": "localhost"}}
        patch = {"db": {"port": 5432}, "cache": {"enabled": True}}
        result = merge_dict(base, patch)
        assert result == {
            "db": {"host": "localhost", "port": 5432},
            "cache": {"enabled": True},
        }

    def test_non_dict_replaces_dict(self) -> None:
        """Non-dict patch value should replace dict base value."""
        base: dict[str, Any] = {"config": {"nested": True}}
        patch: dict[str, Any] = {"config": "simple_value"}
        result = merge_dict(base, patch)
        assert result == {"config": "simple_value"}

    def test_dict_replaces_non_dict(self) -> None:
        """Dict patch value should replace non-dict base value."""
        base: dict[str, Any] = {"config": "simple"}
        patch: dict[str, Any] = {"config": {"nested": True}}
        result = merge_dict(base, patch)
        assert result == {"config": {"nested": True}}

    def test_empty_patch_returns_base_copy(self) -> None:
        """Empty patch should return copy of base."""
        base = {"a": 1, "b": 2}
        result = merge_dict(base, {})
        assert result == {"a": 1, "b": 2}
        assert result is not base  # Should be a copy

    def test_empty_base_returns_patch_copy(self) -> None:
        """Empty base should return patch contents."""
        patch = {"a": 1, "b": 2}
        result = merge_dict({}, patch)
        assert result == {"a": 1, "b": 2}

    def test_original_dicts_not_modified(self) -> None:
        """Original dictionaries should not be modified."""
        base = {"a": 1, "nested": {"x": 10}}
        patch = {"b": 2, "nested": {"y": 20}}
        base_copy = {"a": 1, "nested": {"x": 10}}
        patch_copy = {"b": 2, "nested": {"y": 20}}

        merge_dict(base, patch)

        assert base == base_copy
        assert patch == patch_copy


class TestMergeListReplace:
    """Tests for merge_list_replace function."""

    def test_patch_replaces_base(self) -> None:
        """Patch list should replace base list."""
        base = ["a", "b"]
        patch = ["x", "y", "z"]
        result = merge_list_replace(base, patch)
        assert result == ["x", "y", "z"]

    def test_none_patch_keeps_base(self) -> None:
        """None patch should keep base list."""
        base = ["a", "b"]
        result = merge_list_replace(base, None)
        assert result == ["a", "b"]

    def test_empty_patch_clears_list(self) -> None:
        """Empty patch should result in empty list."""
        base = ["a", "b"]
        result = merge_list_replace(base, [])
        assert result == []

    def test_returns_copy_not_original(self) -> None:
        """Should return a copy, not the original list."""
        base = ["a", "b"]
        patch = ["x", "y"]
        result = merge_list_replace(base, patch)

        # Modify result should not affect original
        result.append("z")
        assert patch == ["x", "y"]

        result2 = merge_list_replace(base, None)
        result2.append("c")
        assert base == ["a", "b"]

    def test_with_integer_list(self) -> None:
        """Should work with integer lists."""
        base = [1, 2, 3]
        patch = [4, 5]
        result = merge_list_replace(base, patch)
        assert result == [4, 5]


class TestApplyListAdd:
    """Tests for apply_list_add function."""

    def test_add_items_to_list(self) -> None:
        """Items should be appended to base list."""
        base = ["a", "b"]
        add = ["c", "d"]
        result = apply_list_add(base, add)
        assert result == ["a", "b", "c", "d"]

    def test_none_add_returns_base_copy(self) -> None:
        """None add_items should return copy of base."""
        base = ["a", "b"]
        result = apply_list_add(base, None)
        assert result == ["a", "b"]
        assert result is not base

    def test_empty_add_returns_base_copy(self) -> None:
        """Empty add_items should return copy of base."""
        base = ["a", "b"]
        result = apply_list_add(base, [])
        assert result == ["a", "b"]

    def test_add_to_empty_base(self) -> None:
        """Should work with empty base."""
        result = apply_list_add([], ["a", "b"])
        assert result == ["a", "b"]

    def test_add_duplicates_allowed(self) -> None:
        """Duplicates should be allowed (no deduplication)."""
        base = ["a", "b"]
        add = ["b", "c"]
        result = apply_list_add(base, add)
        assert result == ["a", "b", "b", "c"]

    def test_original_not_modified(self) -> None:
        """Original lists should not be modified."""
        base = ["a", "b"]
        add = ["c"]
        base_copy = ["a", "b"]

        apply_list_add(base, add)

        assert base == base_copy


class TestApplyListRemove:
    """Tests for apply_list_remove function."""

    def test_remove_string_items(self) -> None:
        """Should remove string items by value."""
        base = ["a", "b", "c"]
        remove = ["b"]
        result = apply_list_remove(base, remove)
        assert result == ["a", "c"]

    def test_remove_multiple_items(self) -> None:
        """Should remove multiple items."""
        base = ["a", "b", "c", "d"]
        remove = ["b", "d"]
        result = apply_list_remove(base, remove)
        assert result == ["a", "c"]

    def test_none_remove_returns_base_copy(self) -> None:
        """None remove_keys should return copy of base."""
        base = ["a", "b"]
        result = apply_list_remove(base, None)
        assert result == ["a", "b"]
        assert result is not base

    def test_remove_nonexistent_key(self) -> None:
        """Removing nonexistent key should not fail."""
        base = ["a", "b"]
        remove = ["x", "y"]
        result = apply_list_remove(base, remove)
        assert result == ["a", "b"]

    def test_empty_remove_returns_base_copy(self) -> None:
        """Empty remove_keys should return copy of base."""
        base = ["a", "b"]
        result = apply_list_remove(base, [])
        assert result == ["a", "b"]

    def test_remove_with_key_extractor(self) -> None:
        """Should use key_extractor for object lists."""
        items = [
            {"name": "feature_a", "enabled": True},
            {"name": "feature_b", "enabled": False},
            {"name": "feature_c", "enabled": True},
        ]
        remove = ["feature_b"]
        result = apply_list_remove(items, remove, key_extractor=lambda i: i["name"])
        assert len(result) == 2
        assert result[0]["name"] == "feature_a"
        assert result[1]["name"] == "feature_c"

    def test_remove_multiple_with_key_extractor(self) -> None:
        """Should remove multiple objects using key_extractor."""
        items = [
            {"id": "1", "value": "a"},
            {"id": "2", "value": "b"},
            {"id": "3", "value": "c"},
        ]
        remove = ["1", "3"]
        result = apply_list_remove(items, remove, key_extractor=lambda i: i["id"])
        assert len(result) == 1
        assert result[0]["id"] == "2"

    def test_original_not_modified(self) -> None:
        """Original list should not be modified."""
        base = ["a", "b", "c"]
        base_copy = ["a", "b", "c"]

        apply_list_remove(base, ["b"])

        assert base == base_copy

    def test_remove_all_items(self) -> None:
        """Should handle removing all items."""
        base = ["a", "b"]
        remove = ["a", "b"]
        result = apply_list_remove(base, remove)
        assert result == []


class TestApplyListOperations:
    """Tests for apply_list_operations function."""

    def test_add_only(self) -> None:
        """Should handle add-only operation."""
        base = ["a", "b"]
        result = apply_list_operations(base, add_items=["c"], remove_keys=None)
        assert result == ["a", "b", "c"]

    def test_remove_only(self) -> None:
        """Should handle remove-only operation."""
        base = ["a", "b", "c"]
        result = apply_list_operations(base, add_items=None, remove_keys=["b"])
        assert result == ["a", "c"]

    def test_add_and_remove(self) -> None:
        """Should handle combined add and remove."""
        base = ["a", "b", "c"]
        result = apply_list_operations(
            base,
            add_items=["d", "e"],
            remove_keys=["b"],
        )
        assert result == ["a", "c", "d", "e"]

    def test_remove_then_add_order(self) -> None:
        """Remove should happen before add (can add item with same key)."""
        base = ["old_a", "b"]
        result = apply_list_operations(
            base,
            add_items=["new_a"],
            remove_keys=["old_a"],
        )
        # old_a removed, then new_a added
        assert result == ["b", "new_a"]

    def test_add_same_key_not_removed(self) -> None:
        """Adding item with same key as removed should work (order matters)."""
        base = ["feature_v1"]
        # Remove v1, add v2 - both should work because remove happens first
        result = apply_list_operations(
            base,
            add_items=["feature_v2"],
            remove_keys=["feature_v1"],
        )
        assert result == ["feature_v2"]

    def test_with_key_extractor(self) -> None:
        """Should work with key_extractor for objects."""
        items = [
            {"name": "x", "version": 1},
            {"name": "y", "version": 1},
        ]
        result = apply_list_operations(
            items,
            add_items=[{"name": "z", "version": 1}],
            remove_keys=["x"],
            key_extractor=lambda i: i["name"],
        )
        assert len(result) == 2
        assert result[0]["name"] == "y"
        assert result[1]["name"] == "z"

    def test_no_ops_returns_copy(self) -> None:
        """No operations should return a copy of base."""
        base = ["a", "b"]
        result = apply_list_operations(base, add_items=None, remove_keys=None)
        assert result == ["a", "b"]
        assert result is not base

    def test_empty_base_with_add(self) -> None:
        """Should handle empty base with add operation."""
        result = apply_list_operations(
            [],
            add_items=["a", "b"],
            remove_keys=None,
        )
        assert result == ["a", "b"]

    def test_original_not_modified(self) -> None:
        """Original list should not be modified."""
        base = ["a", "b", "c"]
        base_copy = ["a", "b", "c"]

        apply_list_operations(
            base,
            add_items=["d"],
            remove_keys=["b"],
        )

        assert base == base_copy


class TestModuleExports:
    """Tests for module exports from __init__.py."""

    def test_all_functions_exported(self) -> None:
        """All merge functions should be exported from module."""
        from omnibase_core.merge import (
            apply_list_add,
            apply_list_operations,
            apply_list_remove,
            merge_dict,
            merge_list_replace,
            merge_scalar,
        )

        # Verify they are the actual functions
        assert callable(merge_scalar)
        assert callable(merge_dict)
        assert callable(merge_list_replace)
        assert callable(apply_list_add)
        assert callable(apply_list_remove)
        assert callable(apply_list_operations)

    def test_module_docstring(self) -> None:
        """Module should have a docstring."""
        import omnibase_core.merge

        assert omnibase_core.merge.__doc__ is not None
        assert "Merge" in omnibase_core.merge.__doc__
