"""
Execution Graph Model.

Model for execution graphs in workflows for the ONEX workflow coordination system.

v1.0 Note:
    ModelExecutionGraph is defined for contract generation purposes only in v1.0.
    The v1.0 workflow executor MUST NOT consult execution_graph - it uses only
    the steps list and their dependency declarations (depends_on) from
    ModelOrchestratorInput.

    The v1.0 executor MUST NOT check for equivalence between the graph and
    the step list, and MUST NOT log warnings if they disagree.

    See: docs/architecture/CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md
    Section: "Execution Graph Prohibition (v1.0.4 Normative)"
"""

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_workflow_node import ModelWorkflowNode


class ModelExecutionGraph(BaseModel):
    """
    Execution graph for a workflow.

    v1.0 Note:
        Defined for contract generation purposes only in v1.0. The executor
        MUST NOT consult this field. The v1.0 executor uses only steps +
        dependencies from ModelOrchestratorInput, not the execution_graph.

        The execution_graph field exists for:
        - Contract schema definition
        - Future version extensibility
        - Documentation of workflow structure

        The v1.0 executor:
        - MUST NOT read this field during execution
        - MUST NOT validate steps against graph nodes
        - MUST NOT emit warnings for graph/step mismatches
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
