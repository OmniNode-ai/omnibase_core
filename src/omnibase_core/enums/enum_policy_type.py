# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Policy type enum for policy state management.

Defines the types of policy state tracked in the objective functions
and reward architecture (OMN-2537).
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumPolicyType"]


@unique
class EnumPolicyType(StrValueHelper, str, Enum):
    """Types of policy state updated by reward signals.

    Each policy type has a defined state shape that is updated by
    RewardAssigned events and transitions through the policy lifecycle.

    Attributes:
        TOOL_RELIABILITY: Reliability score for a specific tool.
        PATTERN_EFFECTIVENESS: Effectiveness score for a code/reasoning pattern.
        MODEL_ROUTING_CONFIDENCE: Routing confidence for a model on a task class.
        RETRY_THRESHOLD: Maximum retry threshold for a context class.
    """

    TOOL_RELIABILITY = "tool_reliability"
    """Reliability score for a tool: { tool_id, reliability_0_1, run_count, failure_count }."""

    PATTERN_EFFECTIVENESS = "pattern_effectiveness"
    """Effectiveness score for a pattern: { pattern_id, effectiveness_0_1, promotion_tier }."""

    MODEL_ROUTING_CONFIDENCE = "model_routing_confidence"
    """Routing confidence for a model: { model_id, task_class, confidence_0_1, cost_per_token }."""

    RETRY_THRESHOLD = "retry_threshold"
    """Retry policy for a context class: { context_class, max_retries, escalation_after }."""
