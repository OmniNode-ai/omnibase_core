"""
Step with parameters model.
"""

from pydantic import BaseModel


class ModelStepWith(BaseModel):
    """Step 'with' parameters."""

    model_config = {"extra": "allow"}  # Allow any additional fields
