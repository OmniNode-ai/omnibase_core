from pydantic import Field

"""
Dictionary Configuration Model for ONEX Configuration System.

Strongly typed model for dictionary return types.
"""

from pydantic import BaseModel


class ModelDictConfig(BaseModel):
    """
    Strongly typed model for dictionary return types.

    Represents configuration dictionaries with proper type safety.
    """

    data: dict[str, str] = Field(
        default_factory=dict,
        description="Configuration data as string key-value pairs",
    )

    def get_value(self, key: str) -> str:
        """Get a configuration value by key."""
        return self.data.get(key, "")

    def set_value(self, key: str, value: str) -> None:
        """Set a configuration value."""
        self.data[key] = value

    def has_key(self, key: str) -> bool:
        """Check if key exists in configuration."""
        return key in self.data

    def get_all_keys(self) -> list[str]:
        """Get all configuration keys."""
        return list(self.data.keys())
