#!/usr/bin/env python3
"""
Protocol definition for Infrastructure Orchestrator.

Defines the interface contract for infrastructure workflow coordination
following ONEX protocol patterns.
"""

from abc import abstractmethod
from typing import Any, Protocol

from omnibase_core.core.onex_container import ONEXContainer


class ProtocolInfrastructureOrchestrator(Protocol):
    """
    Protocol interface for infrastructure orchestration tools.

    Defines the standard interface for infrastructure workflow coordination,
    including bootstrap, health monitoring, and failover coordination.
    """

    def __init__(self, container: ONEXContainer) -> None:
        """Initialize with container injection."""
        ...

    @abstractmethod
    async def coordinate_infrastructure_bootstrap(self) -> dict[str, Any]:
        """
        Coordinate bootstrap of infrastructure adapter services.

        Returns:
            Dict containing bootstrap results for all infrastructure adapters
        """
        ...

    @abstractmethod
    async def coordinate_infrastructure_health_check(self) -> dict[str, Any]:
        """
        Monitor infrastructure adapter health.

        Returns:
            Dict containing health status for all infrastructure adapters
        """
        ...

    @abstractmethod
    async def coordinate_infrastructure_failover(
        self,
        failed_adapter: str,
    ) -> dict[str, Any]:
        """
        Coordinate infrastructure failover scenarios.

        Args:
            failed_adapter: Name of the adapter that failed

        Returns:
            Dict containing failover coordination results
        """
        ...
