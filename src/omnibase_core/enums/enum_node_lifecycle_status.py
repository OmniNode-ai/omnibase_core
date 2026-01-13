"""
Node Lifecycle Status Enum.

Defines the lifecycle states for nodes in the ONEX system.
Used by NodeCoreBase and derived node types for tracking
initialization and cleanup phases.

.. versionadded:: 0.6.5
    Added as part of OMN-1309 (replace hardcoded status strings).
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumNodeLifecycleStatus(StrValueHelper, str, Enum):
    """
    Node lifecycle status values.

    Inherits from ``str`` to ensure proper JSON serialization - enum values
    serialize directly to their lowercase string values.

    Lifecycle Flow::

        INITIALIZED -> INITIALIZING -> READY -> CLEANING_UP -> CLEANED_UP
                                   \\-> FAILED
                                             CLEANING_UP -> CLEANUP_FAILED

    States:
        INITIALIZED: Node has been constructed but not yet started.
        INITIALIZING: Node initialization is in progress.
        READY: Node is fully initialized and ready for processing.
        FAILED: Node initialization or processing failed.
        CLEANING_UP: Node cleanup is in progress.
        CLEANED_UP: Node cleanup completed successfully.
        CLEANUP_FAILED: Node cleanup failed (logged but not raised).
    """

    INITIALIZED = "initialized"
    """Node has been constructed but not yet started."""

    INITIALIZING = "initializing"
    """Node initialization is in progress."""

    READY = "ready"
    """Node is fully initialized and ready for processing."""

    FAILED = "failed"
    """Node initialization or processing failed."""

    CLEANING_UP = "cleaning_up"
    """Node cleanup is in progress."""

    CLEANED_UP = "cleaned_up"
    """Node cleanup completed successfully."""

    CLEANUP_FAILED = "cleanup_failed"
    """Node cleanup failed (logged but not raised)."""

    def is_terminal(self) -> bool:
        """Check if this is a terminal state (no further transitions expected)."""
        return self in {
            EnumNodeLifecycleStatus.CLEANED_UP,
            EnumNodeLifecycleStatus.CLEANUP_FAILED,
            EnumNodeLifecycleStatus.FAILED,
        }

    def is_active(self) -> bool:
        """Check if this state indicates the node is actively processing."""
        return self in {
            EnumNodeLifecycleStatus.INITIALIZING,
            EnumNodeLifecycleStatus.READY,
            EnumNodeLifecycleStatus.CLEANING_UP,
        }

    def is_error(self) -> bool:
        """Check if this state indicates an error condition."""
        return self in {
            EnumNodeLifecycleStatus.FAILED,
            EnumNodeLifecycleStatus.CLEANUP_FAILED,
        }


# Export for use
__all__ = ["EnumNodeLifecycleStatus"]
