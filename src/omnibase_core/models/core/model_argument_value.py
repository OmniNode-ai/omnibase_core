"""
Argument Value Model.

Type-safe argument value wrapper replacing Any usage
with structured argument value handling.
"""

from pydantic import BaseModel, Field

# Define allowed argument value types
# union-ok: Value wrapper legitimately needs multiple primitive types for runtime flexibility
ArgumentValueType = str | int | bool | float | list[str] | list[int] | list[float]


class ModelArgumentValue(BaseModel):
    """
    Type-safe argument value wrapper.

    Provides structured argument value handling replacing
    Any usage with type-safe value containers.
    """

    value: ArgumentValueType = Field(
        default=..., description="The actual argument value"
    )
    original_string: str = Field(
        default=..., description="Original string representation"
    )
    type_name: str = Field(default=..., description="Type name for validation")
    validated: bool = Field(
        default=False,
        description="Whether value has been validated",
    )

    def get_as_string(self) -> str:
        """Get value as string."""
        if isinstance(self.value, str):
            return self.value
        return str(self.value)

    def get_as_int(self) -> int | None:
        """Get value as integer."""
        if isinstance(self.value, int):
            return self.value
        if isinstance(self.value, float | str):
            try:
                return int(self.value)
            except ValueError:
                return None
        return None

    def get_as_float(self) -> float | None:
        """Get value as float."""
        if isinstance(self.value, int | float):
            return float(self.value)
        if isinstance(self.value, str):
            try:
                return float(self.value)
            except ValueError:
                return None
        return None

    def get_as_bool(self) -> bool:
        """Get value as boolean."""
        if isinstance(self.value, bool):
            return self.value
        if isinstance(self.value, str):
            return self.value.lower() in ("true", "yes", "1", "on")
        if isinstance(self.value, int | float):
            return self.value != 0
        return False

    def get_as_list(self) -> list[str]:
        """Get value as list of strings."""
        if isinstance(self.value, list):
            return [str(item) for item in self.value]
        return [str(self.value)]

    def is_type(self, expected_type: str) -> bool:
        """Check if value matches expected type."""
        return self.type_name == expected_type

    @classmethod
    def from_string(cls, value: str, type_name: str = "string") -> "ModelArgumentValue":
        """Create argument value from string."""
        return cls(value=value, original_string=value, type_name=type_name)

    @classmethod
    def from_int(cls, value: int) -> "ModelArgumentValue":
        """Create argument value from integer."""
        return cls(value=value, original_string=str(value), type_name="integer")

    @classmethod
    def from_bool(cls, value: bool) -> "ModelArgumentValue":
        """Create argument value from boolean."""
        return cls(value=value, original_string=str(value).lower(), type_name="boolean")
