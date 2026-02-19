# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Database parameter definition for repository contracts.

Fully specifies each parameter so validators can prove:
- Every placeholder has a definition
- Every definition is actually used
- Constraints are type-consistent
- Defaults are legal
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_parameter_type import EnumParameterType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelDbParam(BaseModel):
    """Database parameter definition for repository contracts.

    Fully specifies each parameter so validators can prove:
    - Every placeholder has a definition
    - Every definition is actually used
    - Constraints are type-consistent
    - Defaults are legal
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Identity
    name: str = Field(..., min_length=1, max_length=100, description="Parameter name")

    # Type definition
    param_type: EnumParameterType = Field(
        default=EnumParameterType.STRING,
        description="Expected parameter type",
    )

    # Required/nullable
    required: bool = Field(default=True, description="Whether parameter is required")
    nullable: bool = Field(default=False, description="Whether parameter accepts NULL")

    # Default value
    default: ModelSchemaValue | None = Field(
        default=None,
        description="Default value if parameter is not provided",
    )

    # Numeric constraints
    ge: float | int | None = Field(
        default=None, description="Greater than or equal constraint"
    )
    le: float | int | None = Field(
        default=None, description="Less than or equal constraint"
    )

    # String constraints
    min_length: int | None = Field(
        default=None, ge=0, description="Minimum string length"
    )
    max_length: int | None = Field(
        default=None, ge=1, description="Maximum string length"
    )
    pattern: str | None = Field(
        default=None, description="Regex pattern for validation"
    )

    # Documentation
    description: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_constraints(self) -> "ModelDbParam":
        """Validate constraint consistency."""
        # ge/le only for numeric types
        numeric_types = {
            EnumParameterType.INTEGER,
            EnumParameterType.NUMBER,
            EnumParameterType.FLOAT,
        }
        if (
            self.ge is not None or self.le is not None
        ) and self.param_type not in numeric_types:
            msg = f"ge/le constraints only allowed for numeric types, got {self.param_type}"
            raise ValueError(msg)

        # min_length/max_length/pattern only for string types
        string_types = {EnumParameterType.STRING}
        if (
            self.min_length is not None
            or self.max_length is not None
            or self.pattern is not None
        ):
            if self.param_type not in string_types:
                msg = f"min_length/max_length/pattern only allowed for string types, got {self.param_type}"
                raise ValueError(msg)

        # min_length <= max_length
        if self.min_length is not None and self.max_length is not None:
            if self.min_length > self.max_length:
                msg = f"min_length ({self.min_length}) cannot exceed max_length ({self.max_length})"
                raise ValueError(msg)

        # ge <= le
        if self.ge is not None and self.le is not None:
            if self.ge > self.le:
                msg = f"ge ({self.ge}) cannot exceed le ({self.le})"
                raise ValueError(msg)

        # If nullable is False, default cannot be null
        if not self.nullable and self.default is not None:
            # Check if default is explicitly null
            if (
                hasattr(self.default, "value_type")
                and self.default.value_type == "null"
            ):
                msg = "default cannot be null when nullable is False"
                raise ValueError(msg)

        return self


__all__ = ["ModelDbParam"]
