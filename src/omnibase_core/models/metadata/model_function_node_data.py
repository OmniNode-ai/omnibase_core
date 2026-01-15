"""
Function node data model.

Clean, strongly-typed replacement for the horrible FunctionNodeData union type.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_config_type import EnumConfigType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_function_status import EnumFunctionStatus
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.enums.enum_standard_category import EnumStandardCategory
from omnibase_core.enums.enum_standard_tag import EnumStandardTag
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.infrastructure.model_value import ModelValue
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel

from .model_nested_configuration import ModelNestedConfiguration
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
    Implements Core protocols:
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
        ...,  # REQUIRED - specify in contract
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
        settings: dict[str, ModelValue],
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
            version=ModelSemVer(major=1, minor=0, patch=0),
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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        display_name = self.display_name.display_name
        if display_name:
            result["name"] = display_name
        description = self.description.summary_description
        if description:
            result["description"] = description
        result["version"] = self.version
        all_tags = self.tags.all_tags
        if all_tags:
            result["tags"] = all_tags
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


__all__ = ["ModelFunctionNodeData"]
