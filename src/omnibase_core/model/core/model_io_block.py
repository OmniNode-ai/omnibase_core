"""
IO block model for ONEX node metadata.
"""

from typing import Annotated

from pydantic import BaseModel, StringConstraints


class ModelIOBlock(BaseModel):
    """Input/Output block definition for ONEX node contracts."""

    name: Annotated[str, StringConstraints(min_length=1)]
    schema_ref: Annotated[str, StringConstraints(min_length=1)]
    required: bool | None = True
    format_hint: str | None = None
    description: Annotated[str, StringConstraints(min_length=1)] | None = None
