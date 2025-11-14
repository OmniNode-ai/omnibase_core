from typing import Literal

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_numeric_value import ModelNumericValue


class ModelNodeConfigurationNumericValue(BaseModel):
    """Numeric configuration value with discriminated union support."""

    value_type: Literal["numeric"] = Field(
        default="numeric",
        description="Type discriminator for numeric values",
    )
    value: ModelNumericValue = Field(
        default=..., description="Numeric configuration value"
    )

    def to_python_value(self) -> int | float:
        """Get the underlying Python value."""
        return self.value.to_python_value()

    def as_string(self) -> str:
        """Get configuration value as string."""
        return str(self.value.to_python_value())

    def as_int(self) -> int:
        """Get configuration value as integer."""
        return self.value.as_int()

    def as_numeric(self) -> int | float:
        """Get value as numeric type."""
        return self.value.to_python_value()
