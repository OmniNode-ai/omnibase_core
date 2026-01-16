"""
Contract Diff Result Model.

Aggregates all differences found between two contract versions into
categorized lists. The diff result separates changes by type:

- **Behavioral changes**: High-priority changes to fields that affect
  runtime behavior (handlers, timeouts, FSM configuration, etc.)
- **Added**: Fields present in the new contract but not the old
- **Removed**: Fields present in the old contract but not the new
- **Changed**: Fields with different values between versions

Example Usage::

    from omnibase_core.models.cli.model_diff_result import ModelDiffResult
    from omnibase_core.models.cli.model_diff_entry import ModelDiffEntry

    # Create a result with some changes
    result = ModelDiffResult(
        old_path="v1.yaml",
        new_path="v2.yaml",
    )
    result.added.append(ModelDiffEntry(
        change_type="added",
        path="new_field",
        new_value="value",
    ))

    # Check for changes
    if result.has_changes:
        print(f"Found {result.total_changes} changes")

.. versionadded:: 0.6.0
    Added as part of Contract CLI Tooling (OMN-1129)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field

from omnibase_core.models.cli.model_diff_entry import ModelDiffEntry
from omnibase_core.types.type_json import JsonType


class ModelDiffResult(BaseModel):
    """Complete diff result between two contract versions.

    This model serves as the top-level container for all differences found
    during contract comparison. Changes are categorized for easy review:

    - **behavioral_changes**: Changes that may affect runtime behavior
      (highlighted first in output due to their importance)
    - **added**: New fields in the updated contract
    - **removed**: Fields no longer present (potential breaking changes)
    - **changed**: Fields with modified values

    The model provides computed properties for quick checks:

    - ``has_changes``: True if any differences were found
    - ``total_changes``: Count of all changes across all categories

    Attributes:
        old_path: Path to the old (baseline) contract file.
        new_path: Path to the new (updated) contract file.
        behavioral_changes: List of changes to behavioral fields
            (handlers, timeouts, FSM, etc.) that may affect runtime.
        added: List of fields added in the new contract.
        removed: List of fields removed from the old contract.
        changed: List of fields with different values (non-behavioral).

    Examples:
        >>> result = ModelDiffResult(old_path="a.yaml", new_path="b.yaml")
        >>> result.has_changes
        False
        >>> result.added.append(ModelDiffEntry(
        ...     change_type="added", path="name", new_value="x"))
        >>> result.has_changes
        True
        >>> result.total_changes
        1
    """

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )

    old_path: str = Field(
        default="",
        description="Path to the old contract file",
    )
    new_path: str = Field(
        default="",
        description="Path to the new contract file",
    )
    behavioral_changes: list[ModelDiffEntry] = Field(
        default_factory=list,
        description="Changes to behavioral fields that may affect runtime",
    )
    added: list[ModelDiffEntry] = Field(
        default_factory=list,
        description="Fields added in the new contract",
    )
    removed: list[ModelDiffEntry] = Field(
        default_factory=list,
        description="Fields removed from the old contract",
    )
    changed: list[ModelDiffEntry] = Field(
        default_factory=list,
        description="Fields with changed values (non-behavioral)",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_changes(self) -> bool:
        """Check if any differences were detected.

        Returns:
            True if any category contains at least one entry.

        Examples:
            >>> result = ModelDiffResult()
            >>> result.has_changes
            False
        """
        return bool(
            self.behavioral_changes or self.added or self.removed or self.changed
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_changes(self) -> int:
        """Get total number of changes across all categories.

        Returns:
            Sum of entries in all four change categories.

        Examples:
            >>> result = ModelDiffResult()
            >>> result.total_changes
            0
        """
        return (
            len(self.behavioral_changes)
            + len(self.added)
            + len(self.removed)
            + len(self.changed)
        )

    def to_dict(self) -> dict[str, JsonType]:
        """Convert to dictionary for JSON/YAML serialization.

        Produces a complete dictionary representation of the diff result,
        using ModelDiffEntry.to_dict() for each entry to ensure consistent
        output format.

        Returns:
            Dictionary containing:

            - old_path, new_path: File paths
            - has_changes: Boolean flag
            - total_changes: Change count
            - behavioral_changes, added, removed, changed: Entry lists

        Examples:
            >>> result = ModelDiffResult(old_path="a.yaml", new_path="b.yaml")
            >>> data = result.to_dict()
            >>> data["has_changes"]
            False
            >>> data["total_changes"]
            0
        """
        return {
            "old_path": self.old_path,
            "new_path": self.new_path,
            "has_changes": self.has_changes,
            "total_changes": self.total_changes,
            "behavioral_changes": [e.to_dict() for e in self.behavioral_changes],
            "added": [e.to_dict() for e in self.added],
            "removed": [e.to_dict() for e in self.removed],
            "changed": [e.to_dict() for e in self.changed],
        }
