"""
Decision Type Enum.

Provides type-safe classification of agent decisions for analysis
and reporting within memory snapshots.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDecisionType(StrValueHelper, str, Enum):
    """Decision type classification for omnimemory snapshots.

    Classifies decisions recorded in memory snapshots to enable systematic
    analysis and reporting of agent decision-making patterns. Each decision
    event is tagged with its type to support explainability, debugging, and
    optimization of agent workflows in the omnimemory system.

    See Also:
        - docs/omnimemory/memory_snapshots.md: Memory snapshot architecture
        - EnumFailureType: Classification of failures (may trigger retry decisions)
        - EnumSubjectType: Classification of memory ownership

    Values:
        MODEL_SELECTION: Decision about which AI model to use for a task
        ROUTE_CHOICE: Decision about routing or path selection in workflow execution
        RETRY_STRATEGY: Decision about retry behavior after a failure occurs
        TOOL_SELECTION: Decision about which tool or capability to invoke
        ESCALATION: Decision to escalate to human oversight or higher authority
        EARLY_TERMINATION: Decision to terminate early (success or abort)
        PARAMETER_CHOICE: Decision about parameter values or configuration settings
        CUSTOM: Forward-compatibility escape hatch for new decision types

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

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a string value is a valid enum member.

        Args:
            value: The string value to check.

        Returns:
            True if the value is a valid enum member, False otherwise.

        Example:
            >>> EnumDecisionType.is_valid("model_selection")
            True
            >>> EnumDecisionType.is_valid("invalid_type")
            False
        """
        return value in cls._value2member_map_

    def is_terminal_decision(self) -> bool:
        """Check if this decision type typically terminates a workflow.

        Returns:
            True if this is a terminal decision type (ESCALATION or EARLY_TERMINATION).

        Example:
            >>> EnumDecisionType.EARLY_TERMINATION.is_terminal_decision()
            True
            >>> EnumDecisionType.MODEL_SELECTION.is_terminal_decision()
            False
        """
        return self in {
            EnumDecisionType.EARLY_TERMINATION,
            EnumDecisionType.ESCALATION,
        }

    def is_selection_decision(self) -> bool:
        """Check if this decision type involves selecting from options.

        Returns:
            True if this is a selection-type decision.

        Example:
            >>> EnumDecisionType.MODEL_SELECTION.is_selection_decision()
            True
            >>> EnumDecisionType.ESCALATION.is_selection_decision()
            False
        """
        return self in {
            EnumDecisionType.MODEL_SELECTION,
            EnumDecisionType.PARAMETER_CHOICE,
            EnumDecisionType.ROUTE_CHOICE,
            EnumDecisionType.TOOL_SELECTION,
        }


__all__ = ["EnumDecisionType"]
