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

v1.1+ Roadmap:
    The execution_graph field is reserved for future versions (v1.1+) where it
    will enable advanced workflow features:

    - **v1.1 (Planned)**: Graph-based execution validation - the executor will
      optionally validate that steps match the declared graph structure.

    - **v1.2+ (Planned)**: Graph-driven optimizations including:
      - Parallel execution constraints and wave optimization
      - Resource allocation hints for compute-intensive steps
      - Cross-step data flow optimization
      - Critical path analysis and automatic step reordering

    - **v1.3+ (Planned)**: Visual workflow editor integration - the graph
      structure will be used to render and edit workflows graphically.

    Until these features are implemented, the executor MUST ignore this field
    and rely solely on ModelOrchestratorInput.steps + depends_on declarations.

    See Linear ticket OMN-656 for tracking of execution_graph activation timeline.
"""

from pydantic import BaseModel, ConfigDict, Field

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
        - Future version extensibility (v1.1+)
        - Documentation of workflow structure

        The v1.0 executor:
        - MUST NOT read this field during execution
        - MUST NOT validate steps against graph nodes
        - MUST NOT emit warnings for graph/step mismatches

    v1.1+ Roadmap:
        This field will be actively used starting in v1.1 for:
        - Graph-based execution validation (v1.1)
        - Parallel execution constraints and wave optimization (v1.2+)
        - Resource allocation hints for compute-intensive steps (v1.2+)
        - Cross-step data flow optimization (v1.2+)
        - Visual workflow editing (v1.3+)

        See Linear ticket OMN-656 for tracking of execution_graph activation.
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

    # v1.0.5 Fix 54: Reserved Fields Governance
    # Uses extra="ignore" (not "forbid") to support forward compatibility.
    # Reserved fields from future versions (v1.1+) are preserved during round-trip
    # serialization but are NOT validated beyond structural type checking and
    # MUST NOT influence any runtime decision in v1.0.
    # See: test_workflow_contract_hardening.py for the comprehensive test coverage.
    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
        frozen=True,
        from_attributes=True,
    )
