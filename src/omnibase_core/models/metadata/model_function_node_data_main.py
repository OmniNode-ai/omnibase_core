"""
Function node data model.

Clean, strongly-typed replacement for the horrible FunctionNodeData union type.
Follows ONEX one-model-per-file naming conventions.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .model_boolean_metrics import ModelBooleanMetrics
from .model_nested_configuration import ModelNestedConfiguration
from .model_numeric_metrics import ModelNumericMetrics
from .model_string_metrics import ModelStringMetrics


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


# Export the model
__all__ = ["ModelFunctionNodeData"]
