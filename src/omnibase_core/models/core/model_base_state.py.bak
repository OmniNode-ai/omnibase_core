"""
Base state models for ONEX.

These are the fundamental models that all input/output states inherit from.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .model_generic_metadata import ModelGenericMetadata


class ModelBaseInputState(BaseModel):
    """Base model for all input states in ONEX"""

    # ONEX_EXCLUDE: dict_str_any - Base state metadata for extensible tool input data
    metadata: ModelGenericMetadata | None = Field(
        default_factory=dict,
        description="Metadata for the input state",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the input was created",
    )


class ModelBaseOutputState(BaseModel):
    """Base model for all output states in ONEX"""

    # ONEX_EXCLUDE: dict_str_any - Base state metadata for extensible tool output data
    metadata: ModelGenericMetadata | None = Field(
        default_factory=dict,
        description="Metadata for the output state",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the output was created",
    )
    processing_time_ms: float | None = Field(
        None,
        description="Time taken to process in milliseconds",
    )
