"""
ModelDependencyGraph - Dependency graph for workflow step ordering.
"""

from uuid import UUID

from omnibase_core.enums.enum_orchestrator_types import EnumWorkflowState
from omnibase_core.models.model_workflow_step import ModelWorkflowStep


class ModelDependencyGraph:
    """
    Dependency graph for workflow step ordering.
    """

    def __init__(self) -> None:
        self.nodes: dict[UUID, ModelWorkflowStep] = {}
        self.edges: dict[UUID, list[UUID]] = {}  # step_id -> [dependent_step_ids]
        self.in_degree: dict[UUID, int] = {}

    def add_step(self, step: ModelWorkflowStep) -> None:
        """Add step to dependency graph."""
        self.nodes[step.step_id] = step
        if step.step_id not in self.edges:
            self.edges[step.step_id] = []
        if step.step_id not in self.in_degree:
            self.in_degree[step.step_id] = 0

    def add_dependency(self, from_step: UUID, to_step: UUID) -> None:
        """Add dependency: to_step depends on from_step."""
        if from_step not in self.edges:
            self.edges[from_step] = []
        self.edges[from_step].append(to_step)
        self.in_degree[to_step] = self.in_degree.get(to_step, 0) + 1

    def get_ready_steps(self) -> list[UUID]:
        """Get steps that are ready to execute (no pending dependencies)."""
        return [
            step_id
            for step_id, degree in self.in_degree.items()
            if degree == 0 and self.nodes[step_id].state == EnumWorkflowState.PENDING
        ]

    def mark_completed(self, step_id: UUID) -> None:
        """Mark step as completed and update dependencies."""
        if step_id in self.nodes:
            self.nodes[step_id].state = EnumWorkflowState.COMPLETED

        # Decrease in-degree for dependent steps
        for dependent_step in self.edges.get(step_id, []):
            if dependent_step in self.in_degree:
                self.in_degree[dependent_step] -= 1

    def has_cycles(self) -> bool:
        """Check if dependency graph has cycles using DFS."""
        visited: set[UUID] = set()
        rec_stack: set[UUID] = set()

        def dfs(node: UUID) -> bool:
            if node in rec_stack:
                return True  # Cycle detected
            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.edges.get(node, []):
                if dfs(neighbor):
                    return True

            rec_stack.remove(node)
            return False

        return any(node not in visited and dfs(node) for node in self.nodes)
