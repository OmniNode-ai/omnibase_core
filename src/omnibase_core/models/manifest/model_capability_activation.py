"""
Capability Activation Model for Execution Manifest.

Defines the ModelCapabilityActivation model which captures a single capability
activation decision during pipeline execution. This provides explainability
for why a capability was activated or skipped.

This is a pure data model with no side effects.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_activation_reason import EnumActivationReason


class ModelCapabilityActivation(BaseModel):
    """
    A single capability activation decision.

    This model captures the decision-making context for why a specific
    capability was activated or skipped during pipeline execution. It
    provides explainability by recording predicate evaluations and
    other factors that influenced the decision.

    Attributes:
        capability_name: Qualified name of the capability
        activated: Whether the capability was activated
        reason: Why the capability was activated or skipped
        predicate_expression: Optional predicate expression that was evaluated
        predicate_inputs: Optional inputs used for predicate evaluation
        predicate_result: Optional result of predicate evaluation
        dependencies_satisfied: Whether all dependencies were satisfied
        conflict_with: List of capabilities this conflicts with

    Example:
        >>> from omnibase_core.enums.enum_activation_reason import EnumActivationReason
        >>> activation = ModelCapabilityActivation(
        ...     capability_name="onex:caching",
        ...     activated=True,
        ...     reason=EnumActivationReason.PREDICATE_TRUE,
        ...     predicate_expression="env.cache_enabled == true",
        ...     predicate_result=True,
        ... )
        >>> activation.is_activated()
        True

    See Also:
        - :class:`~omnibase_core.models.manifest.model_activation_summary.ModelActivationSummary`:
          The summary model that aggregates these activations
        - :class:`~omnibase_core.enums.enum_activation_reason.EnumActivationReason`:
          The enum defining activation/skip reasons

    .. versionadded:: 0.4.0
        Added as part of Manifest Generation & Observability (OMN-1113)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )

    # === Required Fields ===

    capability_name: str = Field(
        ...,
        min_length=1,
        description="Qualified name of the capability (e.g., 'onex:caching')",
    )

    activated: bool = Field(
        ...,
        description="Whether the capability was activated",
    )

    reason: EnumActivationReason = Field(
        ...,
        description="Why the capability was activated or skipped",
    )

    # === Predicate Evaluation Context ===

    predicate_expression: str | None = Field(
        default=None,
        description="Predicate expression that was evaluated",
    )

    predicate_inputs: dict[str, str | int | float | bool | None] | None = Field(
        default=None,
        description="Inputs used for predicate evaluation",
    )

    predicate_result: bool | None = Field(
        default=None,
        description="Result of predicate evaluation (True/False)",
    )

    # === Dependency and Conflict Context ===

    dependencies_satisfied: bool = Field(
        default=True,
        description="Whether all required dependencies were satisfied",
    )

    conflict_with: list[str] = Field(
        default_factory=list,
        description="List of capability names this conflicts with",
    )

    # === Utility Methods ===

    def is_activated(self) -> bool:
        """
        Check if the capability was activated.

        Returns:
            True if capability was activated, False if skipped
        """
        return self.activated

    def is_skipped(self) -> bool:
        """
        Check if the capability was skipped.

        Returns:
            True if capability was skipped, False if activated
        """
        return not self.activated

    def has_predicate(self) -> bool:
        """
        Check if a predicate expression was evaluated.

        Returns:
            True if predicate_expression is set
        """
        return self.predicate_expression is not None

    def has_conflicts(self) -> bool:
        """
        Check if there are any conflicts.

        Returns:
            True if conflict_with list is non-empty
        """
        return len(self.conflict_with) > 0

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        status = "ACTIVATED" if self.activated else "SKIPPED"
        return (
            f"Capability({self.capability_name}: {status}, reason={self.reason.value})"
        )

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelCapabilityActivation(capability_name={self.capability_name!r}, "
            f"activated={self.activated!r}, "
            f"reason={self.reason!r}, "
            f"predicate_result={self.predicate_result!r})"
        )


# Export for use
__all__ = ["ModelCapabilityActivation"]
