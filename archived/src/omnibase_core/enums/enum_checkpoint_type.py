"""
Enum for checkpoint types.
Single responsibility: Centralized checkpoint type definitions.
"""

from enum import Enum


class EnumCheckpointType(str, Enum):
    """Types of workflow checkpoints."""

    MANUAL = "manual"
    AUTOMATIC = "automatic"
    FAILURE_RECOVERY = "failure_recovery"
    STEP_COMPLETION = "step_completion"
    COMPOSITION_BOUNDARY = "composition_boundary"
