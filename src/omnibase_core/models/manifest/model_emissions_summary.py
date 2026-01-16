"""
Emissions Summary Model for Execution Manifest.

Defines the ModelEmissionsSummary model which captures a summary of all
outputs produced during pipeline execution. This answers "what did execution
produce?" without including the actual payloads.

This is a pure data model with no side effects.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelEmissionsSummary(BaseModel):
    """
    Summary of outputs produced during execution.

    This model captures what was emitted during pipeline execution,
    providing counts and types without the actual payload data.
    Emissions include events, intents, projections, and actions.

    Note: This model captures summaries, not payload dumps. Do not
    inline event payloads - reference by type/count only.

    Attributes:
        events_count: Number of events emitted
        event_types: List of unique event type names
        intents_count: Number of intents emitted
        intent_types: List of unique intent type names
        projections_count: Number of projections updated
        projection_types: List of unique projection type names
        actions_count: Number of actions emitted
        action_types: List of unique action type names

    Example:
        >>> summary = ModelEmissionsSummary(
        ...     events_count=5,
        ...     event_types=["UserCreated", "UserUpdated"],
        ...     intents_count=2,
        ...     intent_types=["SendWelcomeEmail"],
        ... )
        >>> summary.total_emissions()
        7

    See Also:
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
        validate_assignment=True,
    )

    # === Events ===

    events_count: int = Field(
        default=0,
        ge=0,
        description="Number of events emitted",
    )

    event_types: list[str] = Field(
        default_factory=list,
        description="List of unique event type names",
    )

    # === Intents ===

    intents_count: int = Field(
        default=0,
        ge=0,
        description="Number of intents emitted",
    )

    intent_types: list[str] = Field(
        default_factory=list,
        description="List of unique intent type names",
    )

    # === Projections ===

    projections_count: int = Field(
        default=0,
        ge=0,
        description="Number of projections updated",
    )

    projection_types: list[str] = Field(
        default_factory=list,
        description="List of unique projection type names",
    )

    # === Actions ===

    actions_count: int = Field(
        default=0,
        ge=0,
        description="Number of actions emitted",
    )

    action_types: list[str] = Field(
        default_factory=list,
        description="List of unique action type names",
    )

    # === Utility Methods ===

    def total_emissions(self) -> int:
        """
        Get the total number of emissions.

        Returns:
            Sum of all emission counts
        """
        return (
            self.events_count
            + self.intents_count
            + self.projections_count
            + self.actions_count
        )

    def is_empty(self) -> bool:
        """
        Check if no emissions were produced.

        Returns:
            True if total_emissions() is 0
        """
        return self.total_emissions() == 0

    def has_events(self) -> bool:
        """
        Check if events were emitted.

        Returns:
            True if events_count > 0
        """
        return self.events_count > 0

    def has_intents(self) -> bool:
        """
        Check if intents were emitted.

        Returns:
            True if intents_count > 0
        """
        return self.intents_count > 0

    def has_projections(self) -> bool:
        """
        Check if projections were updated.

        Returns:
            True if projections_count > 0
        """
        return self.projections_count > 0

    def has_actions(self) -> bool:
        """
        Check if actions were emitted.

        Returns:
            True if actions_count > 0
        """
        return self.actions_count > 0

    def get_all_types(self) -> list[str]:
        """
        Get all unique emission types across all categories.

        Returns:
            Combined list of all emission type names
        """
        return (
            self.event_types
            + self.intent_types
            + self.projection_types
            + self.action_types
        )

    def get_unique_type_count(self) -> int:
        """
        Get the count of unique emission types.

        Returns:
            Number of unique emission type names
        """
        return len(set(self.get_all_types()))

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        parts = []
        if self.events_count:
            parts.append(f"events={self.events_count}")
        if self.intents_count:
            parts.append(f"intents={self.intents_count}")
        if self.projections_count:
            parts.append(f"projections={self.projections_count}")
        if self.actions_count:
            parts.append(f"actions={self.actions_count}")
        content = ", ".join(parts) if parts else "empty"
        return f"EmissionsSummary({content})"

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelEmissionsSummary(events_count={self.events_count}, "
            f"intents_count={self.intents_count}, "
            f"projections_count={self.projections_count}, "
            f"actions_count={self.actions_count})"
        )


# Export for use
__all__ = ["ModelEmissionsSummary"]
