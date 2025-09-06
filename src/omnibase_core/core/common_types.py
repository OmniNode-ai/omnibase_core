"""
Common types for ONEX core modules.

Strong typing patterns for ONEX architecture compliance.
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field, model_validator


class ModelStringValue(BaseModel):
    """Strongly typed string scalar value."""

    value: str = Field(..., description="String value")


class ModelIntValue(BaseModel):
    """Strongly typed integer scalar value."""

    value: int = Field(..., description="Integer value")


class ModelFloatValue(BaseModel):
    """Strongly typed float scalar value."""

    value: float = Field(..., description="Float value")


class ModelBoolValue(BaseModel):
    """Strongly typed boolean scalar value."""

    value: bool = Field(..., description="Boolean value")


class ModelMetadata(BaseModel):
    """Strongly typed metadata container."""

    entries: Dict[str, "ModelScalarValue"] = Field(
        default_factory=dict, description="Metadata entries"
    )


class ModelConfiguration(BaseModel):
    """Strongly typed configuration container."""

    settings: Dict[str, "ModelScalarValue"] = Field(
        default_factory=dict, description="Configuration settings"
    )


class ModelNullValue(BaseModel):
    """Strongly typed null value representation."""

    is_null: bool = Field(True, description="Null value marker")


class ModelScalarValue(BaseModel):
    """Strongly typed scalar value container using discriminated approach."""

    string_value: Optional[str] = Field(
        None, description="String scalar value", max_length=65536
    )
    int_value: Optional[int] = Field(
        None, description="Integer scalar value", ge=-(2**63), le=2**63 - 1
    )
    float_value: Optional[float] = Field(
        None, description="Float scalar value", ge=-1e308, le=1e308
    )
    bool_value: Optional[bool] = Field(None, description="Boolean scalar value")

    @model_validator(mode="after")
    def validate_exactly_one_value(self) -> "ModelScalarValue":
        """Ensure exactly one value type is set."""
        values = [
            self.string_value is not None,
            self.int_value is not None,
            self.float_value is not None,
            self.bool_value is not None,
        ]

        if sum(values) != 1:
            raise ValueError("ModelScalarValue must have exactly one value set")

        return self

    @property
    def type_hint(self) -> str:
        """Auto-generated type hint based on the actual value type."""
        if self.string_value is not None:
            return "str"
        if self.int_value is not None:
            return "int"
        if self.float_value is not None:
            return "float"
        if self.bool_value is not None:
            return "bool"
        return "unknown"

    @classmethod
    def create_string(cls, value: str) -> "ModelScalarValue":
        """Create a string scalar value."""
        return cls(string_value=value)

    @classmethod
    def create_int(cls, value: int) -> "ModelScalarValue":
        """Create an integer scalar value."""
        return cls(int_value=value)

    @classmethod
    def create_float(cls, value: float) -> "ModelScalarValue":
        """Create a float scalar value."""
        return cls(float_value=value)

    @classmethod
    def create_bool(cls, value: bool) -> "ModelScalarValue":
        """Create a boolean scalar value."""
        return cls(bool_value=value)

    @classmethod
    def from_string_primitive(cls, value: str) -> "ModelScalarValue":
        """Create from string primitive."""
        return cls.create_string(value)

    @classmethod
    def from_int_primitive(cls, value: int) -> "ModelScalarValue":
        """Create from int primitive."""
        return cls.create_int(value)

    @classmethod
    def from_float_primitive(cls, value: float) -> "ModelScalarValue":
        """Create from float primitive."""
        return cls.create_float(value)

    @classmethod
    def from_bool_primitive(cls, value: bool) -> "ModelScalarValue":
        """Create from bool primitive."""
        return cls.create_bool(value)

    def to_string_primitive(self) -> str:
        """Extract string value."""
        if self.string_value is not None:
            return self.string_value
        raise ValueError("No string value set in ModelScalarValue")

    def to_int_primitive(self) -> int:
        """Extract int value."""
        if self.int_value is not None:
            return self.int_value
        raise ValueError("No int value set in ModelScalarValue")

    def to_float_primitive(self) -> float:
        """Extract float value."""
        if self.float_value is not None:
            return self.float_value
        raise ValueError("No float value set in ModelScalarValue")

    def to_bool_primitive(self) -> bool:
        """Extract bool value."""
        if self.bool_value is not None:
            return self.bool_value
        raise ValueError("No bool value set in ModelScalarValue")


class ModelStateValue(BaseModel):
    """Strongly typed state value with discriminated value types."""

    scalar_value: Optional[ModelScalarValue] = Field(
        None, description="Scalar value container"
    )
    metadata_value: Optional[ModelMetadata] = Field(
        None, description="Metadata container"
    )
    config_value: Optional[ModelConfiguration] = Field(
        None, description="Configuration container"
    )
    is_null: bool = Field(False, description="Whether this represents a null value")

    @model_validator(mode="after")
    def validate_only_one_value_type(self) -> "ModelStateValue":
        """Ensure only one value type is set at a time."""
        scalar_set = self.scalar_value is not None
        metadata_set = self.metadata_value is not None
        config_set = self.config_value is not None
        null_set = self.is_null

        value_count = sum([scalar_set, metadata_set, config_set, null_set])

        if value_count > 1:
            raise ValueError(
                "ModelStateValue can only have one of: scalar_value, metadata_value, config_value, or is_null=True"
            )

        if value_count == 0:
            # Default to null if nothing is set
            object.__setattr__(self, "is_null", True)

        return self

    @classmethod
    def create_scalar_string(cls, value: str) -> "ModelStateValue":
        """Create a state value from a string scalar."""
        return cls(scalar_value=ModelScalarValue.create_string(value))

    @classmethod
    def create_scalar_int(cls, value: int) -> "ModelStateValue":
        """Create a state value from an integer scalar."""
        return cls(scalar_value=ModelScalarValue.create_int(value))

    @classmethod
    def create_scalar_float(cls, value: float) -> "ModelStateValue":
        """Create a state value from a float scalar."""
        return cls(scalar_value=ModelScalarValue.create_float(value))

    @classmethod
    def create_scalar_bool(cls, value: bool) -> "ModelStateValue":
        """Create a state value from a boolean scalar."""
        return cls(scalar_value=ModelScalarValue.create_bool(value))

    @classmethod
    def create_metadata(cls, entries: Dict[str, ModelScalarValue]) -> "ModelStateValue":
        """Create a state value from metadata entries."""
        return cls(metadata_value=ModelMetadata(entries=entries))

    @classmethod
    def create_config(cls, settings: Dict[str, ModelScalarValue]) -> "ModelStateValue":
        """Create a state value from configuration settings."""
        return cls(config_value=ModelConfiguration(settings=settings))

    @classmethod
    def create_null(cls) -> "ModelStateValue":
        """Create a null state value."""
        return cls(is_null=True)

    def get_scalar_value(self) -> Optional[ModelScalarValue]:
        """Get scalar value container if present."""
        return self.scalar_value

    def get_metadata_value(self) -> Optional[ModelMetadata]:
        """Get metadata value if present."""
        return self.metadata_value

    def get_config_value(self) -> Optional[ModelConfiguration]:
        """Get configuration value if present."""
        return self.config_value

    def is_null_value(self) -> bool:
        """Check if this represents a null value."""
        return self.is_null
