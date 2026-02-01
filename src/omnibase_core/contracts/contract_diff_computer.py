"""
Contract Diff Computer.

Computes semantic diffs between contract versions with identity-based list matching.
Core algorithm for OMN-1148.

Features:
    - Recursive object diffing with path tracking
    - Identity-based list element matching (vs positional)
    - Fingerprint integration for version tracking
    - ModelSchemaValue wrapping for type-safe value representation
    - CLI-friendly markdown output

Example:
    Basic usage::

        from omnibase_core.contracts.contract_diff_computer import (
            ContractDiffComputer,
            compute_contract_diff,
        )

        # Compare two contract versions
        diff = compute_contract_diff(before_contract, after_contract)

        # Render as markdown table
        print(diff.to_markdown_table())

        # Check if contracts differ
        if diff.has_changes:
            print(f"Found {diff.total_changes} changes")

Thread Safety:
    ContractDiffComputer instances are stateless and thread-safe.
    The same instance can be used from multiple threads concurrently.

Performance Considerations:
    Time Complexity:
        - Identity-based list diffing: O(n) where n = list length
        - Positional list diffing: O(n) with early termination
        - Recursive object diffing: O(k) where k = total fields
        - Equality checking: O(d) where d = nesting depth

    Space Complexity:
        - Identity maps: O(n) where n = list length
        - Recursion stack: O(d) where d = max nesting depth (protected by max depth limit)

    Recommendations for Large Contracts:
        - Define identity keys for all list fields to enable O(n) diffing
        - Use field exclusions to skip volatile/large fields
        - Consider chunking very large contracts (>10000 fields)

.. versionadded:: 0.4.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import ValidationError

from omnibase_core.contracts.contract_hash_registry import compute_contract_fingerprint

logger = logging.getLogger(__name__)

# Maximum recursion depth for _items_equal to prevent stack overflow
_MAX_RECURSION_DEPTH = 100

if TYPE_CHECKING:
    from pydantic import BaseModel

    from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch

from omnibase_core.enums.enum_contract_diff_change_type import (
    EnumContractDiffChangeType,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.diff.model_contract_diff import ModelContractDiff
from omnibase_core.models.contracts.diff.model_contract_field_diff import (
    ModelContractFieldDiff,
)
from omnibase_core.models.contracts.diff.model_contract_list_diff import (
    ModelContractListDiff,
)
from omnibase_core.models.contracts.diff.model_diff_configuration import (
    ModelDiffConfiguration,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Extended identity keys for contract diffing
# Maps field paths (or final path components) to the identity key field
DEFAULT_IDENTITY_KEYS: dict[str, str] = {
    # Standard contract fields
    "dependencies": "name",
    "handlers": "name",
    "handlers__add": "name",
    "states": "state_name",
    "transitions": "transition_name",
    "operations": "operation_name",
    "capability_inputs__add": "__value__",
    "capability_outputs__add": "name",
    "consumed_events__add": "__value__",
    "published_events": "event_name",
    "external_services": "service_name",
    # Additional common patterns
    "steps": "step_id",
    "actions": "name",
    "events": "event_type",
}


# naming-ok: utility class in contracts module, not a Node/Protocol/Service
class ContractDiffComputer:
    """Computes semantic diffs between contract versions.

    This class implements the core diff algorithm for comparing two contract
    versions. It handles recursive object diffing, identity-based list
    matching, and produces structured diff results suitable for:

    - CLI output (markdown tables)
    - Programmatic analysis
    - Reverse patch generation (future)

    The algorithm uses identity keys to match list elements semantically
    rather than by position. For example, two transitions with the same
    "name" field are considered the same logical element, even if their
    positions in the list differ.

    Attributes:
        config: Configuration controlling diff behavior (exclusions, identity keys).

    Thread Safety:
        Stateless and thread-safe. The same instance can be safely used
        from multiple threads without synchronization.

    Example:
        >>> computer = ContractDiffComputer()
        >>> diff = computer.compute_diff(old_contract, new_contract)
        >>> print(diff.to_markdown_table())
    """

    def __init__(self, config: ModelDiffConfiguration | None = None) -> None:
        """Initialize the diff computer.

        Args:
            config: Optional configuration for diff behavior. If None, uses
                default configuration with standard exclusions and identity keys.
        """
        self.config = config or ModelDiffConfiguration(
            identity_keys={
                **ModelDiffConfiguration.DEFAULT_IDENTITY_KEYS,
                **DEFAULT_IDENTITY_KEYS,
            }
        )

    def compute_diff(self, before: BaseModel, after: BaseModel) -> ModelContractDiff:
        """Compute semantic diff between two contracts.

        Performs a deep comparison of two contract models, producing a
        structured diff result with field-level and list-level changes.

        Args:
            before: The original contract version.
            after: The modified contract version.

        Returns:
            ModelContractDiff containing all detected differences.

        Example:
            >>> diff = computer.compute_diff(v1_contract, v2_contract)
            >>> if diff.has_changes:
            ...     print(f"Detected {diff.total_changes} changes")
        """
        # Compute fingerprints for both contracts (optional, may fail for non-contracts)
        before_fingerprint = None
        after_fingerprint = None
        try:
            before_fingerprint = compute_contract_fingerprint(before)
            after_fingerprint = compute_contract_fingerprint(after)
        except (
            AttributeError,
            ModelOnexError,
            TypeError,
            ValidationError,
            ValueError,
        ) as e:
            # fallback-ok: fingerprint computation is optional for non-contract models
            logger.debug(
                "Fingerprint computation skipped for %s: %s",
                type(before).__name__,
                str(e),
            )

        # Get contract names for identification
        before_name = self._get_contract_name(before)
        after_name = self._get_contract_name(after)

        # Convert to dicts for comparison
        before_dict = before.model_dump()
        after_dict = after.model_dump()

        # Accumulate diffs
        field_diffs: list[ModelContractFieldDiff] = []
        list_diffs: list[ModelContractListDiff] = []

        # Recursively diff the objects
        self._diff_objects(
            before=before_dict,
            after=after_dict,
            path="",
            field_diffs=field_diffs,
            list_diffs=list_diffs,
        )

        return ModelContractDiff(
            before_contract_name=before_name,
            after_contract_name=after_name,
            before_fingerprint=before_fingerprint,
            after_fingerprint=after_fingerprint,
            field_diffs=field_diffs,
            list_diffs=list_diffs,
        )

    def _get_contract_name(self, contract: BaseModel) -> str:
        """Extract contract name from a contract model.

        Args:
            contract: The contract model.

        Returns:
            The contract name if available, otherwise the class name.
        """
        # Try common name fields
        for attr in ("name", "contract_name", "node_name"):
            if hasattr(contract, attr):
                name = getattr(contract, attr)
                if name is not None:
                    return str(name)
        # Fallback to class name
        return type(contract).__name__

    def _diff_objects(
        self,
        before: dict[str, object],
        after: dict[str, object],
        path: str,
        field_diffs: list[ModelContractFieldDiff],
        list_diffs: list[ModelContractListDiff],
    ) -> None:
        """Recursively diff two dictionary objects.

        Handles nested dicts, lists, and scalar values. Updates the
        field_diffs and list_diffs accumulators with detected changes.

        Args:
            before: The original dict.
            after: The modified dict.
            path: Current dot-separated path for field identification.
            field_diffs: Accumulator for scalar field differences.
            list_diffs: Accumulator for list field differences.
        """
        # Get all keys from both dicts (sorted for deterministic output)
        all_keys = sorted(set(before.keys()) | set(after.keys()))

        for key in all_keys:
            field_path = f"{path}.{key}" if path else key

            # Check exclusions
            if self.config.should_exclude(field_path):
                continue

            in_before = key in before
            in_after = key in after

            if not in_before and in_after:
                # Field added
                self._add_field_diff(
                    field_path=field_path,
                    old_value=None,
                    new_value=after[key],
                    change_type=EnumContractDiffChangeType.ADDED,
                    field_diffs=field_diffs,
                )
            elif in_before and not in_after:
                # Field removed
                self._add_field_diff(
                    field_path=field_path,
                    old_value=before[key],
                    new_value=None,
                    change_type=EnumContractDiffChangeType.REMOVED,
                    field_diffs=field_diffs,
                )
            else:
                # Field exists in both - compare values
                before_val = before[key]
                after_val = after[key]

                if isinstance(before_val, dict) and isinstance(after_val, dict):
                    # Recurse into nested dicts
                    self._diff_objects(
                        before=before_val,
                        after=after_val,
                        path=field_path,
                        field_diffs=field_diffs,
                        list_diffs=list_diffs,
                    )
                elif isinstance(before_val, list) and isinstance(after_val, list):
                    # Handle list comparison
                    identity_key = self.config.get_identity_key(field_path)
                    if identity_key:
                        # Use identity-based matching
                        list_diff = self._diff_list_with_identity(
                            before=before_val,
                            after=after_val,
                            field_path=field_path,
                            identity_key=identity_key,
                        )
                        if list_diff.has_changes or self.config.include_unchanged:
                            list_diffs.append(list_diff)
                    else:
                        # Fallback to positional comparison
                        self._diff_list_positional(
                            before=before_val,
                            after=after_val,
                            field_path=field_path,
                            field_diffs=field_diffs,
                            list_diffs=list_diffs,
                        )
                # Scalar comparison
                elif before_val != after_val:
                    self._add_field_diff(
                        field_path=field_path,
                        old_value=before_val,
                        new_value=after_val,
                        change_type=EnumContractDiffChangeType.MODIFIED,
                        field_diffs=field_diffs,
                    )
                elif self.config.include_unchanged:
                    self._add_field_diff(
                        field_path=field_path,
                        old_value=before_val,
                        new_value=after_val,
                        change_type=EnumContractDiffChangeType.UNCHANGED,
                        field_diffs=field_diffs,
                    )

    def _diff_list_with_identity(
        self,
        before: list[object],
        after: list[object],
        field_path: str,
        identity_key: str,
    ) -> ModelContractListDiff:
        """Diff list using identity-based matching.

        Matches list elements by identity key rather than position.
        This allows detection of additions, removals, modifications,
        and moves of logical elements.

        Args:
            before: The original list.
            after: The modified list.
            field_path: Dot-separated path to the list field.
            identity_key: The field name used to identify elements.
                Use "__value__" for primitive value lists.

        Returns:
            ModelContractListDiff with categorized changes.
        """
        # Handle primitive lists specially
        if identity_key == "__value__":
            return self._diff_primitive_list(
                before=before,
                after=after,
                field_path=field_path,
            )

        # Build identity maps: {id_value: (index, item)}
        before_map = self._build_identity_map(before, identity_key)
        after_map = self._build_identity_map(after, identity_key)

        added_items: list[ModelContractFieldDiff] = []
        removed_items: list[ModelContractFieldDiff] = []
        modified_items: list[ModelContractFieldDiff] = []
        moved_items: list[ModelContractFieldDiff] = []
        unchanged_count = 0

        # Find removed and modified/moved items
        for identity, (before_idx, before_item) in before_map.items():
            if identity not in after_map:
                # Item was removed
                removed_items.append(
                    ModelContractFieldDiff(
                        field_path=f"{field_path}[{identity}]",
                        change_type=EnumContractDiffChangeType.REMOVED,
                        old_value=ModelSchemaValue.from_value(before_item),
                        new_value=None,
                        value_type=type(before_item).__name__,
                    )
                )
            else:
                # Item exists in both - check for modification or move
                after_idx, after_item = after_map[identity]

                # Check content equality
                content_equal = self._items_equal(before_item, after_item)
                position_equal = before_idx == after_idx

                if not content_equal:
                    # Content changed (modification)
                    modified_items.append(
                        ModelContractFieldDiff(
                            field_path=f"{field_path}[{identity}]",
                            change_type=EnumContractDiffChangeType.MODIFIED,
                            old_value=ModelSchemaValue.from_value(before_item),
                            new_value=ModelSchemaValue.from_value(after_item),
                            value_type=type(before_item).__name__,
                        )
                    )
                elif not position_equal:
                    # Same content, different position (move)
                    moved_items.append(
                        ModelContractFieldDiff(
                            field_path=f"{field_path}[{identity}]",
                            change_type=EnumContractDiffChangeType.MOVED,
                            old_value=ModelSchemaValue.from_value(before_item),
                            new_value=ModelSchemaValue.from_value(after_item),
                            value_type=type(before_item).__name__,
                            old_index=before_idx,
                            new_index=after_idx,
                        )
                    )
                else:
                    # Unchanged
                    unchanged_count += 1

        # Find added items
        for identity, (after_idx, after_item) in after_map.items():
            if identity not in before_map:
                # Item was added
                added_items.append(
                    ModelContractFieldDiff(
                        field_path=f"{field_path}[{identity}]",
                        change_type=EnumContractDiffChangeType.ADDED,
                        old_value=None,
                        new_value=ModelSchemaValue.from_value(after_item),
                        value_type=type(after_item).__name__,
                    )
                )

        return ModelContractListDiff(
            field_path=field_path,
            identity_key=identity_key,
            added_items=added_items,
            removed_items=removed_items,
            modified_items=modified_items,
            moved_items=moved_items,
            unchanged_count=unchanged_count,
        )

    def _build_identity_map(
        self,
        items: list[object],
        identity_key: str,
    ) -> dict[str, tuple[int, object]]:
        """Build map from identity value to (index, item).

        Args:
            items: List of items to index.
            identity_key: The field name to use for identity.

        Returns:
            Dictionary mapping identity values to (index, item) tuples.
        """
        identity_map: dict[str, tuple[int, object]] = {}

        for idx, item in enumerate(items):
            identity_value: str | None = None

            if isinstance(item, dict):
                # Extract identity from dict
                raw_value = item.get(identity_key)
                if raw_value is not None:
                    identity_value = str(raw_value)
            elif hasattr(item, identity_key):
                # Extract identity from object attribute
                raw_value = getattr(item, identity_key)
                if raw_value is not None:
                    identity_value = str(raw_value)

            if identity_value is not None:
                if identity_value in identity_map:
                    # Collision detected - use composite key to preserve both items
                    # Use '::idx:' delimiter which is unlikely to appear in real data
                    # (avoids collision with values already containing '__' suffixes)
                    logger.warning(
                        "Duplicate identity key '%s' found at index %d. "
                        "Using composite key '%s::idx:%d' for disambiguation.",
                        identity_value,
                        idx,
                        identity_value,
                        idx,
                    )
                    identity_map[f"{identity_value}::idx:{idx}"] = (idx, item)
                else:
                    identity_map[identity_value] = (idx, item)
            else:
                # Use index as fallback identity
                identity_map[f"__idx_{idx}__"] = (idx, item)

        return identity_map

    def _items_equal(
        self,
        item1: object,
        item2: object,
        _depth: int = 0,
        _seen: set[int] | None = None,
    ) -> bool:
        """Compare two items for equality.

        Handles dicts, lists, and scalar values with deep comparison.
        Protected against circular references and excessive nesting depth.

        Args:
            item1: First item.
            item2: Second item.
            _depth: Current recursion depth (internal use only).
            _seen: Set of visited object IDs for cycle detection (internal use only).

        Returns:
            True if items are equal, False otherwise.

        Note:
            When max recursion depth is exceeded, returns False (assumes unequal)
            rather than attempting a fallback comparison that could still fail.
            Cycle detection handles circular references at shallower depths.
        """
        # Depth check to prevent stack overflow
        if _depth > _MAX_RECURSION_DEPTH:
            logger.warning(
                "Max recursion depth (%d) exceeded in _items_equal for types %s and %s, "
                "assuming items are unequal",
                _MAX_RECURSION_DEPTH,
                type(item1).__name__,
                type(item2).__name__,
            )
            return False

        # Initialize seen set for cycle detection
        if _seen is None:
            _seen = set()

        # Cycle detection for complex objects
        id1, id2 = id(item1), id(item2)
        if isinstance(item1, (dict, list)):
            if id1 in _seen or id2 in _seen:
                # Already visited - avoid infinite loop
                logger.warning(
                    "Circular reference detected in _items_equal, "
                    "falling back to simple equality"
                )
                try:
                    return item1 == item2
                except RecursionError:
                    # cleanup-resilience-ok: malformed data with deep circular refs
                    logger.warning(
                        "RecursionError during fallback equality check, assuming unequal"
                    )
                    return False
            # Track this object (copy set to avoid mutation across branches)
            _seen = _seen | {id1, id2}

        if type(item1) is not type(item2):
            return False

        if isinstance(item1, dict) and isinstance(item2, dict):
            # Exclude volatile fields from comparison
            keys1 = set(item1.keys())
            keys2 = set(item2.keys())
            if keys1 != keys2:
                return False
            for key in keys1:
                if self.config.should_exclude(key):
                    continue
                if not self._items_equal(
                    item1[key], item2[key], _depth=_depth + 1, _seen=_seen
                ):
                    return False
            return True

        if isinstance(item1, list) and isinstance(item2, list):
            if len(item1) != len(item2):
                return False
            for v1, v2 in zip(item1, item2, strict=True):
                if not self._items_equal(v1, v2, _depth=_depth + 1, _seen=_seen):
                    return False
            return True

        return item1 == item2

    def _diff_primitive_list(
        self,
        before: list[object],
        after: list[object],
        field_path: str,
    ) -> ModelContractListDiff:
        """Diff list of primitive values (strings, ints).

        Uses set operations for efficient comparison of primitive lists.

        Args:
            before: The original list.
            after: The modified list.
            field_path: Dot-separated path to the list field.

        Returns:
            ModelContractListDiff with additions and removals.
        """
        # Convert to comparable format (handle unhashable by converting to str)
        before_set = {self._to_hashable(v) for v in before}
        after_set = {self._to_hashable(v) for v in after}

        added_values = after_set - before_set
        removed_values = before_set - after_set
        unchanged_values = before_set & after_set

        added_items: list[ModelContractFieldDiff] = []
        removed_items: list[ModelContractFieldDiff] = []

        for val in sorted(added_values, key=str):
            added_items.append(
                ModelContractFieldDiff(
                    field_path=f"{field_path}[{val}]",
                    change_type=EnumContractDiffChangeType.ADDED,
                    old_value=None,
                    new_value=ModelSchemaValue.from_value(val),
                    value_type=type(val).__name__,
                )
            )

        for val in sorted(removed_values, key=str):
            removed_items.append(
                ModelContractFieldDiff(
                    field_path=f"{field_path}[{val}]",
                    change_type=EnumContractDiffChangeType.REMOVED,
                    old_value=ModelSchemaValue.from_value(val),
                    new_value=None,
                    value_type=type(val).__name__,
                )
            )

        return ModelContractListDiff(
            field_path=field_path,
            identity_key="__value__",
            added_items=added_items,
            removed_items=removed_items,
            modified_items=[],
            moved_items=[],
            unchanged_count=len(unchanged_values),
        )

    def _to_hashable(self, value: object) -> object:
        """Convert value to hashable form for set operations.

        Args:
            value: Value to convert.

        Returns:
            Hashable representation of the value.
        """
        if isinstance(value, dict):
            return tuple(sorted((k, self._to_hashable(v)) for k, v in value.items()))
        if isinstance(value, list):
            return tuple(self._to_hashable(v) for v in value)
        return value

    def _diff_list_positional(
        self,
        before: list[object],
        after: list[object],
        field_path: str,
        field_diffs: list[ModelContractFieldDiff],
        list_diffs: list[ModelContractListDiff],
    ) -> None:
        """Diff list using positional comparison (fallback).

        When no identity key is configured, compares list elements by
        their position. Changes are reported as index-based modifications.

        Args:
            before: The original list.
            after: The modified list.
            field_path: Dot-separated path to the list field.
            field_diffs: Accumulator for field differences.
            list_diffs: Accumulator for list differences (propagated to nested diffs).
        """
        max_len = max(len(before), len(after))

        for i in range(max_len):
            item_path = f"{field_path}[{i}]"

            if i >= len(before):
                # Added at end
                self._add_field_diff(
                    field_path=item_path,
                    old_value=None,
                    new_value=after[i],
                    change_type=EnumContractDiffChangeType.ADDED,
                    field_diffs=field_diffs,
                )
            elif i >= len(after):
                # Removed from end
                self._add_field_diff(
                    field_path=item_path,
                    old_value=before[i],
                    new_value=None,
                    change_type=EnumContractDiffChangeType.REMOVED,
                    field_diffs=field_diffs,
                )
            elif before[i] != after[i]:
                # Modified at position
                before_item = before[i]
                after_item = after[i]
                if isinstance(before_item, dict) and isinstance(after_item, dict):
                    # Recurse into nested dicts - propagate list_diffs accumulator
                    # to capture nested list changes in the parent result
                    self._diff_objects(
                        before=before_item,
                        after=after_item,
                        path=item_path,
                        field_diffs=field_diffs,
                        list_diffs=list_diffs,
                    )
                else:
                    self._add_field_diff(
                        field_path=item_path,
                        old_value=before[i],
                        new_value=after[i],
                        change_type=EnumContractDiffChangeType.MODIFIED,
                        field_diffs=field_diffs,
                    )
            elif self.config.include_unchanged:
                self._add_field_diff(
                    field_path=item_path,
                    old_value=before[i],
                    new_value=after[i],
                    change_type=EnumContractDiffChangeType.UNCHANGED,
                    field_diffs=field_diffs,
                )

    def _add_field_diff(
        self,
        field_path: str,
        old_value: object,
        new_value: object,
        change_type: EnumContractDiffChangeType,
        field_diffs: list[ModelContractFieldDiff],
    ) -> None:
        """Add a field diff to the accumulator.

        Args:
            field_path: Dot-separated path to the field.
            old_value: The original value (may be None).
            new_value: The new value (may be None).
            change_type: The type of change.
            field_diffs: Accumulator list to append to.
        """
        # Determine value type
        if old_value is not None:
            value_type = type(old_value).__name__
        elif new_value is not None:
            value_type = type(new_value).__name__
        else:
            value_type = "NoneType"

        # Wrap values with ModelSchemaValue
        old_wrapped = (
            ModelSchemaValue.from_value(old_value) if old_value is not None else None
        )
        new_wrapped = (
            ModelSchemaValue.from_value(new_value) if new_value is not None else None
        )

        # Handle special case for UNCHANGED
        if change_type == EnumContractDiffChangeType.UNCHANGED:
            # Both values required for UNCHANGED
            old_wrapped = ModelSchemaValue.from_value(old_value)
            new_wrapped = ModelSchemaValue.from_value(new_value)

        field_diffs.append(
            ModelContractFieldDiff(
                field_path=field_path,
                change_type=change_type,
                old_value=old_wrapped,
                new_value=new_wrapped,
                value_type=value_type,
            )
        )


def compute_contract_diff(
    before: BaseModel,
    after: BaseModel,
    config: ModelDiffConfiguration | None = None,
) -> ModelContractDiff:
    """Convenience function to compute diff between contracts.

    Creates a ContractDiffComputer with the given configuration and
    computes the diff in a single call.

    Args:
        before: The original contract version.
        after: The modified contract version.
        config: Optional configuration for diff behavior.

    Returns:
        ModelContractDiff containing all detected differences.

    Example:
        >>> diff = compute_contract_diff(v1, v2)
        >>> print(f"Changes: {diff.total_changes}")
    """
    return ContractDiffComputer(config).compute_diff(before, after)


def render_diff_table(diff: ModelContractDiff) -> str:
    """Render diff as CLI-friendly markdown table.

    Convenience function that delegates to the diff model's
    to_markdown_table() method.

    Args:
        diff: The diff result to render.

    Returns:
        Multi-line markdown string representation of the diff.

    Example:
        >>> diff = compute_contract_diff(v1, v2)
        >>> print(render_diff_table(diff))
        ## Contract Diff: MyContract -> MyContract
        ...
    """
    return diff.to_markdown_table()


def generate_reverse_patch(diff: ModelContractDiff) -> ModelContractPatch:  # stub-ok
    """Generate reverse patch from diff.

    Will create a ModelContractPatch that, when applied to the "after"
    contract, produces the "before" contract.

    Args:
        diff: The diff result to reverse.

    Returns:
        ModelContractPatch that reverses the changes.

    Raises:
        NotImplementedError: This feature is planned for OMN-1149.
    """
    raise NotImplementedError(  # stub-ok: Phase 4 of OMN-1148
        "Reverse patch generation not yet implemented"
    )


__all__ = [
    "ContractDiffComputer",
    "DEFAULT_IDENTITY_KEYS",
    "compute_contract_diff",
    "generate_reverse_patch",
    "render_diff_table",
]
