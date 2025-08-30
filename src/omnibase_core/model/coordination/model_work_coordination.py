"""
Model for work coordination and multi-agent management.

This model represents the coordination state, agent assignments,
and work distribution data for managing multiple Claude Code agents
working on parallel tickets.
"""

from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field

from omnibase_core.model.work.model_work_ticket import WorkTicketPriority


class AgentStatus(str, Enum):
    """Agent status enumeration."""

    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    OFFLINE = "offline"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


class CoordinationMode(str, Enum):
    """Coordination mode enumeration."""

    ACTIVE = "active"
    PAUSED = "paused"
    MAINTENANCE = "maintenance"
    EMERGENCY = "emergency"


class WorkBatchStatus(str, Enum):
    """Work batch status enumeration."""

    CREATED = "created"
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CoordinationStrategy(str, Enum):
    """Coordination strategy enumeration."""

    ROUND_ROBIN = "round_robin"
    CAPABILITY_BASED = "capability_based"
    DEPENDENCY_FIRST = "dependency_first"
    LOAD_BALANCED = "load_balanced"
    PRIORITY_WEIGHTED = "priority_weighted"


class AgentSelectionCriteria(str, Enum):
    """Agent selection criteria enumeration."""

    LEAST_LOADED = "least_loaded"
    BEST_CAPABILITY_MATCH = "best_capability_match"
    HIGHEST_PERFORMANCE = "highest_performance"
    FASTEST_RESPONSE = "fastest_response"
    RANDOM_SELECTION = "random_selection"


class WorkDistributionMode(str, Enum):
    """Work distribution mode enumeration."""

    IMMEDIATE = "immediate"
    BATCHED = "batched"
    SCHEDULED = "scheduled"
    ADAPTIVE = "adaptive"


class ModelAgentCapability(BaseModel):
    """Agent capability and skill model."""

    capability_name: str = Field(description="Name of the capability")
    proficiency_level: float = Field(
        default=1.0,
        description="Proficiency level (0.0 to 5.0)",
    )
    last_used: datetime | None = Field(
        default=None,
        description="When this capability was last used",
    )
    usage_count: int = Field(
        default=0,
        description="Number of times this capability has been used",
    )
    success_rate: float = Field(
        default=1.0,
        description="Success rate for this capability (0.0 to 1.0)",
    )


class ModelAgentPerformance(BaseModel):
    """Agent performance metrics model."""

    tasks_completed: int = Field(
        default=0,
        description="Total number of tasks completed",
    )
    tasks_failed: int = Field(default=0, description="Total number of tasks failed")
    average_completion_time: float | None = Field(
        default=None,
        description="Average completion time in hours",
    )
    quality_score: float = Field(
        default=1.0,
        description="Quality score based on work quality (0.0 to 1.0)",
    )
    reliability_score: float = Field(
        default=1.0,
        description="Reliability score based on consistency (0.0 to 1.0)",
    )
    efficiency_score: float = Field(
        default=1.0,
        description="Efficiency score based on speed (0.0 to 1.0)",
    )
    last_performance_update: datetime = Field(
        default_factory=datetime.now,
        description="When performance metrics were last updated",
    )

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        total_tasks = self.tasks_completed + self.tasks_failed
        if total_tasks == 0:
            return 1.0
        return self.tasks_completed / total_tasks

    @property
    def overall_score(self) -> float:
        """Calculate overall performance score."""
        return (
            self.quality_score + self.reliability_score + self.efficiency_score
        ) / 3.0


