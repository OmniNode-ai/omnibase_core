"""
Metadata tool status enumeration.

Defines lifecycle status for metadata tools.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMetadataToolStatus(StrValueHelper, str, Enum):
    """
    Status of metadata tools.

    Represents the current lifecycle status of metadata tools,
    from active development through deprecation.
    """

    ACTIVE = "active"  # Currently active and supported
    DEPRECATED = "deprecated"  # Deprecated, should not be used for new code
    EXPERIMENTAL = "experimental"  # Experimental, may change
    LEGACY = "legacy"  # Older tool still supported
    DISABLED = "disabled"  # Disabled, not available for use

    @classmethod
    def is_usable(cls, status: EnumMetadataToolStatus) -> bool:
        """
        Check if tool status allows usage.

        Args:
            status: The status to check

        Returns:
            True if status is ACTIVE or EXPERIMENTAL
        """
        return status in {cls.ACTIVE, cls.EXPERIMENTAL}

    @classmethod
    def is_deprecated(cls, status: EnumMetadataToolStatus) -> bool:
        """
        Check if tool is deprecated or legacy.

        Args:
            status: The status to check

        Returns:
            True if status is DEPRECATED or LEGACY
        """
        return status in {cls.DEPRECATED, cls.LEGACY}

    @classmethod
    def requires_warning(cls, status: EnumMetadataToolStatus) -> bool:
        """
        Check if tool usage should trigger a warning.

        Args:
            status: The status to check

        Returns:
            True if status is EXPERIMENTAL, DEPRECATED, or LEGACY
        """
        return status in {cls.EXPERIMENTAL, cls.DEPRECATED, cls.LEGACY}

    @classmethod
    def get_warning_message(cls, status: EnumMetadataToolStatus) -> str:
        """
        Get appropriate warning message for tool status.

        Args:
            status: The status to get message for

        Returns:
            Warning message string
        """
        messages = {
            cls.EXPERIMENTAL: "This is an experimental tool and may change without notice",
            cls.DEPRECATED: "This tool is deprecated and should not be used for new code",
            cls.LEGACY: "This is an older tool that remains available",
            cls.DISABLED: "This tool is disabled and cannot be used",
        }
        return messages.get(status, "")

    @classmethod
    def get_default_status(cls) -> EnumMetadataToolStatus:
        """
        Get the default tool status.

        Returns:
            Default status (ACTIVE)
        """
        return cls.ACTIVE


# Export the enum
__all__ = ["EnumMetadataToolStatus"]
