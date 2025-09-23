"""
Function node data model.

Clean, strongly-typed replacement for the horrible FunctionNodeData union type.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_config_type import EnumConfigType
from omnibase_core.enums.enum_function_status import EnumFunctionStatus
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.models.infrastructure.model_cli_value import ModelCliValue

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

    # Core identification - UUID-based entity references
    node_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the function node",
    )
    node_display_name: str | None = Field(
        None,
        description="Human-readable function node name",
    )
    description: str | None = Field(None, description="Node description")

    # Basic properties
    node_type: EnumNodeType = Field(
        default=EnumNodeType.FUNCTION,
        description="Type of node",
    )
    status: EnumFunctionStatus = Field(
        default=EnumFunctionStatus.ACTIVE,
        description="Node status",
    )
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Node version",
    )

    # Structured data instead of horrible unions
    tags: list[str] = Field(
        default_factory=list,
        description="Tags associated with the node",
    )

    string_properties: list[ModelTypedMetrics[str]] = Field(
        default_factory=list,
        description="String-based properties and metadata",
    )

    numeric_properties: list[ModelTypedMetrics[float]] = Field(
        default_factory=list,
        description="Numeric properties and metrics",
    )

    boolean_properties: list[ModelTypedMetrics[bool]] = Field(
        default_factory=list,
        description="Boolean flags and states",
    )

    configurations: list[ModelNestedConfiguration] = Field(
        default_factory=list,
        description="Nested configuration objects",
    )

    def add_string_property(self, name: str, value: str, **kwargs: Any) -> None:
        """Add a string property."""
        self.string_properties.append(
            ModelTypedMetrics.string_metric(name=name, value=value, **kwargs),
        )

    def add_numeric_property(self, name: str, value: float, **kwargs: Any) -> None:
        """Add a numeric property."""
        # Use float_metric for numeric values (int converted to float automatically)
        metric = ModelTypedMetrics.float_metric(name=name, value=value, **kwargs)
        self.numeric_properties.append(metric)

    def add_boolean_property(self, name: str, value: bool, **kwargs: Any) -> None:
        """Add a boolean property."""
        self.boolean_properties.append(
            ModelTypedMetrics.boolean_metric(name=name, value=value, **kwargs),
        )

    def add_configuration(
        self,
        config_id: UUID,
        config_display_name: str,
        config_type: EnumConfigType,
        settings: dict[str, ModelCliValue],
    ) -> None:
        """Add a configuration object."""
        self.configurations.append(
            ModelNestedConfiguration(
                config_id=config_id,
                config_display_name=config_display_name,
                config_type=config_type,
                settings=settings,
            ),
        )


# Export the model
__all__ = ["ModelFunctionNodeData"]
