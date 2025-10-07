from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelYamlList(BaseModel):
    """Model for YAML files that are primarily lists."""

    model_config = ConfigDict(extra="allow")

    # For files that are root-level arrays
    root_list: list[Any] = Field(default_factory=list, description="Root level list")

    def __init__(self, data: list[Any] | None = None, **kwargs) -> None:
        """Handle case where YAML root is a list."""
        if data is not None and isinstance(data, list):
            super().__init__(root_list=data, **kwargs)
            return
        # data is None or not a list - use default initialization
        super().__init__(**kwargs)
