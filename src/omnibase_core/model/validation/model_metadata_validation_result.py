"""
MetadataValidationResult model.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelMetadataValidationResult(BaseModel):
    """
    Canonical model for metadata validation results in the ONEX tree generator.
    Replaces Dict[str, Any] for validation results.
    """

    valid_artifacts: int = 0
    invalid_artifacts: int = 0
    errors: List[str] = Field(default_factory=list)
