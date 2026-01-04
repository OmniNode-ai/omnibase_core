"""
Contract Diff Model.

Represents the complete diff between two contract versions, including
field-level and list-level differences, fingerprints, and summary statistics.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field

from omnibase_core.enums.enum_contract_diff_change_type import (
    EnumContractDiffChangeType,
)
from omnibase_core.models.contracts.diff.model_contract_field_diff import (
    ModelContractFieldDiff,
)
from omnibase_core.models.contracts.diff.model_contract_list_diff import (
    ModelContractListDiff,
)
from omnibase_core.models.contracts.model_contract_fingerprint import (
    ModelContractFingerprint,
)


class ModelContractDiff(BaseModel):
    """
    Represents the complete diff between two contract versions.

    This model captures all differences between a "before" and "after"
    version of a contract, organizing changes into field-level diffs
    (for scalar values) and list-level diffs (for array fields with
    identity-based element tracking).

    Includes computed properties for summary statistics and methods
    for generating human-readable output.

    Attributes:
        diff_id: Unique identifier for this diff result.
        before_contract_name: Name/identifier of the original contract.
        after_contract_name: Name/identifier of the modified contract.
        before_fingerprint: Fingerprint of the original contract (if available).
        after_fingerprint: Fingerprint of the modified contract (if available).
        field_diffs: List of scalar field-level differences.
        list_diffs: List of array field differences with element tracking.
        computed_at: Timestamp when this diff was computed.
        has_changes: Computed property indicating if any differences exist.
        total_changes: Computed property with total number of changes.
        change_summary: Computed property with counts by change type.

    Example:
        >>> diff = ModelContractDiff(
        ...     before_contract_name="MyContract",
        ...     after_contract_name="MyContract",
        ...     field_diffs=[...],
        ...     list_diffs=[...],
        ... )
        >>> diff.has_changes
        True
        >>> diff.change_summary
        {'added': 2, 'removed': 1, 'modified': 3, 'moved': 0, 'unchanged': 0}
    """

    diff_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this diff result.",
    )

    before_contract_name: str = Field(
        ...,
        min_length=1,
        description="Name or identifier of the original (before) contract.",
    )

    after_contract_name: str = Field(
        ...,
        min_length=1,
        description="Name or identifier of the modified (after) contract.",
    )

    before_fingerprint: ModelContractFingerprint | None = Field(
        default=None,
        description="Fingerprint of the original contract, if available.",
    )

    after_fingerprint: ModelContractFingerprint | None = Field(
        default=None,
        description="Fingerprint of the modified contract, if available.",
    )

    field_diffs: list[ModelContractFieldDiff] = Field(
        default_factory=list,
        description="Scalar field-level differences between contracts.",
    )

    list_diffs: list[ModelContractListDiff] = Field(
        default_factory=list,
        description="Array field differences with identity-based element tracking.",
    )

    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when this diff was computed.",
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
        Check if any differences exist between the contracts.

        Returns:
            True if there are any field diffs or list diffs with changes;
            False if the contracts are identical.

        Example:
            >>> empty_diff = ModelContractDiff(
            ...     before_contract_name="A",
            ...     after_contract_name="A",
            ... )
            >>> empty_diff.has_changes
            False
        """
        if len(self.field_diffs) > 0:
            # Check if any field diff is an actual change (not UNCHANGED)
            for fd in self.field_diffs:
                if fd.change_type != EnumContractDiffChangeType.UNCHANGED:
                    return True

        for ld in self.list_diffs:
            if ld.has_changes:
                return True

        return False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_changes(self) -> int:
        """
        Get the total number of changes across all diffs.

        Counts all field diffs (excluding UNCHANGED) plus all changes
        from list diffs.

        Returns:
            Total count of all detected changes.

        Example:
            >>> diff.total_changes
            12
        """
        count = 0

        # Count field diffs (excluding UNCHANGED)
        for fd in self.field_diffs:
            if fd.change_type != EnumContractDiffChangeType.UNCHANGED:
                count += 1

        # Count list diff changes
        for ld in self.list_diffs:
            count += ld.total_changes

        return count

    @computed_field  # type: ignore[prop-decorator]
    @property
    def change_summary(self) -> dict[str, int]:
        """
        Get a summary of changes organized by change type.

        Returns:
            Dictionary mapping change type names to their counts.
            Keys: 'added', 'removed', 'modified', 'moved', 'unchanged'.

        Example:
            >>> diff.change_summary
            {'added': 5, 'removed': 2, 'modified': 3, 'moved': 1, 'unchanged': 10}
        """
        summary: dict[str, int] = {
            "added": 0,
            "removed": 0,
            "modified": 0,
            "moved": 0,
            "unchanged": 0,
        }

        # Count field diffs
        for fd in self.field_diffs:
            change_type_str = str(fd.change_type)
            if change_type_str in summary:
                summary[change_type_str] += 1

        # Count list diff changes
        for ld in self.list_diffs:
            summary["added"] += len(ld.added_items)
            summary["removed"] += len(ld.removed_items)
            summary["modified"] += len(ld.modified_items)
            summary["moved"] += len(ld.moved_items)
            summary["unchanged"] += ld.unchanged_count

        return summary

    def get_all_field_diffs(self) -> list[ModelContractFieldDiff]:
        """
        Get all field diffs as a flat list including list element diffs.

        Combines scalar field diffs with all element diffs from list diffs.
        Useful for iterating over all changes in a uniform way.

        Returns:
            Combined list of all ModelContractFieldDiff instances.

        Example:
            >>> all_diffs = diff.get_all_field_diffs()
            >>> len(all_diffs)
            25
        """
        result = list(self.field_diffs)

        for ld in self.list_diffs:
            result.extend(ld.get_all_field_diffs())

        return result

    def to_markdown_table(self) -> str:
        """
        Generate a markdown table representation of this diff.

        Creates a formatted markdown table with headers and rows for
        all field-level changes. Includes a summary section at the top.

        Returns:
            Multi-line string containing the markdown table.

        Example:
            >>> print(diff.to_markdown_table())
            ## Contract Diff: MyContract -> MyContract
            ...
        """
        lines: list[str] = []

        # Header
        lines.append(
            f"## Contract Diff: {self.before_contract_name} -> {self.after_contract_name}"
        )
        lines.append("")

        # Fingerprints if available
        if self.before_fingerprint or self.after_fingerprint:
            lines.append("### Fingerprints")
            if self.before_fingerprint:
                lines.append(f"- Before: `{self.before_fingerprint}`")
            if self.after_fingerprint:
                lines.append(f"- After: `{self.after_fingerprint}`")
            lines.append("")

        # Summary
        summary = self.change_summary
        lines.append("### Summary")
        lines.append(f"- **Total Changes**: {self.total_changes}")
        lines.append(
            f"- Added: {summary['added']}, "
            f"Removed: {summary['removed']}, "
            f"Modified: {summary['modified']}, "
            f"Moved: {summary['moved']}"
        )
        lines.append("")

        if not self.has_changes:
            lines.append("*No changes detected.*")
            return "\n".join(lines)

        # Field diffs table
        if self.field_diffs:
            lines.append("### Field Changes")
            lines.append("")
            lines.append("| Field Path | Change Type | Old Value | New Value |")
            lines.append("|------------|-------------|-----------|-----------|")

            for fd in self.field_diffs:
                if fd.change_type != EnumContractDiffChangeType.UNCHANGED:
                    lines.append(fd.to_markdown_row())

            lines.append("")

        # List diffs
        for ld in self.list_diffs:
            if ld.has_changes:
                lines.append(f"### List Changes: `{ld.field_path}`")
                lines.append(f"*Identity Key: `{ld.identity_key}`*")
                lines.append("")
                lines.append("| Field Path | Change Type | Old Value | New Value |")
                lines.append("|------------|-------------|-----------|-----------|")

                for item in ld.get_all_field_diffs():
                    lines.append(item.to_markdown_row())

                lines.append("")

        return "\n".join(lines)


__all__ = ["ModelContractDiff"]
