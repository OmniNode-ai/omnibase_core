"""
Protocol definitions for ONEX Node Services.

Provides abstract interfaces for all node service types to ensure
consistent implementation and proper abstraction across the system.
"""

from abc import abstractmethod
from typing import Any, Protocol, runtime_checkable

from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.protocols.core.protocol_health_check import ProtocolHealthCheck


@runtime_checkable
class ProtocolNodeService(ProtocolHealthCheck, Protocol):
    """Base protocol for all ONEX node services."""

    @property
    @abstractmethod
    def node_id(self) -> str:
        """Get the unique node identifier."""
        ...

    @property
    @abstractmethod
    def container(self) -> ModelONEXContainer:
        """Get the ONEX container instance."""
        ...

    @abstractmethod
    async def start(self) -> None:
        """Start the node service."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the node service."""
        ...


@runtime_checkable
class ProtocolNodeReducerService(ProtocolNodeService, Protocol):
    """Protocol for Reducer node services."""

    @abstractmethod
    async def reduce(self, input_data: Any) -> Any:
        """
        Execute the reduction operation.
        
        Args:
            input_data: The input data to reduce
            
        Returns:
            The reduced result
        """
        ...


@runtime_checkable
class ProtocolNodeComputeService(ProtocolNodeService, Protocol):
    """Protocol for Compute node services."""

    @abstractmethod
    async def compute(self, input_data: Any) -> Any:
        """
        Execute the computation operation.
        
        Args:
            input_data: The input data to compute
            
        Returns:
            The computed result
        """
        ...


@runtime_checkable
class ProtocolNodeEffectService(ProtocolNodeService, Protocol):
    """Protocol for Effect node services."""

    @abstractmethod
    async def effect(self, input_data: Any) -> Any:
        """
        Execute the side effect operation.
        
        Args:
            input_data: The input data for the effect
            
        Returns:
            The effect result
        """
        ...


@runtime_checkable
class ProtocolNodeOrchestratorService(ProtocolNodeService, Protocol):
    """Protocol for Orchestrator node services."""

    @abstractmethod
    async def orchestrate(self, workflow_data: Any) -> Any:
        """
        Execute the orchestration workflow.
        
        Args:
            workflow_data: The workflow data to orchestrate
            
        Returns:
            The orchestration result
        """
        ...