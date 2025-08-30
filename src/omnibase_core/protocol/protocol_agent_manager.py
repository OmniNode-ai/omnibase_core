"""
Protocol for Claude Code Agent Manager Service.

This protocol defines the interface for managing Claude Code agent instances,
including spawning, monitoring, lifecycle management, and resource tracking.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from omnibase_core.model.configuration.model_agent_config import \
    ModelAgentConfig
from omnibase_core.model.core.model_agent_health_status import \
    ModelAgentHealthStatus
from omnibase_core.model.core.model_agent_instance import ModelAgentInstance
from omnibase_core.model.core.model_agent_status import ModelAgentStatus


class ProtocolAgentManager(ABC):
    """Protocol for managing Claude Code agent instances."""

    @abstractmethod
    async def spawn_agent(self, config: ModelAgentConfig) -> ModelAgentInstance:
        """
        Spawn a new Claude Code agent instance.

        Args:
            config: Agent configuration including permissions and environment

        Returns:
            Agent instance with unique ID and status

        Raises:
            AgentSpawnError: If agent spawning fails
            ConfigurationError: If configuration is invalid
        """
        pass

    @abstractmethod
    async def terminate_agent(self, agent_id: str) -> bool:
        """
        Terminate a Claude Code agent instance.

        Args:
            agent_id: Unique identifier of the agent to terminate

        Returns:
            True if termination was successful

        Raises:
            AgentNotFoundError: If agent ID doesn't exist
            TerminationError: If termination fails
        """
        pass

    @abstractmethod
    async def get_agent(self, agent_id: str) -> Optional[ModelAgentInstance]:
        """
        Retrieve agent instance by ID.

        Args:
            agent_id: Unique identifier of the agent

        Returns:
            Agent instance or None if not found
        """
        pass

    @abstractmethod
    async def list_active_agents(self) -> List[ModelAgentInstance]:
        """
        List all active agent instances.

        Returns:
            List of active agent instances
        """
        pass

    @abstractmethod
    async def get_agent_status(self, agent_id: str) -> ModelAgentStatus:
        """
        Get current status of an agent.

        Args:
            agent_id: Unique identifier of the agent

        Returns:
            Current agent status including health and activity

        Raises:
            AgentNotFoundError: If agent ID doesn't exist
        """
        pass

    @abstractmethod
    async def health_check(self) -> ModelAgentHealthStatus:
        """
        Perform health check on the agent manager service.

        Returns:
            Health status including system metrics
        """
        pass

    @abstractmethod
    async def restart_agent(self, agent_id: str) -> ModelAgentInstance:
        """
        Restart an existing agent instance.

        Args:
            agent_id: Unique identifier of the agent to restart

        Returns:
            Restarted agent instance

        Raises:
            AgentNotFoundError: If agent ID doesn't exist
            RestartError: If restart fails
        """
        pass

    @abstractmethod
    async def update_agent_config(
        self, agent_id: str, config: ModelAgentConfig
    ) -> ModelAgentInstance:
        """
        Update configuration of an existing agent.

        Args:
            agent_id: Unique identifier of the agent
            config: New configuration to apply

        Returns:
            Updated agent instance

        Raises:
            AgentNotFoundError: If agent ID doesn't exist
            ConfigurationError: If configuration is invalid
        """
        pass

    @abstractmethod
    async def get_resource_usage(self, agent_id: str) -> Dict[str, float]:
        """
        Get resource usage metrics for an agent.

        Args:
            agent_id: Unique identifier of the agent

        Returns:
            Dictionary of resource usage metrics (CPU, memory, etc.)

        Raises:
            AgentNotFoundError: If agent ID doesn't exist
        """
        pass

    @abstractmethod
    async def set_agent_idle(self, agent_id: str) -> bool:
        """
        Mark an agent as idle and available for work.

        Args:
            agent_id: Unique identifier of the agent

        Returns:
            True if agent was successfully marked idle

        Raises:
            AgentNotFoundError: If agent ID doesn't exist
        """
        pass

    @abstractmethod
    async def set_agent_busy(self, agent_id: str, task_id: str) -> bool:
        """
        Mark an agent as busy with a specific task.

        Args:
            agent_id: Unique identifier of the agent
            task_id: Identifier of the task being executed

        Returns:
            True if agent was successfully marked busy

        Raises:
            AgentNotFoundError: If agent ID doesn't exist
        """
        pass
