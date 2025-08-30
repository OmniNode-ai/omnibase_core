"""
Dependency block model for ONEX node metadata.
"""

from typing import Annotated

from pydantic import BaseModel, StringConstraints


class ModelDependencyBlock(BaseModel):
    """Dependency information for ONEX nodes."""

    name: Annotated[str, StringConstraints(min_length=1)]
    type: Annotated[str, StringConstraints(min_length=1)]
    target: Annotated[str, StringConstraints(min_length=1)]
    binding: str | None = None
    protocol_required: str | None = None
    optional: bool | None = False
    description: Annotated[str, StringConstraints(min_length=1)] | None = None
