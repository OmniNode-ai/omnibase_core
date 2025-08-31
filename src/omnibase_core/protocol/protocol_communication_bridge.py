"""
Protocol for Communication Bridge between ONEX and Claude Code agents.

This protocol defines the interface for bidirectional communication,
message routing, event streaming, and protocol translation.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from omnibase_core.model.communication.model_agent_event import ModelAgentEvent
from omnibase_core.model.communication.model_progress_update import ModelProgressUpdate
from omnibase_core.model.communication.model_work_result import ModelWorkResult
from omnibase_core.model.core.model_onex_event import ModelOnexEvent
from omnibase_core.model.work.model_work_ticket import ModelWorkTicket


class ProtocolCommunicationBridge(ABC):
    """Protocol for ONEX <-> Claude Code agent communication bridge."""

    @abstractmethod
    async def forward_work_request(
        self,
        agent_id: str,
        ticket: ModelWorkTicket,
    ) -> bool:
        """
        Forward work request from ONEX to Claude Code agent.

        Args:
            agent_id: Target agent identifier
            ticket: Work ticket to be processed

        Returns:
            True if request was successfully forwarded

        Raises:
            CommunicationError: If forwarding fails
            AgentNotFoundError: If agent is not available
        """

    @abstractmethod
    async def send_agent_command(
        self,
        agent_id: str,
        command: str,
        parameters: dict[str, str] | None = None,
    ) -> bool:
        """
        Send command to specific Claude Code agent.

        Args:
            agent_id: Target agent identifier
            command: Command to execute (start, stop, pause, resume)
            parameters: Optional command parameters

        Returns:
            True if command was successfully sent

        Raises:
            CommunicationError: If command sending fails
            InvalidCommandError: If command is not recognized
        """

    @abstractmethod
    async def receive_progress_update(self, update: ModelProgressUpdate) -> None:
        """
        Receive progress update from Claude Code agent.

        Args:
            update: Progress update information

        Raises:
            ProcessingError: If update processing fails
        """

    @abstractmethod
    async def receive_work_completion(self, result: ModelWorkResult) -> None:
        """
        Receive work completion notification from Claude Code agent.

        Args:
            result: Work completion result with files and status

        Raises:
            ProcessingError: If result processing fails
        """

    @abstractmethod
    async def receive_agent_event(self, event: ModelAgentEvent) -> None:
        """
        Receive general event from Claude Code agent.

        Args:
            event: Agent event information

        Raises:
            ProcessingError: If event processing fails
        """

    @abstractmethod
    async def subscribe_to_agent_events(
        self,
        agent_id: str,
    ) -> AsyncIterator[ModelAgentEvent]:
        """
        Subscribe to event stream from specific Claude Code agent.

        Args:
            agent_id: Agent to subscribe to

        Yields:
            Agent events as they occur

        Raises:
            SubscriptionError: If subscription fails
        """

    @abstractmethod
    async def publish_to_event_bus(self, event: ModelOnexEvent) -> bool:
        """
        Publish event to ONEX Event Bus.

        Args:
            event: ONEX event to publish

        Returns:
            True if event was successfully published

        Raises:
            PublishError: If publishing fails
        """

    @abstractmethod
    async def subscribe_to_onex_events(
        self,
        event_types: list[str],
    ) -> AsyncIterator[ModelOnexEvent]:
        """
        Subscribe to ONEX Event Bus for specific event types.

        Args:
            event_types: List of event types to subscribe to

        Yields:
            ONEX events as they occur

        Raises:
            SubscriptionError: If subscription fails
        """

    @abstractmethod
    async def register_agent(self, agent_id: str, endpoint_url: str) -> bool:
        """
        Register Claude Code agent with communication bridge.

        Args:
            agent_id: Unique agent identifier
            endpoint_url: Agent's communication endpoint

        Returns:
            True if registration was successful

        Raises:
            RegistrationError: If registration fails
        """

    @abstractmethod
    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister Claude Code agent from communication bridge.

        Args:
            agent_id: Agent identifier to unregister

        Returns:
            True if unregistration was successful

        Raises:
            UnregistrationError: If unregistration fails
        """

    @abstractmethod
    async def get_registered_agents(self) -> list[str]:
        """
        Get list of currently registered agents.

        Returns:
            List of registered agent IDs
        """

    @abstractmethod
    async def check_agent_connectivity(self, agent_id: str) -> bool:
        """
        Check connectivity to specific Claude Code agent.

        Args:
            agent_id: Agent to check connectivity for

        Returns:
            True if agent is reachable
        """

    @abstractmethod
    async def get_message_statistics(self) -> dict[str, int]:
        """
        Get communication statistics.

        Returns:
            Dictionary of message counts and statistics
        """

    @abstractmethod
    async def transform_onex_to_agent_message(
        self,
        onex_event: ModelOnexEvent,
    ) -> dict[str, str] | None:
        """
        Transform ONEX event to Claude Code agent message format.

        Args:
            onex_event: ONEX event to transform

        Returns:
            Transformed message or None if not applicable
        """

    @abstractmethod
    async def transform_agent_to_onex_event(
        self,
        agent_event: ModelAgentEvent,
    ) -> ModelOnexEvent | None:
        """
        Transform Claude Code agent event to ONEX event format.

        Args:
            agent_event: Agent event to transform

        Returns:
            Transformed ONEX event or None if not applicable
        """
