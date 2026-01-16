"""
ModelSubsetFilter - Filter for selecting subset of corpus executions.

This module provides the ModelSubsetFilter model for filtering which
executions from a corpus should be replayed. Supports filtering by
handler name, index range, and tags.

Thread Safety:
    ModelSubsetFilter is frozen (immutable) after creation, making it
    safe to share across threads.

Usage:
    .. code-block:: python

        from omnibase_core.models.replay import ModelSubsetFilter

        # Filter by handler
        filter = ModelSubsetFilter(handler_names=("text-transform",))

        # Filter by index range
        filter = ModelSubsetFilter(index_start=0, index_end=10)

        # Combined filter
        filter = ModelSubsetFilter(
            handler_names=("text-transform", "json-parse"),
            index_start=5,
            index_end=15,
        )

Related:
    - OMN-1204: Corpus Replay Orchestrator
    - ModelExecutionCorpus: Collection of execution manifests

.. versionadded:: 0.6.0
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError


class ModelSubsetFilter(BaseModel):
    """
    Filter for selecting subset of corpus executions to replay.

    Supports multiple filter criteria that are combined with AND logic:
    - handler_names: Only replay executions with matching handler IDs
    - index_start/index_end: Only replay executions within index range
    - tags: Only replay executions with matching tags

    All filters are optional. If no filters are specified, all executions
    are included.

    Attributes:
        handler_names: Tuple of handler names to include (empty = all).
        index_start: Starting index for execution range (inclusive).
        index_end: Ending index for execution range (exclusive).
        tags: Tuple of tags that executions must have (empty = all).

    Thread Safety:
        This model is frozen (immutable) after creation, making it safe
        to share across threads.

    Example:
        >>> filter = ModelSubsetFilter(
        ...     handler_names=("text-transform",),
        ...     index_start=0,
        ...     index_end=10,
        ... )
        >>> filter.has_filters
        True

    .. versionadded:: 0.6.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    handler_names: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Handler names to include (empty = all handlers)",
    )

    index_start: int | None = Field(
        default=None,
        ge=0,
        description="Starting index for execution range (inclusive)",
    )

    index_end: int | None = Field(
        default=None,
        ge=0,
        description="Ending index for execution range (exclusive)",
    )

    tags: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Tags that executions must have (empty = all)",
    )

    @model_validator(mode="after")
    def _validate_index_range(self) -> "ModelSubsetFilter":
        """Validate that index_start <= index_end if both are specified.

        Returns:
            Self if validation passes.

        Raises:
            ModelOnexError: If index_start > index_end.
        """
        if (
            self.index_start is not None
            and self.index_end is not None
            and self.index_start > self.index_end
        ):
            msg = (
                f"index_start ({self.index_start}) must be <= "
                f"index_end ({self.index_end})"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return self

    @property
    def has_filters(self) -> bool:
        """Check if any filters are active.

        Returns:
            True if at least one filter criterion is specified.
        """
        return bool(
            self.handler_names
            or self.index_start is not None
            or self.index_end is not None
            or self.tags
        )

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        parts = []
        if self.handler_names:
            parts.append(f"handlers={list(self.handler_names)}")
        if self.index_start is not None or self.index_end is not None:
            parts.append(f"range=[{self.index_start}:{self.index_end}]")
        if self.tags:
            parts.append(f"tags={list(self.tags)}")
        if not parts:
            return "SubsetFilter(all)"
        return f"SubsetFilter({', '.join(parts)})"


__all__ = ["ModelSubsetFilter"]
