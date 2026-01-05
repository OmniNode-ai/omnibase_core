"""Comparison models for invariant and execution comparison.

This module provides models for comparing execution results,
particularly for invariant evaluation between baseline and replay runs.

Exports:
    ModelExecutionComparison: Complete comparison between baseline and replay execution.
    ModelInvariantComparisonSummary: Aggregated statistics of invariant comparison.
    ModelOutputDiff: Structured representation of output differences.
    ModelValueChange: Single value change between baseline and replay.

Thread Safety:
    All models in this module are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from omnibase_core.models.comparison.model_execution_comparison import (
    ModelExecutionComparison,
)
from omnibase_core.models.comparison.model_invariant_comparison_summary import (
    ModelInvariantComparisonSummary,
)
from omnibase_core.models.comparison.model_output_diff import ModelOutputDiff
from omnibase_core.models.comparison.model_value_change import ModelValueChange

__all__ = [
    "ModelExecutionComparison",
    "ModelInvariantComparisonSummary",
    "ModelOutputDiff",
    "ModelValueChange",
]
