"""
Model for node contract data validation.

Provides strongly typed contract data structure to replace manual YAML validation
in node initialization, ensuring required fields are validated properly.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

if TYPE_CHECKING:
    from omnibase_core.types.type_serializable_value import SerializedDict


class ModelNodeContractData(BaseModel):
    """
    Pydantic model for node contract data.

    Ensures contract data has required fields and provides type safety
    for node initialization instead of manual dictionary access.
    """

    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Required version field for node contract",
    )

    # Allow additional fields since contract data can be flexible
    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_dict(cls, data: "SerializedDict") -> "ModelNodeContractData":
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
