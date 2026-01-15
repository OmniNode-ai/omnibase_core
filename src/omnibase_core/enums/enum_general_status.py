"""
General Status Enumeration - Unified Hierarchy Version.

Comprehensive status enum for general-purpose status tracking. Replaces the
original overly broad EnumStatus with a well-organized hierarchy that leverages
base status values while adding commonly needed general status concepts.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

from .enum_base_status import EnumBaseStatus


@unique
class EnumGeneralStatus(StrValueHelper, str, Enum):
    """
    General purpose status enumeration extending base status hierarchy.

    Provides comprehensive status tracking for models that need general
    status concepts spanning multiple domains. Organized into logical
    categories while maintaining compatibility with base status.

    Base States (from EnumBaseStatus):
    - INACTIVE, ACTIVE, PENDING (lifecycle)
    - RUNNING, COMPLETED, FAILED (execution)
    - VALID, INVALID, UNKNOWN (quality)

    General Extensions:
    - EnumLifecycle: CREATED, UPDATED, DELETED, ARCHIVED
    - Approval: APPROVED, REJECTED, UNDER_REVIEW
    - Availability: AVAILABLE, UNAVAILABLE, MAINTENANCE
    - Quality: DRAFT, PUBLISHED, DEPRECATED
    - Operational: ENABLED, DISABLED, SUSPENDED
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

    # Extended EnumLifecycle states
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ARCHIVED = "archived"

    # Approval workflow states
    APPROVED = "approved"
    REJECTED = "rejected"
    UNDER_REVIEW = "under_review"

    # Availability states
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    MAINTENANCE = "maintenance"

    # Quality/Publishing states
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"

    # Operational states
    ENABLED = "enabled"
    DISABLED = "disabled"
    SUSPENDED = "suspended"

    # Processing states (specific to general status)
    PROCESSING = "processing"

    def to_base_status(self) -> EnumBaseStatus:
        """Convert to base status enum for universal operations."""
        # Map general-specific values to base equivalents
        base_mapping = {
            # EnumLifecycle mappings
            self.CREATED: EnumBaseStatus.ACTIVE,
            self.UPDATED: EnumBaseStatus.ACTIVE,
            self.DELETED: EnumBaseStatus.INACTIVE,
            self.ARCHIVED: EnumBaseStatus.INACTIVE,
            # Approval mappings
            self.APPROVED: EnumBaseStatus.VALID,
            self.REJECTED: EnumBaseStatus.INVALID,
            self.UNDER_REVIEW: EnumBaseStatus.PENDING,
            # Availability mappings
            self.AVAILABLE: EnumBaseStatus.ACTIVE,
            self.UNAVAILABLE: EnumBaseStatus.INACTIVE,
            self.MAINTENANCE: EnumBaseStatus.PENDING,
            # Quality mappings
            self.DRAFT: EnumBaseStatus.PENDING,
            self.PUBLISHED: EnumBaseStatus.ACTIVE,
            self.DEPRECATED: EnumBaseStatus.INACTIVE,
            # Operational mappings
            self.ENABLED: EnumBaseStatus.ACTIVE,
            self.DISABLED: EnumBaseStatus.INACTIVE,
            self.SUSPENDED: EnumBaseStatus.PENDING,
            # Processing mappings
            self.PROCESSING: EnumBaseStatus.RUNNING,
        }

        # If it's a direct base value, return it
        try:
            return EnumBaseStatus(self.value)
        except ValueError:
            # If it's general-specific, map to base equivalent
            return base_mapping.get(self, EnumBaseStatus.UNKNOWN)

    @classmethod
    def from_base_status(cls, base_status: EnumBaseStatus) -> EnumGeneralStatus:
        """Create general status from base status."""
        # Direct mapping for base values
        return cls(base_status.value)

    def is_active_state(self) -> bool:
        """Check if this represents an active state."""
        return self in {
            self.ACTIVE,
            self.RUNNING,
            self.PROCESSING,
            self.ENABLED,
            self.AVAILABLE,
            self.PUBLISHED,
            self.CREATED,
            self.UPDATED,
            self.APPROVED,
        }

    def is_terminal_state(self) -> bool:
        """Check if this represents a terminal state."""
        return self in {
            self.COMPLETED,
            self.FAILED,
            self.DELETED,
            self.ARCHIVED,
            self.DEPRECATED,
            self.REJECTED,
        }

    def is_error_state(self) -> bool:
        """Check if this represents an error state."""
        return self in {
            self.FAILED,
            self.INVALID,
            self.REJECTED,
            self.UNAVAILABLE,
        }

    def is_pending_state(self) -> bool:
        """Check if this represents a pending state."""
        return self in {
            self.PENDING,
            self.RUNNING,
            self.PROCESSING,
            self.UNDER_REVIEW,
            self.DRAFT,
            self.MAINTENANCE,
            self.SUSPENDED,
        }

    def is_quality_state(self) -> bool:
        """Check if this represents a quality/validation state."""
        return self in {
            self.VALID,
            self.INVALID,
            self.UNKNOWN,
            self.APPROVED,
            self.REJECTED,
            self.UNDER_REVIEW,
        }

    def is_lifecycle_state(self) -> bool:
        """Check if this represents a lifecycle state."""
        return self in {
            self.CREATED,
            self.UPDATED,
            self.DELETED,
            self.ARCHIVED,
            self.INACTIVE,
            self.ACTIVE,
        }

    def is_operational_state(self) -> bool:
        """Check if this represents an operational state."""
        return self in {
            self.ENABLED,
            self.DISABLED,
            self.SUSPENDED,
            self.MAINTENANCE,
            self.AVAILABLE,
            self.UNAVAILABLE,
        }

    @classmethod
    def get_approval_states(cls) -> set[EnumGeneralStatus]:
        """Get all approval workflow states."""
        return {cls.APPROVED, cls.REJECTED, cls.UNDER_REVIEW}

    @classmethod
    def get_lifecycle_states(cls) -> set[EnumGeneralStatus]:
        """Get all lifecycle states."""
        return {
            cls.CREATED,
            cls.UPDATED,
            cls.DELETED,
            cls.ARCHIVED,
            cls.ACTIVE,
            cls.INACTIVE,
        }

    @classmethod
    def get_operational_states(cls) -> set[EnumGeneralStatus]:
        """Get all operational states."""
        return {
            cls.ENABLED,
            cls.DISABLED,
            cls.SUSPENDED,
            cls.AVAILABLE,
            cls.UNAVAILABLE,
            cls.MAINTENANCE,
        }


# Deprecated: use EnumGeneralStatus directly
# Note: Python enums cannot extend other enums, so we use module-level alias
EnumStatus: type[EnumGeneralStatus] = EnumGeneralStatus


# Export for use
__all__ = ["EnumGeneralStatus", "EnumStatus"]
