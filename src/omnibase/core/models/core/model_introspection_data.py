"""
Introspection data model to replace Dict[str, object] usage for node introspection.
"""

from datetime import datetime
from typing import List, Optional

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
    description: Optional[str] = Field(None, description="Node description")

    # Capabilities
    supported_operations: List[str] = Field(
        default_factory=list, description="List of supported operations"
    )
    required_dependencies: List[str] = Field(
        default_factory=list, description="Required dependencies"
    )
    optional_dependencies: List[str] = Field(
        default_factory=list, description="Optional dependencies"
    )

    # Configuration
    configuration_schema: Optional[ModelSchema] = Field(
        None, description="JSON schema for configuration"
    )
    default_configuration: Optional[ModelSchema] = Field(
        None, description="Default configuration values"
    )

    # Input/Output contracts
    input_schema: Optional[ModelSchema] = Field(
        None, description="JSON schema for input"
    )
    output_schema: Optional[ModelSchema] = Field(
        None, description="JSON schema for output"
    )

    # Performance characteristics
    estimated_runtime_ms: Optional[float] = Field(
        None, description="Estimated runtime in milliseconds"
    )
    memory_requirements_mb: Optional[float] = Field(
        None, description="Memory requirements in MB"
    )
    cpu_requirements: Optional[float] = Field(
        None, description="CPU requirements (cores)"
    )

    # Metadata
    author: Optional[str] = Field(None, description="Node author")
    license: Optional[str] = Field(None, description="Node license")
    repository: Optional[str] = Field(None, description="Source repository")
    documentation_url: Optional[str] = Field(None, description="Documentation URL")

    # Status and health
    status: str = Field("active", description="Node status")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    deprecation_notice: Optional[str] = Field(
        None, description="Deprecation information"
    )

    # Extension points
    plugins_supported: List[str] = Field(
        default_factory=list, description="Supported plugin types"
    )
    extensibility_points: List[str] = Field(
        default_factory=list, description="Extension points"
    )

    model_config = ConfigDict()

    @field_serializer("last_updated")
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value


# Backward compatibility alias
IntrospectionData = ModelIntrospectionData
