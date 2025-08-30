from typing import Optional

from pydantic import BaseModel, Field


class ModelOnexField(BaseModel):
    """
    Canonical, extensible ONEX field model for all flexible/optional/structured node fields.
    Use this for any field that may contain arbitrary or structured data in ONEX nodes.
    """

    data: Optional[dict] = Field(default=None, description="Arbitrary ONEX field data")

    # Optionally, add more required methods or attributes as needed
