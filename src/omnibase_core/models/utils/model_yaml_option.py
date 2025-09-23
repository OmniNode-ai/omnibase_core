"""
YAML option value model with discriminated union.

Author: ONEX Framework Team
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ModelYamlOption(BaseModel):
    """Discriminated union for YAML dumper option values."""

    option_type: Literal["boolean", "integer", "string"] = Field(
        description="Type discriminator for the option value"
    )
    boolean_value: bool | None = Field(None, description="Boolean option value")
    integer_value: int | None = Field(None, description="Integer option value")
    string_value: str | None = Field(None, description="String option value")

    @classmethod
    def from_bool(cls, value: bool) -> "ModelYamlOption":
        """Create from boolean value."""
        return cls(
            option_type="boolean",
            boolean_value=value,
            integer_value=None,
            string_value=None,
        )

    @classmethod
    def from_int(cls, value: int) -> "ModelYamlOption":
        """Create from integer value."""
        return cls(
            option_type="integer",
            boolean_value=None,
            integer_value=value,
            string_value=None,
        )

    @classmethod
    def from_str(cls, value: str) -> "ModelYamlOption":
        """Create from string value."""
        return cls(
            option_type="string",
            boolean_value=None,
            integer_value=None,
            string_value=value,
        )

    def to_value(self) -> Any:
        """Convert back to Python value."""
        if self.option_type == "boolean":
            return self.boolean_value
        elif self.option_type == "integer":
            return self.integer_value
        elif self.option_type == "string":
            return self.string_value
        raise ValueError(f"Invalid option_type: {self.option_type}")


# Export the model
__all__ = ["ModelYamlOption"]
