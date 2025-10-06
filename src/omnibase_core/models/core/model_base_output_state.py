from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ModelBaseOutputState(BaseModel):
    """Base model for all output states in ONEX"""

    # ONEX_EXCLUDE: dict_str_any - Base state metadata for extensible tool output data
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata for the output state",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the output was created",
    )
    processing_time_ms: float | None = Field(
        default=None,
        description="Time taken to process in milliseconds",
    )
