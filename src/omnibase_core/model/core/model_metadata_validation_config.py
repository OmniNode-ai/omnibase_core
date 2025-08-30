"""
Metadata validation configuration model.
"""

from typing import List, Optional

from pydantic import BaseModel


class ModelMetadataValidationConfig(BaseModel):
    """Configuration for metadata validation."""

    enabled: bool = True
    required_fields: Optional[List[str]] = None
