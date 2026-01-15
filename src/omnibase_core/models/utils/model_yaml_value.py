"""
YAML-serializable data structures model with discriminated union.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_yaml_value_type import EnumYamlValueType
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

# Remove Any import - using object for YAML-serializable data types


class ModelYamlValue(BaseModel):
    """Discriminated union for YAML-serializable data structures.
    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    value_type: EnumYamlValueType = Field(
        description="Type discriminator for the YAML value",
    )
    schema_value: ModelSchemaValue | None = Field(
        default=None, description="Schema value data"
    )
    dict_value: dict[str, "ModelYamlValue"] | None = Field(
        default=None,
        description="Dictionary data",
    )
    list_value: list["ModelYamlValue"] | None = Field(
        default=None, description="List data"
    )

    @classmethod
    def from_schema_value(cls, value: ModelSchemaValue) -> "ModelYamlValue":
        """Create from ModelSchemaValue."""
        return cls(
            value_type=EnumYamlValueType.SCHEMA_VALUE,
            schema_value=value,
            dict_value=None,
            list_value=None,
        )

    @classmethod
    def from_dict_data(cls, value: dict[str, ModelSchemaValue]) -> "ModelYamlValue":
        """Create from dictionary of ModelSchemaValue."""
        dict_value = {k: cls.from_schema_value(v) for k, v in value.items()}
        return cls(
            value_type=EnumYamlValueType.DICT,
            schema_value=None,
            dict_value=dict_value,
            list_value=None,
        )

    @classmethod
    def from_list(cls, value: list[ModelSchemaValue]) -> "ModelYamlValue":
        """Create from list[Any]of ModelSchemaValue."""
        list_value = [cls.from_schema_value(v) for v in value]
        return cls(
            value_type=EnumYamlValueType.LIST,
            schema_value=None,
            dict_value=None,
            list_value=list_value,
        )

    def to_serializable(self) -> object:
        """Convert back to serializable data structure."""
        if self.value_type == EnumYamlValueType.SCHEMA_VALUE:
            return self.schema_value
        if self.value_type == EnumYamlValueType.DICT:
            return {k: v.to_serializable() for k, v in (self.dict_value or {}).items()}
        if self.value_type == EnumYamlValueType.LIST:
            return [
                v.to_serializable()
                for v in (self.list_value if self.list_value is not None else [])
            ]
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Invalid value_type: {self.value_type}",
            details=ModelErrorContext.with_context(
                {
                    "value_type": ModelSchemaValue.from_value(self.value_type),
                    "expected_types": ModelSchemaValue.from_value(
                        ["SCHEMA_VALUE", "DICT", "LIST"],
                    ),
                    "function": ModelSchemaValue.from_value("to_serializable"),
                },
            ),
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            ModelOnexError: If validation fails with details about the failure
        """
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Instance validation failed: {e}",
            ) from e


# Rebuild model to resolve forward references for self-referential fields
try:
    ModelYamlValue.model_rebuild()
except Exception:  # catch-all-ok: circular import protection during model rebuild
    pass


__all__ = ["ModelYamlValue"]
