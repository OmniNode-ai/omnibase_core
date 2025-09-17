"""
Model for node contract data validation.

Provides strongly typed contract data structure to replace manual YAML validation
in node initialization, ensuring required fields are validated properly.
"""

from typing import Any, Dict

from pydantic import BaseModel, Field


class ModelNodeContractData(BaseModel):
    """
    Pydantic model for node contract data.

    Ensures contract data has required fields and provides type safety
    for node initialization instead of manual dictionary access.
    """

    version: str = Field(..., description="Required version field for node contract")

    # Allow additional fields since contract data can be flexible
    model_config = {"extra": "allow"}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelNodeContractData":
        """
        Create model from dictionary data.

        Args:
            data: Dictionary containing contract data

        Returns:
            ModelNodeContractData instance

        Raises:
            ValidationError: If required fields are missing or invalid
        """
        return cls.model_validate(data)
