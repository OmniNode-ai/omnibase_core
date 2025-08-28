"""
IO block model for ONEX node metadata.
"""

from typing import Annotated, Optional

from pydantic import BaseModel, StringConstraints


class ModelIOBlock(BaseModel):
    """Input/Output block definition for ONEX node contracts."""

    name: Annotated[str, StringConstraints(min_length=1)]
    schema_ref: Annotated[str, StringConstraints(min_length=1)]
    required: Optional[bool] = True
    format_hint: Optional[str] = None
    description: Optional[Annotated[str, StringConstraints(min_length=1)]] = None
