"""
Node information summary model.

Clean, strongly-typed replacement for node information dict return types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from ...utils.uuid_utilities import uuid_from_string


class ModelNodeCoreInfoSummary(BaseModel):
    """Core node information summary with specific types."""

    node_id: UUID = Field(description="Node identifier")
    node_name: str = Field(description="Node name")
    node_type: str = Field(description="Node type value")
    node_version: str = Field(description="Node version as string")
    status: str = Field(description="Node status value")
    health: str = Field(description="Node health value")
    is_active: bool = Field(description="Whether node is active")
    is_healthy: bool = Field(description="Whether node is healthy")
    has_description: bool = Field(description="Whether node has description")
    has_author: bool = Field(description="Whether node has author")


class ModelNodeCapabilitiesSummary(BaseModel):
    """Node capabilities summary with specific types."""

    capabilities_count: int = Field(description="Number of capabilities")
    operations_count: int = Field(description="Number of operations")
    dependencies_count: int = Field(description="Number of dependencies")
    has_capabilities: bool = Field(description="Whether node has capabilities")
    has_operations: bool = Field(description="Whether node has operations")
    has_dependencies: bool = Field(description="Whether node has dependencies")
    has_performance_metrics: bool = Field(description="Whether node has performance metrics")
    primary_capability: str | None = Field(description="Primary capability if any")
    metrics_count: int = Field(description="Number of metrics")


class ModelNodeConfigurationSummary(BaseModel):
    """Node configuration summary with specific types."""

    execution: dict[str, str | int | float | bool | None] = Field(
        description="Execution configuration summary"
    )
    resources: dict[str, str | int | float | bool | None] = Field(
        description="Resource configuration summary"
    )
    features: dict[str, str | int | float | bool | None] = Field(
        description="Feature configuration summary"
    )
    connection: dict[str, str | int | float | bool | None] = Field(
        description="Connection configuration summary"
    )
    is_production_ready: bool = Field(description="Whether configuration is production ready")
    is_performance_optimized: bool = Field(description="Whether configuration is performance optimized")
    has_custom_settings: bool = Field(description="Whether configuration has custom settings")


class ModelNodeInformationSummary(BaseModel):
    """
    Clean, strongly-typed model replacing node information dict return types.

    Eliminates: dict[str, Any]

    With proper structured data using specific field types.
    """

    core_info: ModelNodeCoreInfoSummary = Field(
        description="Core node information summary"
    )
    capabilities: ModelNodeCapabilitiesSummary = Field(
        description="Node capabilities summary"
    )
    configuration: ModelNodeConfigurationSummary = Field(
        description="Node configuration summary"
    )
    is_fully_configured: bool = Field(
        description="Whether node is fully configured"
    )

    @classmethod
    def create_from_dict(
        cls,
        data: dict[str, str | int | float | bool | None | list | dict],
    ) -> "ModelNodeInformationSummary":
        """Create node information summary from legacy dict for backward compatibility."""
        core_info_data = data.get("core_info", {}) or data.get("node_info", {})
        capabilities_data = data.get("capabilities", {})
        configuration_data = data.get("configuration", {})

        node_id_raw = core_info_data.get("node_id", "")
        node_id = uuid_from_string(node_id_raw, "node") if isinstance(node_id_raw, str) else node_id_raw

        core_info = ModelNodeCoreInfoSummary(
            node_id=node_id,
            node_name=str(core_info_data.get("node_name", "")),
            node_type=str(core_info_data.get("node_type", "")),
            node_version=str(core_info_data.get("node_version", "")),
            status=str(core_info_data.get("status", "")),
            health=str(core_info_data.get("health", "")),
            is_active=bool(core_info_data.get("is_active", False)),
            is_healthy=bool(core_info_data.get("is_healthy", False)),
            has_description=bool(core_info_data.get("has_description", False)),
            has_author=bool(core_info_data.get("has_author", False)),
        )

        capabilities = ModelNodeCapabilitiesSummary(
            capabilities_count=int(capabilities_data.get("capabilities_count", 0)),
            operations_count=int(capabilities_data.get("operations_count", 0)),
            dependencies_count=int(capabilities_data.get("dependencies_count", 0)),
            has_capabilities=bool(capabilities_data.get("has_capabilities", False)),
            has_operations=bool(capabilities_data.get("has_operations", False)),
            has_dependencies=bool(capabilities_data.get("has_dependencies", False)),
            has_performance_metrics=bool(capabilities_data.get("has_performance_metrics", False)),
            primary_capability=capabilities_data.get("primary_capability"),
            metrics_count=int(capabilities_data.get("metrics_count", 0)),
        )

        configuration = ModelNodeConfigurationSummary(
            execution=configuration_data.get("execution", {}),
            resources=configuration_data.get("resources", {}),
            features=configuration_data.get("features", {}),
            connection=configuration_data.get("connection", {}),
            is_production_ready=bool(configuration_data.get("is_production_ready", False)),
            is_performance_optimized=bool(configuration_data.get("is_performance_optimized", False)),
            has_custom_settings=bool(configuration_data.get("has_custom_settings", False)),
        )

        return cls(
            core_info=core_info,
            capabilities=capabilities,
            configuration=configuration,
            is_fully_configured=bool(data.get("is_fully_configured", False)),
        )


# Export the model
__all__ = ["ModelNodeInformationSummary", "ModelNodeCoreInfoSummary", "ModelNodeCapabilitiesSummary", "ModelNodeConfigurationSummary"]