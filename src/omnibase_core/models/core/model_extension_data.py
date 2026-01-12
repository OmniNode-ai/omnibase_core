"""
Properly structured extension data model with validation.

This model replaces the loose JsonSerializable/ModelExtensionValue pattern
with a properly validated Pydantic model that enforces type safety.

ARCHITECTURAL PRINCIPLE: No dict[str, Any] - always use structured models
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_json import PrimitiveContainer


class ModelExtensionData(BaseModel):
    """
    Properly structured extension data with validation and type safety.

    Supports multiple value types with proper validation:
    - String values
    - Numeric values (int or float)
    - Boolean values
    - List values (homogeneous or heterogeneous primitives)
    - Object values (flat key-value dict[str, Any]ionaries)

    Examples:
        # String extension
        ModelExtensionData(value="custom-value", description="Custom setting")

        # Numeric extension
        ModelExtensionData(value=42, category="performance")

        # List extension
        ModelExtensionData(value=["tag1", "tag2"], description="Tags")

        # Object extension
        ModelExtensionData(
            value={"key1": "value1", "key2": 123},
            description="Configuration"
        )
    """

    # Core value - constrained union of allowed types
    # NO nested objects or list[Any]s - keeps validation simple and predictable
    # Uses PrimitiveContainer type alias: PrimitiveValue | list[PrimitiveValue] | dict[str, PrimitiveValue]
    value: Annotated[
        PrimitiveContainer,
        Field(
            description="Extension value - supports primitives, list[Any]s, and flat objects",
        ),
    ]

    # Metadata fields
    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Human-readable description of this extension",
        ),
    ] = None

    category: Annotated[
        str | None,
        Field(
            default=None,
            description="Category or namespace for this extension",
        ),
    ] = None

    source: Annotated[
        str | None,
        Field(
            default=None,
            description="Source or origin of this extension data",
        ),
    ] = None

    # Pydantic configuration
    model_config = ConfigDict(
        extra="forbid",  # No arbitrary fields allowed - strict validation,
        frozen=False,  # Allow mutation for practical use cases,
    )

    @property
    def value_type(self) -> str:
        """
        Computed property that returns the type of the value.

        Returns:
            str: One of "string", "boolean", "numeric", "list[Any]", "object"
        """
        if isinstance(self.value, str):
            return "string"
        elif isinstance(self.value, bool):  # Must check bool before int!
            return "boolean"
        elif isinstance(self.value, (int, float)):
            return "numeric"
        elif isinstance(self.value, list):
            return "list[Any]"
        elif isinstance(self.value, dict):
            return "object"

    @field_validator("value")
    @classmethod
    def validate_value_constraints(cls, v: object) -> object:
        """
        Validate value constraints for complex types.

        Lists and dict[str, Any]s have additional constraints:
        - Lists: max 100 items
        - Dicts: max 50 keys, no nested structures
        """
        if isinstance(v, list):
            if len(v) > 100:
                msg = f"List values cannot exceed 100 items, got {len(v)}"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )

        elif isinstance(v, dict):
            if len(v) > 50:
                msg = f"Object values cannot exceed 50 keys, got {len(v)}"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )

            # Ensure no nested structures
            for key, val in v.items():
                if not isinstance(val, (str, int, float, bool)):
                    msg = f"Object values must be primitives, got {type(val).__name__} for key '{key}'"
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=msg,
                    )

        return v

    def __str__(self) -> str:
        """String representation showing value and type."""
        return f"ModelExtensionData(type={self.value_type}, value={self.value!r})"

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        parts = [f"value={self.value!r}"]
        if self.description:
            parts.append(f"description={self.description!r}")
        if self.category:
            parts.append(f"category={self.category!r}")
        if self.source:
            parts.append(f"source={self.source!r}")
        return f"ModelExtensionData({', '.join(parts)})"
