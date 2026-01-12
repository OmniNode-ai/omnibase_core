"""Output diff model for structured difference representation.

Captures structured differences between two outputs in a way that's
compatible with deepdiff library output while maintaining type safety.

Thread Safety:
    ModelOutputDiff is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, computed_field

from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any
from omnibase_core.models.replay.model_value_change import ModelValueChange

if TYPE_CHECKING:
    from deepdiff import DeepDiff


class ModelOutputDiff(BaseModel):
    """Structured representation of differences between two outputs.

    Compatible with deepdiff library output format while maintaining
    type safety. All diff categories are optional - only populated
    when differences exist.

    Use the `from_deepdiff()` factory method to convert deepdiff library
    output directly to this model.

    Attributes:
        values_changed: Fields where values differ between baseline and replay.
        items_added: New fields/items present in replay but not in baseline.
        items_removed: Fields/items present in baseline but not in replay.
        type_changes: Fields where the type changed between executions.
        has_differences: Computed property, True if any diff collections are non-empty.

    Example:
        >>> from deepdiff import DeepDiff
        >>> baseline = {"key": "old_value", "removed": 1}
        >>> replay = {"key": "new_value", "added": 2}
        >>> diff = DeepDiff(baseline, replay)
        >>> output_diff = ModelOutputDiff.from_deepdiff(diff)
        >>> output_diff.has_differences
        True

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    values_changed: dict[str, ModelValueChange] = Field(
        default_factory=dict,
        description="Fields where values differ, keyed by JSON path",
    )
    items_added: list[str] = Field(
        default_factory=list,
        description="JSON paths of items added in replay",
    )
    items_removed: list[str] = Field(
        default_factory=list,
        description="JSON paths of items removed in replay",
    )
    type_changes: dict[str, str] = Field(
        default_factory=dict,
        description="Fields where type changed, keyed by path with description",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_differences(self) -> bool:
        """Return True if any differences were detected."""
        return bool(
            self.values_changed
            or self.items_added
            or self.items_removed
            or self.type_changes
        )

    @classmethod
    @allow_dict_any(
        reason="Accepts DeepDiff library output which is dict[str, Any]-like"
    )
    def from_deepdiff(cls, diff_result: DeepDiff | dict[str, Any]) -> ModelOutputDiff:
        """Create ModelOutputDiff from a deepdiff DeepDiff result.

        Factory method that converts deepdiff library output into a structured
        ModelOutputDiff instance. Handles all standard deepdiff output categories
        and gracefully ignores missing keys.

        Args:
            diff_result: A DeepDiff object or dictionary containing diff results.
                Supports the following deepdiff output keys:
                - values_changed: Fields where values differ
                - type_changes: Fields where types changed
                - iterable_item_added: Items added to iterables
                - iterable_item_removed: Items removed from iterables
                - dictionary_item_added: Keys added to dictionaries
                - dictionary_item_removed: Keys removed from dictionaries

        Returns:
            ModelOutputDiff with values converted from deepdiff format.

        Example:
            >>> from deepdiff import DeepDiff
            >>> baseline = {"key": "old_value", "removed": 1}
            >>> replay = {"key": "new_value", "added": 2}
            >>> diff = DeepDiff(baseline, replay)
            >>> output_diff = ModelOutputDiff.from_deepdiff(diff)
            >>> output_diff.has_differences
            True
        """
        # Convert DeepDiff to dict if needed (DeepDiff is dict-like)
        # Note: diff_dict type is inferred as the result of dict() conversion
        diff_dict = dict(diff_result) if diff_result else {}

        # Parse values_changed
        values_changed: dict[str, ModelValueChange] = {}
        raw_values_changed = diff_dict.get("values_changed", {})
        for path, change_data in raw_values_changed.items():
            if isinstance(change_data, dict):
                old_val = change_data.get("old_value")
                new_val = change_data.get("new_value")
            else:
                # Handle case where change_data might be a different structure
                old_val = getattr(change_data, "old_value", None)
                new_val = getattr(change_data, "new_value", None)
            values_changed[path] = ModelValueChange(
                old_value=_serialize_value(old_val),
                new_value=_serialize_value(new_val),
            )

        # Parse type_changes
        type_changes: dict[str, str] = {}
        raw_type_changes = diff_dict.get("type_changes", {})
        for path, change_data in raw_type_changes.items():
            if isinstance(change_data, dict):
                old_type = change_data.get("old_type", type(None))
                new_type = change_data.get("new_type", type(None))
            else:
                old_type = getattr(change_data, "old_type", type(None))
                new_type = getattr(change_data, "new_type", type(None))
            old_type_name = _get_type_name(old_type)
            new_type_name = _get_type_name(new_type)
            type_changes[path] = f"{old_type_name} -> {new_type_name}"

        # Collect items added from multiple deepdiff categories
        items_added: list[str] = []
        for key in ("iterable_item_added", "dictionary_item_added"):
            raw_added = diff_dict.get(key)
            if raw_added is not None:
                # iterable_item_added is a dict {path: value}
                # dictionary_item_added is a SetOrdered of paths
                if hasattr(raw_added, "keys"):
                    items_added.extend(raw_added.keys())
                else:
                    # SetOrdered or other iterable of paths
                    items_added.extend(raw_added)

        # Collect items removed from multiple deepdiff categories
        items_removed: list[str] = []
        for key in ("iterable_item_removed", "dictionary_item_removed"):
            raw_removed = diff_dict.get(key)
            if raw_removed is not None:
                # iterable_item_removed is a dict {path: value}
                # dictionary_item_removed is a SetOrdered of paths
                if hasattr(raw_removed, "keys"):
                    items_removed.extend(raw_removed.keys())
                else:
                    # SetOrdered or other iterable of paths
                    items_removed.extend(raw_removed)

        return cls(
            values_changed=values_changed,
            items_added=items_added,
            items_removed=items_removed,
            type_changes=type_changes,
        )


def _serialize_value(value: Any) -> str:
    """Serialize a value to string representation.

    Args:
        value: Any value to serialize.

    Returns:
        String representation of the value.
    """
    if value is None:
        return "None"
    if isinstance(value, str):
        return value
    return repr(value)


def _get_type_name(type_obj: type | Any) -> str:
    """Get a readable name for a type.

    Args:
        type_obj: A type object or value.

    Returns:
        Human-readable type name string.
    """
    if type_obj is None:
        return "NoneType"
    if isinstance(type_obj, type):
        return type_obj.__name__
    return type(type_obj).__name__


__all__ = ["ModelOutputDiff"]
