"""
Workflow Metadata Model.

Model for workflow metadata in the ONEX workflow coordination system.
Provides versioning, execution configuration, and identification for workflows.

Thread Safety:
    This model is frozen (immutable) after creation, making it safe for
    concurrent read access. The `from_attributes=True` config is safe because
    the model is frozen - source object state cannot affect the created model.

See Also:
    docs/conventions/PYDANTIC_BEST_PRACTICES.md: Guidelines for from_attributes usage.
    docs/architecture/MODEL_ACTION_ARCHITECTURE.md: Workflow execution patterns.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelWorkflowDefinitionMetadata(BaseModel):
    """Metadata for a workflow definition.

    Captures essential metadata for workflow identification, versioning,
    and execution configuration. Used by the orchestration layer for
    workflow management and persistence.

    Attributes:
        version: Model version for schema evolution tracking.
        workflow_name: Human-readable workflow identifier.
        workflow_version: Semantic version of the workflow definition.
        description: Brief description of workflow purpose.
        execution_mode: How workflow steps are executed (sequential, parallel, etc.).
        timeout_ms: Maximum workflow execution time in milliseconds.
        workflow_hash: SHA-256 hash for deduplication and caching.

    Example:
        >>> metadata = ModelWorkflowDefinitionMetadata(
        ...     version=ModelSemVer(major=1, minor=0, patch=0),
        ...     workflow_name="data_pipeline",
        ...     workflow_version=ModelSemVer(major=2, minor=1, patch=0),
        ...     description="ETL data processing pipeline",
        ...     execution_mode="sequential",
        ... )

    Thread Safety:
        This model is frozen (immutable) after creation. Safe for concurrent
        read access without synchronization. The `from_attributes=True` config
        enables ORM/dataclass interoperability and is safe because the model
        is immutable.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    workflow_name: str = Field(default=..., description="Name of the workflow")

    workflow_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the workflow (MUST be provided in YAML contract)",
    )

    description: str = Field(default=..., description="Description of the workflow")

    execution_mode: str = Field(
        default="sequential",
        description="Execution mode: sequential, parallel, batch, conditional, or streaming",
    )

    timeout_ms: int = Field(
        default=600000,
        description="Workflow timeout in milliseconds",
        ge=1000,
    )

    workflow_hash: str | None = Field(
        default=None,
        description=(
            "SHA-256 hash of workflow definition for persistence and caching. "
            "Computed from workflow steps and metadata (excluding runtime data). "
            "Used for workflow identification and deduplication before execution."
        ),
    )

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,  # Safe: model is frozen (immutable)
        frozen=True,  # Immutable after creation for thread safety
    )
