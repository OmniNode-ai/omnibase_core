"""
Workflow Coordination Subcontract Model.



Dedicated subcontract model for workflow coordination functionality providing:
- Workflow instance management and tracking
- Node assignment and coordination
- Progress monitoring and synchronization
- Execution graphs and rule management
- Performance metrics and optimization

This model is composed into node contracts that require workflow coordination functionality,
providing clean separation between node logic and workflow coordination behavior.

Thread Safety:
    ModelWorkflowCoordinationSubcontract is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access from multiple threads or async
    tasks. This follows ONEX thread safety guidelines where configuration models are
    frozen to prevent race conditions during workflow coordination. Note that this
    provides shallow immutability - while the model's fields cannot be reassigned,
    mutable field values (like dict/list contents) can still be modified. For full
    thread safety with mutable nested data, use model_copy(deep=True) to create
    independent copies.

    To modify configuration, create a new instance using model_copy():
        new_config = existing_config.model_copy(update={"max_concurrent_workflows": 20})

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants import TIMEOUT_DEFAULT_MS, TIMEOUT_LONG_MS
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Import all individual model components


class ModelWorkflowCoordinationSubcontract(BaseModel):
    """
    Workflow Coordination Subcontract for ORCHESTRATOR nodes.

    Provides workflow orchestration, node coordination, and execution
    management capabilities specifically for ORCHESTRATOR nodes in the ONEX architecture.

    This model is immutable (frozen=True) after creation, making it thread-safe
    for concurrent read access from multiple threads or async tasks. Unknown
    fields are rejected (extra='forbid') to ensure strict schema compliance.

    To modify a frozen instance, use model_copy():
        >>> modified = subcontract.model_copy(update={"max_concurrent_workflows": 20})

    Attributes:
        version: Model version (MUST be provided in YAML contract).
        subcontract_name: Name of the subcontract (default: "workflow_coordination_subcontract").
        subcontract_version: Version of the subcontract (MUST be provided in YAML contract).
        applicable_node_types: Node types this subcontract applies to (default: ["ORCHESTRATOR"]).
        max_concurrent_workflows: Maximum concurrent workflows (1-100, default 10).
        default_workflow_timeout_ms: Default workflow timeout (60000-3600000 ms, default 600000).
        node_coordination_timeout_ms: Node coordination timeout (5000-TIMEOUT_LONG_MS ms,
            default TIMEOUT_DEFAULT_MS). See omnibase_core.constants for values.
        checkpoint_interval_ms: Checkpoint interval (10000-600000 ms, default 60000).
        auto_retry_enabled: Whether automatic retry is enabled (default True).
        parallel_execution_enabled: Whether parallel execution is enabled (default True).
        workflow_persistence_enabled: Whether workflow state persistence is enabled (default True).
        max_retries: Maximum retries for failed operations (0-10, default 3).
        retry_delay_ms: Delay between retries (1000-60000 ms, default 2000).
        exponential_backoff: Whether to use exponential backoff for retries (default True).

    Example:
        >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
        >>> subcontract = ModelWorkflowCoordinationSubcontract(
        ...     version=ModelSemVer(major=1, minor=0, patch=0),
        ...     subcontract_version=ModelSemVer(major=1, minor=0, patch=0),
        ...     max_concurrent_workflows=5,
        ... )

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    subcontract_name: str = Field(
        default="workflow_coordination_subcontract",
        description="Name of the subcontract",
    )

    subcontract_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the subcontract (MUST be provided in YAML contract)",
    )

    applicable_node_types: list[str] = Field(
        default=["ORCHESTRATOR"],
        description="Node types this subcontract applies to (ORCHESTRATOR only)",
    )

    # Configuration
    max_concurrent_workflows: int = Field(
        default=10,
        description="Maximum number of concurrent workflows",
        ge=1,
        le=100,
    )

    default_workflow_timeout_ms: int = Field(
        default=600000,
        description="Default workflow timeout in milliseconds",
        ge=60000,
        le=3600000,
    )

    node_coordination_timeout_ms: int = Field(
        default=TIMEOUT_DEFAULT_MS,
        description="Node coordination timeout in milliseconds",
        ge=5000,
        le=TIMEOUT_LONG_MS,  # Max 5 minutes (TIMEOUT_LONG_MS)
    )

    checkpoint_interval_ms: int = Field(
        default=60000,
        description="Checkpoint interval in milliseconds",
        ge=10000,
        le=600000,
    )

    auto_retry_enabled: bool = Field(
        default=True,
        description="Whether automatic retry is enabled",
    )

    parallel_execution_enabled: bool = Field(
        default=True,
        description="Whether parallel execution is enabled",
    )

    workflow_persistence_enabled: bool = Field(
        default=True,
        description="Whether workflow state persistence is enabled",
    )

    # Failure recovery configuration
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed operations",
        ge=0,
        le=10,
    )

    retry_delay_ms: int = Field(
        default=2000,
        description="Delay between retries in milliseconds",
        ge=1000,
        le=60000,
    )

    exponential_backoff: bool = Field(
        default=True,
        description="Whether to use exponential backoff for retries",
    )

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        frozen=True,
        use_enum_values=False,  # Keep enum objects, don't convert to strings
    )
