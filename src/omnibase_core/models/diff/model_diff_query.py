"""
Query filter model for diff retrieval.

Defines ModelDiffQuery for filtering diffs by contract names, time range,
change types, and pagination. Used by ProtocolDiffStore.query() and
ProtocolDiffStore.count() methods.

Example:
    >>> from datetime import datetime, UTC, timedelta
    >>> from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
    >>> from omnibase_core.enums.enum_contract_diff_change_type import (
    ...     EnumContractDiffChangeType,
    ... )
    >>>
    >>> # Query for diffs with changes in the last hour
    >>> now = datetime.now(UTC)
    >>> query = ModelDiffQuery(
    ...     has_changes=True,
    ...     computed_after=now - timedelta(hours=1),
    ...     computed_before=now,
    ...     limit=50,
    ... )

See Also:
    - :class:`~omnibase_core.protocols.storage.protocol_diff_store.ProtocolDiffStore`:
      Protocol using this query model
    - :class:`~omnibase_core.enums.enum_contract_diff_change_type.EnumContractDiffChangeType`:
      Change type values for filtering

.. versionadded:: 0.6.0
    Added as part of Diff Storage Infrastructure (OMN-1149)
"""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_contract_diff_change_type import (
    EnumContractDiffChangeType,
)

if TYPE_CHECKING:
    from omnibase_core.models.contracts.diff import ModelContractDiff


