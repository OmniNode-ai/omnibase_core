"""
Workflow Metadata Model.

Model for workflow metadata in the ONEX workflow coordination system.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants.constants_field_limits import MAX_TIMEOUT_MS
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelWorkflowDefinitionMetadata(BaseModel):
    """Metadata for a workflow definition."""

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
        le=MAX_TIMEOUT_MS,
    )

    workflow_hash: str | None = Field(
        default=None,
        description=(
            "SHA-256 hash of workflow definition for persistence and caching. "
            "Computed from workflow steps and metadata (excluding runtime data). "
            "Used for workflow identification and deduplication before execution."
        ),
    )

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
        frozen=True,
    )
