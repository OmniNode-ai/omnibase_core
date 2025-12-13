"""
Request Parameter Model for ONEX Configuration System.

Strongly typed model for HTTP request parameters.
"""

from pydantic import BaseModel, Field


class ModelRequestParameter(BaseModel):
    """
    Strongly typed model for HTTP request parameters.

    Represents query parameters that can be sent in HTTP requests
    with proper type safety.
    """

    name: str = Field(default=..., description="Parameter name")
    value: str = Field(default=..., description="Parameter value")

    # For multiple values with same name
    multiple_values: list[str] | None = Field(
        default=None,
        description="Multiple values for the same parameter name",
    )

    def get_value(self) -> str:
        """Get the primary value."""
        return self.value

    def get_all_values(self) -> list[str]:
        """Get all values including multiples."""
        if self.multiple_values:
            return [self.value, *self.multiple_values]
        return [self.value]
