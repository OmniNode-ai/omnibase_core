"""
Introspection Subcontract Models for ONEX Nodes.

Provides Pydantic models for node discovery, capability reporting, and runtime
introspection capabilities for all ONEX node types.

Generated from introspection subcontract following ONEX patterns.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# Import existing enums instead of duplicating
from omnibase_spi.protocols.types.core_types import HealthStatus, NodeType
from pydantic import BaseModel, Field

# Use HealthStatus from omnibase_core.enums.node instead
# Use EnumNodeType from omnibase_core.enums.node instead


class ModelNodeVersion(BaseModel):
    """Version information for a node."""

    major: int = Field(..., description="Major version number", ge=0)

    minor: int = Field(..., description="Minor version number", ge=0)

    patch: int = Field(..., description="Patch version number", ge=0)

    build: Optional[str] = Field(default=None, description="Build identifier")


class ModelNodeInfo(BaseModel):
    """Basic node information."""

    node_id: str = Field(..., description="Unique identifier for the node")

    node_type: NodeType = Field(..., description="Type of the node")

    node_name: str = Field(..., description="Human-readable name of the node")

    version: ModelNodeVersion = Field(
        ..., description="Version information for the node"
    )

    status: NodeStatus = Field(..., description="Current health status of the node")

    uptime_ms: int = Field(..., description="Node uptime in milliseconds", ge=0)

    last_updated: datetime = Field(
        ..., description="Last time node information was updated"
    )


class ModelActionDefinition(BaseModel):
    """Definition of an action available on a node."""

    action_name: str = Field(..., description="Name of the action")

    description: str = Field(..., description="Description of what the action does")

    required: bool = Field(
        ..., description="Whether this action is required for the node type"
    )

    timeout_ms: int = Field(
        ..., description="Timeout for the action in milliseconds", ge=100
    )

    input_parameters: List[str] = Field(
        default_factory=list, description="List of input parameter names"
    )

    output_parameters: List[str] = Field(
        default_factory=list, description="List of output parameter names"
    )


class ModelCapabilities(BaseModel):
    """Node capabilities information."""

    actions: List[ModelActionDefinition] = Field(
        default_factory=list, description="List of actions available on this node"
    )

    supported_protocols: List[str] = Field(
        default_factory=list, description="List of protocols supported by this node"
    )

    resource_limits: Dict[str, int] = Field(
        default_factory=dict, description="Resource limits for this node"
    )

    configuration_parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Configurable parameters for this node"
    )


class ModelCapabilitySummary(BaseModel):
    """Summary of node capabilities."""

    total_actions: int = Field(
        ..., description="Total number of actions available", ge=0
    )

    required_actions: int = Field(..., description="Number of required actions", ge=0)

    optional_actions: int = Field(..., description="Number of optional actions", ge=0)

    supported_protocols_count: int = Field(
        ..., description="Number of supported protocols", ge=0
    )


class ModelRuntimeStats(BaseModel):
    """Runtime statistics for a node."""

    requests_processed: int = Field(
        ..., description="Total number of requests processed", ge=0
    )

    average_response_time_ms: float = Field(
        ..., description="Average response time in milliseconds", ge=0.0
    )

    error_count: int = Field(
        ..., description="Total number of errors encountered", ge=0
    )

    memory_usage_mb: float = Field(
        ..., description="Current memory usage in megabytes", ge=0.0
    )

    cpu_usage_percent: float = Field(
        ..., description="Current CPU usage percentage", ge=0.0, le=100.0
    )

    active_connections: int = Field(
        default=0, description="Number of active connections", ge=0
    )

    last_activity: Optional[datetime] = Field(
        default=None, description="Timestamp of last activity"
    )


class ModelPerformanceMetrics(BaseModel):
    """Performance metrics for a node."""

    throughput_rps: float = Field(
        ..., description="Throughput in requests per second", ge=0.0
    )

    latency_percentiles: Dict[str, float] = Field(
        default_factory=dict, description="Latency percentiles (p50, p95, p99)"
    )

    error_rate_percent: float = Field(
        ..., description="Error rate as percentage", ge=0.0, le=100.0
    )

    resource_utilization: Dict[str, float] = Field(
        default_factory=dict, description="Resource utilization metrics"
    )


class ModelPeerNode(BaseModel):
    """Information about a peer node."""

    node_id: str = Field(..., description="Unique identifier for the peer node")

    node_type: NodeType = Field(..., description="Type of the peer node")

    endpoint: str = Field(..., description="Endpoint URL for the peer node")

    status: NodeStatus = Field(..., description="Health status of the peer node")

    last_seen: datetime = Field(..., description="Last time this peer was seen")

    capabilities_hash: Optional[str] = Field(
        default=None, description="Hash of the peer's capabilities for change detection"
    )

    response_time_ms: Optional[int] = Field(
        default=None, description="Last measured response time in milliseconds", ge=0
    )


class ModelNetworkTopology(BaseModel):
    """Network topology information."""

    total_nodes: int = Field(
        ..., description="Total number of nodes in the network", ge=0
    )

    nodes_by_type: Dict[str, int] = Field(
        default_factory=dict, description="Count of nodes by type"
    )

    healthy_nodes: int = Field(..., description="Number of healthy nodes", ge=0)

    discovery_timestamp: datetime = Field(
        ..., description="When this topology snapshot was created"
    )

    network_partitions: Optional[List[List[str]]] = Field(
        default=None, description="List of network partitions (if any detected)"
    )


class ModelDependencyInfo(BaseModel):
    """Information about node dependencies."""

    required_dependencies: List[str] = Field(
        default_factory=list, description="List of required dependencies"
    )

    optional_dependencies: List[str] = Field(
        default_factory=list, description="List of optional dependencies"
    )

    dependency_health: Dict[str, str] = Field(
        default_factory=dict, description="Health status of each dependency"
    )

    missing_dependencies: List[str] = Field(
        default_factory=list, description="List of missing required dependencies"
    )


class ModelIntrospectionResult(BaseModel):
    """Complete result of an introspection operation."""

    node_info: ModelNodeInfo = Field(..., description="Basic node information")

    capability_summary: ModelCapabilitySummary = Field(
        ..., description="Summary of node capabilities"
    )

    capabilities: Optional[ModelCapabilities] = Field(
        default=None, description="Detailed capabilities (if requested)"
    )

    runtime_stats: Optional[ModelRuntimeStats] = Field(
        default=None, description="Runtime statistics (if requested)"
    )

    performance_metrics: Optional[ModelPerformanceMetrics] = Field(
        default=None, description="Performance metrics (if requested)"
    )

    peer_nodes: Optional[List[ModelPeerNode]] = Field(
        default=None, description="Discovered peer nodes (if requested)"
    )

    network_topology: Optional[ModelNetworkTopology] = Field(
        default=None, description="Network topology information (if requested)"
    )

    dependency_info: Optional[ModelDependencyInfo] = Field(
        default=None, description="Dependency information (if requested)"
    )


# Main subcontract definition model
class ModelIntrospectionSubcontract(BaseModel):
    """
    Introspection Subcontract for all ONEX nodes.

    Provides node discovery, capability reporting, and runtime introspection
    capabilities for COMPUTE, EFFECT, REDUCER, and ORCHESTRATOR nodes.
    """

    subcontract_name: str = Field(
        default="introspection_subcontract", description="Name of the subcontract"
    )

    subcontract_version: str = Field(
        default="1.0.0", description="Version of the subcontract"
    )

    applicable_node_types: List[str] = Field(
        default=["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"],
        description="Node types this subcontract applies to",
    )

    # Configuration
    auto_registration: bool = Field(
        default=True,
        description="Whether nodes should automatically register with discovery services",
    )

    discovery_interval_ms: int = Field(
        default=60000,
        description="Interval for peer discovery in milliseconds",
        ge=30000,
        le=600000,
    )

    capability_refresh_ms: int = Field(
        default=300000,
        description="Interval for capability refresh in milliseconds",
        ge=60000,
        le=3600000,
    )

    include_performance_data: bool = Field(
        default=True,
        description="Whether to include performance data in introspection results",
    )

    include_dependency_health: bool = Field(
        default=True, description="Whether to include dependency health information"
    )

    peer_discovery_enabled: bool = Field(
        default=True, description="Whether peer discovery is enabled"
    )

    # Discovery configuration
    max_peers_to_track: int = Field(
        default=100, description="Maximum number of peer nodes to track", ge=10, le=1000
    )

    peer_timeout_ms: int = Field(
        default=30000,
        description="Timeout for peer discovery operations in milliseconds",
        ge=5000,
        le=120000,
    )

    peer_health_check_interval_ms: int = Field(
        default=120000,
        description="Interval for peer health checks in milliseconds",
        ge=30000,
        le=600000,
    )

    # Performance tracking configuration
    performance_history_size: int = Field(
        default=100,
        description="Number of performance data points to retain",
        ge=10,
        le=1000,
    )

    metrics_collection_interval_ms: int = Field(
        default=10000,
        description="Interval for collecting performance metrics in milliseconds",
        ge=5000,
        le=60000,
    )

    class Config:
        json_schema_extra = {
            "example": {
                "subcontract_name": "introspection_subcontract",
                "subcontract_version": "1.0.0",
                "applicable_node_types": [
                    "COMPUTE",
                    "EFFECT",
                    "REDUCER",
                    "ORCHESTRATOR",
                ],
                "auto_registration": True,
                "discovery_interval_ms": 60000,
                "capability_refresh_ms": 300000,
                "include_performance_data": True,
                "include_dependency_health": True,
                "peer_discovery_enabled": True,
                "max_peers_to_track": 100,
                "peer_timeout_ms": 30000,
                "peer_health_check_interval_ms": 120000,
                "performance_history_size": 100,
                "metrics_collection_interval_ms": 10000,
            }
        }
