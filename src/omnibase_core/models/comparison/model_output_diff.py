"""Output diff model for structured difference representation.

Captures structured differences between two outputs in a way that's
compatible with deepdiff library output while maintaining type safety.

Thread Safety:
    ModelOutputDiff is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field, computed_field

from omnibase_core.models.comparison.model_value_change import ModelValueChange


class ModelOutputDiff(BaseModel):
    """Structured representation of differences between two outputs.

    Compatible with deepdiff library output format while maintaining
    type safety. All diff categories are optional - only populated
    when differences exist.

    Attributes:
        values_changed: Fields where values differ between baseline and replay.
        items_added: New fields/items present in replay but not in baseline.
        items_removed: Fields/items present in baseline but not in replay.
        type_changes: Fields where the type changed between executions.
        has_differences: Computed property, True if any diff collections are non-empty.

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


__all__ = ["ModelOutputDiff"]
