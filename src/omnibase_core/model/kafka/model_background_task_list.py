"""Model for managing background asyncio tasks."""

import asyncio

from pydantic import BaseModel, Field


class ModelBackgroundTaskList(BaseModel):
    """
    Strongly-typed collection for managing background asyncio tasks.

    Replaces List[asyncio.Task] to comply with ONEX
    standards requiring specific typed models.
    """

    tasks: list[asyncio.Task] = Field(
        default_factory=list,
        description="List of background asyncio tasks",
    )

    class Config:
        # Allow asyncio.Task objects in Pydantic model
        arbitrary_types_allowed = True

    def add_task(self, task: asyncio.Task) -> None:
        """Add a background task."""
        self.tasks.append(task)

    def remove_task(self, task: asyncio.Task) -> bool:
        """Remove a task."""
        if task in self.tasks:
            self.tasks.remove(task)
            return True
        return False

    def get_all_tasks(self) -> list[asyncio.Task]:
        """Get all tasks."""
        return self.tasks

    def get_running_tasks(self) -> list[asyncio.Task]:
        """Get only running (not done) tasks."""
        return [task for task in self.tasks if not task.done()]

    def get_done_tasks(self) -> list[asyncio.Task]:
        """Get completed tasks."""
        return [task for task in self.tasks if task.done()]

    def cancel_all(self) -> None:
        """Cancel all tasks."""
        for task in self.tasks:
            if not task.done():
                task.cancel()

    def remove_done_tasks(self) -> int:
        """Remove completed tasks and return count removed."""
        done_tasks = self.get_done_tasks()
        for task in done_tasks:
            self.tasks.remove(task)
        return len(done_tasks)

    def count(self) -> int:
        """Get total number of tasks."""
        return len(self.tasks)

    def count_running(self) -> int:
        """Get number of running tasks."""
        return len(self.get_running_tasks())

    def clear(self) -> None:
        """Remove all tasks (does not cancel them)."""
        self.tasks.clear()
