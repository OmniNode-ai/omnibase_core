# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Reward target type enum for reward assignment.

Defines the entity types that can receive reward signals in the
objective functions and reward architecture (OMN-2537).
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumRewardTargetType"]


@unique
class EnumRewardTargetType(StrValueHelper, str, Enum):
    """Entity types that can receive reward signals.

    Used in RewardAssignedEvent to identify the target of a reward delta.

    Attributes:
        TOOL: A tool invoked by an agent during execution.
        MODEL: An LLM model used for a task.
        PATTERN: A reusable code or reasoning pattern from the pattern library.
        AGENT: An agent configuration or role definition.
    """

    TOOL = "tool"
    """A tool invoked by an agent during execution."""

    MODEL = "model"
    """An LLM model used for a task class."""

    PATTERN = "pattern"
    """A reusable code or reasoning pattern from the pattern library."""

    AGENT = "agent"
    """An agent configuration or role definition."""
