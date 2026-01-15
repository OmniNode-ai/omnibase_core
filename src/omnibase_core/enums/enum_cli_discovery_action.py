"""
Enumeration for CLI tool discovery actions.

Defines all valid CLI tool discovery actions that can be processed
by the CLI tool discovery system, replacing hardcoded string literals.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCliDiscoveryAction(StrValueHelper, str, Enum):
    """
    Enumeration of valid CLI tool discovery actions.

    Defines all actions that can be sent to the CLI tool discovery
    system for processing, providing type safety and validation.
    """

    # Core discovery operations
    DISCOVER_AVAILABLE_TOOLS = "discover_available_tools"
    RESOLVE_TOOL_IMPLEMENTATION = "resolve_tool_implementation"
    VALIDATE_TOOL_HEALTH = "validate_tool_health"
    GET_TOOL_METADATA = "get_tool_metadata"
    REFRESH_TOOL_REGISTRY = "refresh_tool_registry"
    GET_DISCOVERY_STATS = "get_discovery_stats"
