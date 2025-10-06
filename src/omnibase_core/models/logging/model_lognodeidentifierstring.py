from typing import Literal

from pydantic import BaseModel, Field


class ModelLogNodeIdentifierString(BaseModel):
    """Log node identifier using string fallback."""

    type: Literal["string"] = "string"
    value: str = Field(
        default=..., description="String node identifier (class/module name)"
    )
