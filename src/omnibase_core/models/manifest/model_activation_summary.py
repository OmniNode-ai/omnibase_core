"""
Activation Summary Model for Execution Manifest.

Defines the ModelActivationSummary model which aggregates all capability
activation decisions made during a pipeline run. This answers the question
"what ran and why?" at a summary level.

This is a pure data model with no side effects.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.manifest.model_capability_activation import (
    ModelCapabilityActivation,
)


class ModelActivationSummary(BaseModel):
    """
    Summary of capability activation decisions.

    This model aggregates all capability activation decisions made during
    pipeline execution, providing a high-level view of what was activated
    and what was skipped with their reasons.

    Attributes:
        activated_capabilities: List of capabilities that were activated
        skipped_capabilities: List of capabilities that were skipped
        total_evaluated: Total number of capabilities evaluated

    Example:
        >>> from omnibase_core.enums.enum_activation_reason import EnumActivationReason
        >>> from omnibase_core.models.manifest.model_capability_activation import (
        ...     ModelCapabilityActivation,
        ... )
        >>> activated = ModelCapabilityActivation(
        ...     capability_name="onex:caching",
        ...     activated=True,
        ...     reason=EnumActivationReason.PREDICATE_TRUE,
        ... )
        >>> summary = ModelActivationSummary(
        ...     activated_capabilities=[activated],
        ...     total_evaluated=1,
        ... )
        >>> summary.get_activated_count()
        1

    See Also:
        - :class:`~omnibase_core.models.manifest.model_capability_activation.ModelCapabilityActivation`:
          The individual activation decision model
        - :class:`~omnibase_core.models.manifest.model_execution_manifest.ModelExecutionManifest`:
          The parent manifest model that uses this summary

    .. versionadded:: 0.4.0
        Added as part of Manifest Generation & Observability (OMN-1113)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )

    activated_capabilities: list[ModelCapabilityActivation] = Field(
        default_factory=list,
        description="Capabilities that were activated",
    )

    skipped_capabilities: list[ModelCapabilityActivation] = Field(
        default_factory=list,
        description="Capabilities that were skipped",
    )

    total_evaluated: int = Field(
        default=0,
        ge=0,
        description="Total number of capabilities evaluated",
    )

    # === Utility Methods ===

    def get_activated_count(self) -> int:
        """
        Get the number of activated capabilities.

        Returns:
            Count of activated capabilities
        """
        return len(self.activated_capabilities)

    def get_skipped_count(self) -> int:
        """
        Get the number of skipped capabilities.

        Returns:
            Count of skipped capabilities
        """
        return len(self.skipped_capabilities)

    def is_empty(self) -> bool:
        """
        Check if no capabilities were evaluated.

        Returns:
            True if total_evaluated is 0
        """
        return self.total_evaluated == 0

    def get_activation_rate(self) -> float:
        """
        Get the activation rate as a percentage.

        Returns:
            Percentage of capabilities that were activated (0.0 to 100.0)
        """
        if self.total_evaluated == 0:
            return 0.0
        return (self.get_activated_count() / self.total_evaluated) * 100.0

    def get_capability_names(self, activated_only: bool = False) -> list[str]:
        """
        Get list of capability names.

        Args:
            activated_only: If True, only return activated capability names

        Returns:
            List of capability names
        """
        if activated_only:
            return [cap.capability_name for cap in self.activated_capabilities]
        return [cap.capability_name for cap in self.activated_capabilities] + [
            cap.capability_name for cap in self.skipped_capabilities
        ]

    def has_capability(self, capability_name: str) -> bool:
        """
        Check if a capability was evaluated.

        Args:
            capability_name: Name of the capability to check

        Returns:
            True if capability was evaluated (activated or skipped)

        Note:
            Uses direct iteration for O(n) lookup without creating intermediate lists.
        """
        # Check activated capabilities first (more likely to match in typical usage)
        for cap in self.activated_capabilities:
            if cap.capability_name == capability_name:
                return True
        # Then check skipped capabilities
        for cap in self.skipped_capabilities:
            if cap.capability_name == capability_name:
                return True
        return False

    def was_activated(self, capability_name: str) -> bool:
        """
        Check if a specific capability was activated.

        Args:
            capability_name: Name of the capability to check

        Returns:
            True if capability was activated, False if skipped or not found

        Note:
            Uses direct iteration for O(n) lookup without creating intermediate lists.
        """
        for cap in self.activated_capabilities:
            if cap.capability_name == capability_name:
                return True
        return False

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return (
            f"ActivationSummary(activated={self.get_activated_count()}, "
            f"skipped={self.get_skipped_count()}, "
            f"total={self.total_evaluated})"
        )

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelActivationSummary(activated_count={self.get_activated_count()}, "
            f"skipped_count={self.get_skipped_count()}, "
            f"total_evaluated={self.total_evaluated})"
        )


# Export for use
__all__ = ["ModelActivationSummary"]
