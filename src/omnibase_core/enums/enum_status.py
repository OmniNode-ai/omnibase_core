"""
Status enumeration for general status tracking.

Provides standardized status values for state management across the system.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumStatus(StrValueHelper, str, Enum):
    """
    General status enumeration for state tracking.

    Provides standardized status values that can be used across different
    models for consistent state management and filtering.
    """

    # Basic status states
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"

    # Processing states
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    # EnumLifecycle states
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ARCHIVED = "archived"

    # Validation states
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"

    # Approval states
    APPROVED = "approved"
    REJECTED = "rejected"
    UNDER_REVIEW = "under_review"

    # Availability states
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    MAINTENANCE = "maintenance"

    # Quality states
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"

    # Operational states
    ENABLED = "enabled"
    DISABLED = "disabled"
    SUSPENDED = "suspended"

    def is_active_state(self) -> bool:
        """Check if this represents an active state."""
        return self in {
            EnumStatus.ACTIVE,
            EnumStatus.PROCESSING,
            EnumStatus.ENABLED,
            EnumStatus.AVAILABLE,
            EnumStatus.PUBLISHED,
        }

    def is_terminal_state(self) -> bool:
        """Check if this represents a terminal state."""
        return self in {
            EnumStatus.COMPLETED,
            EnumStatus.FAILED,
            EnumStatus.DELETED,
            EnumStatus.ARCHIVED,
            EnumStatus.DEPRECATED,
        }

    def is_error_state(self) -> bool:
        """Check if this represents an error state."""
        return self in {
            EnumStatus.FAILED,
            EnumStatus.INVALID,
            EnumStatus.REJECTED,
            EnumStatus.UNAVAILABLE,
        }

    def is_pending_state(self) -> bool:
        """Check if this represents a pending state."""
        return self in {
            EnumStatus.PENDING,
            EnumStatus.PROCESSING,
            EnumStatus.UNDER_REVIEW,
            EnumStatus.DRAFT,
        }


# Export for use
__all__ = ["EnumStatus"]