class ModelCoordinatedAgent(BaseModel):
    """Model for an agent in the coordination system."""

    agent_id: str = Field(description="Unique identifier for the agent")
    agent_name: str = Field(description="Human-readable name for the agent")
    status: AgentStatus = Field(
        default=AgentStatus.IDLE,
        description="Current status of the agent",
    )
    capabilities: list[ModelAgentCapability] = Field(
        default_factory=list,
        description="Agent capabilities and skills",
    )
    max_concurrent_work: int = Field(
        default=3,
        description="Maximum concurrent work items",
    )
    current_work_count: int = Field(
        default=0,
        description="Current number of assigned work items",
    )
    assigned_tickets: list[str] = Field(
        default_factory=list,
        description="Currently assigned ticket IDs",
    )
    performance: ModelAgentPerformance = Field(
        default_factory=ModelAgentPerformance,
        description="Agent performance metrics",
    )
    last_heartbeat: datetime | None = Field(
        default=None,
        description="Last heartbeat timestamp",
    )
    registered_at: datetime = Field(
        default_factory=datetime.now,
        description="When the agent was registered",
    )
    last_assignment: datetime | None = Field(
        default=None,
        description="When the agent was last assigned work",
    )
    total_work_time: timedelta = Field(
        default=timedelta(),
        description="Total time spent on work",
    )
    preferred_work_types: list[str] = Field(
        default_factory=list,
        description="Preferred types of work for this agent",
    )
    blacklisted_work_types: list[str] = Field(
        default_factory=list,
        description="Work types this agent should avoid",
    )
    configuration_overrides: dict[str, str] | None = Field(
        default=None,
        description="Agent-specific configuration overrides",
    )

    @property
    def is_available(self) -> bool:
        """Check if agent is available for new work."""
        return (
            self.status in [AgentStatus.ACTIVE, AgentStatus.IDLE]
            and self.current_work_count < self.max_concurrent_work
        )

    @property
    def is_overloaded(self) -> bool:
        """Check if agent is overloaded."""
        return self.current_work_count >= self.max_concurrent_work

    @property
    def workload_percentage(self) -> float:
        """Get workload as percentage of capacity."""
        if self.max_concurrent_work == 0:
            return 100.0
        return (self.current_work_count / self.max_concurrent_work) * 100.0

    @property
    def is_responsive(self) -> bool:
        """Check if agent is responsive (recent heartbeat)."""
        if not self.last_heartbeat:
            return False
        return datetime.now() - self.last_heartbeat < timedelta(minutes=5)

    def has_capability(
        self,
        capability_name: str,
        min_proficiency: float = 1.0,
    ) -> bool:
        """Check if agent has a specific capability at minimum proficiency."""
        for cap in self.capabilities:
            if (
                cap.capability_name == capability_name
                and cap.proficiency_level >= min_proficiency
            ):
                return True
        return False

    def get_capability_score(self, required_capabilities: list[str]) -> float:
        """Get capability match score for required capabilities."""
        if not required_capabilities:
            return 1.0

        total_score = 0.0
        matched_capabilities = 0

        for req_cap in required_capabilities:
            for agent_cap in self.capabilities:
                if agent_cap.capability_name == req_cap:
                    total_score += agent_cap.proficiency_level
                    matched_capabilities += 1
                    break

        if matched_capabilities == 0:
            return 0.0

        # Calculate score: (average proficiency) * (coverage percentage)
        average_proficiency = total_score / matched_capabilities
        coverage = matched_capabilities / len(required_capabilities)

        return (average_proficiency / 5.0) * coverage  # Normalize to 0-1 range

    def assign_work(self, ticket_id: str) -> None:
        """Assign work to this agent."""
        if ticket_id not in self.assigned_tickets:
            self.assigned_tickets.append(ticket_id)
            self.current_work_count = len(self.assigned_tickets)
            self.last_assignment = datetime.now()

            # Update status based on workload
            if self.current_work_count >= self.max_concurrent_work:
                self.status = AgentStatus.OVERLOADED
            elif self.current_work_count > 0:
                self.status = AgentStatus.BUSY

    def complete_work(self, ticket_id: str, success: bool = True) -> None:
        """Mark work as completed for this agent."""
        if ticket_id in self.assigned_tickets:
            self.assigned_tickets.remove(ticket_id)
            self.current_work_count = len(self.assigned_tickets)

            # Update performance metrics
            if success:
                self.performance.tasks_completed += 1
            else:
                self.performance.tasks_failed += 1

            self.performance.last_performance_update = datetime.now()

            # Update status based on new workload
            if self.current_work_count == 0:
                self.status = AgentStatus.IDLE
            elif self.current_work_count < self.max_concurrent_work:
                self.status = AgentStatus.BUSY

    def update_heartbeat(self) -> None:
        """Update agent heartbeat timestamp."""
        self.last_heartbeat = datetime.now()

        # Update status if agent was offline
        if self.status == AgentStatus.OFFLINE:
            if self.current_work_count == 0:
                self.status = AgentStatus.IDLE
            else:
                self.status = AgentStatus.BUSY


