"""
Step with parameters model.
"""

from pydantic import BaseModel, ConfigDict


class ModelStepWith(BaseModel):
    """Step 'with' parameters."""

    model_config = ConfigDict(extra="allow")  # Allow any additional fields
