"""
Protocol for Event Orchestration in Claude Code Agent system.

This protocol defines the interface for coordinating events between
Agent Manager, Communication Bridge, and Agent Configuration services.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime

from omnibase_core.models.communication.model_agent_event import ModelAgentEvent
from omnibase_core.models.communication.model_progress_update import ModelProgressUpdate
from omnibase_core.models.communication.model_work_result import ModelWorkResult
from omnibase_core.models.core.model_agent_status import ModelAgentStatus
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.work.model_work_ticket import ModelWorkTicket


class ProtocolEventOrchestrator(ABC):
    """Protocol for event orchestration and workflow coordination."""

    @abstractmethod
    async def handle_work_ticket_created(self, ticket: ModelWorkTicket) -> bool:
        """
        Handle work ticket creation event and initiate assignment process.

        Args:
            ticket: Work ticket that was created

        Returns:
            True if handling was successful

        Raises:
            OrchestrationError: If handling fails
        """

    @abstractmethod
    async def assign_work_to_agent(
        self,
        ticket: ModelWorkTicket,
        agent_id: str | None = None,
    ) -> str:
        """
        Assign work ticket to an available agent.

        Args:
            ticket: Work ticket to assign
            agent_id: Optional specific agent ID, otherwise auto-select

        Returns:
            ID of the agent assigned to the work

        Raises:
            NoAvailableAgentsError: If no agents are available
            AgentNotFoundError: If specified agent is not found
            AssignmentError: If assignment fails
        """

    @abstractmethod
    async def handle_agent_progress_update(self, update: ModelProgressUpdate) -> bool:
        """
        Handle progress update from agent and broadcast to interested parties.

        Args:
            update: Progress update from agent

        Returns:
            True if handling was successful

        Raises:
            OrchestrationError: If handling fails
        """

    @abstractmethod
    async def handle_work_completion(self, result: ModelWorkResult) -> bool:
        """
        Handle work completion and perform post-completion tasks.

        Args:
            result: Work completion result from agent

        Returns:
            True if handling was successful

        Raises:
            OrchestrationError: If handling fails
        """

    @abstractmethod
    async def handle_agent_error(self, error_event: ModelAgentEvent) -> bool:
        """
        Handle agent error events and perform recovery actions.

        Args:
            error_event: Error event from agent

        Returns:
            True if handling was successful

        Raises:
            OrchestrationError: If handling fails
        """

    @abstractmethod
    async def monitor_agent_health(self) -> dict[str, ModelAgentStatus]:
        """
        Monitor health of all active agents.

        Returns:
            Dictionary mapping agent IDs to their status
        """

    @abstractmethod
    async def rebalance_workload(self) -> bool:
        """
        Rebalance workload across available agents.

        Returns:
            True if rebalancing was performed

        Raises:
            OrchestrationError: If rebalancing fails
        """

    @abstractmethod
    async def handle_agent_spawn_request(self, agent_config_template: str) -> str:
        """
        Handle request to spawn new agent and configure it.

        Args:
            agent_config_template: Template name for agent configuration

        Returns:
            ID of the newly spawned agent

        Raises:
            SpawnError: If agent spawning fails
            ConfigurationError: If configuration fails
        """

    @abstractmethod
    async def handle_agent_termination_request(
        self,
        agent_id: str,
        reason: str,
    ) -> bool:
        """
        Handle request to terminate agent and clean up resources.

        Args:
            agent_id: ID of agent to terminate
            reason: Reason for termination

        Returns:
            True if termination was successful

        Raises:
            TerminationError: If termination fails
        """

    @abstractmethod
    async def get_workflow_metrics(self) -> dict[str, float]:
        """
        Get workflow performance metrics.

        Returns:
            Dictionary of workflow metrics
        """

    @abstractmethod
    async def subscribe_to_orchestration_events(self) -> AsyncIterator[ModelOnexEvent]:
        """
        Subscribe to orchestration events for monitoring.

        Yields:
            Orchestration events as they occur

        Raises:
            SubscriptionError: If subscription fails
        """

    @abstractmethod
    async def handle_ticket_priority_change(
        self,
        ticket_id: str,
        new_priority: str,
    ) -> bool:
        """
        Handle change in work ticket priority and adjust scheduling.

        Args:
            ticket_id: ID of the ticket with priority change
            new_priority: New priority level

        Returns:
            True if handling was successful

        Raises:
            OrchestrationError: If handling fails
        """

    @abstractmethod
    async def handle_agent_capacity_change(
        self,
        agent_id: str,
        new_capacity: int,
    ) -> bool:
        """
        Handle change in agent capacity and adjust workload distribution.

        Args:
            agent_id: ID of the agent with capacity change
            new_capacity: New capacity limit

        Returns:
            True if handling was successful

        Raises:
            OrchestrationError: If handling fails
        """

    @abstractmethod
    async def pause_agent_operations(self, agent_id: str) -> bool:
        """
        Pause operations for a specific agent.

        Args:
            agent_id: ID of agent to pause

        Returns:
            True if pause was successful

        Raises:
            OrchestrationError: If pause fails
        """

    @abstractmethod
    async def resume_agent_operations(self, agent_id: str) -> bool:
        """
        Resume operations for a paused agent.

        Args:
            agent_id: ID of agent to resume

        Returns:
            True if resume was successful

        Raises:
            OrchestrationError: If resume fails
        """

    @abstractmethod
    async def get_pending_work_queue(self) -> list[ModelWorkTicket]:
        """
        Get list of pending work tickets in the queue.

        Returns:
            List of pending work tickets ordered by priority
        """

    @abstractmethod
    async def get_active_work_assignments(self) -> dict[str, list[str]]:
        """
        Get current work assignments for all agents.

        Returns:
            Dictionary mapping agent IDs to lists of assigned ticket IDs
        """

    @abstractmethod
    async def estimate_completion_time(
        self,
        ticket: ModelWorkTicket,
    ) -> datetime | None:
        """
        Estimate completion time for a work ticket.

        Args:
            ticket: Work ticket to estimate completion for

        Returns:
            Estimated completion datetime or None if cannot estimate
        """

    @abstractmethod
    async def handle_dependency_resolution(
        self,
        ticket_id: str,
        dependency_ticket_id: str,
    ) -> bool:
        """
        Handle resolution of work ticket dependencies.

        Args:
            ticket_id: ID of ticket waiting for dependency
            dependency_ticket_id: ID of dependency ticket that was resolved

        Returns:
            True if handling was successful

        Raises:
            OrchestrationError: If handling fails
        """

    @abstractmethod
    async def create_orchestration_report(self) -> dict[str, str]:
        """
        Create comprehensive orchestration status report.

        Returns:
            Dictionary containing orchestration status and metrics
        """

    @abstractmethod
    async def handle_emergency_shutdown(self, reason: str) -> bool:
        """
        Handle emergency shutdown of the orchestration system.

        Args:
            reason: Reason for emergency shutdown

        Returns:
            True if shutdown was successful

        Raises:
            ShutdownError: If shutdown fails
        """
