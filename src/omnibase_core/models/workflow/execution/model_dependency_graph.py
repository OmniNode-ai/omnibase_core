"""
Dependency Graph Model.

Dependency graph for workflow step ordering and execution coordination.

Extracted from node_orchestrator.py to eliminate embedded class anti-pattern.

Security Considerations:
    The MAX_DFS_ITERATIONS constant (10,000) protects against denial-of-service
    attacks from maliciously crafted workflow graphs. Without this limit, an
    attacker could submit workflows designed to cause infinite loops or excessive
    CPU consumption during cycle detection.

    If cycle detection exceeds MAX_DFS_ITERATIONS, a ModelOnexError is raised
    with detailed context for debugging and audit logging.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.validation.validator_workflow_constants import MAX_DFS_ITERATIONS

# MAX_DFS_ITERATIONS: Resource exhaustion protection constant for DFS cycle detection.
# Imported from validator_workflow_constants.py (canonical source).
# Value of 10,000 iterations supports graphs with up to ~5,000 nodes
# (worst case: each node visited twice during DFS traversal).


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
            if degree == 0 and self.nodes[step_id].state == EnumExecutionStatus.PENDING
        ]

    def mark_completed(self, step_id: UUID) -> None:
        """Mark step as completed and update dependencies."""
        # Convert to string to ensure consistent dictionary key
        step_id_str = str(step_id)

        if step_id_str in self.nodes:
            self.nodes[step_id_str].state = EnumExecutionStatus.COMPLETED

        # Decrease in-degree for dependent steps
        for dependent_step in self.edges.get(step_id_str, []):
            if dependent_step in self.in_degree:
                self.in_degree[dependent_step] -= 1

    def has_cycles(self) -> bool:
        """
        Check if dependency graph has cycles using DFS.

        Uses iteration bounds to prevent resource exhaustion from malicious
        or malformed inputs.

        Returns:
            True if cycles detected, False otherwise

        Raises:
            ModelOnexError: If cycle detection exceeds MAX_DFS_ITERATIONS,
                indicating possible malicious input or malformed graph.
        """
        visited: set[str] = set()
        rec_stack: set[str] = set()
        iterations = 0  # Track iterations for resource exhaustion protection

        def dfs(node: str) -> bool:
            nonlocal iterations
            iterations += 1

            # Resource exhaustion protection - prevent malicious/malformed inputs
            if iterations > MAX_DFS_ITERATIONS:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=(
                        f"Cycle detection exceeded {MAX_DFS_ITERATIONS} iterations - "
                        "possible malicious input or malformed graph"
                    ),
                    context={
                        "node_count": len(self.nodes),
                        "max_iterations": MAX_DFS_ITERATIONS,
                        "last_node": node,
                    },
                )

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

    model_config = ConfigDict(
        extra="ignore",
        arbitrary_types_allowed=True,  # For WorkflowStepExecution
        validate_assignment=True,
    )


# Import here to avoid circular dependency
from omnibase_core.models.workflow.execution.model_workflow_step_execution import (
    ModelWorkflowStepExecution,
)

# Update forward references
ModelDependencyGraph.model_rebuild()

# NOTE: MAX_DFS_ITERATIONS is imported from validator_workflow_constants.py (canonical source).
# Import directly from omnibase_core.validation.validator_workflow_constants for this constant.
__all__ = ["ModelDependencyGraph"]
