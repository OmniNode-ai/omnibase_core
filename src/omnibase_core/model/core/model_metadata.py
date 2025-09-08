"""
Metadata Model.

Strongly typed metadata model replacing Dict[str, Union[str, int, float, bool]].
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.model.core.model_scalar_value import ModelScalarValue


class ModelMetadata(BaseModel):
    """
    Type-safe metadata container.

    Provides structured metadata handling replacing
    Dict[str, Union[str, int, float, bool]] with type-safe container.
    """

    entries: dict[str, ModelScalarValue] = Field(
        default_factory=dict, description="Metadata entries"
    )

    @field_validator("entries", mode="before")
    @classmethod
    def convert_entries(cls, v: Any) -> dict[str, ModelScalarValue]:
        """Convert plain dict to ModelScalarValue entries."""
        if isinstance(v, dict):
            result = {}
            for key, value in v.items():
                if isinstance(value, ModelScalarValue):
                    result[key] = value
                elif isinstance(value, (str, int, float, bool)):
                    result[key] = ModelScalarValue.from_any(value)
                else:
                    raise ValueError(
                        f"Invalid metadata value type for key '{key}': {type(value)}"
                    )
            return result
        return v

    def set(self, key: str, value: str | int | float | bool) -> None:
        """Set a metadata entry."""
        self.entries[key] = ModelScalarValue.from_any(value)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a metadata entry."""
        if key in self.entries:
            return self.entries[key].value
        return default

    def get_string(self, key: str, default: str = "") -> str:
        """Get metadata entry as string."""
        if key in self.entries:
            return self.entries[key].get_as_string()
        return default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get metadata entry as integer."""
        if key in self.entries:
            result = self.entries[key].get_as_int()
            return result if result is not None else default
        return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get metadata entry as float."""
        if key in self.entries:
            result = self.entries[key].get_as_float()
            return result if result is not None else default
        return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get metadata entry as boolean."""
        if key in self.entries:
            return self.entries[key].get_as_bool()
        return default

    def has(self, key: str) -> bool:
        """Check if metadata has a key."""
        return key in self.entries

    def remove(self, key: str) -> None:
        """Remove a metadata entry."""
        if key in self.entries:
            del self.entries[key]

    def clear(self) -> None:
        """Clear all metadata entries."""
        self.entries.clear()

    def keys(self) -> list[str]:
        """Get all metadata keys."""
        return list(self.entries.keys())

    def values(self) -> list[Any]:
        """Get all metadata values."""
        return [entry.value for entry in self.entries.values()]

    def items(self) -> list[tuple[str, Any]]:
        """Get all metadata items."""
        return [(key, entry.value) for key, entry in self.entries.items()]

    def to_dict(self) -> dict[str, str | int | float | bool]:
        """Convert to plain dictionary."""
        return {key: entry.value for key, entry in self.entries.items()}

    @classmethod
    def from_dict(cls, data: dict[str, str | int | float | bool]) -> "ModelMetadata":
        """Create metadata from plain dictionary."""
        return cls(entries=data)

    def merge(self, other: "ModelMetadata") -> None:
        """Merge another metadata into this one."""
        for key, value in other.entries.items():
            self.entries[key] = value

    def copy(self) -> "ModelMetadata":
        """Create a copy of this metadata."""
        return ModelMetadata(entries={k: v for k, v in self.entries.items()})