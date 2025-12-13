"""
Discriminated union model for log node identifiers.

BOUNDARY_LAYER_EXCEPTION: This model supports logging infrastructure resilience
by allowing flexible identifiers when strict UUID context is unavailable.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from .model_lognodeidentifierstring import ModelLogNodeIdentifierString


class ModelLogNodeIdentifierUUID(BaseModel):
    """Log node identifier using UUID."""

    type: Literal["uuid"] = "uuid"
    value: UUID = Field(default=..., description="UUID node identifier")


# Discriminated union type
ModelLogNodeIdentifier = ModelLogNodeIdentifierUUID | ModelLogNodeIdentifierString
