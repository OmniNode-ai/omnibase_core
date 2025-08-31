"""Model for managing task assignments."""

from pydantic import BaseModel, Field


class ModelTaskAssignmentMap(BaseModel):
    """
    Strongly-typed mapping for task assignments.

    Replaces Dict[str, str] to comply with ONEX
    standards requiring specific typed models.
    """

    assignments: dict[str, str] = Field(
        default_factory=dict,
        description="Map of task IDs to agent IDs",
    )

    def assign_task(self, task_id: str, agent_id: str) -> None:
        """Assign a task to an agent."""
        self.assignments[task_id] = agent_id

    def get_agent_for_task(self, task_id: str) -> str:
        """Get agent ID assigned to a task."""
        return self.assignments.get(task_id)

    def unassign_task(self, task_id: str) -> bool:
        """Remove a task assignment."""
        if task_id in self.assignments:
            del self.assignments[task_id]
            return True
        return False

    def get_tasks_for_agent(self, agent_id: str) -> list:
        """Get all tasks assigned to an agent."""
        return [
            task_id
            for task_id, assigned_agent in self.assignments.items()
            if assigned_agent == agent_id
        ]

    def has_assignment(self, task_id: str) -> bool:
        """Check if task has an assignment."""
        return task_id in self.assignments

    def count(self) -> int:
        """Get total number of assignments."""
        return len(self.assignments)

    def clear(self) -> None:
        """Remove all assignments."""
        self.assignments.clear()
