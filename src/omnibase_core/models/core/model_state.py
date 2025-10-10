from pydantic import Field

"""
State model for node introspection.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_state_field import ModelStateField
from omnibase_core.primitives.model_semver import ModelSemVer


class ModelState(BaseModel):
    """Model for state model specification."""

    class_name: str = Field(default=..., description="State model class name")
    schema_version: ModelSemVer = Field(
        default=..., description="Schema version for this state model"
    )
    fields: list[ModelStateField] = Field(default=..., description="State model fields")
    schema_file: str | None = Field(
        default=None, description="Path to JSON schema file"
    )
