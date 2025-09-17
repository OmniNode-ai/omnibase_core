"""Model for tracking active tasks."""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelTaskMap(BaseModel):
    """
    Strongly-typed mapping for task tracking.

    Replaces Dict[str, str] to comply with ONEX standards
    requiring specific typed models.
    """

    agent_tasks: dict[str, str] = Field(
        default_factory=dict,
        description="Map of agent ID to task ID",
    )

    task_agents: dict[str, str] = Field(
        default_factory=dict,
        description="Map of task ID to agent ID",
    )

    task_start_times: dict[str, datetime] = Field(
        default_factory=dict,
        description="Map of task ID to start time",
    )

    def assign_task(self, agent_id: str, task_id: str) -> None:
        """Assign a task to an agent."""
        # Remove any previous task assignment for this agent
        if agent_id in self.agent_tasks:
            old_task_id = self.agent_tasks[agent_id]
            if old_task_id in self.task_agents:
                del self.task_agents[old_task_id]
            if old_task_id in self.task_start_times:
                del self.task_start_times[old_task_id]

        # Assign new task
        self.agent_tasks[agent_id] = task_id
        self.task_agents[task_id] = agent_id
        self.task_start_times[task_id] = datetime.utcnow()

    def get_agent_task(self, agent_id: str) -> str | None:
        """Get the current task ID for an agent."""
        return self.agent_tasks.get(agent_id)

    def get_task_agent(self, task_id: str) -> str | None:
        """Get the agent ID assigned to a task."""
        return self.task_agents.get(task_id)

    def remove_task(self, task_id: str) -> bool:
        """Remove a task assignment."""
        if task_id in self.task_agents:
            agent_id = self.task_agents[task_id]
            del self.task_agents[task_id]
            if agent_id in self.agent_tasks and self.agent_tasks[agent_id] == task_id:
                del self.agent_tasks[agent_id]
            if task_id in self.task_start_times:
                del self.task_start_times[task_id]
            return True
        return False

    def remove_agent_task(self, agent_id: str) -> str | None:
        """Remove task assignment for an agent, returns removed task ID."""
        if agent_id in self.agent_tasks:
            task_id = self.agent_tasks[agent_id]
            self.remove_task(task_id)
            return task_id
        return None

    def is_agent_busy(self, agent_id: str) -> bool:
        """Check if an agent has an active task."""
        return agent_id in self.agent_tasks

    def is_task_assigned(self, task_id: str) -> bool:
        """Check if a task is assigned to any agent."""
        return task_id in self.task_agents

    def get_active_agents(self) -> set[str]:
        """Get all agent IDs with active tasks."""
        return set(self.agent_tasks.keys())

    def get_active_tasks(self) -> set[str]:
        """Get all active task IDs."""
        return set(self.task_agents.keys())

    def count_active_tasks(self) -> int:
        """Count the number of active tasks."""
        return len(self.task_agents)

    def get_task_duration(self, task_id: str) -> float | None:
        """Get task duration in seconds if task is active."""
        if task_id in self.task_start_times:
            return (datetime.utcnow() - self.task_start_times[task_id]).total_seconds()
        return None

    def get_long_running_tasks(self, threshold_seconds: int = 3600) -> list[str]:
        """Get task IDs that have been running longer than threshold."""
        long_running = []
        for task_id, start_time in self.task_start_times.items():
            duration = (datetime.utcnow() - start_time).total_seconds()
            if duration > threshold_seconds:
                long_running.append(task_id)
        return long_running

    def clear(self) -> None:
        """Clear all task assignments."""
        self.agent_tasks.clear()
        self.task_agents.clear()
        self.task_start_times.clear()
