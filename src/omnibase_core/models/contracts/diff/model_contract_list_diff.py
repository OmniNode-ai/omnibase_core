"""
Contract List Diff Model.

Represents the diff of a list field within a contract, tracking additions,
removals, modifications, and moves of list elements identified by an
identity key.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field

from omnibase_core.models.contracts.diff.model_contract_field_diff import (
    ModelContractFieldDiff,
)


class ModelContractListDiff(BaseModel):
    """
    Represents the diff of a list field within a contract.

    This model aggregates all changes to elements within a list field,
    organizing them by change type. Elements are matched by an identity
    key (e.g., "name" field) rather than position, enabling detection of:
    - Added elements (new identity keys)
    - Removed elements (missing identity keys)
    - Modified elements (same identity key, different values)
    - Moved elements (same identity key, different position)

    Attributes:
        field_path: Dot-separated path to the list field (e.g., "meta.transitions").
        identity_key: The field name used to identify elements (e.g., "name").
        added_items: Elements added to the list.
        removed_items: Elements removed from the list.
        modified_items: Elements with changed values.
        moved_items: Elements that changed position but not value.
        unchanged_count: Number of elements that did not change.
        has_changes: Computed property indicating if any changes exist.
        total_changes: Computed property with total number of changes.

    Example:
        >>> list_diff = ModelContractListDiff(
        ...     field_path="meta.transitions",
        ...     identity_key="name",
        ...     added_items=[...],
        ...     removed_items=[],
        ...     modified_items=[...],
        ...     moved_items=[],
        ...     unchanged_count=5,
        ... )
        >>> list_diff.has_changes
        True
        >>> list_diff.total_changes
        3
    """

    field_path: str = Field(
        ...,
        min_length=1,
        description="Dot-separated path to the list field (e.g., 'meta.transitions').",
    )

    identity_key: str = Field(
        ...,
        min_length=1,
        description=(
            "The field name used to identify list elements. "
            "Elements with the same identity key value are considered the same logical element."
        ),
    )

    added_items: list[ModelContractFieldDiff] = Field(
        default_factory=list,
        description="Elements added to the list (new identity keys).",
    )

    removed_items: list[ModelContractFieldDiff] = Field(
        default_factory=list,
        description="Elements removed from the list (missing identity keys).",
    )

    modified_items: list[ModelContractFieldDiff] = Field(
        default_factory=list,
        description="Elements with changed values (same identity key, different content).",
    )

    moved_items: list[ModelContractFieldDiff] = Field(
        default_factory=list,
        description="Elements that changed position but not value.",
    )

    unchanged_count: int = Field(
        default=0,
        ge=0,
        description="Number of elements that did not change.",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_changes(self) -> bool:
        """
        Check if any changes exist in this list diff.

        Returns:
            True if there are any additions, removals, modifications,
            or moves; False if all elements are unchanged.

        Example:
            >>> list_diff = ModelContractListDiff(
            ...     field_path="transitions",
            ...     identity_key="name",
            ...     unchanged_count=5,
            ... )
            >>> list_diff.has_changes
            False
        """
        return (
            len(self.added_items) > 0
            or len(self.removed_items) > 0
            or len(self.modified_items) > 0
            or len(self.moved_items) > 0
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_changes(self) -> int:
        """
        Get the total number of changes in this list diff.

        Returns:
            The sum of added, removed, modified, and moved items.

        Example:
            >>> list_diff.total_changes
            7
        """
        return (
            len(self.added_items)
            + len(self.removed_items)
            + len(self.modified_items)
            + len(self.moved_items)
        )

    def get_all_field_diffs(self) -> list[ModelContractFieldDiff]:
        """
        Get all field diffs from this list diff as a flat list.

        Returns a combined list of all added, removed, modified, and moved
        items. Useful for iterating over all changes without regard to
        change type.

        Returns:
            List of all ModelContractFieldDiff instances in this list diff.

        Example:
            >>> all_diffs = list_diff.get_all_field_diffs()
            >>> len(all_diffs) == list_diff.total_changes
            True
        """
        return [
            *self.added_items,
            *self.removed_items,
            *self.modified_items,
            *self.moved_items,
        ]


__all__ = ["ModelContractListDiff"]
