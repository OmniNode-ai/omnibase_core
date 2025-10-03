"""Generic YAML model for ContractLoader."""

from typing import Any

from pydantic import BaseModel, Field


class ModelGenericYaml(BaseModel):
    """Generic YAML content model for safe YAML loading."""

    model_config = {
        "extra": "allow",  # Allow any additional fields
        "arbitrary_types_allowed": True,
    }

    # Allow any fields to be set dynamically
    def __init__(self, **data: Any):
        """Initialize with arbitrary data."""
        super().__init__(**data)

    def __getitem__(self, key: str) -> Any:
        """Support dict-like access."""
        return getattr(self, key, None)

    def get(self, key: str, default: Any = None) -> Any:
        """Support dict-like get method."""
        return getattr(self, key, default)

    def keys(self) -> list[str]:
        """Get all keys."""
        return list(self.model_dump().keys())

    def values(self) -> list[Any]:
        """Get all values."""
        return list(self.model_dump().values())

    def items(self) -> list[tuple[str, Any]]:
        """Get all items."""
        return list(self.model_dump().items())
