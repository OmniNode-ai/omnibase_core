from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ModelBaseInputState(BaseModel):
    """Base model for all input states in ONEX"""

    # ONEX_EXCLUDE: dict_str_any - Base state metadata for extensible tool input data
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata for the input state",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the input was created",
    )
