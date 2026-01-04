"""
Contract Field Diff Model.

Represents a single field-level difference between two contract versions,
including the change type, old/new values, and position information for
list element moves.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_contract_diff_change_type import (
    EnumContractDiffChangeType,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelContractFieldDiff(BaseModel):
    """
    Represents a single field-level difference between contract versions.

    This model captures all information about a change to a specific field
    during contract diff computation, including the change type, old and new
    values, and positional information for list element moves.

    The model enforces consistency between change_type and the presence of
    old_value/new_value/indices through validation:
    - ADDED: Requires new_value only (old_value must be None)
    - REMOVED: Requires old_value only (new_value must be None)
    - MODIFIED: Requires both old_value and new_value
    - MOVED: Requires both indices (old_index and new_index)
    - UNCHANGED: Requires both old_value and new_value (identical values)

    Attributes:
        field_path: Dot-separated path to the changed field (e.g., "meta.name").
        change_type: The type of change (ADDED, REMOVED, MODIFIED, MOVED, UNCHANGED).
        old_value: The value before the change (None for ADDED).
        new_value: The value after the change (None for REMOVED).
        value_type: String representation of the value's Python type.
        old_index: Original position in list (for MOVED changes).
        new_index: New position in list (for MOVED changes).

    Example:
        >>> from omnibase_core.models.common import ModelSchemaValue
        >>> field_diff = ModelContractFieldDiff(
        ...     field_path="meta.name",
        ...     change_type=EnumContractDiffChangeType.MODIFIED,
        ...     old_value=ModelSchemaValue.create_string("OldName"),
        ...     new_value=ModelSchemaValue.create_string("NewName"),
        ...     value_type="str",
        ... )
        >>> field_diff.to_markdown_row()
        '| meta.name | modified | `"OldName"` | `"NewName"` |'
    """

    field_path: str = Field(
        ...,
        min_length=1,
        description="Dot-separated path to the changed field (e.g., 'meta.name').",
    )

    change_type: EnumContractDiffChangeType = Field(
        ...,
        description="The type of change detected for this field.",
    )

    old_value: ModelSchemaValue | None = Field(
        default=None,
        description="The value before the change. None for ADDED changes.",
    )

    new_value: ModelSchemaValue | None = Field(
        default=None,
        description="The value after the change. None for REMOVED changes.",
    )

    value_type: str = Field(
        default="unknown",
        description="String representation of the value's Python type.",
    )

    old_index: int | None = Field(
        default=None,
        ge=0,
        description="Original position in list (for MOVED changes only).",
    )

    new_index: int | None = Field(
        default=None,
        ge=0,
        description="New position in list (for MOVED changes only).",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    @model_validator(mode="after")
    def validate_change_type_consistency(self) -> "ModelContractFieldDiff":
        """
        Validate that old_value, new_value, and indices are consistent with change_type.

        Raises:
            ValueError: If the values/indices are inconsistent with the change type.
        """
        ct = self.change_type

        if ct == EnumContractDiffChangeType.ADDED:
            if self.old_value is not None:
                msg = "ADDED change type must not have old_value"
                raise ValueError(msg)
            if self.new_value is None:
                msg = "ADDED change type requires new_value"
                raise ValueError(msg)

        elif ct == EnumContractDiffChangeType.REMOVED:
            if self.new_value is not None:
                msg = "REMOVED change type must not have new_value"
                raise ValueError(msg)
            if self.old_value is None:
                msg = "REMOVED change type requires old_value"
                raise ValueError(msg)

        elif ct == EnumContractDiffChangeType.MODIFIED:
            if self.old_value is None:
                msg = "MODIFIED change type requires old_value"
                raise ValueError(msg)
            if self.new_value is None:
                msg = "MODIFIED change type requires new_value"
                raise ValueError(msg)

        elif ct == EnumContractDiffChangeType.MOVED:
            if self.old_index is None:
                msg = "MOVED change type requires old_index"
                raise ValueError(msg)
            if self.new_index is None:
                msg = "MOVED change type requires new_index"
                raise ValueError(msg)

        elif ct == EnumContractDiffChangeType.UNCHANGED:
            if self.old_value is None or self.new_value is None:
                msg = "UNCHANGED change type requires both old_value and new_value"
                raise ValueError(msg)

        return self

    def to_reverse(self) -> "ModelContractFieldDiff":
        """
        Create a reversed version of this field diff.

        The reversed diff represents the change needed to undo this change:
        - ADDED becomes REMOVED (and vice versa)
        - old_value and new_value are swapped
        - old_index and new_index are swapped

        Returns:
            A new ModelContractFieldDiff with reversed change semantics.

        Example:
            >>> original = ModelContractFieldDiff(
            ...     field_path="meta.name",
            ...     change_type=EnumContractDiffChangeType.ADDED,
            ...     new_value=ModelSchemaValue.create_string("NewField"),
            ...     value_type="str",
            ... )
            >>> reversed_diff = original.to_reverse()
            >>> reversed_diff.change_type
            <EnumContractDiffChangeType.REMOVED: 'removed'>
        """
        return ModelContractFieldDiff(
            field_path=self.field_path,
            change_type=self.change_type.get_reverse(),
            old_value=self.new_value,
            new_value=self.old_value,
            value_type=self.value_type,
            old_index=self.new_index,
            new_index=self.old_index,
        )

    def to_markdown_row(self) -> str:
        """
        Generate a markdown table row representing this field diff.

        Returns:
            A markdown table row with field path, change type, old value, and new value.
            Values are formatted as inline code.

        Example:
            >>> diff.to_markdown_row()
            '| meta.name | modified | `"OldName"` | `"NewName"` |'
        """
        old_str = self._format_value(self.old_value)
        new_str = self._format_value(self.new_value)
        change_str = str(self.change_type)

        # Add index info for MOVED changes
        if self.change_type == EnumContractDiffChangeType.MOVED:
            change_str = f"{change_str} ({self.old_index} -> {self.new_index})"

        return f"| {self.field_path} | {change_str} | {old_str} | {new_str} |"

    def _format_value(self, value: ModelSchemaValue | None) -> str:
        """Format a ModelSchemaValue for markdown display."""
        if value is None:
            return "-"
        python_value = value.to_value()
        if python_value is None:
            return "`null`"
        if isinstance(python_value, str):
            return f'`"{python_value}"`'
        return f"`{python_value}`"


__all__ = ["ModelContractFieldDiff"]
