"""
Example input data model.

This module provides the ModelExampleInputData class for clean,
strongly-typed replacement for dict[str, Any] in example input data.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...enums.enum_data_type import EnumDataType
from ...enums.enum_io_type import EnumIOType
from ..metadata.model_metadata_value import ModelMetadataValue
from ..metadata.model_semver import ModelSemVer


class ModelExampleInputData(BaseModel):
    """
    Clean model for example input data.

    Replaces dict[str, Any] with structured data model.
    """

    # Core data fields
    data_type: EnumIOType = Field(
        default=EnumIOType.INPUT, description="Type of input data"
    )
    format: EnumDataType = Field(default=EnumDataType.JSON, description="Data format")

    # Input parameters using strongly-typed metadata values
    parameters: dict[str, ModelMetadataValue] = Field(
        default_factory=dict, description="Input parameters with type-safe values"
    )

    # Configuration settings using string values for simplicity
    configuration: dict[str, str] = Field(
        default_factory=dict,
        description="Configuration settings for the input (string values)",
    )

    # Validation info
    schema_version: ModelSemVer | None = Field(
        None, description="Schema version for validation"
    )
    is_validated: bool = Field(default=False, description="Whether input is validated")


# Export the model
__all__ = ["ModelExampleInputData"]
