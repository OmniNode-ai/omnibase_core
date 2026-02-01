"""
Function EnumLifecycle Status Enumeration - Unified Hierarchy Version.

Function lifecycle status using the unified status hierarchy. This enum focuses
on function/component lifecycle states rather than execution states, providing
clear separation from execution-oriented enums.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

from .enum_base_status import EnumBaseStatus


@unique
class EnumFunctionLifecycleStatus(StrValueHelper, str, Enum):
    """
    Function lifecycle status enumeration for component lifecycle management.

    Focuses on the lifecycle and availability status of functions, methods,
    and components. Separate from execution status to eliminate conflicts.

    Base States (from EnumBaseStatus):
    - ACTIVE (function is available and stable)
    - INACTIVE (function is not available)

    EnumLifecycle-Specific States:
    - DEPRECATED (function is marked for removal)
    - DISABLED (function is temporarily disabled)
    - EXPERIMENTAL (function is experimental/beta)
    - MAINTENANCE (function is under maintenance)
    - STABLE (function is production-ready)
    - BETA (function is in beta testing)
    - ALPHA (function is in alpha testing)
    """

    # Base status values (subset relevant to lifecycle)
    ACTIVE = EnumBaseStatus.ACTIVE.value  # Production ready and available
    INACTIVE = EnumBaseStatus.INACTIVE.value  # Not available for use

    # EnumLifecycle-specific states
    DEPRECATED = "deprecated"  # Marked for future removal
    DISABLED = "disabled"  # Temporarily disabled
    EXPERIMENTAL = "experimental"  # Experimental feature
    MAINTENANCE = "maintenance"  # Under maintenance
    STABLE = "stable"  # Production-ready stable version
    BETA = "beta"  # Beta testing phase
    ALPHA = "alpha"  # Alpha testing phase

    def to_base_status(self) -> EnumBaseStatus:
        """Convert to base status enum for universal operations."""
        # Map lifecycle-specific values to base equivalents
        base_mapping = {
            self.DEPRECATED: EnumBaseStatus.ACTIVE,  # Still active but deprecated
            self.DISABLED: EnumBaseStatus.INACTIVE,
            self.EXPERIMENTAL: EnumBaseStatus.ACTIVE,  # Active but experimental
            self.MAINTENANCE: EnumBaseStatus.INACTIVE,  # Temporarily inactive
            self.STABLE: EnumBaseStatus.ACTIVE,
            self.BETA: EnumBaseStatus.ACTIVE,
            self.ALPHA: EnumBaseStatus.ACTIVE,
        }

        # If it's a direct base value, return it
        try:
            return EnumBaseStatus(self.value)
        except ValueError:
            # If it's lifecycle-specific, map to base equivalent
            return base_mapping.get(self, EnumBaseStatus.UNKNOWN)

    @classmethod
    def from_base_status(
        cls,
        base_status: EnumBaseStatus,
    ) -> EnumFunctionLifecycleStatus:
        """Create lifecycle status from base status."""
        # Direct mapping for base values
        return cls(base_status.value)

    @classmethod
    def is_available(cls, status: EnumFunctionLifecycleStatus) -> bool:
        """Check if the function is available for use."""
        return status in {
            cls.ACTIVE,
            cls.EXPERIMENTAL,
            cls.STABLE,
            cls.BETA,
            cls.ALPHA,
        }

    @classmethod
    def requires_warning(cls, status: EnumFunctionLifecycleStatus) -> bool:
        """Check if the function status requires a warning."""
        return status in {
            cls.DEPRECATED,
            cls.EXPERIMENTAL,
            cls.MAINTENANCE,
            cls.BETA,
            cls.ALPHA,
        }

    @classmethod
    def is_production_ready(cls, status: EnumFunctionLifecycleStatus) -> bool:
        """Check if the function is production-ready."""
        return status in {cls.ACTIVE, cls.STABLE}

    @classmethod
    def is_testing_phase(cls, status: EnumFunctionLifecycleStatus) -> bool:
        """Check if the function is in a testing phase."""
        return status in {cls.EXPERIMENTAL, cls.BETA, cls.ALPHA}

    @classmethod
    def is_stable_release(cls, status: EnumFunctionLifecycleStatus) -> bool:
        """Check if the function is a stable release."""
        return status in {cls.ACTIVE, cls.STABLE}

    @classmethod
    def requires_migration_planning(cls, status: EnumFunctionLifecycleStatus) -> bool:
        """Check if the status indicates migration planning is needed."""
        return status in {cls.DEPRECATED}

    @classmethod
    def is_temporarily_unavailable(cls, status: EnumFunctionLifecycleStatus) -> bool:
        """Check if the function is temporarily unavailable."""
        return status in {cls.DISABLED, cls.MAINTENANCE}

    @classmethod
    def get_stability_order(cls, status: EnumFunctionLifecycleStatus) -> int:
        """Get numeric stability order (higher = more stable)."""
        stability_order = {
            cls.ALPHA: 1,
            cls.BETA: 2,
            cls.EXPERIMENTAL: 3,
            cls.ACTIVE: 4,
            cls.STABLE: 5,
            cls.DEPRECATED: 3,  # Stable but deprecated
            cls.DISABLED: 0,
            cls.MAINTENANCE: 2,
            cls.INACTIVE: 0,
        }
        return stability_order.get(status, 0)


# Deprecated: use EnumFunctionLifecycleStatus directly
# Note: Python enums cannot extend other enums, so we use module-level aliases
EnumFunctionStatus: type[EnumFunctionLifecycleStatus] = EnumFunctionLifecycleStatus
EnumMetadataNodeStatus: type[EnumFunctionLifecycleStatus] = EnumFunctionLifecycleStatus


# Export for use
__all__ = [
    "EnumFunctionLifecycleStatus",
    "EnumFunctionStatus",
    "EnumMetadataNodeStatus",
]
