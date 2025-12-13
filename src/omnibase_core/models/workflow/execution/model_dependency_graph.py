"""
Dependency Graph Model.

Dependency graph for workflow step ordering and execution coordination.

Extracted from node_orchestrator.py to eliminate embedded class anti-pattern.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_execution import EnumWorkflowState


class ModelDependencyGraph(BaseModel):
    """
    Dependency graph for workflow step ordering.

    Tracks dependencies between workflow steps and provides
    topological ordering for execution.

    Note: This is converted from a plain class to Pydantic BaseModel
    for better type safety and validation.
    """

    nodes: dict[str, "ModelWorkflowStepExecution"] = Field(
        default_factory=dict,
        description="Map of step_id (as string) to WorkflowStepExecution",
    )

    edges: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Map of step_id (as string) to list of dependent step_ids (as strings)",
    )

    in_degree: dict[str, int] = Field(
        default_factory=dict,
        description="Map of step_id (as string) to incoming edge count",
    )

    def add_step(self, step: "ModelWorkflowStepExecution") -> None:
        """Add step to dependency graph."""
        step_id_str = str(step.step_id)
        self.nodes[step_id_str] = step
        if step_id_str not in self.edges:
            self.edges[step_id_str] = []
        if step_id_str not in self.in_degree:
            self.in_degree[step_id_str] = 0

    def add_dependency(self, from_step: UUID, to_step: UUID) -> None:
        """Add dependency: to_step depends on from_step."""
        # Convert to strings to ensure consistent dictionary keys
        from_step_str = str(from_step)
        to_step_str = str(to_step)

        if from_step_str not in self.edges:
            self.edges[from_step_str] = []
        self.edges[from_step_str].append(to_step_str)
        self.in_degree[to_step_str] = self.in_degree.get(to_step_str, 0) + 1

    def get_ready_steps(self) -> list[str]:
        """Get steps that are ready to execute (no pending dependencies)."""
        return [
            step_id
            for step_id, degree in self.in_degree.items()
            if degree == 0 and self.nodes[step_id].state == EnumWorkflowState.PENDING
        ]

    def mark_completed(self, step_id: UUID) -> None:
        """Mark step as completed and update dependencies."""
        # Convert to string to ensure consistent dictionary key
        step_id_str = str(step_id)

        if step_id_str in self.nodes:
            self.nodes[step_id_str].state = EnumWorkflowState.COMPLETED

        # Decrease in-degree for dependent steps
        for dependent_step in self.edges.get(step_id_str, []):
            if dependent_step in self.in_degree:
                self.in_degree[dependent_step] -= 1

    def has_cycles(self) -> bool:
        """Check if dependency graph has cycles using DFS."""
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node: str) -> bool:
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

    model_config = {
        "extra": "ignore",
        "arbitrary_types_allowed": True,  # For WorkflowStepExecution
        "validate_assignment": True,
    }


# Import here to avoid circular dependency
from omnibase_core.models.workflow.execution.model_workflow_step_execution import (
    ModelWorkflowStepExecution,
)

# Update forward references
ModelDependencyGraph.model_rebuild()
