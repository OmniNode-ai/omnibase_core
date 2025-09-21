"""
Example input data model.

This module provides the ModelExampleInputData class for clean,
strongly-typed replacement for dict[str, Any] in example input data.
Follows ONEX one-model-per-file naming conventions.
"""

from pydantic import BaseModel, Field

from ..metadata.model_semver import ModelSemVer


class ModelExampleInputData(BaseModel):
    """
    Clean model for example input data.

    Replaces dict[str, Any] with structured data model.
    """

    # Core data fields
    data_type: str = Field(default="input", description="Type of input data")
    format: str = Field(default="json", description="Data format")

    # Input parameters
    parameters: dict[str, str | int | bool | float] = Field(
        default_factory=dict, description="Input parameters with basic types"
    )

    # Configuration settings
    configuration: dict[str, str | int | bool] = Field(
        default_factory=dict, description="Configuration settings for the input"
    )

    # Validation info
    schema_version: ModelSemVer | None = Field(
        None, description="Schema version for validation"
    )
    is_validated: bool = Field(default=False, description="Whether input is validated")
