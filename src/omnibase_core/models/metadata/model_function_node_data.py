"""
Function node data model.

Clean, strongly-typed replacement for the horrible FunctionNodeData union type.
Follows ONEX one-model-per-file naming conventions.
"""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelStringMetrics(BaseModel):
    """Model for string-based metrics."""

    name: str = Field(..., description="Metric name")
    value: str = Field(..., description="String metric value")


class ModelNumericMetrics(BaseModel):
    """Model for numeric metrics."""

    name: str = Field(..., description="Metric name")
    value: int | float = Field(..., description="Numeric metric value")


class ModelBooleanMetrics(BaseModel):
    """Model for boolean metrics."""

    name: str = Field(..., description="Metric name")
    value: bool = Field(..., description="Boolean metric value")


class ModelNestedConfiguration(BaseModel):
    """Model for nested configuration data."""

    config_name: str = Field(..., description="Configuration name")
    config_type: str = Field(..., description="Configuration type")
    settings: dict[str, str | int | bool | float] = Field(
        default_factory=dict, description="Configuration settings with basic types only"
    )


class ModelFunctionNodeData(BaseModel):
    """
    Clean, strongly-typed model replacing the horrible FunctionNodeData union type.

    Eliminates: dict[str, str | int | bool | float | list[str] | dict[str, int] |
                     dict[str, str] | dict[str, str | int | bool | float] | None]

    With proper structured data using specific field types.
    """

    # Core identification
    node_id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the function node"
    )

    name: str = Field(..., description="Function node name")
    description: str | None = Field(None, description="Node description")

    # Basic properties
    node_type: str = Field(default="function", description="Type of node")
    status: str = Field(default="active", description="Node status")
    version: str = Field(default="1.0.0", description="Node version")

    # Structured data instead of horrible unions
    tags: list[str] = Field(
        default_factory=list, description="Tags associated with the node"
    )

    string_properties: list[ModelStringMetrics] = Field(
        default_factory=list, description="String-based properties and metadata"
    )

    numeric_properties: list[ModelNumericMetrics] = Field(
        default_factory=list, description="Numeric properties and metrics"
    )

    boolean_properties: list[ModelBooleanMetrics] = Field(
        default_factory=list, description="Boolean flags and states"
    )

    configurations: list[ModelNestedConfiguration] = Field(
        default_factory=list, description="Nested configuration objects"
    )

    # Legacy compatibility
    raw_data: dict[str, Any] | None = Field(
        None, description="Raw data for backward compatibility (to be phased out)"
    )

    def add_string_property(self, name: str, value: str) -> None:
        """Add a string property."""
        self.string_properties.append(ModelStringMetrics(name=name, value=value))

    def add_numeric_property(self, name: str, value: int | float) -> None:
        """Add a numeric property."""
        self.numeric_properties.append(ModelNumericMetrics(name=name, value=value))

    def add_boolean_property(self, name: str, value: bool) -> None:
        """Add a boolean property."""
        self.boolean_properties.append(ModelBooleanMetrics(name=name, value=value))

    def add_configuration(
        self,
        config_name: str,
        config_type: str,
        settings: dict[str, str | int | bool | float],
    ) -> None:
        """Add a configuration object."""
        self.configurations.append(
            ModelNestedConfiguration(
                config_name=config_name, config_type=config_type, settings=settings
            )
        )

    @classmethod
    def from_legacy_dict(cls, data: dict[str, Any]) -> "ModelFunctionNodeData":
        """
        Create from legacy dict data for migration.

        This method helps migrate from the horrible union type to clean model.
        """
        instance = cls(
            name=str(data.get("name", "unknown")),
            description=data.get("description"),
            node_type=str(data.get("node_type", "function")),
            status=str(data.get("status", "active")),
            version=str(data.get("version", "1.0.0")),
        )

        # Convert legacy data
        for key, value in data.items():
            if key in {"name", "description", "node_type", "status", "version"}:
                continue

            if isinstance(value, str):
                instance.add_string_property(key, value)
            elif isinstance(value, (int, float)):
                instance.add_numeric_property(key, value)
            elif isinstance(value, bool):
                instance.add_boolean_property(key, value)
            elif isinstance(value, list) and all(isinstance(x, str) for x in value):
                instance.tags.extend(value)
            elif isinstance(value, dict):
                # Convert dict to configuration
                settings = {
                    k: v
                    for k, v in value.items()
                    if isinstance(v, (str, int, bool, float))
                }
                instance.add_configuration(key, "dict", settings)

        # Store raw data for complete compatibility
        instance.raw_data = data
        return instance


# Export the model
__all__ = [
    "ModelFunctionNodeData",
    "ModelStringMetrics",
    "ModelNumericMetrics",
    "ModelBooleanMetrics",
    "ModelNestedConfiguration",
]
