"""
OmniMemory Constants.

Centralized constants for the OmniMemory subsystem, including floating point
comparison tolerances and other configuration values.

Overview
--------
This module defines constants used by the OmniMemory models for cost tracking,
diff computation, and related operations.

Rationale
---------
**FLOAT_COMPARISON_EPSILON (1e-9)**:

Cost values in OmniMemory typically represent dollar amounts ranging from
fractions of a cent (LLM API calls at $0.0001) to tens of thousands of dollars
(large batch operations). Standard IEEE 754 double-precision floating point
arithmetic can introduce errors at approximately 15-16 significant digits.

For practical cost comparisons:
- $0.0001 with 1e-9 tolerance ignores differences < $0.0000000001
- $10,000 with 1e-9 tolerance ignores differences < $0.00001

This 1e-9 threshold is small enough to detect any meaningful cost change
(even sub-cent differences) while filtering out floating point noise from
arithmetic operations like subtraction, summation, and rounding.

.. versionadded:: 0.6.0
    Added as part of OmniMemory core infrastructure (OMN-1243)
"""

# =============================================================================
# Floating Point Comparison Constants
# =============================================================================
#
# These constants define tolerances for floating point comparisons in the
# OmniMemory subsystem. Use these instead of hardcoded magic numbers to
# ensure consistent behavior across the codebase.
# =============================================================================

# Float comparison epsilon for cost deltas.
#
# Purpose: Determine if a cost difference is significant enough to report
# or include in diff summaries.
#
# Rationale: 1e-9 is chosen because:
#   - It's below typical floating point precision errors for dollar amounts
#     in the expected range ($0.0001 to $100,000)
#   - Avoids noise from float arithmetic (addition, subtraction, rounding)
#   - Small enough to detect any meaningful cost change (sub-cent precision)
#   - Large enough to filter IEEE 754 representation artifacts
#
# Use cases:
#   - ModelMemoryDiff.has_changes property
#   - ModelMemorySnapshot.diff_from() summary generation
#   - Cost delta reporting in __str__ methods
#
# Example:
#   >>> cost_delta = 0.0000000001  # $0.0000000001
#   >>> if abs(cost_delta) > FLOAT_COMPARISON_EPSILON:
#   ...     print("Significant cost change detected")
#   >>> # No output - difference is below epsilon threshold
#
# Units: Dimensionless (used with abs() for comparison)
FLOAT_COMPARISON_EPSILON: float = 1e-9

# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "FLOAT_COMPARISON_EPSILON",
]
