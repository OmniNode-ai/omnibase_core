from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from omnibase_core.models.discovery.model_output_metadata_item import (
    ModelOutputMetadataItem,
)


class ModelOutputMetadata(BaseModel):
    """Output metadata container with strong typing."""

    items: list[ModelOutputMetadataItem] = Field(
        default_factory=list,
        description="List of typed output metadata items",
    )
    execution_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When metadata was created",
    )

    def get_metadata_dict(self) -> dict[str, str | int | float | bool]:
        """Convert to dict[str, Any]ionary format for current standards."""
        return {item.key: item.value for item in self.items}

    @classmethod
    def from_dict(
        cls,
        metadata_dict: dict[str, str | int | float | bool],
    ) -> "ModelOutputMetadata":
        """Create from dict[str, Any]ionary with type inference."""
        items = []
        for key, value in metadata_dict.items():
            # Check bool before int since bool is a subclass of int in Python
            if isinstance(value, bool):
                value_type = "boolean"
            elif isinstance(value, str):
                value_type = "string"
            elif isinstance(value, int):
                value_type = "integer"
            elif isinstance(value, float):
                value_type = "float"

            items.append(
                ModelOutputMetadataItem(key=key, value=value, value_type=value_type),
            )

        return cls(items=items)
