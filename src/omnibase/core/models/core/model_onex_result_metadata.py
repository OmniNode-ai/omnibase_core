from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class ModelOnexResultMetadata(BaseModel):
    """
    Define canonical fields for result metadata, extend as needed
    """

    key: Optional[str] = None
    value: Optional[Any] = None
    # Add more fields as needed for protocol

    model_config = {"arbitrary_types_allowed": True}
