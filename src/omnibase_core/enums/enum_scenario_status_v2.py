"""
Scenario Status Enumeration v2 - Unified Hierarchy Version.

Enhanced scenario status using the unified status hierarchy. Extends base status
values with scenario-specific states while eliminating conflicts with other domains.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

from .enum_base_status import EnumBaseStatus


@unique
class EnumScenarioStatusV2(StrValueHelper, str, Enum):
    """
    Scenario status enumeration extending base status hierarchy.

    Inherits fundamental status values from EnumBaseStatus and adds
    scenario-specific states. Eliminates conflicts while maintaining
    all original functionality.

    Base States (from EnumBaseStatus):
    - INACTIVE, ACTIVE, PENDING (lifecycle)
    - RUNNING, COMPLETED, FAILED (execution)
    - VALID, INVALID, UNKNOWN (quality)

    Scenario-Specific Extensions:
    - NOT_EXECUTED (scenario not yet run)
    - QUEUED (scenario waiting to run)
    - SKIPPED (scenario was skipped)
    """

    # Base status values (inherited semantically)
    INACTIVE = EnumBaseStatus.INACTIVE.value
    ACTIVE = EnumBaseStatus.ACTIVE.value
    PENDING = EnumBaseStatus.PENDING.value
    RUNNING = EnumBaseStatus.RUNNING.value
    COMPLETED = EnumBaseStatus.COMPLETED.value
    FAILED = EnumBaseStatus.FAILED.value
    VALID = EnumBaseStatus.VALID.value
    INVALID = EnumBaseStatus.INVALID.value
    UNKNOWN = EnumBaseStatus.UNKNOWN.value

    # Scenario-specific extensions
    NOT_EXECUTED = "not_executed"  # Scenario hasn't been run yet
    QUEUED = "queued"  # Scenario is queued for execution
    SKIPPED = "skipped"  # Scenario was skipped during execution

    def to_base_status(self) -> EnumBaseStatus:
        """Convert to base status enum for universal operations."""
        # Map scenario-specific values to base equivalents
        base_mapping = {
            self.NOT_EXECUTED: EnumBaseStatus.INACTIVE,
            self.QUEUED: EnumBaseStatus.PENDING,
            self.SKIPPED: EnumBaseStatus.INACTIVE,
        }

        # If it's a direct base value, return it
        try:
            return EnumBaseStatus(self.value)
        except ValueError:
            # If it's scenario-specific, map to base equivalent
            return base_mapping.get(self, EnumBaseStatus.UNKNOWN)

    @classmethod
    def from_base_status(cls, base_status: EnumBaseStatus) -> EnumScenarioStatusV2:
        """Create scenario status from base status."""
        # Direct mapping for base values
        return cls(base_status.value)

    @classmethod
    def is_executable(cls, status: EnumScenarioStatusV2) -> bool:
        """Check if the scenario can be executed."""
        return status in {
            cls.NOT_EXECUTED,
            cls.QUEUED,
            cls.PENDING,
            cls.INACTIVE,
        }

    @classmethod
    def is_executing(cls, status: EnumScenarioStatusV2) -> bool:
        """Check if the scenario is currently executing."""
        return status in {cls.RUNNING, cls.ACTIVE}

    @classmethod
    def is_terminal(cls, status: EnumScenarioStatusV2) -> bool:
        """Check if the status represents a terminal state."""
        return status in {
            cls.COMPLETED,
            cls.FAILED,
            cls.SKIPPED,
        }

    @classmethod
    def requires_attention(cls, status: EnumScenarioStatusV2) -> bool:
        """Check if the status requires attention."""
        return status in {cls.FAILED, cls.INVALID}

    @classmethod
    def is_waiting(cls, status: EnumScenarioStatusV2) -> bool:
        """Check if the scenario is waiting to execute."""
        return status in {
            cls.NOT_EXECUTED,
            cls.QUEUED,
            cls.PENDING,
        }

    @classmethod
    def is_successful(cls, status: EnumScenarioStatusV2) -> bool:
        """Check if the scenario completed successfully."""
        return status in {cls.COMPLETED, cls.VALID}


# Deprecated: use EnumScenarioStatusV2 directly
# Note: Python enums cannot extend other enums, so we use module-level alias
EnumScenarioStatus: type[EnumScenarioStatusV2] = EnumScenarioStatusV2


# Export for use
__all__ = ["EnumScenarioStatus", "EnumScenarioStatusV2"]
