# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelTaskTree - Represents the full task dispatch hierarchy for a session.

Aggregates ModelTaskDispatch events into a tree structure that captures the
complete parent-child dispatch chain. Used by audit consumers and the
omnidash dashboard to visualize task hierarchies.

Strict typing is enforced: No Any types allowed in implementation.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.audit.model_task_dispatch import ModelTaskDispatch


class ModelTaskTree(BaseModel):
    """
    Represents the full task dispatch hierarchy for a session.

    Aggregates individual ModelTaskDispatch events into a tree that captures
    the complete parent-child dispatch chain. Supports serialization for
    dashboard visualization and audit queries.

    This model enables:
    - Building the full tree from flat dispatch events
    - Querying depth and breadth of task hierarchies
    - Identifying root dispatches and leaf tasks
    - Serializing the tree for omnidash visualization

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Identity
    session_id: UUID = Field(
        ...,
        description="Session ID this tree belongs to",
    )

    # Tree content
    dispatches: list[ModelTaskDispatch] = Field(
        default_factory=list,
        description="All dispatch events in this session, ordered by time",
    )

    @property
    def root_dispatches(self) -> list[ModelTaskDispatch]:
        """Get root-level dispatches (no parent).

        Returns:
            List of dispatch events with no parent_task_id.
        """
        return [d for d in self.dispatches if d.parent_task_id is None]

    @property
    def depth(self) -> int:
        """Calculate the maximum depth of the dispatch tree.

        Returns:
            Maximum nesting depth (0 for empty tree, 1 for flat dispatches).
        """
        if not self.dispatches:
            return 0

        # Build parent -> children mapping
        children: dict[UUID | None, list[UUID]] = {}
        for d in self.dispatches:
            parent = d.parent_task_id
            if parent not in children:
                children[parent] = []
            children[parent].append(d.task_id)

        # BFS to find max depth
        max_depth = 0
        queue: list[tuple[UUID | None, int]] = [(None, 0)]
        while queue:
            parent_id, current_depth = queue.pop(0)
            child_ids = children.get(parent_id, [])
            if child_ids:
                for child_id in child_ids:
                    queue.append((child_id, current_depth + 1))
            else:
                max_depth = max(max_depth, current_depth)

        return max_depth

    @property
    def total_dispatches(self) -> int:
        """Get total number of dispatch events.

        Returns:
            Count of all dispatch events in the tree.
        """
        return len(self.dispatches)

    def get_children(self, task_id: UUID) -> list[ModelTaskDispatch]:
        """Get child dispatches for a given task.

        Args:
            task_id: The parent task ID to find children for.

        Returns:
            List of dispatch events whose parent_task_id matches.
        """
        return [d for d in self.dispatches if d.parent_task_id == task_id]

    def get_dispatch(self, task_id: UUID) -> ModelTaskDispatch | None:
        """Get a specific dispatch by task ID.

        Args:
            task_id: The task ID to look up.

        Returns:
            The matching dispatch event, or None if not found.
        """
        for d in self.dispatches:
            if d.task_id == task_id:
                return d
        return None

    model_config = ConfigDict(
        extra="ignore",
    )


__all__ = [
    "ModelTaskTree",
]