class ModelDiffQuery(BaseModel):
    """
    Query filters for diff retrieval and counting.

    All filter fields are optional. When multiple filters are specified,
    they are applied conjunctively (AND logic). Unspecified filters match
    all diffs.

    Attributes:
        before_contract_name: Filter by the before contract name (exact match).
            If None, matches all before contract names.
        after_contract_name: Filter by the after contract name (exact match).
            If None, matches all after contract names.
        contract_name: Filter by either before OR after contract name.
            If specified, matches diffs where either before_contract_name or
            after_contract_name equals this value.
        computed_after: Include only diffs computed at or after this time.
            If None, no lower time bound is applied.
        computed_before: Include only diffs computed before this time.
            If None, no upper time bound is applied.
        change_types: Filter by change types present in the diff.
            If specified, matches diffs containing at least one of the
            specified change types. If None, matches all change types.
        has_changes: Filter by whether the diff contains changes.
            True = only diffs with changes, False = only unchanged diffs,
            None = all diffs.
        limit: Maximum number of diffs to return (1-1000, default 100).
        offset: Number of diffs to skip for pagination (default 0).

    Example:
        >>> from datetime import datetime, UTC, timedelta
        >>> from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
        >>> from omnibase_core.enums.enum_contract_diff_change_type import (
        ...     EnumContractDiffChangeType,
        ... )
        >>>
        >>> # Basic query - get diffs with changes
        >>> query = ModelDiffQuery(has_changes=True)
        >>>
        >>> # Filter by contract name
        >>> query = ModelDiffQuery(contract_name="MyContract")
        >>>
        >>> # Time-bounded query
        >>> now = datetime.now(UTC)
        >>> query = ModelDiffQuery(
        ...     computed_after=now - timedelta(hours=24),
        ...     computed_before=now,
        ... )
        >>>
        >>> # Filter by change types
        >>> query = ModelDiffQuery(
        ...     change_types=frozenset({
        ...         EnumContractDiffChangeType.ADDED,
        ...         EnumContractDiffChangeType.REMOVED,
        ...     })
        ... )
        >>>
        >>> # Paginated query
        >>> query = ModelDiffQuery(limit=50, offset=100)

    .. versionadded:: 0.6.0
        Added as part of Diff Storage Infrastructure (OMN-1149)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )

    # === Contract Name Filters ===

    before_contract_name: str | None = Field(
        default=None,
        description="Filter by before contract name (exact match)",
    )

    after_contract_name: str | None = Field(
        default=None,
        description="Filter by after contract name (exact match)",
    )

    contract_name: str | None = Field(
        default=None,
        description="Filter by either before OR after contract name",
    )

    # === Time Range Filters ===

    computed_after: datetime | None = Field(
        default=None,
        description="Include only diffs computed at or after this time",
    )

    computed_before: datetime | None = Field(
        default=None,
        description="Include only diffs computed before this time",
    )

    # === Change Type Filters ===

    change_types: frozenset[EnumContractDiffChangeType] | None = Field(
        default=None,
        description="Filter by change types present in the diff. "
        "If specified, must be non-empty. Use None to match all.",
    )

    has_changes: bool | None = Field(
        default=None,
        description="Filter by whether diff has changes (True/False/None)",
    )

    # === Pagination Fields ===

    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of diffs to return (1-1000)",
    )

    offset: int = Field(
        default=0,
        ge=0,
        description="Number of diffs to skip for pagination",
    )

    # === Validators ===

    @model_validator(mode="after")
    def validate_time_range(self) -> "ModelDiffQuery":
        """Validate that computed_before is not before computed_after."""
        if self.computed_before is not None and self.computed_after is not None:
            if self.computed_before < self.computed_after:
                raise ValueError(
                    f"computed_before ({self.computed_before}) cannot be before "
                    f"computed_after ({self.computed_after})"
                )
        return self

    @model_validator(mode="after")
    def validate_change_types_not_empty(self) -> "ModelDiffQuery":
        """Validate that change_types is not an empty set when specified."""
        if self.change_types is not None and len(self.change_types) == 0:
            raise ValueError(
                "change_types must be non-empty when specified. "
                "Use None to match all change types."
            )
        return self

    # === Utility Methods ===

    def has_time_filter(self) -> bool:
        """
        Check if any time-based filter is specified.

        Returns:
            True if computed_after or computed_before is set.
        """
        return self.computed_after is not None or self.computed_before is not None

    def has_filters(self) -> bool:
        """
        Check if any filter (non-pagination) is specified.

        Returns:
            True if any filter field is set.
        """
        return any(
            [
                self.before_contract_name is not None,
                self.after_contract_name is not None,
                self.contract_name is not None,
                self.computed_after is not None,
                self.computed_before is not None,
                self.change_types is not None,
                self.has_changes is not None,
            ]
        )

    def matches_diff(self, diff: "ModelContractDiff") -> bool:
        """
        Check if a diff matches all specified filters.

        Args:
            diff: The contract diff to check.

        Returns:
            True if the diff matches all filter criteria.
        """
        # Check before_contract_name filter
        if self.before_contract_name is not None:
            if diff.before_contract_name != self.before_contract_name:
                return False

        # Check after_contract_name filter
        if self.after_contract_name is not None:
            if diff.after_contract_name != self.after_contract_name:
                return False

        # Check contract_name filter (matches either before OR after)
        if self.contract_name is not None:
            if (
                diff.before_contract_name != self.contract_name
                and diff.after_contract_name != self.contract_name
            ):
                return False

        # Check time range - computed_after
        if self.computed_after is not None:
            if diff.computed_at < self.computed_after:
                return False

        # Check time range - computed_before
        if self.computed_before is not None:
            if diff.computed_at >= self.computed_before:
                return False

        # Check has_changes filter
        if self.has_changes is not None:
            if diff.has_changes != self.has_changes:
                return False

        # Check change_types filter
        if self.change_types is not None:
            # Get all change types present in the diff
            diff_change_types: set[EnumContractDiffChangeType] = set()
            for field_diff in diff.field_diffs:
                diff_change_types.add(field_diff.change_type)
            for list_diff in diff.list_diffs:
                if list_diff.added_items:
                    diff_change_types.add(EnumContractDiffChangeType.ADDED)
                if list_diff.removed_items:
                    diff_change_types.add(EnumContractDiffChangeType.REMOVED)
                if list_diff.modified_items:
                    diff_change_types.add(EnumContractDiffChangeType.MODIFIED)
                if list_diff.moved_items:
                    diff_change_types.add(EnumContractDiffChangeType.MOVED)

            # Check if any requested change type is present
            if not diff_change_types.intersection(self.change_types):
                return False

        return True

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        filters: list[str] = []
        if self.before_contract_name is not None:
            filters.append(f"before={self.before_contract_name}")
        if self.after_contract_name is not None:
            filters.append(f"after={self.after_contract_name}")
        if self.contract_name is not None:
            filters.append(f"contract={self.contract_name}")
        if self.computed_after is not None:
            filters.append(f"after>={self.computed_after.isoformat()}")
        if self.computed_before is not None:
            filters.append(f"before<{self.computed_before.isoformat()}")
        if self.change_types is not None:
            types_str = ",".join(ct.value for ct in self.change_types)
            filters.append(f"types=[{types_str}]")
        if self.has_changes is not None:
            filters.append(f"has_changes={self.has_changes}")
        filters.append(f"limit={self.limit}")
        if self.offset > 0:
            filters.append(f"offset={self.offset}")
        return f"DiffQuery({', '.join(filters)})"


__all__ = ["ModelDiffQuery"]
