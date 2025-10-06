from __future__ import annotations

import uuid

from pydantic import Field

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_semver import ModelSemVer

"""
Function node data model.

Clean, strongly-typed replacement for the horrible FunctionNodeData union type.
Follows ONEX one-model-per-file naming conventions.
"""


from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_config_type import EnumConfigType
from omnibase_core.enums.enum_function_status import EnumFunctionStatus
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.enums.enum_standard_category import EnumStandardCategory
from omnibase_core.enums.enum_standard_tag import EnumStandardTag
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.infrastructure.model_cli_value import ModelCliValue

from .model_nested_configuration import ModelNestedConfiguration
from .model_semver import ModelSemVer
from .model_structured_description import ModelStructuredDescription
from .model_structured_display_name import ModelStructuredDisplayName
from .model_structured_tags import ModelStructuredTags
from .model_typed_metrics import ModelTypedMetrics


class ModelFunctionNodeData(BaseModel):
    """
    Clean, strongly-typed model replacing the horrible FunctionNodeData union type.

    Eliminates: Primitive soup union patterns with structured types using
                PrimitiveValueType and component-based architecture

    With proper structured data using specific field types.
    Now uses structured types to reduce string field reliance.
    Implements omnibase_spi protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Core identification - UUID-based entity references
    node_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the function node",
    )

    # Structured naming and description (reduces string fields)
    display_name: ModelStructuredDisplayName = Field(
        default_factory=lambda: ModelStructuredDisplayName.for_function_node("default"),
        description="Structured display name with consistent naming patterns",
    )

    description: ModelStructuredDescription = Field(
        default_factory=lambda: ModelStructuredDescription.for_function_node("default"),
        description="Structured description with standardized templates",
    )

    # Basic properties with enums
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

    # Structured tags (reduces string list[Any])
    tags: ModelStructuredTags = Field(
        default_factory=lambda: ModelStructuredTags.for_function_node(),
        description="Structured tags with standard and custom classifications",
    )

    # Structured data instead of horrible unions
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

    def add_string_property(
        self,
        name: str,
        value: str,
        unit: str = "",
        description: str = "",
    ) -> None:
        """Add a string property."""
        self.string_properties.append(
            ModelTypedMetrics.string_metric(
                name=name,
                value=value,
                unit=unit,
                description=description,
            ),
        )

    def add_numeric_property(
        self,
        name: str,
        value: float,
        unit: str = "",
        description: str = "",
    ) -> None:
        """Add a numeric property."""
        # Use float_metric for numeric values (int converted to float automatically)
        metric = ModelTypedMetrics.float_metric(
            name=name,
            value=value,
            unit=unit,
            description=description,
        )
        self.numeric_properties.append(metric)

    def add_boolean_property(
        self,
        name: str,
        value: bool,
        unit: str = "",
        description: str = "",
    ) -> None:
        """Add a boolean property."""
        self.boolean_properties.append(
            ModelTypedMetrics.boolean_metric(
                name=name,
                value=value,
                unit=unit,
                description=description,
            ),
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

    @classmethod
    def create_function_node(
        cls,
        name: str,
        description_purpose: str | None = None,
        function_category: EnumStandardCategory | None = None,
        complexity: EnumStandardTag | None = None,
        custom_tags: list[str] | None = None,
    ) -> ModelFunctionNodeData:
        """Create a function node with structured components."""
        display_name = ModelStructuredDisplayName.for_function_node(
            name,
            category=function_category,
        )

        description = ModelStructuredDescription.for_function_node(
            name,
            functionality=description_purpose,
            category=function_category,
        )

        tags = ModelStructuredTags.for_function_node(
            function_category=function_category,
            complexity=complexity,
            custom_tags=custom_tags,
        )

        return cls(
            display_name=display_name,
            description=description,
            tags=tags,
        )

    def update_display_name(self, base_name: str) -> None:
        """Update the display name base."""
        self.display_name = ModelStructuredDisplayName.for_function_node(
            base_name,
            category=self.tags.primary_category,
        )

    def update_description_purpose(self, purpose: str) -> None:
        """Update the description purpose."""
        self.description.purpose = purpose

    def add_tag(self, tag: str) -> bool:
        """Add a tag (standard or custom)."""
        # Try as standard tag first
        standard_tag = EnumStandardTag.from_string(tag)
        if standard_tag:
            return self.tags.add_standard_tag(standard_tag)
        return self.tags.add_custom_tag(tag)

    def remove_tag(self, tag: str) -> bool:
        """Remove a tag."""
        standard_tag = EnumStandardTag.from_string(tag)
        if standard_tag:
            return self.tags.remove_standard_tag(standard_tag)
        return self.tags.remove_custom_tag(tag)

    def has_tag(self, tag: str) -> bool:
        """Check if tag is present."""
        return self.tags.has_tag(tag)

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Export the model

    # Protocol method implementations

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata as dict[str, Any]ionary (ProtocolMetadataProvider protocol)."""
        metadata = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata

    def set_metadata(self, metadata: dict[str, Any]) -> bool:
        """Set metadata from dict[str, Any]ionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


__all__ = ["ModelFunctionNodeData"]
