"""
Phase Step Model for Runtime Execution Sequencing.

This module defines the ModelPhaseStep model which represents a single phase unit
in the ONEX Runtime Execution Sequencing Model. Each phase step contains an ordered
list of handler identifiers that should execute during that phase.

This is a pure data model with no side effects.

.. versionadded:: 0.4.0
    Added as part of Runtime Execution Sequencing Model (OMN-1108)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase


class ModelPhaseStep(BaseModel):
    """
    A single phase step in the execution sequence.

    This model represents one phase unit with an ordered list of handler
    identifiers. It is used by the runtime to determine which handlers
    to execute and in what order during a specific execution phase.

    The model is immutable (frozen) to ensure thread safety and prevent
    accidental modification during execution.

    Attributes:
        phase: The execution phase this step represents (PREFLIGHT, BEFORE, etc.)
        handler_ids: Ordered list of handler identifiers to execute in this phase
        ordering_rationale: Optional explanation of why handlers are ordered this way
        metadata: Optional metadata about this phase step

    Example:
        >>> from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
        >>> step = ModelPhaseStep(
        ...     phase=EnumHandlerExecutionPhase.EXECUTE,
        ...     handler_ids=["handler_validate", "handler_transform", "handler_save"],
        ...     ordering_rationale="Validate before transform, save last"
        ... )
        >>> step.handler_count()
        3
        >>> step.is_empty()
        False

    See Also:
        - :class:`~omnibase_core.enums.enum_handler_execution_phase.EnumHandlerExecutionPhase`:
          The enum defining available execution phases
        - :class:`~omnibase_core.models.contracts.model_execution_profile.ModelExecutionProfile`:
          The profile model that uses phase steps

    .. versionadded:: 0.4.0
        Added as part of Runtime Execution Sequencing Model (OMN-1108)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
        validate_assignment=True,
    )

    phase: EnumHandlerExecutionPhase = Field(
        ...,
        description="The execution phase this step represents",
    )

    handler_ids: list[str] = Field(
        default_factory=list,
        description="Ordered list of handler identifiers to execute in this phase",
    )

    ordering_rationale: str | None = Field(
        default=None,
        description="Optional explanation of why handlers are ordered this way",
    )

    metadata: dict[str, str | int | float | bool | None] | None = Field(
        default=None,
        description="Optional metadata about this phase step",
    )

    def is_empty(self) -> bool:
        """
        Check if this phase step has no handlers.

        Returns:
            True if handler_ids is empty, False otherwise
        """
        return len(self.handler_ids) == 0

    def handler_count(self) -> int:
        """
        Get the number of handlers in this phase step.

        Returns:
            The number of handler identifiers in handler_ids
        """
        return len(self.handler_ids)

    def has_handler(self, handler_id: str) -> bool:
        """
        Check if a specific handler is in this phase step.

        Args:
            handler_id: The handler identifier to check for

        Returns:
            True if the handler_id is in handler_ids, False otherwise
        """
        return handler_id in self.handler_ids

    def get_handler_index(self, handler_id: str) -> int | None:
        """
        Get the index of a handler in the execution order.

        Args:
            handler_id: The handler identifier to find

        Returns:
            Zero-based index of the handler, or None if not found
        """
        try:
            return self.handler_ids.index(handler_id)
        except ValueError:
            return None

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        handler_list = ", ".join(self.handler_ids) if self.handler_ids else "(empty)"
        return f"PhaseStep({self.phase.value}: [{handler_list}])"

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelPhaseStep(phase={self.phase!r}, "
            f"handler_ids={self.handler_ids!r}, "
            f"ordering_rationale={self.ordering_rationale!r}, "
            f"metadata={self.metadata!r})"
        )


# Export for use
__all__ = ["ModelPhaseStep"]
