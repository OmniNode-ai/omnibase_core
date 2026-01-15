"""Pydantic model for mixin configuration field definitions.

This module provides the ModelMixinConfigField class for defining
configuration schema in mixin metadata.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelMixinConfigField(BaseModel):
    """Configuration field definition in mixin metadata.

    Attributes:
        type: Field type (string, integer, float, boolean, array, object)
        default: Default value for the field
        description: Human-readable field description
        minimum: Minimum value (for numeric types)
        maximum: Maximum value (for numeric types)
        enum: Allowed values (for enum types)
        items: Item schema (for array types)
    """

    model_config = ConfigDict(extra="forbid")

    type: str = Field(..., description="Field type")
    default: object = Field(None, description="Default value")
    description: str = Field("", description="Field description")
    minimum: float | int | None = Field(None, description="Minimum value")
    maximum: float | int | None = Field(None, description="Maximum value")
    enum: list[str] | None = Field(None, description="Allowed enum values")
    items: SerializedDict | None = Field(None, description="Array item schema")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate field type is supported.

        Type distinctions:
        - 'number': Accepts both int and float values (flexible numeric type)
        - 'float': Explicit floating-point type only (strict validation)
        - 'integer': Explicit integer type only (strict validation)
        - 'string': Text values
        - 'boolean': True/False values
        - 'array': List/array values (use 'items' to define schema)
        - 'object': Dictionary/object values

        Use 'number' for flexibility when both int and float are acceptable.
        Use specific types ('float' or 'integer') for strict type validation.
        """
        valid_types = {
            "string",
            "integer",
            "float",
            "number",
            "boolean",
            "array",
            "object",
        }
        if v not in valid_types:
            raise ModelOnexError(
                message=f"Invalid field type '{v}'. Must be one of {valid_types}",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )
        return v
