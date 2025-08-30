"""
Node information model.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelNodeConfiguration(BaseModel):
    """Configuration for a node."""

    # Execution settings
    max_retries: Optional[int] = Field(None, description="Maximum retry attempts")
    timeout_seconds: Optional[int] = Field(None, description="Execution timeout")
    batch_size: Optional[int] = Field(None, description="Batch processing size")
    parallel_execution: bool = Field(False, description="Enable parallel execution")

    # Resource limits
    max_memory_mb: Optional[int] = Field(None, description="Maximum memory usage in MB")
    max_cpu_percent: Optional[float] = Field(
        None, description="Maximum CPU usage percentage"
    )

    # Feature flags
    enable_caching: bool = Field(False, description="Enable result caching")
    enable_monitoring: bool = Field(True, description="Enable monitoring")
    enable_tracing: bool = Field(False, description="Enable detailed tracing")

    # Connection settings
    endpoint: Optional[str] = Field(None, description="Service endpoint")
    port: Optional[int] = Field(None, description="Service port")
    protocol: Optional[str] = Field(None, description="Communication protocol")

    # Custom configuration for extensibility
    custom_settings: Optional[Dict[str, str]] = Field(
        None, description="Custom string settings"
    )
    custom_flags: Optional[Dict[str, bool]] = Field(
        None, description="Custom boolean flags"
    )
    custom_limits: Optional[Dict[str, int]] = Field(
        None, description="Custom numeric limits"
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
    description: Optional[str] = Field(None, description="Node description")
    author: Optional[str] = Field(None, description="Node author")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # Node capabilities
    capabilities: List[str] = Field(
        default_factory=list, description="Node capabilities"
    )
    supported_operations: List[str] = Field(
        default_factory=list, description="Supported operations"
    )

    # Node configuration
    configuration: ModelNodeConfiguration = Field(
        default_factory=ModelNodeConfiguration, description="Node configuration"
    )

    # Node status
    status: str = Field("active", description="Node status")
    health: str = Field("healthy", description="Node health")

    # Performance metrics
    performance_metrics: Optional[Dict[str, float]] = Field(
        None, description="Performance metrics"
    )

    # Dependencies
    dependencies: List[str] = Field(
        default_factory=list, description="Node dependencies"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)

    @classmethod
    def from_dict(
        cls, data: Optional[Dict[str, Any]]
    ) -> Optional["ModelNodeInformation"]:
        """Create from dictionary for easy migration."""
        if data is None:
            return None

        # Ensure required fields
        if "node_id" not in data:
            data["node_id"] = data.get("id", "unknown")
        if "node_name" not in data:
            data["node_name"] = data.get("name", "unknown")
        if "node_type" not in data:
            data["node_type"] = data.get("type", "generic")
        if "node_version" not in data:
            data["node_version"] = data.get("version", "1.0.0")

        return cls(**data)
