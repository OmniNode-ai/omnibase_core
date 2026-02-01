"""
Correlation Configuration Model.

Model for specifying correlation ID location in request-response event bus patterns.
Defines where to find the correlation ID within messages for tracking request-response pairs.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelCorrelationConfig"]


class ModelCorrelationConfig(BaseModel):
    """
    Configuration for correlation ID extraction in request-response patterns.

    Specifies where to find the correlation ID in messages, enabling the event bus
    to track request-response pairs across asynchronous message exchanges.
    """

    location: Literal["body", "headers"] = Field(
        default="body",
        description="Where the correlation ID is found in the message",
    )

    field: str = Field(
        default="correlation_id",
        description="Field name containing the correlation ID",
    )

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        from_attributes=True,
    )
