"""
Model for subcontract reference representation in ONEX contracts.

This model represents the reference structure used in main contracts
to link to subcontract files with integration fields.

"""

from pydantic import BaseModel, Field


class ModelSubcontractReference(BaseModel):
    """Model representing a subcontract reference in main contracts."""

    path: str = Field(
        default=..., description="Relative path to the subcontract YAML file"
    )
    integration_field: str = Field(
        default=...,
        description="Field name for integrating subcontract configuration",
    )
