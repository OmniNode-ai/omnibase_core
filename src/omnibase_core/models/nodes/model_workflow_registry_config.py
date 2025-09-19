"""
Workflow registry configuration model for ORCHESTRATOR nodes.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.nodes import EnumStorageType


class ModelWorkflowRegistryConfig(BaseModel):
    """Workflow registry configuration for ORCHESTRATOR nodes."""

    model_config = ConfigDict(extra="forbid")

    storage_type: EnumStorageType = Field(
        default=EnumStorageType.MEMORY,
        description="Storage type for workflow registry",
    )
    max_workflows: int = Field(
        default=10000,
        description="Maximum number of workflows to store",
        ge=1,
    )
    cleanup_interval_ms: int = Field(
        default=300000,
        description="Cleanup interval in milliseconds",
        ge=60000,
    )
