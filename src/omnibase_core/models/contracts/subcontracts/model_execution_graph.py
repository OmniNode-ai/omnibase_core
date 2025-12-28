"""
Execution Graph Model.

Model for execution graphs in workflows for the ONEX workflow coordination system.

v1.0 Scope:
    This model provides basic DAG-based workflow execution with:
    - Node dependency tracking via `depends_on`
    - Sequential/parallel/batch execution modes
    - Topological ordering for execution sequence

v1.1+ Roadmap:
    Future versions will extend this model with:
    - Priority-based scheduling (respecting `priority` field in nodes)
    - Conditional execution paths (branching based on runtime state)
    - Dynamic graph modification during execution
    - Streaming execution mode for continuous data processing
    - Sub-graph isolation for partial workflow execution

See Also:
    - docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md for node type details
    - docs/guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md for usage
"""

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_workflow_node import ModelWorkflowNode


class ModelExecutionGraph(BaseModel):
    """
    Execution graph for a workflow.

    Represents the DAG structure of workflow nodes and their dependencies.
    In v1.0, execution order is determined by topological sort of dependencies.

    v1.1+ Roadmap:
        - Priority-based scheduling within dependency tiers
        - Conditional edge weights for dynamic routing
        - Graph versioning for runtime modifications
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    nodes: list[ModelWorkflowNode] = Field(
        default_factory=list,
        description="Nodes in the execution graph",
    )

    model_config = {
        "extra": "forbid",
        "use_enum_values": False,
        "validate_assignment": True,
        "frozen": True,
        # from_attributes=True allows Pydantic to accept objects with matching
        # attributes even when class identity differs (e.g., in pytest-xdist
        # parallel execution where model classes are imported in separate workers)
        "from_attributes": True,
    }
