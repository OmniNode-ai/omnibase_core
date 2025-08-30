"""
Protocol for LLM Agent Provider.

Defines the interface for providing LLM-based agents using various providers
with unified agent management and task routing.
"""

from abc import ABC, abstractmethod

from omnibase_core.enums.enum_agent_capability import EnumAgentCapability
from omnibase_core.enums.enum_llm_provider import EnumLLMProvider
from omnibase_core.model.agent.model_llm_agent_config import ModelLLMAgentConfig
from omnibase_core.model.core.model_agent_instance import ModelAgentInstance
from omnibase_core.model.llm.model_llm_response import ModelLLMResponse


class ProtocolLLMAgentProvider(ABC):
    """Protocol for providing LLM-based agents using various providers."""

    @abstractmethod
    async def spawn_agent(self, config: ModelLLMAgentConfig) -> ModelAgentInstance:
        """
        Spawn a new LLM agent instance.

        Args:
            config: Agent configuration including provider and model settings

        Returns:
            Spawned agent instance

        Raises:
            AgentSpawnError: If agent spawning fails
            ProviderNotAvailableError: If LLM provider is not available
            ConfigurationError: If configuration is invalid
        """

    @abstractmethod
    async def terminate_agent(self, agent_id: str) -> bool:
        """
        Terminate an existing agent.

        Args:
            agent_id: ID of the agent to terminate

        Returns:
            True if termination was successful

        Raises:
            AgentNotFoundError: If agent doesn't exist
        """

    @abstractmethod
    async def get_agent(self, agent_id: str) -> ModelAgentInstance | None:
        """
        Get agent instance by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent instance or None if not found
        """

    @abstractmethod
    async def list_active_agents(self) -> list[ModelAgentInstance]:
        """
        List all active agent instances.

        Returns:
            List of active agent instances
        """

    @abstractmethod
    async def execute_task(
        self,
        agent_id: str,
        prompt: str,
        system_prompt: str | None = None,
    ) -> ModelLLMResponse:
        """
        Execute a task using a specific agent.

        Args:
            agent_id: ID of the agent to use
            prompt: Task prompt
            system_prompt: Optional system prompt

        Returns:
            Response from the agent

        Raises:
            AgentNotFoundError: If agent doesn't exist
            AgentBusyError: If agent is currently busy
            ExecutionError: If task execution fails
        """

    @abstractmethod
    async def get_agents_by_capability(
        self,
        capability: EnumAgentCapability,
    ) -> list[ModelAgentInstance]:
        """
        Get agents that have a specific capability.

        Args:
            capability: Required capability

        Returns:
            List of agents with the specified capability
        """

    @abstractmethod
    async def get_agents_by_provider(
        self,
        provider: EnumLLMProvider,
    ) -> list[ModelAgentInstance]:
        """
        Get agents using a specific LLM provider.

        Args:
            provider: LLM provider type

        Returns:
            List of agents using the specified provider
        """

    @abstractmethod
    async def health_check_agents(self) -> dict[str, str]:
        """
        Perform health check on all agents.

        Returns:
            Dictionary mapping agent IDs to health status
        """

    @abstractmethod
    def get_provider_status(self, provider: EnumLLMProvider) -> str:
        """
        Get status of a specific LLM provider.

        Args:
            provider: Provider to check

        Returns:
            Provider status (available, unavailable, degraded)
        """

    @abstractmethod
    async def restart_agent(self, agent_id: str) -> ModelAgentInstance:
        """
        Restart an existing agent.

        Args:
            agent_id: ID of the agent to restart

        Returns:
            Restarted agent instance

        Raises:
            AgentNotFoundError: If agent doesn't exist
            RestartError: If restart fails
        """
