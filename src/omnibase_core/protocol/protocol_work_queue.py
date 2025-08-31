"""
Protocol for Work Queue Integration with ONEX Work Ticket System.

This protocol defines the interface for integrating Claude Code agents
with the ONEX work ticket infrastructure, enabling seamless ticket
assignment, processing, and status synchronization.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime
from enum import Enum

from omnibase_core.model.work.model_work_assignment import ModelWorkAssignment
from omnibase_core.model.work.model_work_ticket import ModelWorkTicket


class WorkQueuePriority(str, Enum):
    """Work queue priority levels."""

    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    DEFERRED = "deferred"


class AssignmentStrategy(str, Enum):
    """Work assignment strategy types."""

    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    CAPABILITY_BASED = "capability_based"
    PRIORITY_WEIGHTED = "priority_weighted"
    DEPENDENCY_OPTIMIZED = "dependency_optimized"


class ProtocolWorkQueue(ABC):
    """Protocol for work queue integration and ticket management."""

    @abstractmethod
    async def connect_to_work_system(self) -> bool:
        """
        Connect to the ONEX work ticket system.

        Returns:
            True if connection was successful

        Raises:
            ConnectionError: If connection fails
        """

    @abstractmethod
    async def fetch_pending_tickets(
        self,
        limit: int | None = None,
    ) -> list[ModelWorkTicket]:
        """
        Fetch pending work tickets from the ONEX system.

        Args:
            limit: Maximum number of tickets to fetch

        Returns:
            List of pending work tickets

        Raises:
            FetchError: If fetching fails
        """

    @abstractmethod
    async def subscribe_to_ticket_updates(self) -> AsyncIterator[ModelWorkTicket]:
        """
        Subscribe to real-time work ticket updates.

        Yields:
            Work tickets as they are created or updated

        Raises:
            SubscriptionError: If subscription fails
        """

    @abstractmethod
    async def assign_ticket_to_agent(
        self,
        ticket_id: str,
        agent_id: str,
    ) -> ModelWorkAssignment:
        """
        Assign a work ticket to a specific agent.

        Args:
            ticket_id: ID of the ticket to assign
            agent_id: ID of the agent to assign to

        Returns:
            Work assignment details

        Raises:
            AssignmentError: If assignment fails
            TicketNotFoundError: If ticket doesn't exist
            AgentNotFoundError: If agent doesn't exist
        """

    @abstractmethod
    async def update_ticket_status(
        self,
        ticket_id: str,
        status: str,
        message: str | None = None,
    ) -> bool:
        """
        Update the status of a work ticket.

        Args:
            ticket_id: ID of the ticket to update
            status: New status value
            message: Optional status message

        Returns:
            True if update was successful

        Raises:
            UpdateError: If update fails
            TicketNotFoundError: If ticket doesn't exist
        """

    @abstractmethod
    async def update_ticket_progress(
        self,
        ticket_id: str,
        progress_percent: float,
    ) -> bool:
        """
        Update the progress percentage of a work ticket.

        Args:
            ticket_id: ID of the ticket to update
            progress_percent: Progress percentage (0-100)

        Returns:
            True if update was successful

        Raises:
            UpdateError: If update fails
            TicketNotFoundError: If ticket doesn't exist
        """

    @abstractmethod
    async def complete_ticket(
        self,
        ticket_id: str,
        result_data: dict[str, str],
    ) -> bool:
        """
        Mark a work ticket as completed with result data.

        Args:
            ticket_id: ID of the ticket to complete
            result_data: Completion result data

        Returns:
            True if completion was successful

        Raises:
            CompletionError: If completion fails
            TicketNotFoundError: If ticket doesn't exist
        """

    @abstractmethod
    async def fail_ticket(self, ticket_id: str, error_message: str) -> bool:
        """
        Mark a work ticket as failed with error information.

        Args:
            ticket_id: ID of the ticket to fail
            error_message: Error description

        Returns:
            True if failure marking was successful

        Raises:
            UpdateError: If update fails
            TicketNotFoundError: If ticket doesn't exist
        """

    @abstractmethod
    async def get_ticket_by_id(self, ticket_id: str) -> ModelWorkTicket | None:
        """
        Retrieve a specific work ticket by ID.

        Args:
            ticket_id: ID of the ticket to retrieve

        Returns:
            Work ticket if found, None otherwise

        Raises:
            FetchError: If fetching fails
        """

    @abstractmethod
    async def get_tickets_by_priority(
        self,
        priority: WorkQueuePriority,
    ) -> list[ModelWorkTicket]:
        """
        Retrieve work tickets filtered by priority.

        Args:
            priority: Priority level to filter by

        Returns:
            List of tickets matching the priority

        Raises:
            FetchError: If fetching fails
        """

    @abstractmethod
    async def get_tickets_by_agent(self, agent_id: str) -> list[ModelWorkTicket]:
        """
        Retrieve work tickets assigned to a specific agent.

        Args:
            agent_id: ID of the agent

        Returns:
            List of tickets assigned to the agent

        Raises:
            FetchError: If fetching fails
        """

    @abstractmethod
    async def get_available_tickets(
        self,
        agent_capabilities: list[str] | None = None,
        max_priority: WorkQueuePriority | None = None,
    ) -> list[ModelWorkTicket]:
        """
        Get tickets available for assignment based on criteria.

        Args:
            agent_capabilities: Required capabilities for the agent
            max_priority: Maximum priority level to consider

        Returns:
            List of available tickets

        Raises:
            FetchError: If fetching fails
        """

    @abstractmethod
    async def reserve_ticket(
        self,
        ticket_id: str,
        agent_id: str,
        duration_minutes: int = 30,
    ) -> bool:
        """
        Reserve a ticket for an agent temporarily to prevent conflicts.

        Args:
            ticket_id: ID of the ticket to reserve
            agent_id: ID of the agent reserving
            duration_minutes: Reservation duration in minutes

        Returns:
            True if reservation was successful

        Raises:
            ReservationError: If reservation fails
            TicketNotFoundError: If ticket doesn't exist
        """

    @abstractmethod
    async def release_ticket_reservation(self, ticket_id: str, agent_id: str) -> bool:
        """
        Release a previously reserved ticket.

        Args:
            ticket_id: ID of the ticket to release
            agent_id: ID of the agent releasing

        Returns:
            True if release was successful

        Raises:
            ReleaseError: If release fails
            ReservationNotFoundError: If reservation doesn't exist
        """

    @abstractmethod
    async def get_queue_statistics(self) -> dict[str, int]:
        """
        Get current work queue statistics.

        Returns:
            Dictionary containing queue metrics
        """

    @abstractmethod
    async def get_ticket_dependencies(self, ticket_id: str) -> list[str]:
        """
        Get list of ticket IDs that this ticket depends on.

        Args:
            ticket_id: ID of the ticket

        Returns:
            List of dependency ticket IDs

        Raises:
            FetchError: If fetching fails
            TicketNotFoundError: If ticket doesn't exist
        """

    @abstractmethod
    async def add_ticket_dependency(
        self,
        ticket_id: str,
        dependency_ticket_id: str,
    ) -> bool:
        """
        Add a dependency relationship between tickets.

        Args:
            ticket_id: ID of the ticket that depends
            dependency_ticket_id: ID of the ticket it depends on

        Returns:
            True if dependency was added

        Raises:
            DependencyError: If adding dependency fails
            CircularDependencyError: If this would create a cycle
        """

    @abstractmethod
    async def remove_ticket_dependency(
        self,
        ticket_id: str,
        dependency_ticket_id: str,
    ) -> bool:
        """
        Remove a dependency relationship between tickets.

        Args:
            ticket_id: ID of the ticket that depends
            dependency_ticket_id: ID of the dependency to remove

        Returns:
            True if dependency was removed

        Raises:
            DependencyError: If removing dependency fails
        """

    @abstractmethod
    async def get_blocked_tickets(self) -> list[ModelWorkTicket]:
        """
        Get tickets that are blocked by unresolved dependencies.

        Returns:
            List of blocked tickets

        Raises:
            FetchError: If fetching fails
        """

    @abstractmethod
    async def get_ready_tickets(self) -> list[ModelWorkTicket]:
        """
        Get tickets that are ready for assignment (no pending dependencies).

        Returns:
            List of ready tickets

        Raises:
            FetchError: If fetching fails
        """

    @abstractmethod
    async def set_assignment_strategy(self, strategy: AssignmentStrategy) -> bool:
        """
        Set the work assignment strategy for the queue.

        Args:
            strategy: Assignment strategy to use

        Returns:
            True if strategy was set

        Raises:
            ConfigurationError: If strategy configuration fails
        """

    @abstractmethod
    async def get_assignment_strategy(self) -> AssignmentStrategy:
        """
        Get the current work assignment strategy.

        Returns:
            Current assignment strategy
        """

    @abstractmethod
    async def requeue_ticket(self, ticket_id: str, reason: str) -> bool:
        """
        Requeue a ticket for reassignment.

        Args:
            ticket_id: ID of the ticket to requeue
            reason: Reason for requeuing

        Returns:
            True if requeuing was successful

        Raises:
            RequeueError: If requeuing fails
            TicketNotFoundError: If ticket doesn't exist
        """

    @abstractmethod
    async def estimate_completion_time(self, ticket_id: str) -> datetime | None:
        """
        Estimate completion time for a ticket based on historical data.

        Args:
            ticket_id: ID of the ticket

        Returns:
            Estimated completion time or None if cannot estimate

        Raises:
            EstimationError: If estimation fails
        """

    @abstractmethod
    async def get_ticket_metrics(self, ticket_id: str) -> dict[str, float]:
        """
        Get performance metrics for a specific ticket.

        Args:
            ticket_id: ID of the ticket

        Returns:
            Dictionary of ticket metrics

        Raises:
            FetchError: If fetching fails
            TicketNotFoundError: If ticket doesn't exist
        """

    @abstractmethod
    async def create_ticket_checkpoint(
        self,
        ticket_id: str,
        checkpoint_data: dict[str, str],
    ) -> str:
        """
        Create a checkpoint for work in progress.

        Args:
            ticket_id: ID of the ticket
            checkpoint_data: Checkpoint state data

        Returns:
            Checkpoint ID for restoration

        Raises:
            CheckpointError: If checkpoint creation fails
        """

    @abstractmethod
    async def restore_ticket_checkpoint(
        self,
        ticket_id: str,
        checkpoint_id: str,
    ) -> bool:
        """
        Restore a ticket to a previous checkpoint.

        Args:
            ticket_id: ID of the ticket
            checkpoint_id: ID of the checkpoint to restore

        Returns:
            True if restoration was successful

        Raises:
            RestoreError: If restoration fails
            CheckpointNotFoundError: If checkpoint doesn't exist
        """
