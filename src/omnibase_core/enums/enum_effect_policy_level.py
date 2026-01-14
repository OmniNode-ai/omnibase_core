"""Effect Policy Level Enum for replay enforcement.

Defines enforcement levels for non-deterministic effect handling during replay.
Part of the effect boundary system for OMN-1147.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumEffectPolicyLevel"]


@unique
class EnumEffectPolicyLevel(StrValueHelper, str, Enum):
    """Policy enforcement levels for non-deterministic effects during replay.

    Determines how the runtime handles detected non-deterministic effects
    when executing in replay or deterministic mode.
    """

    STRICT = "strict"
    """Block all non-deterministic effects during replay."""

    WARN = "warn"
    """Log warnings but allow execution to proceed."""

    PERMISSIVE = "permissive"
    """Allow execution with audit trail for compliance tracking."""

    MOCKED = "mocked"
    """Replace with deterministic mocks during replay."""

    @classmethod
    def blocks_execution(cls, level: "EnumEffectPolicyLevel") -> bool:
        """Check if this policy level blocks non-deterministic execution."""
        return level == cls.STRICT

    @classmethod
    def requires_mock(cls, level: "EnumEffectPolicyLevel") -> bool:
        """Check if this policy level requires mocking non-deterministic effects."""
        return level == cls.MOCKED
