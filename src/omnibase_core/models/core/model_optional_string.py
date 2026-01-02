"""Model for optional string values."""

from collections.abc import Callable

from pydantic import BaseModel, Field


class ModelOptionalString(BaseModel):
    """
    Strongly-typed model for optional string values.

    Replaces str | None to comply with ONEX standards
    requiring specific typed models instead of generic types.
    """

    value: str | None = Field(default=None, description="Optional string value")

    def get(self) -> str | None:
        """Get the optional value."""
        return self.value

    def set(self, value: str | None) -> None:
        """Set the optional value."""
        self.value = value

    def has_value(self) -> bool:
        """Check if value is present."""
        return self.value is not None

    def get_or_default(self, default: str) -> str:
        """Get value or return default if None."""
        return self.value if self.value is not None else default

    def map(self, func: Callable[[str], str]) -> "ModelOptionalString":
        """Apply function to value if present."""
        if self.value is not None:
            return ModelOptionalString(value=func(self.value))
        return self

    def __bool__(self) -> bool:
        """Boolean representation based on value presence.

        Warning:
            This differs from standard Pydantic behavior where ``bool(model)``
            always returns ``True``. Here, ``bool(optional)`` returns ``False``
            when the value is ``None``, enabling idiomatic presence checks.

        Returns:
            bool: True if value is present (not None), False if None.

        Example:
            >>> value = ModelOptionalString(value="hello")
            >>> if value:
            ...     print(f"Got: {value.value}")
            Got: hello

            >>> empty = ModelOptionalString(value=None)
            >>> if not empty:
            ...     print("No value")
            No value
        """
        return self.has_value()
