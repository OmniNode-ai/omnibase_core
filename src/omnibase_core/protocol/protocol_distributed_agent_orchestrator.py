"""
Protocol for Distributed Agent Orchestrator.

Defines the interface for orchestrating agents across multiple devices
with location-aware routing, failover, and load balancing capabilities.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from omnibase_core.enums.enum_agent_capability import EnumAgentCapability
from omnibase_core.model.agent.model_agent_summary import ModelAgentSummary
from omnibase_core.model.core.model_agent_instance import ModelAgentInstance
from omnibase_core.model.llm.model_llm_response import ModelLLMResponse


class ProtocolDistributedAgentOrchestrator(ABC):
    """Protocol for distributed agent orchestration across multiple devices."""

    @abstractmethod
    async def spawn_agents_for_device(
        self, device_name: str
    ) -> List[ModelAgentInstance]:
        """
        Spawn agents for a specific device based on configuration.

        Args:
            device_name: Name of the device to spawn agents for

        Returns:
            List of spawned agent instances

        Raises:
            DeviceNotFoundError: If device configuration doesn't exist
            AgentSpawnError: If agent spawning fails
        """
        pass

    @abstractmethod
    async def route_task(
        self,
        task_type: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        prefer_local: bool = True,
        required_capabilities: Optional[List[EnumAgentCapability]] = None,
    ) -> ModelLLMResponse:
        """
        Route a task to the most appropriate agent.

        Args:
            task_type: Type of task to route
            prompt: Task prompt
            system_prompt: Optional system prompt
            prefer_local: Whether to prefer local agents over remote
            required_capabilities: Required agent capabilities

        Returns:
            Response from the selected agent

        Raises:
            NoAgentsAvailableError: If no suitable agents are available
            TaskRoutingError: If task routing fails
        """
        pass

    @abstractmethod
    async def find_best_agent(
        self,
        task_type: str,
        required_capabilities: Optional[List[EnumAgentCapability]] = None,
        prefer_local: bool = True,
    ) -> Optional[ModelAgentInstance]:
        """
        Find the best agent for a given task type.

        Args:
            task_type: Type of task
            required_capabilities: Required capabilities
            prefer_local: Whether to prefer local agents

        Returns:
            Best agent instance or None if no suitable agent found
        """
        pass

    @abstractmethod
    def get_agent_summary(self) -> ModelAgentSummary:
        """
        Get summary of all agents and their status.

        Returns:
            Comprehensive agent summary with health and status information
        """
        pass

    @abstractmethod
    async def health_check_agents(self) -> Dict[str, str]:
        """
        Perform health check on all active agents.

        Returns:
            Dictionary mapping agent IDs to health status
        """
        pass

    @abstractmethod
    async def rebalance_agents(self) -> bool:
        """
        Rebalance agents across devices based on current load.

        Returns:
            True if rebalancing was successful

        Raises:
            RebalancingError: If rebalancing fails
        """
        pass

    @abstractmethod
    def set_location(self, location: str) -> None:
        """
        Set current location context for routing decisions.

        Args:
            location: Current location ('at_home', 'remote', 'unknown')
        """
        pass

    @abstractmethod
    async def get_device_agents(self, device_name: str) -> List[ModelAgentInstance]:
        """
        Get all agents running on a specific device.

        Args:
            device_name: Name of the device

        Returns:
            List of agent instances on the device
        """
        pass

    @abstractmethod
    async def get_agents_by_role(self, role: str) -> List[ModelAgentInstance]:
        """
        Get all agents with a specific role.

        Args:
            role: Agent role to search for

        Returns:
            List of agent instances with the specified role
        """
        pass

    @abstractmethod
    async def terminate_agent(self, agent_id: str) -> bool:
        """
        Terminate a specific agent.

        Args:
            agent_id: ID of the agent to terminate

        Returns:
            True if termination was successful

        Raises:
            AgentNotFoundError: If agent doesn't exist
        """
        pass

    @abstractmethod
    async def restart_agent(self, agent_id: str) -> ModelAgentInstance:
        """
        Restart a specific agent.

        Args:
            agent_id: ID of the agent to restart

        Returns:
            Restarted agent instance

        Raises:
            AgentNotFoundError: If agent doesn't exist
            RestartError: If restart fails
        """
        pass
