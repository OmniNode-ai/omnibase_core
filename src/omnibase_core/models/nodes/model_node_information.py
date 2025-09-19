"""
Node information model.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ModelNodeConfiguration(BaseModel):
    """Configuration for a node."""

    # Execution settings
    max_retries: int | None = Field(default=None, description="Maximum retry attempts")
    timeout_seconds: int | None = Field(default=None, description="Execution timeout")
    batch_size: int | None = Field(default=None, description="Batch processing size")
    parallel_execution: bool = Field(
        default=False, description="Enable parallel execution"
    )

    # Resource limits
    max_memory_mb: int | None = Field(
        default=None, description="Maximum memory usage in MB"
    )
    max_cpu_percent: float | None = Field(
        default=None,
        description="Maximum CPU usage percentage",
    )

    # Feature flags
    enable_caching: bool = Field(default=False, description="Enable result caching")
    enable_monitoring: bool = Field(default=True, description="Enable monitoring")
    enable_tracing: bool = Field(default=False, description="Enable detailed tracing")

    # Connection settings
    endpoint: str | None = Field(default=None, description="Service endpoint")
    port: int | None = Field(default=None, description="Service port")
    protocol: str | None = Field(default=None, description="Communication protocol")

    # Custom configuration for extensibility
    custom_settings: dict[str, str] | None = Field(
        default=None,
        description="Custom string settings",
    )
    custom_flags: dict[str, bool] | None = Field(
        default=None,
        description="Custom boolean flags",
    )
    custom_limits: dict[str, int] | None = Field(
        default=None,
        description="Custom numeric limits",
    )


class ModelNodeInformation(BaseModel):
    """
    Node information with typed fields.
    Replaces Dict[str, Any] for node_information fields.
    """

    # Node identification
    node_id: str = Field(..., description="Node identifier")
    node_name: str = Field(..., description="Node name")
    node_type: str = Field(..., description="Node type")
    node_version: str = Field(..., description="Node version")

    # Node metadata
    description: str | None = Field(None, description="Node description")
    author: str | None = Field(None, description="Node author")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    # Node capabilities
    capabilities: list[str] = Field(
        default_factory=list,
        description="Node capabilities",
    )
    supported_operations: list[str] = Field(
        default_factory=list,
        description="Supported operations",
    )

    # Node configuration
    configuration: ModelNodeConfiguration = Field(
        default_factory=lambda: ModelNodeConfiguration(),
        description="Node configuration",
    )

    # Node status
    status: str = Field("active", description="Node status")
    health: str = Field("healthy", description="Node health")

    # Performance metrics
    performance_metrics: dict[str, float] | None = Field(
        None,
        description="Performance metrics",
    )

    # Dependencies
    dependencies: list[str] = Field(
        default_factory=list,
        description="Node dependencies",
    )

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> Optional["ModelNodeInformation"]:
        """Create from dictionary for easy migration."""
        if data is None:
            return None

        # Create a copy to avoid mutating original data
        normalized_data = data.copy()

        # Apply field mappings for current standards
        normalized_data.setdefault("node_id", normalized_data.get("id", "unknown"))
        normalized_data.setdefault("node_name", normalized_data.get("name", "unknown"))
        normalized_data.setdefault("node_type", normalized_data.get("type", "generic"))
        normalized_data.setdefault(
            "node_version",
            normalized_data.get("version", "1.0.0"),
        )

        # Use Pydantic validation instead of manual validation
        return cls.model_validate(normalized_data)