class ModelWorkBatch(BaseModel):
    """Model for batched work coordination."""

    batch_id: str = Field(description="Unique identifier for the work batch")
    batch_name: str = Field(description="Human-readable name for the batch")
    status: WorkBatchStatus = Field(
        default=WorkBatchStatus.CREATED,
        description="Current status of the batch",
    )
    ticket_ids: list[str] = Field(description="List of ticket IDs in this batch")
    assigned_agents: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of ticket_id to agent_id",
    )
    priority: WorkTicketPriority = Field(
        default=WorkTicketPriority.MEDIUM,
        description="Priority level of the batch",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When the batch was created",
    )
    started_at: datetime | None = Field(
        default=None,
        description="When batch execution started",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When batch execution completed",
    )
    estimated_duration: float | None = Field(
        default=None,
        description="Estimated duration in hours",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of batch IDs this batch depends on",
    )
    metadata: dict[str, str] | None = Field(
        default=None,
        description="Additional metadata for the batch",
    )

    @property
    def is_ready(self) -> bool:
        """Check if batch is ready for execution."""
        return self.status == WorkBatchStatus.CREATED

    @property
    def is_executing(self) -> bool:
        """Check if batch is currently executing."""
        return self.status == WorkBatchStatus.EXECUTING

    @property
    def is_completed(self) -> bool:
        """Check if batch is completed."""
        return self.status == WorkBatchStatus.COMPLETED

    @property
    def completion_percentage(self) -> float:
        """Get completion percentage of the batch."""
        if not self.ticket_ids:
            return 100.0

        completed_count = len([t for t in self.assigned_agents.values() if t])
        return (completed_count / len(self.ticket_ids)) * 100.0

    def start_execution(self) -> None:
        """Mark batch as started."""
        self.status = WorkBatchStatus.EXECUTING
        self.started_at = datetime.now()

    def complete_execution(self, success: bool = True) -> None:
        """Mark batch as completed."""
        self.status = WorkBatchStatus.COMPLETED if success else WorkBatchStatus.FAILED
        self.completed_at = datetime.now()


