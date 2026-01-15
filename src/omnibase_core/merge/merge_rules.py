"""
Merge rules for contract patching system.

This module implements the core merge semantics for combining base contracts
with patch overlays. These rules form the foundation of the typed contract
merge engine, enabling environment-specific customizations.

Merge Semantics:
    - **Scalars**: Patch value overrides base value (if patch is not None)
    - **Dicts**: Recursive merge (patch keys override/add to base keys)
    - **Lists**: Replace by default, or use explicit add/remove operations

Special Operations:
    For fine-grained list control, use explicit operations:
    - ``field__add``: Append items to the base list
    - ``field__remove``: Remove items from the base list by key

.. versionadded:: 0.4.0

Example:
    Basic dict merge::

        >>> base = {"host": "localhost", "port": 8080, "debug": False}
        >>> patch = {"port": 9090, "debug": True}
        >>> merge_dict(base, patch)
        {'host': 'localhost', 'port': 9090, 'debug': True}

    List with add/remove operations::

        >>> base_list = ["feature_a", "feature_b"]
        >>> apply_list_operations(
        ...     base_list,
        ...     add_items=["feature_c"],
        ...     remove_keys=["feature_a"],
        ... )
        ['feature_b', 'feature_c']
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar, cast

from omnibase_core.types.type_json import JsonType

T = TypeVar("T")


def merge_scalar(base: T | None, patch: T | None) -> T | None:
    """
    Merge scalar values using override semantics.

    The patch value takes precedence if it is not None. This allows patches
    to explicitly override base values while preserving base values when
    the patch doesn't specify them.

    Args:
        base: The base scalar value (may be None).
        patch: The patch scalar value (may be None).

    Returns:
        The patch value if not None, otherwise the base value.

    Example:
        >>> merge_scalar("default", "override")
        'override'
        >>> merge_scalar("default", None)
        'default'
        >>> merge_scalar(None, "new_value")
        'new_value'
        >>> merge_scalar(None, None) is None
        True
    """
    return patch if patch is not None else base


def merge_dict(
    base: dict[str, JsonType], patch: dict[str, JsonType]
) -> dict[str, JsonType]:
    """
    Recursively merge dictionaries with patch override semantics.

    Patch keys override or add to base keys. For nested dictionaries,
    the merge is performed recursively, allowing deep merging of
    configuration structures.

    Args:
        base: The base dictionary to merge into.
        patch: The patch dictionary with overrides/additions.

    Returns:
        A new dictionary with merged contents. The original dictionaries
        are not modified.

    Note:
        - Non-dict values in patch completely replace base values
        - If both base and patch have a dict at the same key, they merge recursively
        - New keys in patch are added to the result

    Example:
        >>> base = {"db": {"host": "localhost", "port": 5432}}
        >>> patch = {"db": {"port": 5433}, "cache": {"enabled": True}}
        >>> result = merge_dict(base, patch)
        >>> result["db"]
        {'host': 'localhost', 'port': 5433}
        >>> result["cache"]
        {'enabled': True}
    """
    result = dict(base)
    for key, patch_value in patch.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(patch_value, dict)
        ):
            # Cast for result[key] is needed because isinstance narrows dict but not
            # its type parameters. patch_value is already narrowed by isinstance.
            base_dict = cast(dict[str, JsonType], result[key])
            result[key] = merge_dict(base_dict, patch_value)
        else:
            result[key] = patch_value
    return result


def merge_list_replace(base: list[T], patch: list[T] | None) -> list[T]:
    """
    Merge lists using replacement semantics.

    If the patch list is not None, it completely replaces the base list.
    This is the default behavior for list merging when no explicit
    add/remove operations are specified.

    Args:
        base: The base list.
        patch: The patch list (may be None to keep base).

    Returns:
        A copy of the patch list if not None, otherwise a copy of the base list.

    Note:
        Always returns a new list (defensive copy) to prevent mutation
        of the original lists.

    Example:
        >>> merge_list_replace(["a", "b"], ["x", "y", "z"])
        ['x', 'y', 'z']
        >>> merge_list_replace(["a", "b"], None)
        ['a', 'b']
        >>> merge_list_replace(["a", "b"], [])
        []
    """
    return list(patch) if patch is not None else list(base)


def apply_list_add(base: list[T], add_items: list[T] | None) -> list[T]:
    """
    Apply __add operation to append items to a base list.

    This enables explicit addition of items without replacing the entire list,
    useful for extending lists like features, plugins, or endpoints.

    Args:
        base: The base list to append to.
        add_items: Items to append (may be None for no-op).

    Returns:
        A new list with base items followed by add_items.

    Example:
        >>> apply_list_add(["feature_a"], ["feature_b", "feature_c"])
        ['feature_a', 'feature_b', 'feature_c']
        >>> apply_list_add(["feature_a"], None)
        ['feature_a']
        >>> apply_list_add([], ["new_item"])
        ['new_item']
    """
    if add_items is None:
        return list(base)
    return list(base) + list(add_items)


def apply_list_remove(
    base: list[T],
    remove_keys: list[str] | None,
    key_extractor: Callable[[T], str] | None = None,
) -> list[T]:
    """
    Apply __remove operation to remove items from a base list by key.

    Items are identified by key for removal. For simple string lists,
    the string value itself is the key. For object lists, a key_extractor
    function should be provided to extract the identifying key from each item.

    Args:
        base: The base list to remove from.
        remove_keys: Keys/names of items to remove (may be None for no-op).
        key_extractor: Function to extract key from each item.
            If None, items are converted to strings for comparison.

    Returns:
        A new list with matching items removed.

    Example:
        String list::

            >>> apply_list_remove(["a", "b", "c"], ["b"])
            ['a', 'c']

        Object list with key extractor::

            >>> items = [{"name": "x", "val": 1}, {"name": "y", "val": 2}]
            >>> apply_list_remove(items, ["x"], key_extractor=lambda i: i["name"])
            [{'name': 'y', 'val': 2}]
    """
    if remove_keys is None:
        return list(base)
    remove_set = set(remove_keys)
    if key_extractor is None:
        return [item for item in base if str(item) not in remove_set]
    return [item for item in base if key_extractor(item) not in remove_set]


def apply_list_operations(
    base: list[T],
    add_items: list[T] | None,
    remove_keys: list[str] | None,
    key_extractor: Callable[[T], str] | None = None,
) -> list[T]:
    """
    Apply both add and remove operations to a list.

    This combines remove and add operations in a single call. The order
    of operations is: **remove first, then add**. This prevents accidentally
    removing items that were just added in the same operation.

    Args:
        base: The base list to modify.
        add_items: Items to append after removal (may be None).
        remove_keys: Keys of items to remove first (may be None).
        key_extractor: Function to extract key from items for removal.
            If None, items are converted to strings for comparison.

    Returns:
        A new list with remove and add operations applied.

    Example:
        >>> base = ["feature_a", "feature_b", "feature_c"]
        >>> apply_list_operations(
        ...     base,
        ...     add_items=["feature_d"],
        ...     remove_keys=["feature_b"],
        ... )
        ['feature_a', 'feature_c', 'feature_d']

        With objects::

            >>> items = [{"name": "x"}, {"name": "y"}]
            >>> apply_list_operations(
            ...     items,
            ...     add_items=[{"name": "z"}],
            ...     remove_keys=["x"],
            ...     key_extractor=lambda i: i["name"],
            ... )
            [{'name': 'y'}, {'name': 'z'}]
    """
    result = apply_list_remove(base, remove_keys, key_extractor)
    result = apply_list_add(result, add_items)
    return result
