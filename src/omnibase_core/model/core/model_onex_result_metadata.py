from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ModelOnexResultMetadata(BaseModel):
    """
    Define canonical fields for result metadata, extend as needed
    """

    key: str | None = None
    value: Any | None = None
    # Add more fields as needed for protocol

    model_config = {"arbitrary_types_allowed": True}