class ModelCoordinationState(BaseModel):
    """Model for overall coordination system state."""

    coordination_id: str = Field(
        description="Unique identifier for this coordination instance",
    )
    mode: CoordinationMode = Field(
        default=CoordinationMode.ACTIVE,
        description="Current coordination mode",
    )
    strategy: str = Field(
        default="dependency_first",
        description="Current coordination strategy",
    )
    active_agents: dict[str, ModelCoordinatedAgent] = Field(
        default_factory=dict,
        description="Currently active agents",
    )
    work_batches: dict[str, ModelWorkBatch] = Field(
        default_factory=dict,
        description="Active work batches",
    )
    ticket_assignments: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of ticket_id to agent_id",
    )
    agent_workloads: dict[str, int] = Field(
        default_factory=dict,
        description="Current workload count per agent",
    )
    coordination_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Coordination performance metrics",
    )
    last_balance_time: datetime | None = Field(
        default=None,
        description="When workload was last balanced",
    )
    last_assignment_time: datetime | None = Field(
        default=None,
        description="When work was last assigned",
    )
    total_tickets_processed: int = Field(
        default=0,
        description="Total number of tickets processed",
    )
    total_assignments_made: int = Field(
        default=0,
        description="Total number of assignments made",
    )
    average_assignment_time: float | None = Field(
        default=None,
        description="Average time to assign work in seconds",
    )
    system_efficiency: float = Field(
        default=1.0,
        description="Overall system efficiency score",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When coordination system was created",
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="When coordination state was last updated",
    )

    @property
    def total_agents(self) -> int:
        """Get total number of registered agents."""
        return len(self.active_agents)

    @property
    def available_agents(self) -> int:
        """Get number of available agents."""
        return len(
            [agent for agent in self.active_agents.values() if agent.is_available],
        )

    @property
    def busy_agents(self) -> int:
        """Get number of busy agents."""
        return len(
            [
                agent
                for agent in self.active_agents.values()
                if agent.status == AgentStatus.BUSY
            ],
        )

    @property
    def overloaded_agents(self) -> int:
        """Get number of overloaded agents."""
        return len(
            [agent for agent in self.active_agents.values() if agent.is_overloaded],
        )

    @property
    def total_active_work(self) -> int:
        """Get total number of active work items."""
        return sum(agent.current_work_count for agent in self.active_agents.values())

    @property
    def system_capacity(self) -> int:
        """Get total system capacity."""
        return sum(agent.max_concurrent_work for agent in self.active_agents.values())

    @property
    def capacity_utilization(self) -> float:
        """Get capacity utilization percentage."""
        if self.system_capacity == 0:
            return 0.0
        return (self.total_active_work / self.system_capacity) * 100.0

    @property
    def is_balanced(self) -> bool:
        """Check if workload is well balanced."""
        if not self.active_agents:
            return True

        workloads = [agent.workload_percentage for agent in self.active_agents.values()]
        if not workloads:
            return True

        avg_workload = sum(workloads) / len(workloads)
        max_deviation = max(abs(w - avg_workload) for w in workloads)

        return max_deviation <= 20.0  # Consider balanced if within 20% deviation

    def add_agent(self, agent: ModelCoordinatedAgent) -> None:
        """Add an agent to the coordination system."""
        self.active_agents[agent.agent_id] = agent
        self.agent_workloads[agent.agent_id] = agent.current_work_count
        self.last_updated = datetime.now()

    def remove_agent(self, agent_id: str) -> ModelCoordinatedAgent | None:
        """Remove an agent from the coordination system."""
        agent = self.active_agents.pop(agent_id, None)
        self.agent_workloads.pop(agent_id, None)

        # Remove agent assignments
        tickets_to_reassign = [
            ticket_id
            for ticket_id, assigned_agent in self.ticket_assignments.items()
            if assigned_agent == agent_id
        ]

        for ticket_id in tickets_to_reassign:
            del self.ticket_assignments[ticket_id]

        self.last_updated = datetime.now()
        return agent

    def assign_work(self, ticket_id: str, agent_id: str) -> bool:
        """Assign work to an agent."""
        if agent_id not in self.active_agents:
            return False

        agent = self.active_agents[agent_id]
        if not agent.is_available:
            return False

        agent.assign_work(ticket_id)
        self.ticket_assignments[ticket_id] = agent_id
        self.agent_workloads[agent_id] = agent.current_work_count
        self.total_assignments_made += 1
        self.last_assignment_time = datetime.now()
        self.last_updated = datetime.now()

        return True

    def complete_work(self, ticket_id: str, success: bool = True) -> bool:
        """Mark work as completed."""
        agent_id = self.ticket_assignments.get(ticket_id)
        if not agent_id or agent_id not in self.active_agents:
            return False

        agent = self.active_agents[agent_id]
        agent.complete_work(ticket_id, success)

        del self.ticket_assignments[ticket_id]
        self.agent_workloads[agent_id] = agent.current_work_count
        self.total_tickets_processed += 1
        self.last_updated = datetime.now()

        return True

    def get_least_loaded_agent(self) -> str | None:
        """Get the agent with the least workload."""
        available_agents = [
            (agent_id, agent)
            for agent_id, agent in self.active_agents.items()
            if agent.is_available
        ]

        if not available_agents:
            return None

        return min(available_agents, key=lambda x: x[1].workload_percentage)[0]

    def get_best_agent_for_capabilities(
        self,
        required_capabilities: list[str],
    ) -> str | None:
        """Get the best agent for specific capabilities."""
        available_agents = [
            (agent_id, agent)
            for agent_id, agent in self.active_agents.items()
            if agent.is_available
        ]

        if not available_agents:
            return None

        # Score agents based on capability match and workload
        scored_agents = []
        for agent_id, agent in available_agents:
            capability_score = agent.get_capability_score(required_capabilities)
            workload_factor = 1.0 - (agent.workload_percentage / 100.0)
            performance_factor = agent.performance.overall_score

            combined_score = (
                capability_score * 0.5
                + workload_factor * 0.3
                + performance_factor * 0.2
            )
            scored_agents.append((agent_id, combined_score))

        if not scored_agents:
            return None

        return max(scored_agents, key=lambda x: x[1])[0]

    def update_metrics(self) -> None:
        """Update coordination metrics."""
        self.coordination_metrics = {
            "total_agents": float(self.total_agents),
            "available_agents": float(self.available_agents),
            "capacity_utilization": self.capacity_utilization,
            "system_efficiency": self.system_efficiency,
            "average_agent_performance": sum(
                agent.performance.overall_score for agent in self.active_agents.values()
            )
            / max(len(self.active_agents), 1),
            "workload_balance_score": (
                100.0
                - max(
                    abs(
                        agent.workload_percentage
                        - (self.capacity_utilization / self.total_agents),
                    )
                    for agent in self.active_agents.values()
                )
                if self.active_agents
                else 100.0
            ),
        }

        self.last_updated = datetime.now()
