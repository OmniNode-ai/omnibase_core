"""
Enum for storage tool names.
Single responsibility: Centralized storage tool name definitions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumStorageToolNames(StrValueHelper, str, Enum):
    """Storage tool names following ONEX enum-backed naming standards."""

    TOOL_FILESYSTEM_STORAGE = "tool_filesystem_storage"
    TOOL_POSTGRESQL_STORAGE = "tool_postgresql_storage"
    TOOL_STORAGE_FACTORY = "tool_storage_factory"
    TOOL_CHECKPOINT_MANAGER_ENHANCED = "tool_checkpoint_manager_enhanced"


__all__ = ["EnumStorageToolNames"]
