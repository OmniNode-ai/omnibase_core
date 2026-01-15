"""
Base Status Enumeration for ONEX Status Hierarchy.

Provides fundamental status values that serve as the foundation for all
domain-specific status enums. This eliminates value conflicts while
maintaining semantic clarity across different domains.

Design Principles:
- Universal: Contains only status values that are truly universal
- Fundamental: Basic states that apply across all domains
- Extendable: Designed to be extended by domain-specific enums
- Conflict-Free: No overlapping values with domain-specific concepts
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumBaseStatus(StrValueHelper, str, Enum):
    """
    Base status enumeration for universal state management.

    Contains fundamental status values that are common across all domains
    in the ONEX system. Domain-specific enums should extend or reference
    these values to maintain consistency.

    Categories:
    - EnumLifecycle: Basic object lifecycle states
    - Execution: Universal execution states
    - Quality: Universal quality states
    """

    # Core EnumLifecycle States (universal across all domains)
    INACTIVE = "inactive"
    ACTIVE = "active"
    PENDING = "pending"

    # Core Execution States (universal execution outcomes)
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    # Core Quality States (universal quality indicators)
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"

    def is_active_state(self) -> bool:
        """Check if this represents an active/running state."""
        return self in {
            EnumBaseStatus.ACTIVE,
            EnumBaseStatus.RUNNING,
            EnumBaseStatus.PENDING,
        }

    def is_terminal_state(self) -> bool:
        """Check if this represents a terminal state."""
        return self in {
            EnumBaseStatus.COMPLETED,
            EnumBaseStatus.FAILED,
            EnumBaseStatus.INACTIVE,
        }

    def is_error_state(self) -> bool:
        """Check if this represents an error state."""
        return self in {
            EnumBaseStatus.FAILED,
            EnumBaseStatus.INVALID,
        }

    def is_pending_state(self) -> bool:
        """Check if this represents a pending state."""
        return self in {
            EnumBaseStatus.PENDING,
            EnumBaseStatus.RUNNING,
            EnumBaseStatus.UNKNOWN,
        }

    def is_quality_state(self) -> bool:
        """Check if this represents a quality validation state."""
        return self in {
            EnumBaseStatus.VALID,
            EnumBaseStatus.INVALID,
            EnumBaseStatus.UNKNOWN,
        }


# Export for use
__all__ = ["EnumBaseStatus"]
