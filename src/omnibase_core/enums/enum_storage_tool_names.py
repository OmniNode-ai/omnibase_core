"""
Enum for storage tool names.
Single responsibility: Centralized storage tool name definitions.
"""

from enum import Enum, unique


@unique
class EnumStorageToolNames(str, Enum):
    """Storage tool names following ONEX enum-backed naming standards."""

    TOOL_FILESYSTEM_STORAGE = "tool_filesystem_storage"
    TOOL_POSTGRESQL_STORAGE = "tool_postgresql_storage"
    TOOL_STORAGE_FACTORY = "tool_storage_factory"
    TOOL_CHECKPOINT_MANAGER_ENHANCED = "tool_checkpoint_manager_enhanced"
