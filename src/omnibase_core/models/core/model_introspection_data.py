"""
Introspection data model to replace Dict[str, object] usage for node introspection.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from .model_schema import ModelSchema


class ModelIntrospectionData(BaseModel):
    """
    Node introspection data with typed fields.
    Replaces Dict[str, object] for introspection fields.
    """

    # Core introspection fields
    node_name: str = Field(..., description="Node name")
    node_version: str = Field(..., description="Node version")
    node_type: str = Field(..., description="Node type/category")
    description: str | None = Field(None, description="Node description")

    # Capabilities
    supported_operations: list[str] = Field(
        default_factory=list,
        description="List of supported operations",
    )
    required_dependencies: list[str] = Field(
        default_factory=list,
        description="Required dependencies",
    )
    optional_dependencies: list[str] = Field(
        default_factory=list,
        description="Optional dependencies",
    )

    # Configuration
    configuration_schema: ModelSchema | None = Field(
        None,
        description="JSON schema for configuration",
    )
    default_configuration: ModelSchema | None = Field(
        None,
        description="Default configuration values",
    )

    # Input/Output contracts
    input_schema: ModelSchema | None = Field(
        None,
        description="JSON schema for input",
    )
    output_schema: ModelSchema | None = Field(
        None,
        description="JSON schema for output",
    )

    # Performance characteristics
    estimated_runtime_ms: float | None = Field(
        None,
        description="Estimated runtime in milliseconds",
    )
    memory_requirements_mb: float | None = Field(
        None,
        description="Memory requirements in MB",
    )
    cpu_requirements: float | None = Field(
        None,
        description="CPU requirements (cores)",
    )

    # Metadata
    author: str | None = Field(None, description="Node author")
    license: str | None = Field(None, description="Node license")
    repository: str | None = Field(None, description="Source repository")
    documentation_url: str | None = Field(None, description="Documentation URL")

    # Status and health
    status: str = Field("active", description="Node status")
    last_updated: datetime | None = Field(None, description="Last update timestamp")
    deprecation_notice: str | None = Field(
        None,
        description="Deprecation information",
    )

    # Extension points
    plugins_supported: list[str] = Field(
        default_factory=list,
        description="Supported plugin types",
    )
    extensibility_points: list[str] = Field(
        default_factory=list,
        description="Extension points",
    )

    model_config = ConfigDict()

    @field_serializer("last_updated")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value and isinstance(value, datetime):
            return value.isoformat()
        return None


# Compatibility alias
IntrospectionData = ModelIntrospectionData
