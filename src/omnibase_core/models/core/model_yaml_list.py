from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelYamlList(BaseModel):
    """Model for YAML files that are primarily lists."""

    model_config = ConfigDict(extra="allow")

    # For files that are root-level arrays
    root_list: list[Any] = Field(default_factory=list, description="Root level list")

    def __init__(self, data: list[Any] | None = None, **kwargs: Any) -> None:
        """Handle case where YAML root is a list."""
        if data is not None and isinstance(data, list):
            # Filter out root_list from kwargs to avoid conflict
            filtered_kwargs = {k: v for k, v in kwargs.items() if k != "root_list"}
            super().__init__(root_list=data, **filtered_kwargs)
            return
        # data is None or not a list - use default initialization
        super().__init__(**kwargs)
