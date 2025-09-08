"""
State Value Model.

Strongly typed state value model replacing Union[str, int, float, bool, Dict[str, Any], None].
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ModelStateValue(BaseModel):
    """
    Type-safe state value wrapper.

    Provides structured state value handling replacing
    Union[str, int, float, bool, Dict[str, Any], None] with type-safe container.
    """

    value: str | int | float | bool | dict[str, Any] | None = Field(
        ..., description="The state value"
    )
    value_type: Literal[
        "string", "integer", "float", "boolean", "object", "null"
    ] = Field(..., description="Type of the state value")
    is_complex: bool = Field(
        default=False, description="Whether this is a complex object value"
    )

    @model_validator(mode="before")
    @classmethod
    def set_value_type(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Automatically set value_type and is_complex based on the value."""
        if "value" in values:
            value = values["value"]
            if "value_type" not in values:
                if value is None:
                    values["value_type"] = "null"
                elif isinstance(value, bool):
                    values["value_type"] = "boolean"
                elif isinstance(value, int):
                    values["value_type"] = "integer"
                elif isinstance(value, float):
                    values["value_type"] = "float"
                elif isinstance(value, str):
                    values["value_type"] = "string"
                elif isinstance(value, dict):
                    values["value_type"] = "object"

            if "is_complex" not in values:
                values["is_complex"] = isinstance(value, dict)

        return values

    def get_as_string(self) -> str | None:
        """Get value as string."""
        if self.value is None:
            return None
        if isinstance(self.value, str):
            return self.value
        if isinstance(self.value, dict):
            import json

            return json.dumps(self.value)
        return str(self.value)

    def get_as_int(self) -> int | None:
        """Get value as integer."""
        if self.value is None:
            return None
        if isinstance(self.value, int):
            return self.value
        if isinstance(self.value, bool):
            return 1 if self.value else 0
        if isinstance(self.value, float):
            return int(self.value)
        if isinstance(self.value, str):
            try:
                return int(self.value)
            except ValueError:
                return None
        return None

    def get_as_float(self) -> float | None:
        """Get value as float."""
        if self.value is None:
            return None
        if isinstance(self.value, (int, float)):
            return float(self.value)
        if isinstance(self.value, bool):
            return 1.0 if self.value else 0.0
        if isinstance(self.value, str):
            try:
                return float(self.value)
            except ValueError:
                return None
        return None

    def get_as_bool(self) -> bool | None:
        """Get value as boolean."""
        if self.value is None:
            return None
        if isinstance(self.value, bool):
            return self.value
        if isinstance(self.value, str):
            return self.value.lower() in ("true", "yes", "1", "on")
        if isinstance(self.value, (int, float)):
            return self.value != 0
        if isinstance(self.value, dict):
            return len(self.value) > 0
        return False

    def get_as_dict(self) -> dict[str, Any] | None:
        """Get value as dictionary."""
        if self.value is None:
            return None
        if isinstance(self.value, dict):
            return self.value
        if isinstance(self.value, str):
            try:
                import json

                return json.loads(self.value)
            except (json.JSONDecodeError, ValueError):
                return None
        return None

    def is_null(self) -> bool:
        """Check if value is null."""
        return self.value is None

    def is_numeric(self) -> bool:
        """Check if value is numeric."""
        return self.value_type in ("integer", "float")

    def is_scalar(self) -> bool:
        """Check if value is a scalar (not object or null)."""
        return self.value_type in ("string", "integer", "float", "boolean")

    @classmethod
    def from_string(cls, value: str) -> "ModelStateValue":
        """Create state value from string."""
        return cls(value=value, value_type="string")

    @classmethod
    def from_int(cls, value: int) -> "ModelStateValue":
        """Create state value from integer."""
        return cls(value=value, value_type="integer")

    @classmethod
    def from_float(cls, value: float) -> "ModelStateValue":
        """Create state value from float."""
        return cls(value=value, value_type="float")

    @classmethod
    def from_bool(cls, value: bool) -> "ModelStateValue":
        """Create state value from boolean."""
        return cls(value=value, value_type="boolean")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ModelStateValue":
        """Create state value from dictionary."""
        return cls(value=value, value_type="object", is_complex=True)

    @classmethod
    def from_null(cls) -> "ModelStateValue":
        """Create null state value."""
        return cls(value=None, value_type="null")

    @classmethod
    def from_any(cls, value: Any) -> "ModelStateValue":
        """Create state value from any supported type."""
        if value is None:
            return cls.from_null()
        elif isinstance(value, bool):
            return cls.from_bool(value)
        elif isinstance(value, int):
            return cls.from_int(value)
        elif isinstance(value, float):
            return cls.from_float(value)
        elif isinstance(value, str):
            return cls.from_string(value)
        elif isinstance(value, dict):
            return cls.from_dict(value)
        else:
            raise ValueError(f"Unsupported type for state value: {type(value)}")