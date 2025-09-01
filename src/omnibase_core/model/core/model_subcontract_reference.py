"""
Model for subcontract reference representation in ONEX contracts.

This model represents the reference structure used in main contracts
to link to subcontract files with integration fields.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, Field


class ModelSubcontractReference(BaseModel):
    """Model representing a subcontract reference in main contracts."""

    path: str = Field(..., description="Relative path to the subcontract YAML file")
    integration_field: str = Field(
        ..., description="Field name for integrating subcontract configuration"
    )
