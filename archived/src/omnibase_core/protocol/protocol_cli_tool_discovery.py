"""
CLI Tool Discovery Protocol for ONEX CLI Interface

Defines the protocol interface for CLI tool discovery and resolution,
providing duck-typed tool execution without hardcoded import paths.
"""

from typing import Protocol

from omnibase_core.models.core.model_cli_discovery_stats import ModelCliDiscoveryStats
from omnibase_core.models.core.model_tool_health_status import ModelToolHealthStatus
from omnibase_core.models.core.model_tool_implementation import ModelToolImplementation
from omnibase_core.models.discovery.model_tool_discovery_response import (
    ModelDiscoveredTool,
)


class ProtocolCliToolDiscovery(Protocol):
    """
    Protocol interface for CLI tool discovery and resolution.

    Provides duck-typed tool execution capabilities for the CLI
    without requiring hardcoded tool import paths, enabling proper
    abstraction and compliance with direct tool import guards.
    """

    def discover_available_tools(
        self,
        health_filter: bool = True,
        timeout_seconds: float | None = None,
    ) -> list[ModelDiscoveredTool]:
        """
        Discover all available CLI tools.

        Args:
            health_filter: Only return healthy tools if True
            timeout_seconds: Discovery timeout (uses default if None)

        Returns:
            List of discovered tools available for CLI execution

        Raises:
            ModelDiscoveryError: If discovery fails
            ModelDiscoveryTimeoutError: If discovery times out
        """
        ...

    def resolve_tool_implementation(
        self,
        tool_name: str,
    ) -> ModelToolImplementation | None:
        """
        Resolve tool implementation via protocol abstraction.

        Args:
            tool_name: Name of the tool to resolve

        Returns:
            Tool implementation metadata or None if not found

        Notes:
            Returns ModelToolImplementation to provide type safety
            while maintaining protocol abstraction.
        """
        ...

    def validate_tool_health(
        self,
        tool_name: str,
        timeout_seconds: float | None = None,
    ) -> ModelToolHealthStatus:
        """
        Validate tool health via introspection protocol.

        Args:
            tool_name: Name of the tool to validate
            timeout_seconds: Health check timeout

        Returns:
            Tool health status with validation details
        """
        ...

    def get_tool_metadata(self, tool_name: str) -> ModelDiscoveredTool | None:
        """
        Get detailed metadata for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool metadata or None if tool not found
        """
        ...

    def refresh_tool_registry(self) -> bool:
        """
        Refresh the tool registry cache.

        Returns:
            True if refresh succeeded, False otherwise
        """
        ...

    def get_discovery_stats(self) -> ModelCliDiscoveryStats:
        """
        Get discovery client statistics and health.

        Returns:
            Structured discovery statistics model
        """
        ...
