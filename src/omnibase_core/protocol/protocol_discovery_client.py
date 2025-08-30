"""
Discovery Client Protocol for ONEX Event-Driven Service Discovery

Defines the protocol interface for discovery client implementations.
"""

from typing import Any, Dict, List, Optional, Protocol

from omnibase_core.model.discovery.model_tool_discovery_response import \
    ModelDiscoveredTool


class ProtocolDiscoveryClient(Protocol):
    """
    Protocol interface for discovery client implementations.

    Defines the contract for event-driven service discovery with timeout
    handling, correlation tracking, and response aggregation.
    """

    async def discover_tools(
        self,
        filters: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        max_results: Optional[int] = None,
        include_metadata: bool = True,
        retry_count: int = 0,
        retry_delay: float = 1.0,
    ) -> List[ModelDiscoveredTool]:
        """
        Discover available tools/services based on filters.

        Args:
            filters: Discovery filters (tags, protocols, actions, etc.)
            timeout: Timeout in seconds (uses default if None)
            max_results: Maximum number of results to return
            include_metadata: Whether to include full metadata
            retry_count: Number of retries on timeout (0 = no retries)
            retry_delay: Delay between retries in seconds

        Returns:
            List of discovered tools matching the filters

        Raises:
            ModelDiscoveryTimeoutError: If request times out
            ModelDiscoveryError: If discovery fails
        """
        ...

    async def discover_tools_by_protocol(
        self, protocol: str, timeout: Optional[float] = None, **kwargs
    ) -> List[ModelDiscoveredTool]:
        """
        Convenience method to discover tools by protocol.

        Args:
            protocol: Protocol to filter by (e.g. 'mcp', 'graphql')
            timeout: Timeout in seconds
            **kwargs: Additional discovery options

        Returns:
            List of tools supporting the protocol
        """
        ...

    async def discover_tools_by_tags(
        self, tags: List[str], timeout: Optional[float] = None, **kwargs
    ) -> List[ModelDiscoveredTool]:
        """
        Convenience method to discover tools by tags.

        Args:
            tags: Tags to filter by (e.g. ['generator', 'validated'])
            timeout: Timeout in seconds
            **kwargs: Additional discovery options

        Returns:
            List of tools with the specified tags
        """
        ...

    async def discover_healthy_tools(
        self, timeout: Optional[float] = None, **kwargs
    ) -> List[ModelDiscoveredTool]:
        """
        Convenience method to discover only healthy tools.

        Args:
            timeout: Timeout in seconds
            **kwargs: Additional discovery options

        Returns:
            List of healthy tools
        """
        ...

    async def close(self) -> None:
        """
        Close the discovery client and clean up resources.

        Cancels any pending requests and unsubscribes from events.
        """
        ...

    def get_pending_request_count(self) -> int:
        """Get the number of pending discovery requests"""
        ...

    def get_client_stats(self) -> Dict[str, Any]:
        """
        Get client statistics.

        Returns:
            Dictionary with client statistics
        """
        ...
