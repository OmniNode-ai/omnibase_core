"""
State model for node introspection.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_state_field import ModelStateField


class ModelState(BaseModel):
    """Model for state model specification."""

    class_name: str = Field(..., description="State model class name")
    schema_version: str = Field(..., description="Schema version for this state model")
    fields: List[ModelStateField] = Field(..., description="State model fields")
    schema_file: Optional[str] = Field(None, description="Path to JSON schema file")
