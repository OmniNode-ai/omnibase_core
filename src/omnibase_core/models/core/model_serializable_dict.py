"""
Serializable Dictionary Model for ONEX Configuration System.

Strongly typed model for serializable dictionary data.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelSerializableDict(BaseModel):
    """
    Strongly typed model for serializable dictionary data.

    Represents dictionary data that can be serialized with proper type safety.
    """

    data: dict[str, str] = Field(
        default_factory=dict,
        description="Serializable data as string key-value pairs",
    )

    def get_value(self, key: str) -> str:
        """Get a value by key."""
        return self.data.get(key, "")

    def set_value(self, key: str, value: str) -> None:
        """Set a value."""
        self.data[key] = value

    def has_key(self, key: str) -> bool:
        """Check if key exists."""
        return key in self.data

    def get_all_keys(self) -> list[Any]:
        """Get all keys."""
        return list(self.data.keys())

    def get_all_values(self) -> list[Any]:
        """Get all values."""
        return list(self.data.values())

    def items(self) -> Any:
        """Get all items."""
        return self.data.items()

    def keys(self) -> Any:
        """Get all keys."""
        return self.data.keys()

    def values(self) -> Any:
        """Get all values."""
        return self.data.values()
