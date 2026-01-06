"""
Decision type enum for decision classification.

Provides type-safe classification of agent decisions for analysis
and reporting within memory snapshots.
"""

from enum import Enum


class EnumDecisionType(str, Enum):
    """Decision types for classification.

    Each decision in a memory snapshot is tagged with its type,
    enabling systematic analysis and reporting of decision patterns.

    Attributes:
        MODEL_SELECTION: Decision about which AI model to use
        ROUTE_CHOICE: Decision about routing or path selection
        RETRY_STRATEGY: Decision about retry behavior after failure
        TOOL_SELECTION: Decision about which tool to invoke
        ESCALATION: Decision to escalate to human or higher authority
        EARLY_TERMINATION: Decision to terminate early (success or abort)
        PARAMETER_CHOICE: Decision about parameter values or configuration
        CUSTOM: Escape hatch for forward-compatibility with new decision types
    """

    MODEL_SELECTION = "model_selection"
    ROUTE_CHOICE = "route_choice"
    RETRY_STRATEGY = "retry_strategy"
    TOOL_SELECTION = "tool_selection"
    ESCALATION = "escalation"
    EARLY_TERMINATION = "early_termination"
    PARAMETER_CHOICE = "parameter_choice"
    CUSTOM = "custom"
