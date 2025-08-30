"""
Protocol for dynamic tool name resolution.

Defines the interface for contract-based tool name discovery and resolution,
replacing the monolithic enum approach.
"""

from pathlib import Path
from typing import Dict, List, Optional, Protocol, Set

from omnibase_core.model.core.model_tool_info import ModelToolInfo


class ProtocolToolNameResolver(Protocol):
    """
    Protocol for tool name resolution from contracts.

    Implementations should provide dynamic tool discovery by reading
    contract.yaml files instead of relying on central enums.
    """

    def get_tool_name(self, tool_path: str) -> Optional[str]:
        """
        Get tool name from its path by reading contract.yaml.

        Args:
            tool_path: Path to the tool directory

        Returns:
            Tool name from contract, or None if not found
        """
        ...

    def discover_all_tools(
        self, force_refresh: bool = False
    ) -> Dict[str, ModelToolInfo]:
        """
        Discover all tools by scanning for contract.yaml files.

        Args:
            force_refresh: Force cache refresh even if not expired

        Returns:
            Dictionary mapping tool names to ModelToolInfo objects
        """
        ...

    def validate_tool_name_uniqueness(self) -> List[str]:
        """
        Validate that all tool names are unique across the codebase.

        Returns:
            List of validation errors (empty if all unique)
        """
        ...

    def get_tool_path(self, tool_name: str) -> Optional[Path]:
        """
        Get the path to a tool by its name.

        Args:
            tool_name: Name of the tool to find

        Returns:
            Path to the tool directory, or None if not found
        """
        ...

    def get_all_tool_names(self) -> Set[str]:
        """
        Get all available tool names.

        Returns:
            Set of all tool names discovered from contracts
        """
        ...

    def tool_exists(self, tool_name: str) -> bool:
        """
        Check if a tool exists.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if tool exists, False otherwise
        """
        ...

    def clear_cache(self) -> None:
        """Clear the tool discovery cache."""
        ...
