"""Model for managing active task requests."""

from typing import Dict

from pydantic import BaseModel, Field

from omnibase_core.model.events.model_agent_task_event import \
    ModelAgentTaskRequest


class ModelTaskRequestMap(BaseModel):
    """
    Strongly-typed mapping for active task management.

    Replaces Dict[str, ModelAgentTaskRequest] to comply with ONEX
    standards requiring specific typed models.
    """

    tasks: Dict[str, ModelAgentTaskRequest] = Field(
        default_factory=dict, description="Map of task IDs to task requests"
    )

    def add_task(self, task_id: str, task: ModelAgentTaskRequest) -> None:
        """Add a task request."""
        self.tasks[task_id] = task

    def get_task(self, task_id: str) -> ModelAgentTaskRequest:
        """Get task request by ID."""
        return self.tasks.get(task_id)

    def remove_task(self, task_id: str) -> bool:
        """Remove a task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False

    def has_task(self, task_id: str) -> bool:
        """Check if task exists."""
        return task_id in self.tasks

    def count(self) -> int:
        """Get total number of active tasks."""
        return len(self.tasks)

    def get_all_tasks(self) -> Dict[str, ModelAgentTaskRequest]:
        """Get all tasks."""
        return self.tasks

    def clear(self) -> None:
        """Remove all tasks."""
        self.tasks.clear()
