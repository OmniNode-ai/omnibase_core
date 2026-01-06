"""
Decision Type Enum.

Provides type-safe classification of agent decisions for analysis
and reporting within memory snapshots.
"""

from enum import Enum, unique


@unique
class EnumDecisionType(str, Enum):
    """Decision types for memory snapshot classification.

    Each decision in a memory snapshot is tagged with its type,
    enabling systematic analysis and reporting of decision patterns.
    This enum supports the omnimemory system for tracking agent
    decision-making processes.

    Example:
        >>> decision_type = EnumDecisionType.MODEL_SELECTION
        >>> str(decision_type)
        'model_selection'

        >>> # Use with Pydantic (string coercion works)
        >>> from pydantic import BaseModel
        >>> class DecisionRecord(BaseModel):
        ...     decision_type: EnumDecisionType
        >>> record = DecisionRecord(decision_type="tool_selection")
        >>> record.decision_type == EnumDecisionType.TOOL_SELECTION
        True
    """

    MODEL_SELECTION = "model_selection"
    """Decision about which AI model to use for a task."""

    ROUTE_CHOICE = "route_choice"
    """Decision about routing or path selection in workflow execution."""

    RETRY_STRATEGY = "retry_strategy"
    """Decision about retry behavior after a failure occurs."""

    TOOL_SELECTION = "tool_selection"
    """Decision about which tool or capability to invoke."""

    ESCALATION = "escalation"
    """Decision to escalate to human oversight or higher authority."""

    EARLY_TERMINATION = "early_termination"
    """Decision to terminate early (success or abort)."""

    PARAMETER_CHOICE = "parameter_choice"
    """Decision about parameter values or configuration settings."""

    CUSTOM = "custom"
    """Escape hatch for forward-compatibility with new decision types."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value


__all__ = ["EnumDecisionType"]
