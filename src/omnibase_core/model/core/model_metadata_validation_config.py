"""
Metadata validation configuration model.
"""

from pydantic import BaseModel


class ModelMetadataValidationConfig(BaseModel):
    """Configuration for metadata validation."""

    enabled: bool = True
    required_fields: list[str] | None = None
