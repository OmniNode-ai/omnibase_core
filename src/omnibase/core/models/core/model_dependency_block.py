"""
Dependency block model for ONEX node metadata.
"""

from typing import Annotated, Optional

from pydantic import BaseModel, StringConstraints


class ModelDependencyBlock(BaseModel):
    """Dependency information for ONEX nodes."""

    name: Annotated[str, StringConstraints(min_length=1)]
    type: Annotated[str, StringConstraints(min_length=1)]
    target: Annotated[str, StringConstraints(min_length=1)]
    binding: Optional[str] = None
    protocol_required: Optional[str] = None
    optional: Optional[bool] = False
    description: Optional[Annotated[str, StringConstraints(min_length=1)]] = None
