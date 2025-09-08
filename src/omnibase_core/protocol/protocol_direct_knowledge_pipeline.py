"""
Protocol definition for Direct Knowledge Pipeline Service.

This protocol defines the interface for services that bypass the repository
and write directly to PostgreSQL for debug logs, velocity tracking, PR descriptions,
and agent actions using strong typing throughout.
"""

from typing import Protocol

from omnibase_core.model.agent.model_agent_action import ModelAgentAction
from omnibase_core.model.ai_workflows.model_ai_execution_metrics import ModelMetricValue
from omnibase_core.model.core.model_health_status import ModelHealthStatus
from omnibase_core.model.intelligence.model_agent_debug_intelligence import (
    ModelAgentDebugIntelligence,
)
from omnibase_core.model.pr.model_pr_ticket import ModelPrTicket
from omnibase_core.model.velocity.model_velocity_log import ModelVelocityLog


class ProtocolDirectKnowledgePipeline(Protocol):
    """
    Protocol for direct-to-database knowledge pipeline services.

    This protocol defines the standard interface that all direct knowledge
    pipeline implementations must follow, ensuring consistency across
    different storage backends and service implementations.
    """

    async def initialize(self) -> None:
        """
        Initialize the knowledge pipeline service and establish connections.

        Raises:
            OnexError: If initialization fails
        """
        ...

    async def store_debug_log(
        self,
        debug_intelligence: ModelAgentDebugIntelligence,
    ) -> str:
        """
        Store debug log directly to database bypassing repository.

        Args:
            debug_intelligence: Complete debug intelligence data model

        Returns:
            Log entry ID

        Raises:
            OnexError: If storage fails
        """
        ...

    async def store_velocity_log(self, velocity_log: ModelVelocityLog) -> str:
        """
        Store velocity tracking data directly to database.

        Args:
            velocity_log: Complete velocity log data model

        Returns:
            Velocity log ID

        Raises:
            OnexError: If storage fails
        """
        ...

    async def store_pr_ticket(self, pr_ticket: ModelPrTicket) -> str:
        """
        Store PR ticket with UUID tracking directly to database.

        Args:
            pr_ticket: Complete PR ticket data model

        Returns:
            PR ticket ID

        Raises:
            OnexError: If storage fails
        """
        ...

    async def store_agent_action(self, agent_action: ModelAgentAction) -> str:
        """
        Store agent action for audit trail and learning.

        Args:
            agent_action: Complete agent action data model

        Returns:
            Agent action ID

        Raises:
            OnexError: If storage fails
        """
        ...

    async def get_velocity_analytics(
        self,
        agent_id: str | None = None,
        task_type: str | None = None,
        days: int = 7,
    ) -> list[ModelMetricValue]:
        """
        Get velocity analytics for agents and tasks.

        Args:
            agent_id: Optional filter by specific agent
            task_type: Optional filter by task type
            days: Number of days to include in analysis

        Returns:
            List of velocity metrics

        Raises:
            OnexError: If retrieval fails
        """
        ...

    async def get_agent_productivity(
        self,
        agent_id: str,
        days: int = 30,
    ) -> list[ModelMetricValue]:
        """
        Get productivity metrics for a specific agent.

        Args:
            agent_id: ID of the agent to analyze
            days: Number of days to include in analysis

        Returns:
            List of productivity metrics

        Raises:
            OnexError: If retrieval fails
        """
        ...

    async def search_debug_logs(
        self,
        agent_id: str | None = None,
        success: bool | None = None,
        keywords: str | None = None,
        limit: int = 100,
    ) -> list[ModelAgentDebugIntelligence]:
        """
        Search debug logs with filters.

        Args:
            agent_id: Optional filter by agent ID
            success: Optional filter by success status
            keywords: Optional keyword search in task descriptions
            limit: Maximum number of results to return

        Returns:
            List of debug intelligence entries

        Raises:
            OnexError: If search fails
        """
        ...

    async def get_pr_tickets(
        self,
        agent_id: str | None = None,
        status: str | None = None,
        branch: str | None = None,
        limit: int = 50,
    ) -> list[ModelPrTicket]:
        """
        Get PR tickets with optional filters.

        Args:
            agent_id: Optional filter by agent ID
            status: Optional filter by PR status
            branch: Optional filter by branch name
            limit: Maximum number of results to return

        Returns:
            List of PR ticket entries

        Raises:
            OnexError: If retrieval fails
        """
        ...

    async def get_agent_actions(
        self,
        agent_id: str | None = None,
        action_type: str | None = None,
        correlation_id: str | None = None,
        work_session_id: str | None = None,
        limit: int = 200,
    ) -> list[ModelAgentAction]:
        """
        Get agent actions with optional filters.

        Args:
            agent_id: Optional filter by agent ID
            action_type: Optional filter by action type
            correlation_id: Optional filter by correlation ID
            work_session_id: Optional filter by work session
            limit: Maximum number of results to return

        Returns:
            List of agent action entries

        Raises:
            OnexError: If retrieval fails
        """
        ...

    async def emit_omnimemory_event(self, event: ModelAgentAction) -> None:
        """
        Emit event to OmniMemory for learning and pattern recognition.

        Args:
            event: Agent action event to emit

        Raises:
            OnexError: If event emission fails
        """
        ...

    async def health_check(self) -> ModelHealthStatus:
        """
        Check health of the knowledge pipeline service.

        Returns:
            Health status with metrics

        Raises:
            OnexError: If health check fails
        """
        ...

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the knowledge pipeline service.

        Raises:
            OnexError: If shutdown fails
        """
        ...

    @property
    def is_connected(self) -> bool:
        """
        Check if the service is connected and operational.

        Returns:
            True if connected and ready for operations
        """
        ...

    @property
    def pipeline_type(self) -> str:
        """
        Get the type of knowledge pipeline implementation.

        Returns:
            Pipeline type identifier (e.g., 'postgresql', 'hybrid')
        """
        ...


class ProtocolVelocityTracker(Protocol):
    """
    Specialized protocol for velocity tracking components.

    This protocol defines methods specifically for tracking and analyzing
    development velocity metrics.
    """

    async def start_task_timer(
        self,
        agent_id: str,
        task_description: str,
        task_type: str,
        work_session_id: str | None = None,
    ) -> str:
        """
        Start timing a new task.

        Args:
            agent_id: ID of the agent starting the task
            task_description: Description of the task
            task_type: Type of task being started
            work_session_id: Optional work session ID

        Returns:
            Task timer ID
        """
        ...

    async def complete_task_timer(
        self,
        timer_id: str,
        success: bool,
        metrics: Dict[str, Any] | None = None,
    ) -> None:
        """
        Complete a task timer and store velocity data.

        Args:
            timer_id: ID of the timer to complete
            success: Whether the task was completed successfully
            metrics: Optional additional metrics
        """
        ...

    async def get_current_velocity(self, agent_id: str) -> Dict[str, Any]:
        """
        Get current velocity metrics for an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Current velocity metrics
        """
        ...


class ProtocolAgentActionTracker(Protocol):
    """
    Specialized protocol for tracking agent actions.

    This protocol defines methods for capturing and analyzing
    individual agent actions for learning and audit purposes.
    """

    async def start_action_tracking(
        self,
        agent_id: str,
        action_type: str,
        action_description: str,
        correlation_id: str | None = None,
    ) -> str:
        """
        Start tracking a new agent action.

        Args:
            agent_id: ID of the agent performing the action
            action_type: Type of action being tracked
            action_description: Description of the action
            correlation_id: Optional correlation ID

        Returns:
            Action tracking ID
        """
        ...

    async def complete_action_tracking(
        self,
        tracking_id: str,
        success: bool,
        output_data: Dict[str, Any],
        reasoning: Dict[str, Any] | None = None,
    ) -> None:
        """
        Complete action tracking and store results.

        Args:
            tracking_id: ID of the tracking session
            success: Whether the action was successful
            output_data: Results of the action
            reasoning: Optional reasoning/decision process data
        """
        ...

    async def get_action_patterns(
        self,
        agent_id: str,
        action_type: str | None = None,
    ) -> list[Dict[str, Any]]:
        """
        Get patterns in agent actions for learning.

        Args:
            agent_id: ID of the agent
            action_type: Optional filter by action type

        Returns:
            List of identified patterns
        """
        ...
