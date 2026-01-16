"""
Ordering Summary Model for Execution Manifest.

Defines the ModelOrderingSummary model which captures the resolved execution
order for a pipeline run. This answers "in what order were things executed,
and why that order?".

This is a pure data model with no side effects.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.manifest.model_dependency_edge import ModelDependencyEdge


class ModelOrderingSummary(BaseModel):
    """
    Resolved execution ordering information.

    This model captures the execution order that was resolved for the
    pipeline run, including phases, handler order, and the dependency
    relationships used to determine that order.

    Determinism requirement: Given the same node + contract + registry,
    the ordering must be identical.

    Attributes:
        phases: List of phases in execution order
        resolved_order: Handler IDs in resolved execution order
        dependency_edges: Dependency relationships used for ordering
        ordering_policy: Policy used for ordering (e.g., 'topological_sort')
        ordering_rationale: Human-readable explanation of ordering

    Example:
        >>> summary = ModelOrderingSummary(
        ...     phases=["preflight", "before", "execute", "after", "emit", "finalize"],
        ...     resolved_order=["handler_validate", "handler_transform", "handler_save"],
        ...     ordering_policy="topological_sort",
        ... )
        >>> summary.get_handler_count()
        3

    See Also:
        - :class:`~omnibase_core.models.manifest.model_dependency_edge.ModelDependencyEdge`:
          The dependency edge model
        - :class:`~omnibase_core.models.manifest.model_execution_manifest.ModelExecutionManifest`:
          The parent manifest model

    .. versionadded:: 0.4.0
        Added as part of Manifest Generation & Observability (OMN-1113)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )

    phases: list[str] = Field(
        default_factory=list,
        description="Phases in canonical execution order",
    )

    resolved_order: list[str] = Field(
        default_factory=list,
        description="Handler IDs in resolved execution order (flattened)",
    )

    dependency_edges: list[ModelDependencyEdge] = Field(
        default_factory=list,
        description="Dependency relationships used for ordering",
    )

    ordering_policy: str | None = Field(
        default=None,
        description="Policy used for ordering (e.g., 'topological_sort', 'priority')",
    )

    ordering_rationale: str | None = Field(
        default=None,
        description="Human-readable explanation of why this order was chosen",
    )

    # === Utility Methods ===

    def get_phase_count(self) -> int:
        """
        Get the number of phases.

        Returns:
            Count of phases in the execution order
        """
        return len(self.phases)

    def get_handler_count(self) -> int:
        """
        Get the number of handlers in the resolved order.

        Returns:
            Count of handlers
        """
        return len(self.resolved_order)

    def get_dependency_count(self) -> int:
        """
        Get the number of dependency edges.

        Returns:
            Count of dependency edges
        """
        return len(self.dependency_edges)

    def is_empty(self) -> bool:
        """
        Check if the ordering is empty.

        Returns:
            True if no handlers are in the resolved order
        """
        return len(self.resolved_order) == 0

    def has_handler(self, handler_id: str) -> bool:
        """
        Check if a handler is in the resolved order.

        Args:
            handler_id: The handler ID to check

        Returns:
            True if handler is in the resolved order
        """
        return handler_id in self.resolved_order

    def get_handler_index(self, handler_id: str) -> int | None:
        """
        Get the index of a handler in the resolved order.

        Args:
            handler_id: The handler ID to find

        Returns:
            Zero-based index or None if not found
        """
        try:
            return self.resolved_order.index(handler_id)
        except ValueError:
            return None

    def get_dependencies_for(self, handler_id: str) -> list[str]:
        """
        Get the handlers that a specific handler depends on.

        Args:
            handler_id: The handler to get dependencies for

        Returns:
            List of handler IDs that must run before this handler
        """
        return [
            edge.to_handler_id
            for edge in self.dependency_edges
            if edge.from_handler_id == handler_id
        ]

    def get_dependents_of(self, handler_id: str) -> list[str]:
        """
        Get the handlers that depend on a specific handler.

        Args:
            handler_id: The handler to get dependents for

        Returns:
            List of handler IDs that depend on this handler
        """
        return [
            edge.from_handler_id
            for edge in self.dependency_edges
            if edge.to_handler_id == handler_id
        ]

    def all_dependencies_satisfied(self) -> bool:
        """
        Check if all dependencies were satisfied.

        Returns:
            True if all dependency edges are marked as satisfied
        """
        return all(edge.satisfied for edge in self.dependency_edges)

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        handler_str = (
            " -> ".join(self.resolved_order) if self.resolved_order else "(empty)"
        )
        return f"OrderingSummary[{handler_str}]"

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelOrderingSummary(phases={self.phases!r}, "
            f"resolved_order={self.resolved_order!r}, "
            f"ordering_policy={self.ordering_policy!r})"
        )


# Export for use
__all__ = ["ModelOrderingSummary"]
