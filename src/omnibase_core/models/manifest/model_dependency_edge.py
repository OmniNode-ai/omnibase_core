"""
Dependency Edge Model for Execution Manifest.

Defines the ModelDependencyEdge model which represents a dependency
relationship between handlers in the execution ordering.

This is a pure data model with no side effects.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelDependencyEdge(BaseModel):
    """
    A dependency relationship between handlers.

    This model represents an edge in the dependency graph used to
    determine execution ordering. It captures which handler depends
    on which other handler.

    Attributes:
        from_handler_id: The dependent handler (the one that requires the other)
        to_handler_id: The handler being depended upon
        dependency_type: Type of dependency (e.g., 'requires', 'after')
        satisfied: Whether the dependency was satisfied during execution

    Example:
        >>> edge = ModelDependencyEdge(
        ...     from_handler_id="handler_transform",
        ...     to_handler_id="handler_validate",
        ...     dependency_type="requires",
        ...     satisfied=True,
        ... )
        >>> edge.from_handler_id
        'handler_transform'

    Note:
        Direction is from_handler_id -> to_handler_id, meaning
        from_handler_id depends on (and must execute after) to_handler_id.

    See Also:
        - :class:`~omnibase_core.models.manifest.model_ordering_summary.ModelOrderingSummary`:
          The summary model that contains these edges

    .. versionadded:: 0.4.0
        Added as part of Manifest Generation & Observability (OMN-1113)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )

    from_handler_id: str = Field(  # string-id-ok: user-facing identifier
        ...,
        min_length=1,
        description="The dependent handler (requires the other to run first)",
    )

    to_handler_id: str = Field(  # string-id-ok: user-facing identifier
        ...,
        min_length=1,
        description="The handler being depended upon (must run first)",
    )

    dependency_type: str = Field(
        default="requires",
        description="Type of dependency relationship",
    )

    satisfied: bool = Field(
        default=True,
        description="Whether the dependency was satisfied during execution",
    )

    # === Utility Methods ===

    def involves_handler(self, handler_id: str) -> bool:
        """
        Check if this edge involves a specific handler.

        Args:
            handler_id: The handler ID to check

        Returns:
            True if the handler is either the source or target of this edge
        """
        return handler_id in (self.from_handler_id, self.to_handler_id)

    def is_satisfied(self) -> bool:
        """
        Check if the dependency was satisfied.

        Returns:
            True if satisfied, False otherwise
        """
        return self.satisfied

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        status = "satisfied" if self.satisfied else "unsatisfied"
        return f"{self.from_handler_id} --[{self.dependency_type}]--> {self.to_handler_id} ({status})"

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelDependencyEdge(from_handler_id={self.from_handler_id!r}, "
            f"to_handler_id={self.to_handler_id!r}, "
            f"dependency_type={self.dependency_type!r}, "
            f"satisfied={self.satisfied!r})"
        )


# Export for use
__all__ = ["ModelDependencyEdge"]
