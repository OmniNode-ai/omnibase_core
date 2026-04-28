# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Eval Metric Type Enum.

Metric types collected during eval runs.
"""

from enum import Enum, unique


@unique
class EnumEvalMetricType(str, Enum):
    """Types of metrics collected during eval runs.

    Each metric type has a standard unit:
    - LATENCY_MS: milliseconds
    - TOKEN_COUNT: count
    - SUCCESS_RATE: ratio (0.0-1.0)
    - PATTERN_HIT_RATE: ratio (0.0-1.0)
    - ERROR_COUNT: count
    - RETRY_COUNT: count
    """

    LATENCY_MS = "latency_ms"
    """Wall-clock time for task completion in milliseconds."""

    TOKEN_COUNT = "token_count"
    """Total tokens consumed during the run."""

    SUCCESS_RATE = "success_rate"
    """Fraction of success criteria met (0.0-1.0)."""

    PATTERN_HIT_RATE = "pattern_hit_rate"
    """Fraction of decisions where a pattern was applied (0.0-1.0)."""

    ERROR_COUNT = "error_count"
    """Number of errors encountered during the run."""

    RETRY_COUNT = "retry_count"
    """Number of retried tool calls during the run."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
