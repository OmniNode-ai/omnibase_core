"""MCP tool type enumeration.

Defines the types of tools that can be exposed via the Model Context Protocol.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMCPToolType(StrValueHelper, str, Enum):
    """Types of MCP tools.

    These map to the MCP protocol's tool type categories:
        - FUNCTION: Executable functions that perform actions
        - RESOURCE: Read-only data sources
        - PROMPT: Template-based prompt generators
        - SAMPLING: LLM sampling/completion tools
    """

    FUNCTION = "function"
    RESOURCE = "resource"
    PROMPT = "prompt"
    SAMPLING = "sampling"


__all__ = ["EnumMCPToolType"]
