"""
Function node data model.

Clean, strongly-typed replacement for the horrible FunctionNodeData union type.
Follows ONEX one-model-per-file naming conventions.
"""

from typing import Any, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .model_nested_configuration import ModelNestedConfiguration
from .model_semver import ModelSemVer
from .model_typed_metrics import ModelTypedMetrics


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
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Node version",
    )

    # Structured data instead of horrible unions
    tags: list[str] = Field(
        default_factory=list, description="Tags associated with the node"
    )

    string_properties: list[ModelTypedMetrics[str]] = Field(
        default_factory=list, description="String-based properties and metadata"
    )

    numeric_properties: list[
        Union[ModelTypedMetrics[int], ModelTypedMetrics[float]]
    ] = Field(default_factory=list, description="Numeric properties and metrics")

    boolean_properties: list[ModelTypedMetrics[bool]] = Field(
        default_factory=list, description="Boolean flags and states"
    )

    configurations: list[ModelNestedConfiguration] = Field(
        default_factory=list, description="Nested configuration objects"
    )

    def add_string_property(self, name: str, value: str, **kwargs: Any) -> None:
        """Add a string property."""
        self.string_properties.append(
            ModelTypedMetrics.string_metric(name=name, value=value, **kwargs)
        )

    def add_numeric_property(
        self, name: str, value: int | float, **kwargs: Any
    ) -> None:
        """Add a numeric property."""
        if isinstance(value, int):
            # Use int_metric for integer values
            metric: Union[ModelTypedMetrics[int], ModelTypedMetrics[float]] = (
                ModelTypedMetrics.int_metric(name=name, value=value, **kwargs)
            )
        else:
            # Use float_metric for float values
            metric = ModelTypedMetrics.float_metric(name=name, value=value, **kwargs)
        self.numeric_properties.append(metric)

    def add_boolean_property(self, name: str, value: bool, **kwargs: Any) -> None:
        """Add a boolean property."""
        self.boolean_properties.append(
            ModelTypedMetrics.boolean_metric(name=name, value=value, **kwargs)
        )

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
